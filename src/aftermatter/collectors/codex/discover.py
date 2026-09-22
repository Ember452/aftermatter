"""Codex 会话发现：`~/.codex/sessions/YYYY/MM/DD/*.jsonl` 的枚举与元数据抽样。

真实宿主按日期分目录（实测 `2026/08/05`、`2026/08/13`、`2026/09/07`），目录名不含工作区
信息，因此工作区归属只能靠 `session_meta`/`turn_context` 里声明的 `cwd`。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from aftermatter.collectors.artifacts import is_self_artifact
from aftermatter.collectors.codex.mapping import HOST, LineDisposition, classify_record
from aftermatter.core.errors import AfterMatterError
from aftermatter.core.pathutil import norm_path
from aftermatter.evidence.models import SessionRef, source_id_for

PROBE_BYTES = 1 << 20


@dataclass(frozen=True)
class SessionProbe:
    """文件头抽样：版本、声明的 cwd、归属判定。"""

    version: str | None = None
    cwd: str | None = None
    foreign: bool = False


def default_sessions_root() -> Path:
    return Path.home() / ".codex" / "sessions"


def _head_records(raw: bytes) -> list[Mapping[str, object]]:
    records: list[Mapping[str, object]] = []
    for line in raw[:PROBE_BYTES].split(b"\n"):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(record, Mapping):
            records.append(record)
    return records


def probe_session(raw: bytes) -> SessionProbe:
    """定归属与版本。

    归属沿用 Claude 侧同一原则：需要正面证据（命中外宿主信封键）才判 foreign；
    只是没解出行或字段缺失也不误判外来。版本取首个 `session_meta.payload.cli_version`
    （实测形如 `0.153.1`、`0.147.0-alpha.1.2`）。
    """
    for record in _head_records(raw):
        if classify_record(record)[0] is LineDisposition.NOT_OURS:
            return SessionProbe(foreign=True)
        payload = record.get("payload")
        if record.get("type") == "session_meta" and isinstance(payload, Mapping):
            version = payload.get("cli_version")
            cwd = payload.get("cwd")
            return SessionProbe(
                version=version if isinstance(version, str) and version else None,
                cwd=cwd if isinstance(cwd, str) and cwd else None,
            )
    return SessionProbe()


def belongs_to_workspace(probe: SessionProbe, workspace: str | Path) -> bool:
    """探测不到 cwd 时保留（无法证明不属于），有 cwd 时按纯字符串包含关系判定。"""
    if not probe.cwd:
        return True
    try:
        norm_path(workspace, probe.cwd)
    except AfterMatterError:
        return False
    return True


def discover_sessions(
    sessions_root: Path,
    *,
    workspace: str | Path | None = None,
) -> list[SessionRef]:
    source_id = source_id_for(HOST, str(sessions_root))
    refs: list[SessionRef] = []
    for path in sorted(sessions_root.rglob("*.jsonl")):
        if not path.is_file() or is_self_artifact(str(path)):
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
                format_version=probe.version,
            )
        )
    return refs
