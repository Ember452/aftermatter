"""Codex 会话 JSONL → L0 事件模型的声明式映射（依据 2026-09-22 本机真实样本）。

实测结构（3 个会话、138 行、409 KB）：每行信封恒为 `{timestamp, type, payload}`，
真正的判别在**两层**：外层 `type` ∈ {response_item 91, event_msg 38, session_meta 3,
turn_context 3, world_state 3}，内层 `payload.type` 才是事件种类。

两个必须由数据决定的判定，不靠记忆：
1. **双计风险**：`event_msg/agent_message`（5）与 `response_item/message` 的 assistant
   角色（5）是同一份对话的两个视图，`event_msg/user_message`（3）同理。因此对话事件只从
   `response_item` 取，`event_msg` 侧一律 `ignored:duplicate_of_response_item`。
2. **归属判定要正面证据**：Codex 记录恒不带 `uuid`/`sessionId`/`isSidechain` 这些 Claude
   信封键（138/138 实测），命中即判外来；只缺字段不算外来，按畸形行计。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

from aftermatter.evidence.models import EventKind

HOST: Literal["codex"] = "codex"

# 外层信封类型（实测五个值）；不在表内的外层类型走 unparsed。
OUTER_TYPES: frozenset[str] = frozenset(
    {"session_meta", "turn_context", "world_state", "response_item", "event_msg"}
)

# 非行为记录：回合上下文与世界状态声明（turn_context 仍被 parse 读取以carry model/cwd）。
IGNORED_OUTER: frozenset[str] = frozenset({"turn_context", "world_state"})

# 与 response_item 携带同一份对话的 event_msg 记录：忽略以防双计。
DUPLICATE_PAIRS: frozenset[tuple[str, str | None]] = frozenset(
    {
        ("event_msg", "agent_message"),
        ("event_msg", "user_message"),
        ("event_msg", "custom_tool_call"),
        ("event_msg", "custom_tool_call_output"),
    }
)

# 宿主侧簿记：token 计数、补丁回执、思考摘要——都不是 L0 行为事实。
IGNORED_PAIRS: frozenset[tuple[str, str | None]] = frozenset(
    {
        ("event_msg", "token_count"),
        ("event_msg", "patch_apply_end"),
        ("response_item", "reasoning"),
    }
)

# 会话/回合状态记录 → lifecycle（实测 task_started 3、task_complete 2、turn_aborted 1）。
# 内层可为 None：session_meta 的 payload 没有自己的 type（实测 3 次）。
LIFECYCLE_PAIRS: frozenset[tuple[str, str | None]] = frozenset(
    {
        ("session_meta", None),
        ("event_msg", "task_started"),
        ("event_msg", "task_complete"),
        ("event_msg", "turn_aborted"),
    }
)

# 消息角色 → kind。`developer`（实测 10 条）是注入的指令而非用户输入，不产事件。
MESSAGE_ROLES: Mapping[str, EventKind | None] = {
    "user": EventKind.USER_PROMPT,
    "assistant": EventKind.ASSISTANT_MESSAGE,
    "developer": None,
}

# 工具往返：arguments 是 **JSON 字符串**（实测 24/24），需二次解析。
CALL_PAIRS: frozenset[tuple[str, str | None]] = frozenset(
    {
        ("response_item", "function_call"),
        ("response_item", "custom_tool_call"),
    }
)
OUTPUT_PAIRS: frozenset[tuple[str, str | None]] = frozenset(
    {
        ("response_item", "function_call_output"),
        ("response_item", "custom_tool_call_output"),
    }
)

# 工具输入里承载 shell 命令的键（实测 exec_command 的 arguments 含 cmd 21 次）。
COMMAND_KEYS: tuple[str, ...] = ("cmd", "command")
# apply_patch 的 `input` 是补丁文本，路径只出现在 `*** <Keyword>: <path>` 标记行上。
PATCH_MARKER_PREFIX = "*** "
PATCH_PATH_KEYWORDS: frozenset[str] = frozenset(
    {
        "Add File",
        "Update File",
        "Delete File",
    }
)

# Claude 信封键：Codex 记录恒不带（实测 0/138），出现即正面判为外来宿主。
FOREIGN_MARKER_KEYS: frozenset[str] = frozenset(
    {
        "uuid",
        "parentUuid",
        "leafUuid",
        "sessionId",
        "isSidechain",
        "userType",
    }
)

REASON_MAX_LEN = 40


class LineDisposition(StrEnum):
    """单行去向，与 Claude 侧同名同义（跨宿主统计必须可合并）。"""

    PARSED = "parsed"
    IGNORED = "ignored"
    UNPARSED = "unparsed"
    NOT_OURS = "not_ours"
    MALFORMED = "malformed"


def safe_reason(raw: object) -> str:
    """把宿主可控字符串压成安全 token：reasons 的键会进报告，不得携带路径或任意长文本。"""
    text = raw if isinstance(raw, str) else type(raw).__name__
    cleaned = "".join(char if char.isalnum() or char in "._-" else "_" for char in text)
    cleaned = cleaned.strip("_")[:REASON_MAX_LEN]
    return cleaned or "unnamed"


def classify_record(record: Mapping[str, object]) -> tuple[LineDisposition, str]:
    """判定一行该走哪条路，reason 为机器可读 token。"""
    if any(key in record for key in FOREIGN_MARKER_KEYS):
        return LineDisposition.NOT_OURS, "not_codex_session"
    outer = record.get("type")
    if not isinstance(outer, str) or not outer:
        return LineDisposition.MALFORMED, "missing_type"
    if outer not in OUTER_TYPES:
        return LineDisposition.UNPARSED, safe_reason(outer)
    if outer in IGNORED_OUTER:
        return LineDisposition.IGNORED, safe_reason(outer)
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        return LineDisposition.MALFORMED, "missing_payload"
    inner = payload.get("type")
    inner_name = inner if isinstance(inner, str) else ""
    pair = (outer, inner_name or None)
    if pair in LIFECYCLE_PAIRS:
        return LineDisposition.PARSED, "lifecycle"
    if pair in DUPLICATE_PAIRS:
        return LineDisposition.IGNORED, "duplicate_of_response_item"
    if pair in IGNORED_PAIRS:
        return LineDisposition.IGNORED, safe_reason(inner_name)
    if pair in CALL_PAIRS or pair in OUTPUT_PAIRS:
        return LineDisposition.PARSED, safe_reason(inner_name)
    if pair == ("response_item", "message"):
        return LineDisposition.PARSED, "message"
    return LineDisposition.UNPARSED, safe_reason(f"{outer}_{inner_name}")


def message_kind(payload: Mapping[str, object]) -> tuple[EventKind | None, str]:
    """`response_item/message` 按 role 决定 kind；developer 不产事件。"""
    role = payload.get("role")
    if not isinstance(role, str) or not role:
        return None, "missing_role"
    if role not in MESSAGE_ROLES:
        return None, f"role_{safe_reason(role)}"
    kind = MESSAGE_ROLES[role]
    return (kind, "") if kind is not None else (None, "role_developer")


def parse_arguments(raw: object) -> tuple[Mapping[str, object] | None, str | None]:
    """`arguments` 实测是 JSON 字符串：解不开就只丢字段，不弃整行。

    返回 (参数字典或 None, 字段级 reason)。reason 不改动五个行级计数器——
    行本身仍产出了合法 tool_call，与 Claude 侧 `outside_workspace` 同一口径。
    """
    if isinstance(raw, Mapping):
        return raw, None
    if not isinstance(raw, str) or not raw.strip():
        return None, "arguments_unparsable"
    try:
        decoded = json.loads(raw)
    except ValueError:
        return None, "arguments_unparsable"
    if not isinstance(decoded, Mapping):
        return None, "arguments_not_object"
    return decoded, None


def command_from(arguments: Mapping[str, object] | None) -> str | None:
    if not arguments:
        return None
    for key in COMMAND_KEYS:
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def paths_from_patch(text: object) -> list[str]:
    """从 apply_patch 文本里取 `*** Add File: <path>` 等标记行的路径。

    实测 1 例（`markers=1`，keyword `Add File`）。只认这三个关键字，其余行（含上下文
    diff 正文）一律不解析——不猜未观测过的形状。
    """
    if not isinstance(text, str):
        return []
    found: list[str] = []
    for line in text.splitlines():
        if not line.startswith(PATCH_MARKER_PREFIX):
            continue
        keyword, sep, rest = line[len(PATCH_MARKER_PREFIX) :].partition(":")
        if not sep or keyword.strip() not in PATCH_PATH_KEYWORDS:
            continue
        path = rest.strip()
        if path:
            found.append(path)
    return found


def workdir_from(arguments: Mapping[str, object] | None) -> str | None:
    if not arguments:
        return None
    value = arguments.get("workdir")
    return value if isinstance(value, str) and value else None
