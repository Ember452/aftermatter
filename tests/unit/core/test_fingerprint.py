"""core.fingerprint 测试：canonical JSON 稳定性、宽度、拒绝不可序列化输入。"""

from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any

import pytest

from aftermatter.core.errors import ContractViolation
from aftermatter.core.fingerprint import FINGERPRINT_HEX_WIDTH, fingerprint


class _StubModel:
    """鸭子类型的 pydantic 替身：core 不 import pydantic（modules §1）。"""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[dict[str, Any]] = []

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self._payload


def _sha256_prefix(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:FINGERPRINT_HEX_WIDTH]


def test_output_is_16_lowercase_hex() -> None:
    value = fingerprint({"a": 1})
    assert len(value) == FINGERPRINT_HEX_WIDTH == 16
    assert re.fullmatch(r"[0-9a-f]{16}", value)


def test_mapping_key_order_does_not_matter() -> None:
    assert fingerprint({"b": 1, "a": 2}) == fingerprint({"a": 2, "b": 1})
    assert fingerprint(OrderedDict([("b", 1), ("a", 2)])) == fingerprint({"a": 2, "b": 1})


def test_canonical_form_is_sorted_compact_unescaped() -> None:
    assert fingerprint({"b": [1, 2], "a": "中文"}) == _sha256_prefix('{"a":"中文","b":[1,2]}')


def test_sequence_order_matters() -> None:
    assert fingerprint([1, 2]) != fingerprint([2, 1])
    # tuple 与 list 在 JSON 层同形：契约模型用 tuple，指纹不区分二者。
    assert fingerprint({"t": (1, 2)}) == fingerprint({"t": [1, 2]})


def test_bool_and_int_are_not_confused() -> None:
    assert fingerprint({"a": True}) != fingerprint({"a": 1})


def test_str_and_bytes_are_hashed_directly() -> None:
    assert fingerprint("raw-line") == _sha256_prefix("raw-line")
    assert fingerprint(b"raw-line") == fingerprint("raw-line")
    assert fingerprint(b"\x00\xff") == hashlib.sha256(b"\x00\xff").hexdigest()[:16]


def test_model_is_dumped_in_json_mode_once() -> None:
    model = _StubModel({"a": 1})
    assert fingerprint(model) == fingerprint({"a": 1})
    assert model.calls == [{"mode": "json"}]


def test_nested_model_is_recursively_canonicalized() -> None:
    inner = _StubModel({"host": "claude"})
    outer = _StubModel({"lane": inner, "n": 1})
    assert fingerprint(outer) == fingerprint({"lane": {"host": "claude"}, "n": 1})


def test_repeat_calls_are_stable() -> None:
    payload = {"z": [1, {"y": "x"}], "a": None}
    assert fingerprint(payload) == fingerprint(payload) == fingerprint(dict(payload))


@pytest.mark.parametrize(
    "payload",
    [{"a", "b"}, {"a": frozenset({1})}, {"a": float("nan")}, {"a": float("inf")}],
)
def test_rejects_hash_order_dependent_or_non_finite(payload: object) -> None:
    with pytest.raises(ContractViolation):
        fingerprint(payload)


def test_rejects_non_str_key_instead_of_coercing() -> None:
    with pytest.raises(ContractViolation) as caught:
        fingerprint({1: "a"})
    assert caught.value.code == "fingerprint_non_str_key"
    assert str(caught.value) == "fingerprint_non_str_key retryable=False type=int"
    # 拒绝而非强转：否则 {1: 'a'} 与 {'1': 'a'} 会撞成同一指纹。
    assert fingerprint({"1": "a"}) == _sha256_prefix('{"1":"a"}')


def test_unsupported_error_carries_type_only() -> None:
    class _Opaque:
        pass

    with pytest.raises(ContractViolation) as caught:
        fingerprint(_Opaque())
    assert caught.value.code == "fingerprint_unserializable"
    assert str(caught.value) == "fingerprint_unserializable retryable=False type=_Opaque"
    assert caught.value.__cause__ is None


def test_deeply_nested_structure_is_still_canonical() -> None:
    deep = {"b": {"a": [{"z": 1, "y": None}]}, "a": "é"}
    assert fingerprint(deep) == _sha256_prefix('{"a":"é","b":{"a":[{"y":null,"z":1}]}}')
