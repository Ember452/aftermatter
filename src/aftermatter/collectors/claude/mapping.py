"""Claude 宿主 JSONL → L0 事件模型的声明式映射（纯数据 + 纯函数，可单测）。

三类去向严格分开（collectors.md §行分类器）：
`parsed` 映射表命中的会话事件；`ignored` 本就不属 L0 事件模型的东西；
`unparsed` 映射表外的未知 type——**只有它是格式漂移信号**。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

HOST: Literal["claude"] = "claude"

# 宿主侧元事件：真实探雷在本机 samples 里实测到这些 type，它们不是会话行为事实。
IGNORED_TYPES: frozenset[str] = frozenset(
    {
        "file-history-snapshot",
        "file-history-delta",
        "last-prompt",
        "attachment",
        "mode",
        "permission-mode",
        "ai-title",
        "cost-state",
        "agent-color",
        "atis-latch",
        "slug",
        "queue-operation",
    }
)

# 映射表认识的 type；不在表内也不在 IGNORED 里的 type 走 unparsed。
MAPPED_TYPES: frozenset[str] = frozenset({"user", "assistant", "system"})

# 别的工具往同目录写的记录带这些独有键——命中即判不属于本宿主。
FOREIGN_KEYS: frozenset[str] = frozenset({"atis-latch", "agent-color", "cost-state", "ai-title"})

# 自身产物路径清单（collectors.md §防自污染）：命中即从 target_paths 剔除。
SELF_ARTIFACT_MARKERS: tuple[str, ...] = (".aftermatter/", ".aftermatter\\")

# compact 是唯一认识的 system subtype；其余 subtype 属未知宿主事件 → unparsed。
LIFECYCLE_SUBTYPES: frozenset[str] = frozenset({"compact_boundary"})

# 内容块类型 → 是否产事件。
CONTENT_BLOCK_KINDS: Mapping[str, str] = {
    "text": "text",
    "tool_use": "tool_use",
    "tool_result": "tool_result",
    "thinking": "thinking",
}


# tool_use.input 里可能出现目标路径的键（实测：Write/Edit 用 file_path，Read 两种都见过）。
PATH_INPUT_KEYS: tuple[str, ...] = ("file_path", "path", "notebook_path")
# 命令类工具的输入键（RawEvent.command_text 的原文，仅本机保存）。
COMMAND_INPUT_KEYS: tuple[str, ...] = ("command", "cmd")


class LineDisposition(StrEnum):
    """单行/单块的去向。"""

    PARSED = "parsed"
    IGNORED = "ignored"
    UNPARSED = "unparsed"
    NOT_OURS = "not_ours"
    MALFORMED = "malformed"


def classify_record(record: Mapping[str, object]) -> tuple[LineDisposition, str]:
    """判定一条已解析成 dict 的记录该走哪条路，reason 是机器可读的类型名。"""
    if any(key in record for key in FOREIGN_KEYS):
        return LineDisposition.NOT_OURS, "not_claude_session"
    record_type = record.get("type")
    if not isinstance(record_type, str) or not record_type:
        return LineDisposition.MALFORMED, "missing_type"
    if record_type in IGNORED_TYPES:
        return LineDisposition.IGNORED, record_type
    if record_type in MAPPED_TYPES:
        return LineDisposition.PARSED, record_type
    return LineDisposition.UNPARSED, record_type


def is_self_artifact(path: str) -> bool:
    """路径是否指向 AfterMatter 自己的产物（防自我污染）。"""
    return any(marker in path for marker in SELF_ARTIFACT_MARKERS)


REASON_MAX_LEN = 40
_REASON_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_reason(raw: str) -> str:
    """把宿主可控的 type 串压成安全枚举 token。

    `ParseStats.reasons` 的键会直接进报告与上传载荷；type 名里出现斜杠、盘符分隔符或
    任意长内容时，不能原样穿透——这是“键不带路径”这条红线的实现点，不靠下游脱敏兼底。
    """
    cleaned = _REASON_SAFE.sub("_", raw).strip("_")
    return cleaned[:REASON_MAX_LEN] or "unnamed_type"


def looks_like_claude(record: Mapping[str, object]) -> bool:
    """归属判定：这条记录是不是 Claude Code 写的。

    判 `not_ours` 只认**正面证据**（命中外来独有键）。字段缺失不算——否则空对象与残行
    会被当成别的工具的输出，丢掉 `malformed_json` 这个真实信号（fixture `malformed/m3`
    与 `foreign/f1` 分别钉住这两条边界）。
    """
    return not any(key in record for key in FOREIGN_KEYS)


def content_blocks(message: object) -> list[Mapping[str, object]]:
    """取出 `message.content` 里的块列表；bare string 视作单个 text 块。"""
    if not isinstance(message, Mapping):
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [block for block in content if isinstance(block, Mapping)]
    return []
