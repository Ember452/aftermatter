"""core 异常树：机器可读 code + 有界摘要（契约见 docs/architecture/core.md）。"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

# 异常文本会进日志与报告，单个 context 值必须有界。
MAX_CONTEXT_VALUE = 80


def _clip(value: object) -> str:
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= MAX_CONTEXT_VALUE else f"{text[:MAX_CONTEXT_VALUE]}…"


class AfterMatterError(Exception):
    """本项目异常基类。

    调用方按 `code` 分流，不解析 message 文本；`context` 只放有界元信息（计数、长度、
    枚举值），永不放原始会话内容或真实路径——它们会随 traceback 进日志与报告。
    """

    default_code: ClassVar[str] = "aftermatter_error"
    default_retryable: ClassVar[bool] = False

    def __init__(
        self,
        code: str | None = None,
        retryable: bool | None = None,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.code: str = code or type(self).default_code
        self.retryable: bool = type(self).default_retryable if retryable is None else retryable
        self.context: Mapping[str, object] = MappingProxyType(dict(context or {}))
        super().__init__()

    def _extra(self) -> Mapping[str, object]:
        """子类补充进渲染文本的结构化字段（默认无）。"""
        return {}

    def __str__(self) -> str:
        merged: dict[str, object] = {**self._extra(), **dict(self.context)}
        fields = " ".join(f"{key}={_clip(value)}" for key, value in sorted(merged.items()))
        head = f"{self.code} retryable={self.retryable}"
        return f"{head} {fields}" if fields else head


class ParseError(AfterMatterError):
    """适配器遇到不可解行；只带行号与内容摘要，不带原文。"""

    default_code = "parse_failed"

    def __init__(
        self,
        code: str | None = None,
        retryable: bool | None = None,
        *,
        context: Mapping[str, object] | None = None,
        line_no: int | None = None,
        raw_digest: str | None = None,
    ) -> None:
        self.line_no = line_no
        self.raw_digest = raw_digest
        super().__init__(code, retryable, context=context)

    def _extra(self) -> Mapping[str, object]:
        extra: dict[str, object] = {}
        if self.line_no is not None:
            extra["line_no"] = self.line_no
        if self.raw_digest is not None:
            extra["raw_digest"] = self.raw_digest
        return extra


class EvidenceError(AfterMatterError):
    """ERef 解析失败或与 IntegrityManifest 哈希不符（引用闸的返回异常）。"""

    default_code = "evidence_invalid"


class ContractViolation(AfterMatterError):
    """白名单外状态迁移、lane 越界、旁路写入等契约破坏。"""

    default_code = "contract_violation"


class PathOutsideWorkspace(ContractViolation):
    """归一化后的落点越出仓库根（路径沙箱边界）。"""

    default_code = "path_outside_root"


class ProviderError(AfterMatterError):
    """LLM 客户端错误；rate/timeout/auth/schema 子类在 providers 内细化。"""

    default_code = "provider_error"


class SandboxUnavailable(AfterMatterError):
    """docker 缺失或权限不足，执行级证据不可得。"""

    default_code = "sandbox_unavailable"


class ConfigError(AfterMatterError):
    """装配层配置非法。"""

    default_code = "config_invalid"
