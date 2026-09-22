"""宿主 JSONL 的字节精确行读取（跨宿主共用）。

必须按 `b"\\n"` 切分并只剥 BOM 与行尾 `\\r`：`str.splitlines()` 会把 JSON 字符串里的
`U+2028`、`\\x0b` 等当行边界，那样 `byte_start`/`byte_len` 与 digest 就对不上原始字节，
引用闸会全线失效。各宿主共用这一份实现，避免第二个宿主抄出一个略有差异的版本。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True)
class JsonlLine:
    """一行的定位信息：`content` 不含行尾换行符，`byte_start` 指向其第一个字节。"""

    line_no: int
    byte_start: int
    content: bytes


def _trim(raw: bytes, position: int, stop: int) -> tuple[int, bytes]:
    start = position
    if raw.startswith(BOM, start):
        start += len(BOM)
    content = raw[start:stop]
    if content.endswith(b"\r"):
        content = content[:-1]
    return start, content


def read_lines(raw: bytes, since_offset: int = 0) -> Iterator[JsonlLine]:
    """从 `since_offset` 起逐行产出；空白行跳过但行号照计。

    `line_no` 按文件真实行号计算（含被跳过的空白行与 `since_offset` 之前的行），
    因此断点续读与全量读得到同一编号，`line_no` 才能当人类可读提示用。
    """
    size = len(raw)
    position = since_offset
    line_no = raw.count(b"\n", 0, min(since_offset, size)) + 1
    while position < size:
        end = raw.find(b"\n", position)
        stop = size if end == -1 else end
        start, content = _trim(raw, position, stop)
        if content.strip():
            yield JsonlLine(line_no, start, content)
        line_no += 1
        if end == -1:
            return
        position = end + 1
