"""`evidence.models` 测试：ERef / SourceEntry 的约束与不可变性。"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from pydantic import ValidationError

from aftermatter.core.fingerprint import fingerprint
from aftermatter.evidence.models import ERef, SourceEntry

DIGEST = hashlib.sha256(b"line-one\n").hexdigest()
VALID_REF: dict[str, Any] = {
    "source_path": "sessions/a.jsonl",
    "byte_start": 0,
    "byte_len": 9,
    "digest": DIGEST,
}


def _eref(**overrides: Any) -> ERef:
    payload = dict(VALID_REF)
    payload.update(overrides)
    return ERef(**payload)


def _entry(**overrides: Any) -> SourceEntry:
    payload: dict[str, Any] = {"path": "sessions/a.jsonl", "sha256": DIGEST, "size": 9}
    payload.update(overrides)
    return SourceEntry(**payload)


def test_valid_erefs_and_optional_line_no() -> None:
    assert _eref().line_no is None
    assert _eref(line_no=1).line_no == 1
    assert _eref(byte_start=9, byte_len=1, line_no=2).byte_start == 9


@pytest.mark.parametrize("field", ["source_path", "byte_start", "byte_len", "digest"])
def test_required_fields_are_enforced(field: str) -> None:
    payload = dict(VALID_REF)
    payload.pop(field)
    with pytest.raises(ValidationError):
        ERef(**payload)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/etc/passwd",
        "C:/repo/a.jsonl",
        "sessions\\a.jsonl",
        "../outside.jsonl",
        "sessions/../../outside.jsonl",
    ],
)
def test_source_path_must_be_repo_relative(value: str) -> None:
    with pytest.raises(ValidationError):
        _eref(source_path=value)


def test_dotted_file_names_are_not_parent_segments() -> None:
    assert _eref(source_path="sessions/a..b.jsonl").source_path == "sessions/a..b.jsonl"
    assert _eref(source_path=".").source_path == "."


@pytest.mark.parametrize(
    "digest",
    ["abc", DIGEST[:-1], DIGEST + "0", DIGEST.upper(), "g" * 64, DIGEST[:63] + "0 "],
)
def test_digest_shape(digest: str) -> None:
    with pytest.raises(ValidationError):
        _eref(digest=digest)


@pytest.mark.parametrize("value", [-1, -999])
def test_byte_start_rejects_negative(value: int) -> None:
    with pytest.raises(ValidationError):
        _eref(byte_start=value)


@pytest.mark.parametrize("value", [0, -1])
def test_byte_len_must_be_positive(value: int) -> None:
    with pytest.raises(ValidationError):
        _eref(byte_len=value)


@pytest.mark.parametrize("value", [0, -1])
def test_line_no_rejects_non_positive(value: int) -> None:
    with pytest.raises(ValidationError):
        _eref(line_no=value)


def test_eref_is_frozen() -> None:
    ref = _eref()
    with pytest.raises(ValidationError):
        ref.byte_start = 5


def test_source_entry_is_frozen() -> None:
    entry = _entry()
    with pytest.raises(ValidationError):
        entry.size = 10


def test_source_entry_path_follows_the_same_rule() -> None:
    _entry()
    with pytest.raises(ValidationError):
        _entry(path="/srv/sessions/a.jsonl")
    with pytest.raises(ValidationError):
        _entry(sha256=DIGEST.upper())
    with pytest.raises(ValidationError):
        _entry(size=-1)


def test_erefs_are_immutable_but_serializable() -> None:
    original = _eref(line_no=3)
    dumped = original.model_dump(mode="json")
    assert ERef.model_validate(dumped) == original
    assert dumped["digest"] == DIGEST


def test_identical_refs_share_fingerprint_and_differences_do_not() -> None:
    left = _eref(line_no=1)
    right = _eref(line_no=1)
    assert fingerprint(left) == fingerprint(right)
    assert fingerprint(left) == fingerprint(left.model_dump(mode="json"))
    assert fingerprint(left) != fingerprint(_eref(byte_len=8, line_no=1))
