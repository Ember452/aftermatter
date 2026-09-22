"""日志与 TraceId：只配置 `aftermatter` 一支，禁止污染 root logger。"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from secrets import token_hex

# 一次 analyze run 一个 id；未绑定时用占位符保证列宽稳定。
TRACE_ID_FALLBACK = "-"
TRACE_ID_BYTES = 6
ROOT_LOGGER_NAME = "aftermatter"

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(trace_id)s %(name)s: %(message)s"

trace_id_var: ContextVar[str] = ContextVar("aftermatter.trace_id", default=TRACE_ID_FALLBACK)


def new_trace_id() -> str:
    """随机 12 位十六进制：够用于 run 关联，且不撑爆日志列宽。"""
    return token_hex(TRACE_ID_BYTES)


class TraceIdFilter(logging.Filter):
    """给记录补 `trace_id` 字段。

    挂在 handler 而不是 logger 上：子 logger 经 propagate=False 后仍会把记录送到该
    handler，挂在 logger 上的过滤器不会被子 logger 触发，格式串就会 KeyError。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = trace_id_var.get()
        return True


class _CoreHandler(logging.StreamHandler):
    """带身份标记的 handler，供 `setup_logging` 幂等移除自己安装的那一个。"""


@contextmanager
def use_trace_id(trace_id: str | None = None) -> Iterator[str]:
    """在 with 块内绑定 trace_id，退出时恢复。

    基于 contextvar，asyncio 任务各持副本：并发 run 的日志不会互相串 id。
    """
    value = trace_id or new_trace_id()
    token = trace_id_var.set(value)
    try:
        yield value
    finally:
        trace_id_var.reset(token)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """配置 `aftermatter` logger（输出到 stderr，诊断不与 `--json`  stdout 争道）。

    幂等：重复调用不叠加 handler，否则库被多次装配时每条日志会翻倍。
    不装 root handler、不读配置文件：core 不做 IO 策略与配置加载（core.md 职责边界）。
    """
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    for handler in [h for h in logger.handlers if isinstance(h, _CoreHandler)]:
        logger.removeHandler(handler)
    handler = _CoreHandler()
    handler.addFilter(TraceIdFilter())
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
