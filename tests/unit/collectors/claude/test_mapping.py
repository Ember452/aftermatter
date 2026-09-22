"""`collectors.claude.mapping` 测试：分类表的三类去向与归属判定。"""

from __future__ import annotations

import pytest

from aftermatter.collectors.artifacts import is_self_artifact
from aftermatter.collectors.claude import mapping
from aftermatter.collectors.claude.mapping import LineDisposition, classify_record, content_blocks


@pytest.mark.parametrize(
    ("record_type", "reason"),
    [("file-history-snapshot", "file-history-snapshot"), ("mode", "mode"), ("slug", "slug")],
)
def test_known_non_session_events_are_ignored_not_unparsed(record_type: str, reason: str) -> None:
    disposition, captured = classify_record({"type": record_type, "uuid": "u"})
    assert disposition is LineDisposition.IGNORED
    assert captured == reason


def test_unrecognized_type_is_the_drift_signal() -> None:
    assert classify_record({"type": "brand-new-thing", "uuid": "u"}) == (
        LineDisposition.UNPARSED,
        "brand-new-thing",
    )


@pytest.mark.parametrize("record", [{}, {"cwd": "/repo"}, {"type": ""}, {"type": None}])
def test_missing_type_is_malformed(record: dict[str, object]) -> None:
    assert classify_record(record) == (LineDisposition.MALFORMED, "missing_type")


@pytest.mark.parametrize("record", [{"type": "user"}, {"type": "assistant"}, {"type": "system"}])
def test_mapped_types_pass_through(record: dict[str, object]) -> None:
    assert classify_record(record)[0] is LineDisposition.PARSED


def test_foreign_markers_are_positive_evidence_and_beat_everything_else() -> None:
    # 同时带 type 与外来独有键：归属优先，不进入 kind 映射。
    for marker in mapping.FOREIGN_KEYS:
        assert classify_record({"type": "user", marker: 1}) == (
            LineDisposition.NOT_OURS,
            "not_claude_session",
        )


@pytest.mark.parametrize("path", ["/home/u/.aftermatter/runs/b.json", ".aftermatter/x.json"])
def test_self_artifact_paths(path: str) -> None:
    """防自污染判定已上收到跨宿主共享层（collectors/artifacts.py）。"""
    assert is_self_artifact(path) is True
    assert is_self_artifact("/repo/src/a.py") is False


def test_content_blocks_normalizes_shapes() -> None:
    assert content_blocks({"content": "hi"}) == [{"type": "text", "text": "hi"}]
    assert content_blocks({"content": [{"type": "text"}, "junk"]}) == [{"type": "text"}]
    assert content_blocks(None) == []
    assert content_blocks({"content": None}) == []
    assert content_blocks({"no_content": 1}) == []


def test_ignored_list_covers_the_measured_non_session_types() -> None:
    """2026-09-22 本机探雷实测到的非会话 type 必须全在忽略清单里。"""
    measured = {
        "file-history-snapshot",
        "file-history-delta",
        "last-prompt",
        "attachment",
        "mode",
        "permission-mode",
        "ai-title",
        "cost-state",
        "agent-color",
        "atis-latch",
    }
    assert measured <= mapping.IGNORED_TYPES
    assert not (measured & mapping.MAPPED_TYPES)


def test_ownership_check_needs_positive_evidence() -> None:
    """只缺字段的残行仍算本宿主（否则丢掉 malformed 信号）；空对象也是。"""
    assert mapping.looks_like_claude({}) is True
    assert mapping.looks_like_claude({"cwd": "/repo"}) is True
    assert mapping.looks_like_claude({"agent-color": "red"}) is False
