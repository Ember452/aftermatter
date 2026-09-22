"""引用闸测试：四态核验与篡改注入（M1 验收第 3 项的单元侧预演）。"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from aftermatter.evidence.integrity import VerifyOutcome, verify_ref
from aftermatter.evidence.models import ERef, SourceEntry

REL = "sessions/a.jsonl"
CONTENT = b"line-one\nline-two\n"
SPAN = b"line-one\n"
SPAN_SHA = hashlib.sha256(SPAN).hexdigest()
SOURCE_ID = hashlib.sha256(b"claude\0~/.claude/projects").hexdigest()[:12]
OTHER_SOURCE_ID = hashlib.sha256(b"claude\0~/.codex/sessions").hexdigest()[:12]


def _repo(tmp_path: Path, content: bytes = CONTENT) -> Path:
    target = tmp_path / REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return tmp_path


def _roots(root: Path, extra: dict[str, str | Path] | None = None) -> dict[str, str | Path]:
    return {SOURCE_ID: root, **(extra or {})}


def _entry(content: bytes = CONTENT, **overrides: Any) -> SourceEntry:
    payload: dict[str, Any] = {
        "source_id": SOURCE_ID,
        "path": REL,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }
    payload.update(overrides)
    return SourceEntry(**payload)


def _ref(**overrides: Any) -> ERef:
    payload: dict[str, Any] = {
        "source_id": SOURCE_ID,
        "source_path": REL,
        "byte_start": 0,
        "byte_len": 9,
        "digest": SPAN_SHA,
    }
    payload.update(overrides)
    return ERef(**payload)


def test_valid_reference_is_ok(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    assert verify_ref(_ref(), [_entry()], roots=_roots(root)) is VerifyOutcome.OK


def test_outcomes_are_machine_readable_strings() -> None:
    assert [str(outcome) for outcome in VerifyOutcome] == [
        "ok",
        "not_found",
        "hash_mismatch",
        "out_of_manifest",
    ]
    assert VerifyOutcome.OK == "ok"


@pytest.mark.parametrize("entries", [[], [_entry(path="sessions/b.jsonl")]])
def test_unlisted_source_is_out_of_manifest(tmp_path: Path, entries: list[SourceEntry]) -> None:
    root = _repo(tmp_path)
    assert verify_ref(_ref(), entries, roots=_roots(root)) is VerifyOutcome.OUT_OF_MANIFEST


def test_source_id_without_a_root_is_out_of_manifest(tmp_path: Path) -> None:
    # 入册条目在，但本机 run 上下文没登记这个源根——只能判"不在册"，不能猜目录。
    root = _repo(tmp_path)
    assert (
        verify_ref(_ref(), [_entry()], roots={OTHER_SOURCE_ID: root})
        is VerifyOutcome.OUT_OF_MANIFEST
    )


def test_entry_belonging_to_another_source_is_out_of_manifest(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    entries = [_entry(source_id=OTHER_SOURCE_ID)]
    assert verify_ref(_ref(), entries, roots=_roots(root)) is VerifyOutcome.OUT_OF_MANIFEST


def test_missing_file_is_not_found(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / REL).unlink()
    assert verify_ref(_ref(), [_entry()], roots=_roots(root)) is VerifyOutcome.NOT_FOUND


def test_span_past_end_of_file_is_not_found(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    ref = _ref(byte_start=len(CONTENT) - 3, byte_len=9)
    assert verify_ref(ref, [_entry()], roots=_roots(root)) is VerifyOutcome.NOT_FOUND


def test_tampered_span_bytes_are_hash_mismatch(tmp_path: Path) -> None:
    # 入册内容与实际文件一致（同尺寸、一字节之差），失配只可能来自区间哈希。
    tampered = b"line-onX\nline-two\n"
    root = _repo(tmp_path, tampered)
    assert verify_ref(_ref(), [_entry(tampered)], roots=_roots(root)) is VerifyOutcome.HASH_MISMATCH


def test_grown_file_breaks_the_manifest_even_if_span_is_intact(tmp_path: Path) -> None:
    root = _repo(tmp_path, CONTENT + b"appended\n")
    assert verify_ref(_ref(), [_entry()], roots=_roots(root)) is VerifyOutcome.HASH_MISMATCH


def test_forged_digest_is_hash_mismatch(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    forged = "f" * 64
    assert (
        verify_ref(_ref(digest=forged), [_entry()], roots=_roots(root))
        is VerifyOutcome.HASH_MISMATCH
    )


def test_line_no_never_participates_in_verification(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    assert verify_ref(_ref(line_no=1), [_entry()], roots=_roots(root)) is VerifyOutcome.OK
    assert verify_ref(_ref(line_no=99), [_entry()], roots=_roots(root)) is VerifyOutcome.OK


def test_verification_is_read_only_and_idempotent(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    before = hashlib.sha256((root / REL).read_bytes()).hexdigest()
    results = [verify_ref(_ref(), [_entry()], roots=_roots(root)) for _ in range(3)]
    assert results == [VerifyOutcome.OK] * 3
    assert hashlib.sha256((root / REL).read_bytes()).hexdigest() == before


def test_two_sources_resolve_independently(tmp_path: Path) -> None:
    first = _repo(tmp_path / "one")
    second = _repo(tmp_path / "two", b"line-ONEX\nline-two-x\n")
    entries = [
        _entry(),
        _entry(second.joinpath(REL).read_bytes(), source_id=OTHER_SOURCE_ID),
    ]
    roots = {SOURCE_ID: first, OTHER_SOURCE_ID: second}
    assert verify_ref(_ref(), entries, roots=roots) is VerifyOutcome.OK
    # 同一区间在两个源里内容不同：拿 A 源的 digest 去引 B 源，必须因哈希不符被拒。
    assert (
        verify_ref(_ref(source_id=OTHER_SOURCE_ID), entries, roots=roots)
        is VerifyOutcome.HASH_MISMATCH
    )
    shifted = _ref(
        source_id=OTHER_SOURCE_ID,
        byte_start=10,
        byte_len=11,
        digest=hashlib.sha256(b"line-two-x\n").hexdigest(),
    )
    assert verify_ref(shifted, entries, roots=roots) is VerifyOutcome.OK


@pytest.mark.parametrize("as_string", [True, False])
def test_roots_accept_str_and_path_values(tmp_path: Path, as_string: bool) -> None:
    root = _repo(tmp_path)
    target: str | Path = str(root) if as_string else root
    assert verify_ref(_ref(), [_entry()], roots={SOURCE_ID: target}) is VerifyOutcome.OK
