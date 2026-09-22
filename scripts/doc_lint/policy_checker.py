"""政策违规检查：中文文件名 / 硬编码 ADR 计数区间。

规则（对齐 ADR-0011 §决定 1–3）：
1. **中文文件名**：仓库内所有文件（含 .md 与非 .md）文件名必须为纯 ASCII
   （英文/数字/连字符/下划线/点）；例外：`docs/tests/` 下的实测文档（ADR-0013）；
2. **硬编码 ADR 计数区间**（如 `0001–0006`、`0001-0008`）：
   - `docs/adr/` 目录**之外**一律禁止（AGENTS.md、CLAUDE.md、docs/README.md、
     docs/plans/ 等出现即违规——它们在 ADR 增长时必然过期）；
   - 内联代码与围栏代码块内的区间视为示例引用，允许（strip_code 后扫描）。

裸节号引用（如"见 §3"缺章节标题）检测容易误伤（很多是合法的当文档内引用），
本期不实现，留作未来 ADR 决策。参见 docs/README.md "§5 交叉引用规则"。
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import Finding, iter_markdown_docs, strip_code

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
# 中文文件名豁免目录（ADR-0013）：docs/tests/ 的实测文档按 PRD §9 的中文指标名检索更直接。
# 只这一个目录：再出现第二处需求，视为该约束需整体重议，而不是继续加白名单。
_CJK_NAME_EXEMPT_DIRS: tuple[tuple[str, ...], ...] = (("docs", "tests"),)
# ADR 编号固定 4 位且首位为 0（长期不会过 0999）；限定首位避免把
# "2020-2025""1000-2000" 等年份/页码区间误判为硬编码 ADR 引用。
_ADR_RANGE_RE = re.compile(r"\b0\d{3}\s*[\u2013\u2014-]\s*0\d{3}\b")


def _is_under_adr(rel_parts: tuple[str, ...]) -> bool:
    return len(rel_parts) >= 2 and rel_parts[0] == "docs" and rel_parts[1] == "adr"


def _is_cjk_name_exempt(path: Path, repo_root: Path) -> bool:
    """路径是否落在中文文件名豁免目录下。"""
    rel = path.relative_to(repo_root)
    return any(rel.parts[: len(prefix)] == prefix for prefix in _CJK_NAME_EXEMPT_DIRS)


def _check_filenames(repo_root: Path) -> list[Finding]:
    """中文文件名扫描。覆盖 docs/、tests/、scripts/、根目录；docs/tests/ 豁免见 ADR-0013。"""
    findings: list[Finding] = []
    scan_dirs = [repo_root / "docs", repo_root / "tests", repo_root / "scripts"]
    for base in scan_dirs:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if _is_cjk_name_exempt(path, repo_root):
                continue
            if _CJK_RE.search(path.name):
                findings.append(
                    Finding(
                        path=path.relative_to(repo_root),
                        rule="policy.chinese_filename",
                        line=None,
                        message=f"文件名含中文，违反 ADR-0011 分层双语：{path.name}",
                        hint="按 `git mv <旧> <新英文名>` 改名并同步全部引用",
                    )
                )
    return findings


def _check_adr_ranges(repo_root: Path) -> list[Finding]:
    """硬编码 ADR 计数区间扫描（docs/adr/ 之外，跳过内联/围栏代码）。"""
    findings: list[Finding] = []
    for doc in iter_markdown_docs(repo_root):
        rel = doc.relative_to(repo_root)
        if _is_under_adr(rel.parts):
            continue
        stripped = strip_code(doc.read_text(encoding="utf-8"))
        for lineno, line in enumerate(stripped.splitlines(), start=1):
            match = _ADR_RANGE_RE.search(line)
            if not match:
                continue
            findings.append(
                Finding(
                    path=doc,
                    rule="policy.hardcoded_adr_range",
                    line=lineno,
                    message=(
                        f"检测到硬编码 ADR 区间 `{match.group(0)}`，"
                        "ADR 数量变化时会失效（见 ADR-0011 §决定 3）"
                    ),
                    hint=(
                        '改为活引用，例如 "docs/adr/ 全量索引见其 README"；'
                        "或在句中使用具体单个 ADR 编号 + 标题；"
                        "示例引用请用反引号包起来跳过本检查"
                    ),
                )
            )
    return findings


def check(repo_root: Path) -> list[Finding]:
    return [*_check_filenames(repo_root), *_check_adr_ranges(repo_root)]
