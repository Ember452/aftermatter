"""core 基础设施：时间、指纹、路径、日志与异常树。

依赖仅标准库（modules §1）。这里只导出契约点名的公共 API，内部实现细节不外泄。
"""

from __future__ import annotations

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
from aftermatter.core.fingerprint import FINGERPRINT_HEX_WIDTH, fingerprint
from aftermatter.core.logctx import (
    LOG_FORMAT,
    ROOT_LOGGER_NAME,
    TRACE_ID_FALLBACK,
    TraceIdFilter,
    new_trace_id,
    setup_logging,
    trace_id_var,
    use_trace_id,
)
from aftermatter.core.pathutil import norm_path
from aftermatter.core.timeutil import event_millis, parse_ts

__all__ = [
    "FINGERPRINT_HEX_WIDTH",
    "LOG_FORMAT",
    "MAX_CONTEXT_VALUE",
    "ROOT_LOGGER_NAME",
    "TRACE_ID_FALLBACK",
    "AfterMatterError",
    "ConfigError",
    "ContractViolation",
    "EvidenceError",
    "ParseError",
    "PathOutsideWorkspace",
    "ProviderError",
    "SandboxUnavailable",
    "TraceIdFilter",
    "event_millis",
    "fingerprint",
    "new_trace_id",
    "norm_path",
    "parse_ts",
    "setup_logging",
    "trace_id_var",
    "use_trace_id",
]
