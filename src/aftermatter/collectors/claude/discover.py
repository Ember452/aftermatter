"""Claude 会话发现：源根 → SessionRef 列表（版本众数 + 归属抽样 + 自污染剔除）。

discover 只读文件头若干行定版本与归属，不解析全量事件；真正的行级解析在 `parse`。
`path` 存主机绝对路径（仅本机有效），跨边界引用一律走 `source_id` + 源根相对路径。
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from aftermatter.collectors.claude.mapping import HOST, looks_like_claude
from aftermatter.core.errors import AfterMatterError
from aftermatter.core.pathutil import norm_path
from aftermatter.evidence.models import SessionRef, source_id_for

# 探测头 N 行足够定版本与归属（真实宿主会话最大 0.4MB，采样只为省 IO）。
PROBE_LINES = 16
PROBE_BYTES = 1 << 20


@dataclass(frozen=True)
class SessionProbe:
    """文件头采样结果：版本众数、声明过的 cwd、以及归属判定。"""

    versions: tuple[str, ...] = ()
    cwds: tuple[str, ...] = ()
    foreign: bool = False

    @property
    def format_version(self) -> str | None:
        return self.versions[0] if self.versions else None


def default_sessions_root() -> Path:
    """Claude Code 的会话根目录（可被参数覆盖，测试用 tmp_path）。"""
    return Path.home() / ".claude" / "projects"


def is_session_file(path: Path) -> bool:
    """文件级自污染剔除：AfterMatter 自己产出的 jsonl 不当成宿主会话。"""
    return path.name.endswith(".jsonl") and ".aftermatter" not in path.parts


def head_lines(raw: bytes) -> list[bytes]:
    """取文件头若干非空行。采样只做启发式判定，不处理半行：
    `probe_session` 对解不了的行直接 skip，不会因尾部截断误判 foreign。"""
    lines = raw[:PROBE_BYTES].split(b"\n")
    return [line for line in lines if line.strip()][:PROBE_LINES]


def probe_session(raw: bytes) -> SessionProbe:
    """从文件头采样定版本众数、cwd 集合与归属。"""
    versions: Counter[str] = Counter()
    cwds: list[str] = []
    judged = False
    foreign = False
    for line in head_lines(raw):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, Mapping):
            continue
        if not judged:
            foreign = not looks_like_claude(record)
            judged = True
        version = record.get("version")
        if isinstance(version, str) and version:
            versions[version] += 1
        cwd = record.get("cwd")
        if isinstance(cwd, str) and cwd and cwd not in cwds:
            cwds.append(cwd)
    return SessionProbe(
        versions=tuple(name for name, _ in versions.most_common()),
        cwds=tuple(cwds),
        foreign=foreign,
    )


def belongs_to_workspace(probe: SessionProbe, workspace: str | Path) -> bool:
    """会话声明的 cwd 覆盖 workspace → 属于该工作区。

    没有 cwd 信息时**保留**而非丢弃：无法证明它不属于，误判丢弃等于丢证据，代价更高。
    """
    if not probe.cwds:
        return True
    for cwd in probe.cwds:
        try:
            norm_path(workspace, cwd)
        except AfterMatterError:
            continue
        return True
    return False


def discover_sessions(
    sessions_root: Path,
    *,
    workspace: str | Path | None = None,
) -> list[SessionRef]:
    """枚举源根下的宿主会话文件，产出 `SessionRef`。

    归属判定在 discover 就做（foreign → 跳过）：解析一个不属于本宿主的文件只会用假事件
    污染下游，而 `ParseStats.not_ours` 记的是"被正面证据判定为外来"的文件数。
    """
    source_id = source_id_for(HOST, str(sessions_root))
    refs: list[SessionRef] = []
    for path in sorted(sessions_root.rglob("*.jsonl")):
        if not is_session_file(path) or not path.is_file():
            continue
        raw = path.read_bytes()
        probe = probe_session(raw)
        if probe.foreign:
            continue
        if workspace is not None and not belongs_to_workspace(probe, workspace):
            continue
        refs.append(
            SessionRef(
                host=HOST,
                source_id=source_id,
                path=str(path),
                size=len(raw),
                content_hash=hashlib.sha256(raw).hexdigest(),
                format_version=probe.format_version,
            )
        )
    return refs
