"""fixture 驱动的 Codex 解析测试：期望事件序列、ParseStats 与引用可回验。

期望值来自 `tests/fixtures/codex/<scenario>/<name>.expected.json`，先于实现存在
（开发计划 §1 铁律 3），本文件不接受"改期望让它过"的修法。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from aftermatter.collectors.codex import CodexAdapter
from aftermatter.core.errors import ParseError
from aftermatter.evidence.integrity import VerifyOutcome, verify_ref
from aftermatter.evidence.models import RawEvent, SessionRef, SourceEntry, source_id_for

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "codex"
CASES = sorted(FIXTURES.rglob("*.jsonl"))
IDS = [case.relative_to(FIXTURES).as_posix() for case in CASES]
TS_REAL = "2026-09-21T08:00:00.123Z"


def _expected(case: Path) -> dict[str, Any]:
    return json.loads(case.with_name(case.stem + ".expected.json").read_text(encoding="utf-8"))


def _session_ref(case: Path) -> SessionRef:
    raw = case.read_bytes()
    return SessionRef(
        host="codex",
        source_id=source_id_for("codex", str(case.parent)),
        path=str(case),
        size=len(raw),
        content_hash=hashlib.sha256(raw).hexdigest(),
    )


def _as_dict(event: RawEvent) -> dict[str, Any]:
    """投影到 expected.json 的形状；`command_text` 是 Codex 侧唯一承载 shell 命令的字段。"""
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
        "command_text": event.command_text,
    }


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_fixture_events_match_expectation(case: Path) -> None:
    adapter = CodexAdapter(case.parent)
    events = [event async for event in adapter.parse(_session_ref(case))]
    assert [_as_dict(event) for event in events] == _expected(case)["events"], case.name


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_fixture_stats_match_expectation(case: Path) -> None:
    adapter = CodexAdapter(case.parent)
    [event async for event in adapter.parse(_session_ref(case))]
    assert adapter.stats.model_dump() == _expected(case)["stats"], case.name


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_every_emitted_reference_resolves_back_to_its_bytes(case: Path) -> None:
    ref = _session_ref(case)
    adapter = CodexAdapter(case.parent)
    entry = SourceEntry(
        source_id=ref.source_id,
        path=case.name,
        sha256=ref.content_hash,
        size=ref.size,
    )
    events = [event async for event in adapter.parse(ref)]
    for event in events:
        assert verify_ref(event.evidence_ref, [entry], roots={ref.source_id: case.parent}) is (
            VerifyOutcome.OK
        )


async def test_session_meta_backfills_identity_for_later_lines(tmp_path: Path) -> None:
    """`session_id`/`cwd` 只在 session_meta 出现（实测 3 次），后续行必须继承。"""
    body = (
        json.dumps(
            {
                "timestamp": "2026-09-21T08:00:00.123Z",
                "type": "session_meta",
                "payload": {"session_id": "s-9", "cwd": "/repo", "cli_version": "0.153.1"},
            }
        )
        + "\n"
        + json.dumps(
            {
                "timestamp": "2026-09-21T08:00:01.000Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "id": "m",
                    "content": [{"type": "input_text", "text": "x"}],
                },
            }
        )
        + "\n"
    ).encode("utf-8")
    path = tmp_path / "s.jsonl"
    path.write_bytes(body)
    ref = SessionRef(
        host="codex",
        source_id=source_id_for("codex", str(tmp_path)),
        path=str(path),
        size=len(body),
        content_hash=hashlib.sha256(body).hexdigest(),
    )
    events = [event async for event in CodexAdapter(tmp_path).parse(ref)]
    assert [str(event.kind) for event in events] == ["lifecycle", "user_prompt"]
    assert {event.session_id for event in events} == {"s-9"}
    assert {event.cwd for event in events} == {"/repo"}


async def test_discover_rejects_claude_shaped_file_at_file_level(tmp_path: Path) -> None:
    """归属判定在 discover 就生效：Claude 信封键是正面证据，整文件不入候选。"""
    body = (
        json.dumps(
            {
                "type": "user",
                "uuid": "u",
                "sessionId": "s",
                "isSidechain": False,
                "userType": "external",
                "cwd": "/repo",
                "timestamp": "2026-09-21T08:00:00.123Z",
                "message": {"role": "user", "content": []},
            }
        ).encode("utf-8")
        + b"\n"
    )
    (tmp_path / "x.jsonl").write_bytes(body)
    adapter = CodexAdapter(tmp_path)
    assert adapter.discover() == []
    assert adapter.healthcheck().support == "unknown"


def _scratch(tmp_path: Path, body: bytes) -> tuple[CodexAdapter, SessionRef]:
    path = tmp_path / "s.jsonl"
    path.write_bytes(body)
    ref = SessionRef(
        host="codex",
        source_id=source_id_for("codex", str(tmp_path)),
        path=str(path),
        size=len(body),
        content_hash=hashlib.sha256(body).hexdigest(),
    )
    return CodexAdapter(tmp_path), ref


def _line(payload: dict[str, object], *, ts: str = TS_REAL) -> bytes:
    return json.dumps({"timestamp": ts, **payload}, ensure_ascii=False).encode("utf-8") + b"\n"


async def test_json_array_line_is_not_an_object(tmp_path: Path) -> None:
    """解得动但不是字典的行走 malformed/not_object，不污染 unparsed 信号。"""
    adapter, ref = _scratch(tmp_path, b"[1, 2]\n")
    assert [event async for event in adapter.parse(ref)] == []
    assert adapter.stats.reasons == {"not_object": 1}


async def test_unparsable_timestamp_is_unparsed_but_still_carries_identity(tmp_path: Path) -> None:
    body = _line(
        {"type": "session_meta", "payload": {"session_id": "s-9", "cwd": "/repo"}}, ts="nope"
    ) + _line(
        {
            "type": "response_item",
            "payload": {"type": "message", "role": "user", "content": "裸字符串形式"},
        }
    )
    adapter, ref = _scratch(tmp_path, body)
    events = [event async for event in adapter.parse(ref)]
    assert [str(event.kind) for event in events] == ["user_prompt"]
    assert adapter.stats.reasons == {"ts_unparsable": 1}
    assert (events[0].session_id, events[0].cwd) == ("s-9", "/repo")


async def test_content_bare_string_and_mixed_blocks_are_normalised(tmp_path: Path) -> None:
    """`content` 实测是块列表；字符串形式与混入的非字典块都要能处理。"""
    body = _line(
        {"type": "response_item", "payload": {"type": "message", "role": "user", "content": "hi"}}
    ) + _line(
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": ["junk", {"type": "output_text"}],
            },
        }
    )
    adapter, ref = _scratch(tmp_path, body)
    kinds = [str(event.kind) for event in [e async for e in adapter.parse(ref)]]
    assert kinds == ["user_prompt", "assistant_message"]


async def test_message_without_text_blocks_is_ignored(tmp_path: Path) -> None:
    body = _line(
        {
            "type": "response_item",
            "payload": {"type": "message", "role": "user", "content": [{"type": "image"}]},
        }
    )
    adapter, ref = _scratch(tmp_path, body)
    assert [event async for event in adapter.parse(ref)] == []
    assert adapter.stats.reasons == {"no_text_block": 1}
    assert adapter.stats.ignored == 1


async def test_message_with_null_content_is_ignored_not_crashing(tmp_path: Path) -> None:
    """`content` 为 null 时不得报错，也不得假产事件。"""
    body = _line(
        {
            "type": "response_item",
            "payload": {"type": "message", "role": "user", "content": None},
        }
    )
    adapter, ref = _scratch(tmp_path, body)
    assert [event async for event in adapter.parse(ref)] == []
    assert adapter.stats.ignored == 1
    assert adapter.stats.unparsed == 0


async def test_unreadable_session_fails_hard_without_leaking_the_path(tmp_path: Path) -> None:
    adapter, ref = _scratch(tmp_path, b"")
    Path(ref.path).unlink()
    with pytest.raises(ParseError) as caught:
        [event async for event in adapter.parse(ref)]
    assert caught.value.code == "session_unreadable"
    assert Path(ref.path).name not in str(caught.value)


async def test_path_outside_the_source_root_degrades_to_its_name(tmp_path: Path) -> None:
    nested = tmp_path / "real"
    nested.mkdir()
    body = _line(
        {"type": "response_item", "payload": {"type": "message", "role": "user", "content": "hi"}}
    )
    path = nested / "s.jsonl"
    path.write_bytes(body)
    ref = SessionRef(
        host="codex",
        source_id=source_id_for("codex", str(tmp_path)),
        path=str(path),
        size=len(body),
        content_hash=hashlib.sha256(body).hexdigest(),
    )
    events = [event async for event in CodexAdapter(tmp_path / "other").parse(ref)]
    assert events[0].evidence_ref.source_path == "s.jsonl"
