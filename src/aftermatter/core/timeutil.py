"""时间规范化：ISO8601 → UTC datetime（毫秒精度，向下截断）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aftermatter.core.errors import ParseError

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)


def _floor_millis(moment: datetime) -> datetime:
    return moment.replace(microsecond=moment.microsecond - moment.microsecond % 1000)


def parse_ts(raw: str) -> datetime:
    """解析单个 ISO8601 时间戳为 UTC datetime。

    毫秒向下截断而非四舍五入：同一原始串在任何路径下必须只有一种指纹。
    无时区的输入按失败处理而不是默默当 UTC——宿主会话恒带 `Z`，出现 naive 值说明
    格式漂移，需要被看见（计入 unparsed_count），不能被猜测掩盖。
    异常链用 `from None` 断开：`fromisoformat` 的 ValueError 文本会把原始输入带回
    traceback，而异常内容可能进日志与报告。
    """
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        raise ParseError("ts_parse", context={"length": len(raw)}) from None
    if parsed.tzinfo is None:
        raise ParseError("ts_naive", context={"length": len(raw)})
    return _floor_millis(parsed.astimezone(UTC))


def event_millis(value: str | datetime | None) -> int | None:
    """时间戳 → epoch 毫秒；任何解析失败返回 None，绝不抛。

    整数算法（不经过 float）避免舍入漂移。供 Episode 缺口比较使用（`episode_gap_ms`）。
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            moment = parse_ts(value)
        except ParseError:
            return None
    elif value.tzinfo is None:
        return None
    else:
        moment = _floor_millis(value.astimezone(UTC))
    return (moment - _EPOCH) // _MILLISECOND
