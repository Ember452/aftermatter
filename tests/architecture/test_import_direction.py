"""依赖方向守卫：把 `architecture/overview.md` 的「§3 分层与依赖方向」机器化。

覆盖五条规则：

① 低层不得 import 上层（分层秩，违规消息含"不得 import 上层"）；
② `analysis` 不得越过 evidence 直连 `collectors`（防二次采集造成证据漂移）；
③ 任何模块不得 import `serve` / `daemon`（`REPO-LAYOUT.md` §8：装配层在最外圈）；
④ `collectors` 下的宿主适配器子包互不 import（防格式逻辑串味）；
⑤ 顶层子包名必须在 `REPO-LAYOUT.md` §2 清单内（把"禁止 utils/common/helpers/base"
   从口头约束变成守卫）。

分层秩的一个契约例外：`evidence` 的 `models` 子包按 L0 计（见 overview §3）——跨层
数据模型的唯一定义处必须能被采集层 import，否则 `RawEvent` 造不出来；但 `evidence`
其余单元（freezer/integrity/redaction）仍是 L1，采集层 import 它们依旧判违规。

拦截能力由 `tmp_path` 注入违规样例自证，样例文件不入库——否则 M0 期 `src/` 只有
一个 `__init__.py`，"零违规"是必然的假绿。
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_PACKAGE_NAME = "aftermatter"

# 分层秩：overview §3 四层 + modules §0 模块总序（sandbox 属判断与产物层）。
LAYER_RANK: dict[str, int] = {
    "core": 0,
    "collectors": 0,
    "evidence": 1,
    "episodes": 1,
    "analysis": 2,
    "repair": 2,
    "sandbox": 2,
    "longitudinal": 2,
    "report": 2,
    "cli": 3,
    "serve": 3,
    "daemon": 3,
}
# 契约模型子包例外：这些子包参与 L0 比较（overview §3、evidence.md 职责边界）。
MODEL_SUBPACKAGES: dict[str, tuple[str, ...]] = {"evidence": ("models",)}
# REPO-LAYOUT §2 允许、但不参与分层秩比较的顶层目录（版本化脚本序列，非架构层）。
UNRANKED = frozenset({"migrations"})
# 规则③的目标层：真需要 cli 装配 import daemon 时另开 ADR 放宽，不加静默豁免。
ASSEMBLY_ONLY = frozenset({"serve", "daemon"})
_SKIP_DIR_NAMES = frozenset({"__pycache__", ".venv", "venv", ".pytest_cache"})


def _top_level_of(dotted: str) -> str | None:
    """`aftermatter.analysis.engine` → `analysis`；非本包返回 None。"""
    if dotted != _PACKAGE_NAME and not dotted.startswith(f"{_PACKAGE_NAME}."):
        return None
    rest = dotted[len(_PACKAGE_NAME) :].strip(".")
    return rest.split(".")[0] if rest else None


def _host_of(dotted: str, hosts: frozenset[str] | None = None) -> str | None:
    """`aftermatter.collectors.claude.parse` → `claude`；非适配器返回 None。

    传入 `hosts`（从文件系统实探到的宿主子包名）时只认目录型子包为宿主：
    `collectors/protocol.py` 这种**共享模块**不是宿主，跨层引用它不算违规（T1.3 首次暴露）。
    不传时退化为“任何子名都是宿主”，注入样例仍能自证拦截力。
    """
    parts = dotted.split(".")
    if len(parts) < 3 or parts[:2] != [_PACKAGE_NAME, "collectors"]:
        return None
    candidate = parts[2]
    if hosts is not None and candidate not in hosts:
        return None
    return candidate


def _host_packages(package_root: Path) -> frozenset[str]:
    """collectors 下的**子包**（含 `__init__.py` 的目录）才是宿主。"""
    collectors = package_root / _PACKAGE_NAME / "collectors"
    if not collectors.is_dir():
        return frozenset()
    return frozenset(
        child.name
        for child in collectors.iterdir()
        if child.is_dir() and (child / "__init__.py").is_file()
    )


def _package_of(module_dotted: str, is_package: bool) -> str:
    """模块所在包的点分名（相对导入按它展开）。"""
    if is_package:
        return module_dotted
    return module_dotted.rsplit(".", 1)[0] if "." in module_dotted else module_dotted


def _effective_rank(dotted: str) -> tuple[str | None, int | None]:
    """返回 (顶层名, 参与比较的秩)；契约模型子包按 L0 计，非本包返回 (None, None)。"""
    top = _top_level_of(dotted)
    if top is None:
        return None, None
    parts = dotted.split(".")
    sub_package = parts[2] if len(parts) > 2 else ""
    if sub_package in MODEL_SUBPACKAGES.get(top, ()):
        return top, 0
    return top, LAYER_RANK.get(top)


def _resolve_targets(package_dotted: str, node: ast.Import | ast.ImportFrom) -> list[str]:
    """把一条 import 语句解析成绝对点分名（相对导入按所在包展开）。

    `from . import x` 保守地解成 `包.x`：x 既可能是子模块也可能是包内名字，
    取前缀不会漏报（只会偶尔把属性名当模块，不危害方向判定）。
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if not node.level:  # 绝对导入：目标自带完整点分名，不能再拼前缀
        return [node.module] if node.module else []
    parts = package_dotted.split(".")
    drop = node.level - 1
    base = ".".join(parts[: len(parts) - drop]) if drop else package_dotted
    if node.module:
        return [f"{base}.{node.module}"]
    return [f"{base}.{alias.name}" for alias in node.names]


