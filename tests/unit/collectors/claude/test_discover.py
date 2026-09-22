"""Claude 会话发现测试：自污染剔除、版本众数、归属抽样、workspace 过滤。"""

from __future__ import annotations

import json
from pathlib import Path

from aftermatter.collectors.claude import ClaudeAdapter
from aftermatter.collectors.claude.discover import (
    SessionProbe,
    belongs_to_workspace,
    default_sessions_root,
    discover_sessions,
    is_session_file,
    probe_session,
)
from aftermatter.evidence.models import AdapterHealth, source_id_for


def _write(path: Path, records: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in records))
    return path


def _claude_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "type": "user",
        "uuid": "u-1",
        "parentUuid": None,
        "sessionId": "s-1",
        "cwd": "/repo",
        "version": "2.1.252",
    }
    record.update(overrides)
    return record


def test_discover_finds_nested_session_files(tmp_path: Path) -> None:
    _write(tmp_path / "projA" / "s1.jsonl", [_claude_record()])
    _write(tmp_path / "projB" / "deep" / "s2.jsonl", [_claude_record()])
    refs = discover_sessions(tmp_path)
    assert sorted(Path(ref.path).name for ref in refs) == ["s1.jsonl", "s2.jsonl"]


def test_discover_skips_our_own_artifacts(tmp_path: Path) -> None:
    _write(tmp_path / "proj" / "real.jsonl", [_claude_record()])
    mine = tmp_path / ".aftermatter" / "runs" / "own.jsonl"
    _write(mine, [_claude_record()])
    assert [Path(ref.path).name for ref in discover_sessions(tmp_path)] == ["real.jsonl"]
    assert is_session_file(mine) is False


def test_discover_drops_foreign_sessions(tmp_path: Path) -> None:
    _write(tmp_path / "x.jsonl", [{"atis-latch": 1, "agent-color": "red"}])
    assert discover_sessions(tmp_path) == []


def test_format_version_is_the_mode_not_the_first_seen(tmp_path: Path) -> None:
    seen = ["2.1.220", "2.1.221", "2.1.221", "2.1.220", "2.1.220"]
    records = [_claude_record(version=v) for v in seen]
    path = _write(tmp_path / "s.jsonl", records)
    refs = discover_sessions(path.parent)
    assert [ref.format_version for ref in refs] == ["2.1.220"]


def test_missing_version_yields_none_format_version(tmp_path: Path) -> None:
    path = _write(tmp_path / "s.jsonl", [{"type": "user", "uuid": "u"}])
    assert discover_sessions(path.parent)[0].format_version is None


def test_path_is_absolute_and_source_id_is_path_free(tmp_path: Path) -> None:
    path = _write(tmp_path / "proj" / "s.jsonl", [_claude_record()])
    ref = discover_sessions(path.parent)[0]
    assert Path(ref.path).is_absolute()
    assert "\\" not in ref.source_id and "/" not in ref.source_id
    assert ref.source_id == source_id_for("claude", str(path.parent))
    assert ref.size == path.stat().st_size


def test_probe_on_truncated_tail_does_not_lose_the_complete_head(tmp_path: Path) -> None:
    body = json.dumps(_claude_record()).encode("utf-8") + b"\n" + b'{"type": "us'
    probe = probe_session(body)
    assert probe.versions == ("2.1.252",)
    assert probe.foreign is False


def test_probe_of_unreadable_shape_is_not_marked_foreign() -> None:
    assert probe_session(b"not json at all\n").foreign is False


def test_probe_records_mixed_shapes() -> None:
    raw = b'[1, 2]\n"string"\n' + json.dumps(_claude_record()).encode("utf-8") + b"\n"
    assert probe_session(raw).versions == ("2.1.252",)


def test_workspace_membership_uses_declared_cwd() -> None:
    probe = SessionProbe(cwds=("/repo",))
    assert belongs_to_workspace(probe, "/repo") is True
    assert belongs_to_workspace(probe, "/repo/sub") is True
    assert belongs_to_workspace(probe, "/other") is False


def test_unknown_cwd_keeps_the_session_rather_than_dropping_evidence() -> None:
    assert belongs_to_workspace(SessionProbe(cwds=()), "/repo") is True


def test_discover_workspace_filter_drops_other_repos(tmp_path: Path) -> None:
    _write(tmp_path / "a.jsonl", [_claude_record(cwd="/repo")])
    _write(tmp_path / "b.jsonl", [_claude_record(cwd="/elsewhere")])
    scoped = [Path(r.path).name for r in discover_sessions(tmp_path, workspace="/repo")]
    assert scoped == ["a.jsonl"]
    every = [Path(r.path).name for r in discover_sessions(tmp_path)]
    assert every == ["a.jsonl", "b.jsonl"]


def test_healthcheck_states_support_from_detected_versions(tmp_path: Path) -> None:
    adapter = ClaudeAdapter(tmp_path)
    assert adapter.healthcheck() == AdapterHealth(host="claude", support="unknown")

    _write(tmp_path / "s.jsonl", [_claude_record(version="2.1.9")])
    adapter.discover()
    assert adapter.healthcheck().support == "ok"

    _write(tmp_path / "future.jsonl", [_claude_record(version="9.9.9")])
    adapter.discover()
    health = adapter.healthcheck()
    assert health.support == "degraded"
    assert health.detected_versions == ("2.1.9", "9.9.9")


def test_default_sessions_root_points_at_claude_projects() -> None:
    assert default_sessions_root() == Path.home() / ".claude" / "projects"
