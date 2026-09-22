"""Codex 映射表测试：两层判别、双计识别、arguments 二次解析与补丁标记路径。

每条断言都标注了它所依据的实测事实（2026-09-22，3 会话 / 138 行）。
"""

from __future__ import annotations

import pytest

from aftermatter.collectors.codex.mapping import (
    LineDisposition,
    classify_record,
    command_from,
    message_kind,
    parse_arguments,
    paths_from_patch,
    safe_reason,
    workdir_from,
)
from aftermatter.evidence.models import EventKind


def _envelope(outer: object, inner: object = None) -> dict[str, object]:
    payload: dict[str, object] = {}
    if inner is not None:
        payload["type"] = inner
    return {"timestamp": "t", "type": outer, "payload": payload}


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"uuid": "u"}, LineDisposition.NOT_OURS),
        ({"type": "user", "sessionId": "s"}, LineDisposition.NOT_OURS),
        ({}, LineDisposition.MALFORMED),
        ({"timestamp": "t"}, LineDisposition.MALFORMED),
        ({"type": None}, LineDisposition.MALFORMED),
        (_envelope("brand_new_outer"), LineDisposition.UNPARSED),
        (_envelope("turn_context", "x"), LineDisposition.IGNORED),
        (_envelope("world_state", "x"), LineDisposition.IGNORED),
        ({"type": "response_item", "timestamp": "t"}, LineDisposition.MALFORMED),
        (_envelope("session_meta"), LineDisposition.PARSED),
        (_envelope("event_msg", "task_started"), LineDisposition.PARSED),
        (_envelope("event_msg", "agent_message"), LineDisposition.IGNORED),
        (_envelope("event_msg", "user_message"), LineDisposition.IGNORED),
        (_envelope("event_msg", "token_count"), LineDisposition.IGNORED),
        (_envelope("response_item", "reasoning"), LineDisposition.IGNORED),
        (_envelope("response_item", "function_call"), LineDisposition.PARSED),
        (_envelope("response_item", "custom_tool_call_output"), LineDisposition.PARSED),
        (_envelope("response_item", "message"), LineDisposition.PARSED),
        (_envelope("response_item", "quantum-flux"), LineDisposition.UNPARSED),
    ],
)
def test_classify_covers_every_measured_pair(record: dict[str, object], expected: object) -> None:
    assert classify_record(record)[0] is expected


def test_foreign_evidence_beats_a_valid_codex_type() -> None:
    """同时带 Claude 信封键与 Codex type：归属优先，不进 kind 映射。"""
    record = _envelope("response_item", "message")
    record["sessionId"] = "s"
    assert classify_record(record) == (LineDisposition.NOT_OURS, "not_codex_session")


def test_unpaired_reason_is_composite_and_path_free() -> None:
    reason = classify_record(_envelope("response_item", "a/b:c"))[1]
    assert reason == "response_item_a_b_c"


def test_message_role_mapping() -> None:
    assert message_kind({"role": "user"}) == (EventKind.USER_PROMPT, "")
    assert message_kind({"role": "assistant"}) == (EventKind.ASSISTANT_MESSAGE, "")
    assert message_kind({"role": "developer"}) == (None, "role_developer")
    assert message_kind({}) == (None, "missing_role")
    assert message_kind({"role": "tool"}) == (None, "role_tool")


def test_arguments_is_a_json_string_and_must_be_reparsed() -> None:
    parsed, note = parse_arguments('{"cmd": "pytest -q"}')
    assert note is None
    assert parsed is not None and parsed["cmd"] == "pytest -q"


@pytest.mark.parametrize("raw", [None, "", "   ", "{not json", "[1, 2]"])
def test_unparsable_arguments_keep_the_line_but_note_the_field(raw: object) -> None:
    parsed, note = parse_arguments(raw)
    assert parsed is None
    assert note in {"arguments_unparsable", "arguments_not_object"}


def test_arguments_already_a_mapping_passes_through() -> None:
    arguments = {"cmd": "ls"}
    assert parse_arguments(arguments) == (arguments, None)


def test_command_and_workdir_extraction() -> None:
    assert command_from({"cmd": "pytest"}) == "pytest"
    assert command_from({"command": "ls"}) == "ls"
    assert command_from({"cmd": "  "}) is None
    assert command_from(None) is None
    assert workdir_from({"workdir": "/repo/src"}) == "/repo/src"
    assert workdir_from({"workdir": ""}) is None
    assert workdir_from(None) is None


def test_patch_paths_come_only_from_known_markers() -> None:
    text = (
        "*** Begin Patch\n"
        "*** Add File: src/new.py\n+print(1)\n"
        "*** Update File: src/old.py\n"
        "*** Delete File: gone.py\n"
        "*** Unknown Keyword: nope\n"
        "no marker line\n"
        "*** Add File:\n"
    )
    assert paths_from_patch(text) == ["src/new.py", "src/old.py", "gone.py"]
    assert paths_from_patch(None) == []
    assert paths_from_patch(12) == []


def test_safe_reason_handles_non_strings_and_length() -> None:
    assert safe_reason(12) == "int"
    assert safe_reason(None) == "NoneType"
    assert safe_reason("///") == "unnamed"
    assert len(safe_reason("x" * 200)) == 40
    assert safe_reason("file-history-snapshot") == "file-history-snapshot"
