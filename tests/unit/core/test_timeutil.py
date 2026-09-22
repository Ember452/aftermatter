"""core.timeutil 测试：UTC 归一、毫秒向下截断、容错语义、不泄漏原文。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aftermatter.core.errors import ParseError
from aftermatter.core.timeutil import event_millis, parse_ts


def test_parse_ts_keeps_utc_input_and_truncates_millis_down() -> None:
    parsed = parse_ts("2026-09-22T10:20:30.123456Z")
    assert parsed == datetime(2026, 9, 22, 10, 20, 30, 123000, tzinfo=UTC)
    assert parsed.tzinfo is UTC


def test_parse_ts_rounds_microsecond_boundary_down_not_up() -> None:
    assert parse_ts("2026-01-01T00:00:00.999999Z").microsecond == 999000
    assert parse_ts("2026-01-01T00:00:00.9999999Z").microsecond == 999000


def test_parse_ts_converts_non_utc_offset_to_utc() -> None:
    assert parse_ts("2026-09-22T18:20:30+08:00") == parse_ts("2026-09-22T10:20:30Z")


def test_parse_ts_accepts_space_separator_and_stable_repeat() -> None:
    first = parse_ts("2026-09-22 10:20:30Z")
    assert first == parse_ts("2026-09-22T10:20:30Z")
    assert parse_ts("2026-09-22T10:20:30Z") == first


def test_parse_ts_handles_extreme_years() -> None:
    assert parse_ts("9999-12-31T23:59:59.999999Z").year == 9999
    assert parse_ts("0001-01-01T00:00:00Z").tzinfo is UTC


@pytest.mark.parametrize("raw", ["2026-09-22T10:20:30", "2026-09-22", "not-a-time", "", " "])
def test_parse_ts_rejects_naive_and_garbage(raw: str) -> None:
    with pytest.raises(ParseError):
        parse_ts(raw)


def test_parse_ts_error_codes_distinguish_naive_from_unparsable() -> None:
    with pytest.raises(ParseError) as naive:
        parse_ts("2026-09-22T10:20:30")
    assert naive.value.code == "ts_naive"
    with pytest.raises(ParseError) as garbage:
        parse_ts("yesterday")
    assert garbage.value.code == "ts_parse"


def test_parse_ts_error_text_never_leaks_raw_input() -> None:
    marker = "ghp_SECRETISH_2026-13-45T99:99"
    with pytest.raises(ParseError) as caught:
        parse_ts(marker)
    assert marker not in str(caught.value)
    assert "length" in str(caught.value)
    assert caught.value.__cause__ is None


def _millis(value: str | datetime) -> int:
    """`event_millis` 是容错接口，比较前先排除 None（不让失败伪装成差异）。"""
    millis = event_millis(value)
    assert millis is not None
    return millis


def test_event_millis_matches_parse_ts_and_epoch_math() -> None:
    raw = "1970-01-01T00:00:01.500Z"
    assert event_millis(raw) == 1500
    assert event_millis(raw) == event_millis(parse_ts(raw))


def test_event_millis_accepts_aware_datetime_and_floors_micros() -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    anchor = _millis(base)
    assert anchor > 0
    assert _millis(base + timedelta(microseconds=1_999)) - anchor == 1
    assert _millis(base + timedelta(microseconds=1_500)) - anchor == 1
    assert _millis(base + timedelta(microseconds=999_999)) - anchor == 999


def test_event_millis_is_negative_before_epoch() -> None:
    assert event_millis("1969-12-31T23:59:59Z") == -1000


@pytest.mark.parametrize("value", [None, "", "yesterday", "2026-09-22T10:20:30"])
def test_event_millis_returns_none_instead_of_raising(value: object) -> None:
    assert event_millis(value) is None  # type: ignore[arg-type]


def test_event_millis_rejects_naive_datetime() -> None:
    assert event_millis(datetime(2026, 9, 22, 10, 20, 30)) is None