def _violations_for_source(
    module_dotted: str,
    source: str,
    *,
    is_package: bool = False,
    hosts: frozenset[str] | None = None,
) -> list[str]:
    """单个模块的依赖方向违规清单（纯函数，便于注入样例做负向测试）。"""
    package_dotted = _package_of(module_dotted, is_package)
    my_top, my_rank = _effective_rank(module_dotted)
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        for target in _resolve_targets(package_dotted, node):
            their_top, their_rank = _effective_rank(target)
            if their_top is None:
                continue
            where = f"{module_dotted}:{node.lineno}"
            if their_top not in LAYER_RANK and their_top not in UNRANKED:
                violations.append(
                    f"{where}: 未知顶层子包 `{their_top}`（不在 REPO-LAYOUT §2 清单）"
                )
                continue
            if my_rank is not None and their_rank is not None and their_rank > my_rank:
                violations.append(
                    f"{where}: `{my_top}`(L{my_rank}) 不得 import 上层 `{their_top}`(L{their_rank})"
                )
            if my_top == "analysis" and their_top == "collectors":
                violations.append(f"{where}: analysis 不得越过 evidence 直连 collectors")
            if their_top in ASSEMBLY_ONLY and my_top not in ASSEMBLY_ONLY:
                violations.append(f"{where}: 任何模块不得 import 装配层 `{their_top}`")
            my_host, their_host = _host_of(module_dotted, hosts), _host_of(target, hosts)
            if my_host and their_host and my_host != their_host:
                violations.append(f"{where}: 宿主适配器子包不得互相 import")
    return violations


def _iter_python_files(package_root: Path) -> Iterator[Path]:
    pkg = package_root / _PACKAGE_NAME
    if not pkg.is_dir():
        return
    for path in sorted(pkg.rglob("*.py")):
        if not _SKIP_DIR_NAMES.isdisjoint(path.parts):
            continue
        yield path


