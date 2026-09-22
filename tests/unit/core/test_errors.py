"""core.errors 测试：树形状、code 唯一性、有界摘要。"""

from __future__ import annotations

import pytest

from aftermatter.core.errors import (
    MAX_CONTEXT_VALUE,
    AfterMatterError,
    ConfigError,
    ContractViolation,
    EvidenceError,
    ParseError,
    PathOutsideWorkspace,
    ProviderError,
    SandboxUnavailable,
)


def _descendants(cls: type[AfterMatterError]) -> list[type[AfterMatterError]]:
    tree = [cls]
    for child in cls.__subclasses__():
        tree.extend(_descendants(child))
    return tree


def test_default_codes_are_unique_across_tree() -> None:
    tree = _descendants(AfterMatterError)
    codes = [cls.default_code for cls in tree]
    assert len(codes) == len(set(codes)), f"重复 code: {codes}"
    assert all(code for code in codes), "存在空 code"


def test_tree_shape_follows_core_doc() -> None:
    assert issubclass(PathOutsideWorkspace, ContractViolation)
    for cls in (
        ParseError,
        EvidenceError,
        ContractViolation,
        ProviderError,
        SandboxUnavailable,
        ConfigError,
    ):
        assert cls.__bases__ == (AfterMatterError,), cls


def test_bare_instance_uses_default_code_and_not_retryable() -> None:
    for cls in _descendants(AfterMatterError):
        error = cls()
        assert error.code == cls.default_code
        assert error.retryable is False
        assert str(error) == f"{cls.default_code} retryable=False"


def test_caller_can_override_code_and_retryable() -> None:
    error = AfterMatterError("custom_code", True, context={"events": 3})
    assert error.code == "custom_code"
    assert error.retryable is True
    assert str(error) == "custom_code retryable=True events=3"


def test_parse_error_carries_line_no_and_digest_only() -> None:
    error = ParseError("ts_parse", line_no=42, raw_digest="a1b2c3d4")
    assert error.line_no == 42
    assert error.raw_digest == "a1b2c3d4"
    assert str(error) == "ts_parse retryable=False line_no=42 raw_digest=a1b2c3d4"


def test_parse_error_without_optional_fields_renders_minimally() -> None:
    assert str(ParseError()) == "parse_failed retryable=False"


def test_context_values_are_clipped() -> None:
    secret = "x" * 500
    error = ParseError(raw_digest=secret)
    rendered = str(error)
    assert secret not in rendered
    assert f"{secret[:MAX_CONTEXT_VALUE]}…" in rendered


def test_context_is_immutable() -> None:
    error = ContractViolation(context={"lane": "session"})
    with pytest.raises(TypeError):
        error.context["lane"] = "project"  # type: ignore[index]


def test_context_keys_render_sorted_and_typed() -> None:
    error = EvidenceError(context={"b_count": 2, "a_state": "partial"})
    assert str(error) == "evidence_invalid retryable=False a_state=partial b_count=2"
