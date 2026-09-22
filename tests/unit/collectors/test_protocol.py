"""跨宿主公共层测试：`ParseTally` 快照与 `SessionAdapter` 结构一致性。"""

from __future__ import annotations

from pathlib import Path

from aftermatter.collectors.claude import ClaudeAdapter
from aftermatter.collectors.protocol import ParseTally, SessionAdapter
from aftermatter.evidence.models import ParseStats


def test_tally_starts_empty_and_snapshots_to_frozen_stats() -> None:
    tally = ParseTally()
    stats = tally.to_stats()
    assert isinstance(stats, ParseStats)
    assert stats.model_dump() == {
        "lines_total": 0,
        "parsed": 0,
        "ignored": 0,
        "unparsed": 0,
        "not_ours": 0,
        "malformed_json": 0,
        "excluded_self_artifact": 0,
        "outside_path_count": 0,
        "reasons": {},
    }


def test_tally_accumulates_reasons_without_losing_counts() -> None:
    tally = ParseTally()
    tally.lines_total = 3
    tally.add_reason("mode")
    tally.add_reason("mode")
    tally.add_reason("quantum-flux")
    stats = tally.to_stats()
    assert stats.reasons == {"mode": 2, "quantum-flux": 1}
    assert stats.lines_total == 3


def test_snapshot_is_detached_from_later_mutation() -> None:
    """`to_stats()` 之后再累加不得改写已交出的快照——跨层模型必须不可变。"""
    tally = ParseTally()
    tally.add_reason("mode")
    snapshot = tally.to_stats()
    tally.add_reason("mode")
    assert snapshot.reasons == {"mode": 1}


def test_claude_adapter_satisfies_the_session_protocol() -> None:
    assert isinstance(ClaudeAdapter(Path(".")), SessionAdapter)


def test_protocol_only_requires_the_three_lifecycle_methods() -> None:
    class _Fake:
        def discover(self, workspace: str | Path | None = None) -> list[object]:
            return []

        async def parse(self, ref: object, *, since_offset: int = 0) -> object:
            raise NotImplementedError

        def healthcheck(self) -> object:
            raise NotImplementedError

    assert isinstance(_Fake(), SessionAdapter)