def _module_of(package_root: Path, path: Path) -> tuple[str, bool]:
    rel = path.relative_to(package_root).with_suffix("")
    parts = list(rel.parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts.pop()
    return ".".join(parts), is_package


def _collect_violations(package_root: Path) -> list[str]:
    """扫描真实包树，返回全部依赖方向违规。"""
    violations: list[str] = []
    hosts = _host_packages(package_root)
    for path in _iter_python_files(package_root):
        module_dotted, is_package = _module_of(package_root, path)
        source = path.read_text(encoding="utf-8")
        violations.extend(
            _violations_for_source(module_dotted, source, is_package=is_package, hosts=hosts)
        )
    return violations


def test_src_has_no_illegal_imports() -> None:
    assert (_SRC_ROOT / _PACKAGE_NAME / "__init__.py").is_file(), "src layout 未落地"
    assert _collect_violations(_SRC_ROOT) == []


def test_src_top_level_matches_repo_layout() -> None:
    """规则⑤的反向半边：src 下不得出现清单外的顶层子包（兜底 utils/common 等）。

    只看 import 关系会漏报"建了个没人 import 的兜底目录"，这里直接对目录树兜住。
    """
    allowed = set(LAYER_RANK) | set(UNRANKED)
    pkg = _SRC_ROOT / _PACKAGE_NAME
    actual = {
        path.name for path in pkg.iterdir() if path.is_dir() and path.name not in _SKIP_DIR_NAMES
    }
    unlisted = sorted(actual - allowed)
    assert not unlisted, f"未登记于 REPO-LAYOUT §2 的顶层子包: {unlisted}"


@pytest.mark.parametrize(
    ("module_dotted", "source", "expected_keyword"),
    [
        # ① 四条向下越向上的样例，每层各一例
        (
            "aftermatter.core.timeutil",
            "from aftermatter.analysis.engine import run",
            "不得 import 上层",
        ),
        (
            "aftermatter.collectors.repo.scanner",
            "import aftermatter.evidence.bundle",
            "不得 import 上层",
        ),
        (
            "aftermatter.episodes.segment",
            "from aftermatter.report.render import render",
            "不得 import 上层",
        ),
        ("aftermatter.evidence.bundle", "import aftermatter.cli", "不得 import 上层"),
        # ② analysis 直连 collectors
        (
            "aftermatter.analysis.engine.lead",
            "from aftermatter.collectors.claude import parse",
            "collectors",
        ),
        # ③ 装配层不可被 import（cli 也在禁内，见 ADR-0012 决定 7）
        (
            "aftermatter.evidence.bundle",
            "from aftermatter.serve.api import ingest",
            "装配层",
        ),
        ("aftermatter.cli.app", "import aftermatter.daemon.server", "装配层"),
        # ④ 宿主适配器互不 import
        (
            "aftermatter.collectors.codex.parse",
            "from aftermatter.collectors.claude.parse import x",
            "宿主适配器",
        ),
        # 契约模型例外只放 `models`：采集层 import evidence 的其他单元依旧越级
        (
            "aftermatter.collectors.claude.parse",
            "from aftermatter.evidence.freezer import freeze",
            "不得 import 上层",
        ),
        # L0 例外不等于豁免检查：models 自身也不得向上 import
        (
            "aftermatter.evidence.models",
            "from aftermatter.analysis.engine import run",
            "不得 import 上层",
        ),
        # ⑤ 兜底目录与未知子包
        (
            "aftermatter.core.timeutil",
            "from aftermatter.utils import slugify",
            "未知顶层子包",
        ),
        # 相对导入也逃不掉：from ..analysis 位于 evidence(L1) → 指向上层 L2
        ("aftermatter.evidence.bundle", "from ..analysis import judge", "不得 import 上层"),
    ],
)
def test_guard_rejects_injected_violations(
    module_dotted: str, source: str, expected_keyword: str
) -> None:
    violations = _violations_for_source(module_dotted, source)
    assert violations, f"规则未被拦截: {module_dotted} → {source}"
    assert any(expected_keyword in item for item in violations), violations


def test_guard_allows_legal_directions() -> None:
    legal = [
        ("aftermatter.analysis.engine.lead", "from aftermatter.evidence.bundle import freeze"),
        ("aftermatter.report.render", "from aftermatter.core.fingerprint import fingerprint"),
        ("aftermatter.cli.app", "from aftermatter.analysis.deterministic import baseline"),
        ("aftermatter.collectors.claude.parse", "from aftermatter.core.pathutil import norm_path"),
        # L0 例外正向半边：采集层必须能拿到契约模型，否则 RawEvent 造不出来
        ("aftermatter.collectors.claude.parse", "from aftermatter.evidence.models import ERef"),
        ("aftermatter.episodes.segment", "from aftermatter.evidence.models import RawEvent"),
        ("aftermatter.analysis.engine.lead", "from aftermatter.repair.plan import RepairPlan"),
        ("aftermatter.analysis.engine.lead", "from .. import budget"),
        ("aftermatter.migrations.v1", "from aftermatter.longitudinal.store import SCHEMA"),
    ]
    for module_dotted, source in legal:
        assert _violations_for_source(module_dotted, source) == [], f"{module_dotted}: {source}"


HOSTS = frozenset({"claude", "codex"})


def test_collectors_shared_module_is_not_a_host() -> None:
    """`collectors/protocol.py` 是共享模块，被各宿主 import 不算跨宿主。"""
    allowed = _violations_for_source(
        "aftermatter.collectors.claude.parse",
        "from aftermatter.collectors.protocol import ParseTally",
        hosts=HOSTS,
    )
    assert allowed == [], allowed


def test_cross_host_root_import_is_still_rejected() -> None:
    """按目录判定不能放过真越界：`claude` 直接 import `codex` 包仍拦得住。"""
    violations = _violations_for_source(
        "aftermatter.collectors.claude.parse",
        "from aftermatter.collectors.codex import CodexAdapter",
        hosts=HOSTS,
    )
    assert any("宿主适配器" in item for item in violations), violations


def test_host_packages_are_read_from_the_filesystem(tmp_path: Path) -> None:
    hosts_root = tmp_path / _PACKAGE_NAME / "collectors"
    (hosts_root / "claude").mkdir(parents=True)
    (hosts_root / "claude" / "__init__.py").write_text('"""pkg."""\n', encoding="utf-8")
    (hosts_root / "protocol.py").write_text('"""mod."""\n', encoding="utf-8")
    assert _host_packages(tmp_path) == frozenset({"claude"})


def test_guard_catches_violating_file_on_disk(tmp_path: Path) -> None:
    """端到端：磁盘上真放一个违规文件，walk 必须抓到（注入样例必红的机器证据）。"""
    pkg = tmp_path / _PACKAGE_NAME
    (pkg / "core").mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""probe."""\n', encoding="utf-8")
    (pkg / "core" / "__init__.py").write_text('"""probe."""\n', encoding="utf-8")
    (pkg / "core" / "_probe.py").write_text(
        "from aftermatter.analysis.engine import run\n", encoding="utf-8"
    )
    violations = _collect_violations(tmp_path)
    assert len(violations) == 1, violations
    assert "不得 import 上层" in violations[0]
