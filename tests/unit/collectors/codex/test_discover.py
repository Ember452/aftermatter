"""Codex 发现层测试：目录布局、版本抽样、归属、自污染与 workspace 过滤。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from aftermatter.collectors.codex import CodexAdapter
from aftermatter.collectors.codex.discover import (
    SessionProbe,
    belongs_to_workspace,
    default_sessions_root,
    discover_sessions,
    probe_session,
)
from aftermatter.collectors.codex.mapping import HOST
from aftermatter.evidence.models import SessionRef, source_id_for

TS = "2026-09-21T08:00:00.123Z"


def _meta(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {"session_id": "s-1", "cwd": "/repo", "cli_version": "0.153.1"}
    payload.update(overrides)
    return {"timestamp": TS, "type": "session_meta", "payload": payload}


def _write(path: Path, records: list[object], *, raw: bytes | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        raw
        if raw is not None
        else b"".join(
            (json.dumps(record) if not isinstance(record, str) else record).encode("utf-8") + b"\n"
            for record in records
        )
    )
    path.write_bytes(body)
    return path


def _msg(role: str = "user") -> dict[str, object]:
    return {
        "timestamp": TS,
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": role,
            "content": [{"type": "input_text", "text": "x"}],
        },
    }


def test_sessions_live_under_date_directories(tmp_path: Path) -> None:
    _write(tmp_path / "2026" / "09" / "21" / "rollout-a.jsonl", [_meta(), _msg()])
    refs = discover_sessions(tmp_path)
    assert [ref.host for ref in refs] == [HOST]
    assert refs[0].source_id == source_id_for(HOST, str(tmp_path))
    assert refs[0].format_version == "0.153.1"
    assert refs[0].size == (tmp_path / "2026" / "09" / "21" / "rollout-a.jsonl").stat().st_size
    assert refs[0].content_hash and len(refs[0].content_hash) == 64


def test_default_sessions_root_is_codex_sessions() -> None:
    assert default_sessions_root() == Path.home() / ".codex" / "sessions"


def test_self_artifact_files_are_skipped(tmp_path: Path) -> None:
    mine = tmp_path / "proj" / ".aftermatter" / "run.jsonl"
    _write(mine, [_meta()])
    _write(tmp_path / "proj" / "real.jsonl", [_meta(), _msg()])
    assert [Path(ref.path).name for ref in discover_sessions(tmp_path)] == ["real.jsonl"]


def test_claude_shaped_session_is_not_discovered(tmp_path: Path) -> None:
    _write(
        tmp_path / "c.jsonl",
        [],
        raw=json.dumps(
            {
                "type": "user",
                "uuid": "u",
                "sessionId": "s",
                "isSidechain": False,
                "userType": "external",
                "cwd": "/repo",
            }
        ).encode("utf-8")
        + b"\n",
    )
    assert discover_sessions(tmp_path) == []


def test_head_lines_that_do_not_parse_do_not_hurt_the_probe(tmp_path: Path) -> None:
    body = b"garbage line\n[1, 2]\n" + json.dumps(_meta()).encode("utf-8") + b"\n"
    path = _write(tmp_path / "s.jsonl", [], raw=body)
    probe = probe_session(path.read_bytes())
    assert probe.version == "0.153.1"
    assert probe.cwd == "/repo"
    assert probe.foreign is False


def test_file_without_session_meta_has_no_version(tmp_path: Path) -> None:
    path = _write(tmp_path / "s.jsonl", [_msg()])
    probe = probe_session(path.read_bytes())
    assert probe.version is None and probe.cwd is None and probe.foreign is False
    refs = discover_sessions(tmp_path)
    assert [ref.format_version for ref in refs] == [None]


def test_malformed_payload_in_session_meta_yields_no_version() -> None:
    probe = probe_session(json.dumps({"type": "session_meta", "payload": "junk"}).encode() + b"\n")
    assert probe.version is None


def test_workspace_membership_uses_declared_cwd() -> None:
    probe = SessionProbe(cwd="/repo")
    assert belongs_to_workspace(probe, "/repo") is True
    assert belongs_to_workspace(probe, "/repo/sub") is True
    assert belongs_to_workspace(probe, "/other") is False


def test_probe_without_cwd_is_kept_rather_than_dropped() -> None:
    assert belongs_to_workspace(SessionProbe(), "/repo") is True


def test_discover_filters_by_workspace(tmp_path: Path) -> None:
    _write(tmp_path / "a.jsonl", [_meta(cwd="/repo")])
    _write(tmp_path / "b.jsonl", [_meta(cwd="/elsewhere")])
    assert [Path(r.path).name for r in discover_sessions(tmp_path, workspace="/repo")] == [
        "a.jsonl"
    ]
    assert len(discover_sessions(tmp_path)) == 2


def test_adapter_healthcheck_reports_detected_versions(tmp_path: Path) -> None:
    _write(tmp_path / "a.jsonl", [_meta(), _msg()])
    adapter = CodexAdapter(tmp_path)
    assert adapter.healthcheck().support == "unknown"
    adapter.discover()
    assert adapter.healthcheck().detected_versions == ("0.153.1",)
    assert adapter.healthcheck().support == "ok"


def test_healthcheck_degrades_on_unsupported_version(tmp_path: Path) -> None:
    _write(tmp_path / "a.jsonl", [_meta(cli_version="9.9.9")])
    adapter = CodexAdapter(tmp_path)
    adapter.discover()
    assert adapter.healthcheck().support == "degraded"


def test_stats_accumulate_and_reset(tmp_path: Path) -> None:
    path = _write(tmp_path / "a.jsonl", [_meta(), _msg()])
    adapter = CodexAdapter(tmp_path)
    ref = discover_sessions(tmp_path)[0]
    assert _event_count(adapter, ref) == 2
    assert adapter.stats.lines_total == 2
    adapter.reset_stats()
    assert adapter.stats.lines_total == 0
    assert path.is_file()


def _event_count(adapter: CodexAdapter, ref: SessionRef) -> int:
    async def _run() -> int:
        return len([event async for event in adapter.parse(ref)])

    return asyncio.run(_run())
