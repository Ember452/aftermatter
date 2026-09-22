"""跨宿主适配器契约：`SessionAdapter` 与行计数器 `ParseTally`（modules §2）。

接口独立成文件的依据是 AGENTS §四.5——实现不止一个（claude 已落地，codex 在 T1.4），
把 Protocol 和某一个实现放在一起会让采集层互相牵连。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from aftermatter.evidence.models import AdapterHealth, ParseStats, RawEvent, SessionRef


class ParseTally:
    """适配器边读边累加的行级计数器。

    与 frozen 的 `ParseStats` 刻意分开：累加需要可变性，跨层快照需要不可变性；
    `to_stats()` 是两者之间唯一的转换点。
    """

    def __init__(self) -> None:
        self.lines_total = 0
        self.parsed = 0
        self.ignored = 0
        self.unparsed = 0
        self.not_ours = 0
        self.malformed_json = 0
        self.excluded_self_artifact = 0
        self.outside_path_count = 0
        self.reasons: dict[str, int] = {}

    def add_reason(self, reason: str, count: int = 1) -> None:
        self.reasons[reason] = self.reasons.get(reason, 0) + count

    def to_stats(self) -> ParseStats:
        return ParseStats(
            lines_total=self.lines_total,
            parsed=self.parsed,
            ignored=self.ignored,
            unparsed=self.unparsed,
            not_ours=self.not_ours,
            malformed_json=self.malformed_json,
            excluded_self_artifact=self.excluded_self_artifact,
            outside_path_count=self.outside_path_count,
            reasons=dict(self.reasons),
        )


@runtime_checkable
class SessionAdapter(Protocol):
    """每家宿主的采集契约：发现 → 流式解析 → 健康度。"""

    def discover(self, workspace: str | Path | None = None) -> list[SessionRef]:
        """列出候选会话文件；给定 workspace 时只保留与该仓库相关的会话。"""
        ...

    def parse(self, ref: SessionRef, *, since_offset: int = 0) -> AsyncIterator[RawEvent]:
        """流式解析，行级 fail-soft；`since_offset` 支持断点续读。"""
        ...

    def healthcheck(self) -> AdapterHealth:
        """最近一次 discover 探测到的版本是否落在支持矩阵内。"""
        ...
