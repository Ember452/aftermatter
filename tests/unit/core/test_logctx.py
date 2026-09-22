"""core.logctx 测试：幂等装配、trace_id 贯穿、不污染 root logger。"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Iterator

import pytest

from aftermatter.core.logctx import (
    TRACE_ID_FALLBACK,
    TraceIdFilter,
    _CoreHandler,
    new_trace_id,
    setup_logging,
    trace_id_var,
    use_trace_id,
)


@pytest.fixture(autouse=True)
def _restore_logger_state() -> Iterator[None]:
    """core 会改动全局 logging 单例，测试后必须复原，否则会污染同进程其他测试。"""
    logger = logging.getLogger("aftermatter")
    saved = (list(logger.handlers), logger.level, logger.propagate)
    root_saved = list(logging.root.handlers)
    yield
    logger.handlers[:] = saved[0]
    logger.setLevel(saved[1])
    logger.propagate = saved[2]
    logging.root.handlers[:] = root_saved


def _core_handlers() -> list[logging.Handler]:
    handlers = logging.getLogger("aftermatter").handlers
    return [handler for handler in handlers if isinstance(handler, _CoreHandler)]


def test_setup_logging_is_idempotent() -> None:
    logger = setup_logging()
    setup_logging()
    assert len(_core_handlers()) == 1
    assert logger.handlers == _core_handlers()


def test_setup_does_not_touch_root_logger() -> None:
    root_before = list(logging.root.handlers)
    logger = setup_logging()
    assert logger.name == "aftermatter"
    assert logger.propagate is False
    assert logging.root.handlers == root_before


def test_child_logger_writes_stderr_once(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging()
    setup_logging()
    logging.getLogger("aftermatter.collectors").warning("hello")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("hello") == 1


def test_bound_trace_id_reaches_output(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging()
    with use_trace_id("abc123def456"):
        logging.getLogger("aftermatter.core").info("ping")
    assert " abc123def456 " in capsys.readouterr().err


def test_fallback_column_when_unbound(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging()
    logging.getLogger("aftermatter.core").info("ping")
    assert f" {TRACE_ID_FALLBACK} " in capsys.readouterr().err


def test_use_trace_id_generates_and_restores() -> None:
    assert trace_id_var.get() == TRACE_ID_FALLBACK
    with use_trace_id() as generated:
        assert trace_id_var.get() == generated
    assert trace_id_var.get() == TRACE_ID_FALLBACK


def test_use_trace_id_supports_nesting() -> None:
    with use_trace_id("outer") as outer:
        with use_trace_id("inner") as inner:
            assert trace_id_var.get() == inner
        assert trace_id_var.get() == outer


async def test_concurrent_tasks_do_not_share_trace_id() -> None:
    seen: list[str] = []

    async def worker(index: int) -> None:
        with use_trace_id(f"task{index}"):
            await asyncio.sleep(0)
            seen.append(trace_id_var.get())

    await asyncio.gather(worker(1), worker(2))
    assert sorted(seen) == ["task1", "task2"]
    assert trace_id_var.get() == TRACE_ID_FALLBACK


def test_new_trace_id_shape_and_uniqueness() -> None:
    drawn = [new_trace_id() for _ in range(200)]
    assert all(re.fullmatch(r"[0-9a-f]{12}", value) for value in drawn)
    assert len(set(drawn)) == len(drawn)


def _plain_record() -> logging.LogRecord:
    return logging.LogRecord("aftermatter.cli", logging.INFO, "f.py", 1, "msg", (), None)


def test_filter_fills_trace_id_from_contextvar() -> None:
    record = _plain_record()
    assert TraceIdFilter().filter(record) is True
    assert record.__dict__["trace_id"] == TRACE_ID_FALLBACK


def test_filter_keeps_existing_trace_id() -> None:
    record = _plain_record()
    record.__dict__["trace_id"] = "preset"
    with use_trace_id("other"):
        TraceIdFilter().filter(record)
    assert record.__dict__["trace_id"] == "preset"


def test_handler_filter_and_formatter_work_together() -> None:
    setup_logging()
    handler = _core_handlers()[0]
    assert len(handler.filters) == 1
    trace_filter = handler.filters[0]
    assert isinstance(trace_filter, TraceIdFilter)

    record = logging.getLogger("aftermatter.report").makeRecord(
        "aftermatter.report", logging.INFO, "r.py", 7, "done", (), None
    )
    with use_trace_id("feedface0011"):
        assert trace_filter.filter(record) is True
        line = handler.format(record)
    assert "feedface0011" in line
    assert line.endswith("aftermatter.report: done")
