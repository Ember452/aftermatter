"""fixture 驱动的 Claude 解析测试：逐条对期望事件序列与 ParseStats。

期望值来自 `tests/fixtures/claude/<scenario>/<name>.expected.json`，它们**先于实现**存在
（开发计划 §1 铁律 3）；本文件因此不接受"改期望让它过"的修法。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from aftermatter.collectors.claude import ClaudeAdapter
from aftermatter.collectors.claude.mapping import safe_reason
from aftermatter.core.errors import ParseError
from aftermatter.evidence.integrity import VerifyOutcome, verify_ref
from aftermatter.evidence.models import RawEvent, SessionRef, SourceEntry, source_id_for

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "claude"
CASES = sorted(FIXTURES.rglob("*.jsonl"))


def _expected(case: Path) -> dict[str, Any]:
    return json.loads(case.with_name(case.stem + ".expected.json").read_text(encoding="utf-8"))


def _session_ref(case: Path) -> SessionRef:
    raw = case.read_bytes()
    return SessionRef(
        host="claude",
        source_id=source_id_for("claude", str(case.parent)),
        path=str(case),
        size=len(raw),
        content_hash=hashlib.sha256(raw).hexdigest(),
    )


def _as_dict(event: RawEvent) -> dict[str, Any]:
    """按 expected.json 的形状取投影；`ts` 还原成宿主原始的 Z 毫秒写法便于对照。"""
    moment = event.ts
    return {
        "kind": str(event.kind),
        "seq": event.seq,
        "ts": f"{moment:%Y-%m-%dT%H:%M:%S}.{moment.microsecond // 1000:03d}Z",
        "tool_name": event.tool_name,
        "result_ok": event.result_ok,
        "target_paths": list(event.target_paths),
        "line_no": event.evidence_ref.line_no,
        "model": event.model,
    }


@pytest.mark.parametrize("case", CASES, ids=[c.relative_to(FIXTURES).as_posix() for c in CASES])
async def test_fixture_events_match_expectation(case: Path) -> None:
    expect = _expected(case)
    adapter = ClaudeAdapter(case.parent)
    events = [event async for event in adapter.parse(_session_ref(case))]
    assert [_as_dict(event) for event in events] == expect["events"], case.name


@pytest.mark.parametrize("case", CASES, ids=[c.relative_to(FIXTURES).as_posix() for c in CASES])
async def test_fixture_stats_match_expectation(case: Path) -> None:
    expect = _expected(case)
    adapter = ClaudeAdapter(case.parent)
    [event async for event in adapter.parse(_session_ref(case))]
    assert adapter.stats.model_dump() == expect["stats"], case.name


@pytest.mark.parametrize("case", CASES, ids=[c.relative_to(FIXTURES).as_posix() for c in CASES])
async def test_every_emitted_reference_resolves_back_to_its_bytes(case: Path) -> None:
    """解析产出的每条 ERef 必须能被引用闸验回 ok——否则"可指回原始字节"只是口号。"""
    ref = _session_ref(case)
    adapter = ClaudeAdapter(case.parent)
    entry = SourceEntry(
        source_id=ref.source_id,
        path=case.name,
        sha256=ref.content_hash,
        size=ref.size,
    )
    roots = {ref.source_id: case.parent}
    events = [event async for event in adapter.parse(ref)]
    assert len(events) == _expected(case)["stats"]["parsed"], case.name
    for event in events:
        assert verify_ref(event.evidence_ref, [entry], roots=roots) is VerifyOutcome.OK


# --- 适配器行为（不靠 fixture 部分） ------------------------------------


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "type": "user",
        "uuid": "u",
        "sessionId": "s-1",
        "cwd": "/repo",
        "timestamp": "2026-09-20T10:00:00.123Z",
        "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]},
    }
    record.update(overrides)
    return record


def _to_line(line: object) -> bytes:
    if isinstance(line, str):
        return line.encode("utf-8") + b"\n"
    return json.dumps(line).encode("utf-8") + b"\n"


def _session(tmp_path: Path, records: list[object]) -> tuple[Path, ClaudeAdapter, SessionRef]:
    """写一个临时会话文件；字符串元素按原文写入（用于造非法行）。"""
    path = tmp_path / "proj" / "s.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = b"".join(_to_line(line) for line in records)
    path.write_bytes(body)
    adapter = ClaudeAdapter(path.parent)
    ref = SessionRef(
        host="claude",
        source_id=source_id_for("claude", str(path.parent)),
        path=str(path),
        size=len(body),
        content_hash=hashlib.sha256(body).hexdigest(),
    )
    return path, adapter, ref


async def _collect(
    adapter: ClaudeAdapter, ref: SessionRef, *, since_offset: int = 0
) -> list[RawEvent]:
    return [event async for event in adapter.parse(ref, since_offset=since_offset)]


async def test_resume_yields_the_same_suffix_as_the_full_read(tmp_path: Path) -> None:
    first = json.dumps(_record()).encode("utf-8") + b"\n"
    path, adapter, ref = _session(tmp_path, [_record(), _record(), _record()])
    whole = await _collect(adapter, ref)
    adapter.reset_stats()
    resumed = await _collect(adapter, ref, since_offset=len(first))
    assert [str(e.kind) for e in resumed] == [str(e.kind) for e in whole][1:]
    assert resumed[0].evidence_ref.byte_start == len(first)
    assert resumed[0].evidence_ref.line_no == 2
    assert path.is_file()


async def test_stats_accumulate_across_sessions_and_reset_clears_them(tmp_path: Path) -> None:
    _, adapter, ref = _session(tmp_path, [_record()])
    await _collect(adapter, ref)
    await _collect(adapter, ref)
    assert adapter.stats.lines_total == 2
    adapter.reset_stats()
    assert adapter.stats.model_dump(mode="json")["lines_total"] == 0
    assert adapter.stats.reasons == {}


async def test_unreadable_session_fails_hard_without_leaking_the_path(tmp_path: Path) -> None:
    _, adapter, ref = _session(tmp_path, [_record()])
    Path(ref.path).unlink()
    with pytest.raises(ParseError) as caught:
        await _collect(adapter, ref)
    assert caught.value.code == "session_unreadable"
    assert Path(ref.path).name not in str(caught.value)


async def test_blank_lines_are_not_counted_as_lines(tmp_path: Path) -> None:
    _, adapter, ref = _session(tmp_path, [_record()])
    Path(ref.path).write_bytes(b"\n   \n" + json.dumps(_record()).encode("utf-8") + b"\n")
    events = await _collect(adapter, ref)
    assert adapter.stats.lines_total == 1
    assert len(events) == 1
    assert events[0].evidence_ref.line_no == 3


async def test_unparsable_ts_is_unparsed_and_does_not_stop_the_stream(tmp_path: Path) -> None:
    _, adapter, ref = _session(tmp_path, [_record(timestamp="2026-09-20T10:00:00"), _record()])
    events = await _collect(adapter, ref)
    stats = adapter.stats
    assert stats.unparsed == 1 and stats.parsed == 1
    assert stats.reasons == {"ts_unparsable": 1}
    assert [event.seq for event in events] == [1]


async def test_host_controlled_type_names_are_sanitized_into_safe_tokens(tmp_path: Path) -> None:
    """reasons 的键会直接进报告：宿主可控的 type 串必须先净化，不得原样穿透。"""
    nasty = "..\\subdir/name:with~user\n" + "x" * 60
    _, adapter, ref = _session(tmp_path, [_record(type=nasty)])
    await _collect(adapter, ref)
    keys = list(adapter.stats.reasons)
    assert len(keys) == 1
    assert not {"/", "\\", ":", "~", "\n"} & set(keys[0]), keys[0]
    assert len(keys[0]) <= 40, keys[0]


def test_safe_reason_never_returns_an_empty_token() -> None:
    assert safe_reason("///") == "unnamed_type"
    assert safe_reason("file-history-snapshot") == "file-history-snapshot"


async def test_json_that_is_not_an_object_is_malformed(tmp_path: Path) -> None:
    _, adapter, ref = _session(tmp_path, ["[1, 2]"])
    assert await _collect(adapter, ref) == []
    assert adapter.stats.reasons == {"not_object": 1}
    assert adapter.stats.malformed_json == 1


async def test_unknown_system_subtype_is_ignored_not_unparsed(tmp_path: Path) -> None:
    _, adapter, ref = _session(tmp_path, [_record(type="system", subtype="api_error")])
    assert await _collect(adapter, ref) == []
    assert adapter.stats.ignored == 1
    assert adapter.stats.unparsed == 0
    assert adapter.stats.reasons == {"system_subtype": 1}


async def test_line_without_content_blocks_is_counted_as_ignored(tmp_path: Path) -> None:
    """被认下来的行不能从所有计数器里静默消失，否则去向账对不上。"""
    empty = {"role": "user", "content": []}
    _, adapter, ref = _session(tmp_path, [_record(message=empty)])
    assert await _collect(adapter, ref) == []
    assert adapter.stats.ignored == 1
    assert adapter.stats.reasons == {"no_blocks": 1}


async def test_assistant_thinking_only_line_produces_no_event(tmp_path: Path) -> None:
    thinking = {"role": "assistant", "content": [{"type": "thinking", "thinking": "mm"}]}
    _, adapter, ref = _session(tmp_path, [_record(type="assistant", message=thinking)])
    assert await _collect(adapter, ref) == []
    assert adapter.stats.reasons == {"thinking_block": 1}


async def test_tool_input_that_is_not_an_object_yields_a_bare_call(tmp_path: Path) -> None:
    block = {"type": "tool_use", "name": "Bash", "input": "not-a-dict"}
    message = {"role": "assistant", "content": [block]}
    _, adapter, ref = _session(tmp_path, [_record(type="assistant", message=message)])
    events = await _collect(adapter, ref)
    assert [str(e.kind) for e in events] == ["tool_call"]
    assert events[0].tool_name == "Bash"
    assert events[0].target_paths == ()
    assert events[0].command_text is None


async def test_command_text_is_taken_from_the_tool_input(tmp_path: Path) -> None:
    block = {"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q"}}
    message = {"role": "assistant", "content": [block]}
    _, adapter, ref = _session(tmp_path, [_record(type="assistant", message=message)])
    events = await _collect(adapter, ref)
    assert events[0].command_text == "pytest -q"


async def test_crlf_line_excludes_the_carriage_return_from_the_reference(tmp_path: Path) -> None:
    """ERef 的字节区间必须就是被哈希的那段：`\r` 不能混进 byte_len。"""
    path, adapter, ref = _session(tmp_path, [_record()])
    body = json.dumps(_record()).encode("utf-8") + b"\r\n"
    path.write_bytes(body)
    events = await _collect(adapter, ref)
    ref_line = events[0].evidence_ref
    assert ref_line.byte_len == len(body) - 2
    assert body[ref_line.byte_start : ref_line.byte_start + ref_line.byte_len].endswith(b"}")


async def test_session_outside_the_source_root_falls_back_to_its_name(tmp_path: Path) -> None:
    """越出源根时降级为文件名：引用仍可读，但不会把主机路径写进模型。"""
    _, adapter, ref = _session(tmp_path, [_record()])
    elsewhere = ref.path
    adapter = ClaudeAdapter(tmp_path / "not-the-parent")
    events = await _collect(adapter, _touch(ref, elsewhere))
    assert events[0].evidence_ref.source_path == "s.jsonl"


def _touch(ref: SessionRef, path: str) -> SessionRef:
    return ref.model_copy(update={"path": path})
