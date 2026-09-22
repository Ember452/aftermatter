"""L0 契约模型：证据引用、原始事件与采集侧类型（data-model §0.1/§1/§1.1 的化身）。

本模块是依赖方向的例外：它按 L0 参与判定（见 overview §3），因为所有层都需要这里的
模型。字段语义只在 data-model.md 定义，此处不复述。
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 完整宽度 sha256 的十六进制表示。core.fingerprint 只交付 16 位去重指纹，
# 引用闸要的是可比对的全文哈希（core.md：core 不发明第二套宽度）。
SHA256_HEX_PATTERN = r"^[0-9a-f]{64}$"
# 证据源根的稳定别名（data-model §0.1）：跨边界数据只出现它，不出现源根路径。
SOURCE_ID_PATTERN = r"^[0-9a-f]{12}$"


def _has_drive_prefix(value: str) -> bool:
    """`C:/x` 或 `c:\\x` 这类盘符开头——它不是相对路径，而是主机绝对路径。"""
    return len(value) >= 2 and value[1] == ":" and value[0].isalpha()


def _require_source_relative(value: str) -> str:
    """跨边界数据里不允许出现主机绝对路径、反斜杠或上跳段。

    这是隐私红线的结构化表达：`ERef.source_path` 是相对其 `source_id` 所指源根的 posix 串
    （`core.norm_path` 的输出形态），真实路径必须在进入模型之前就被归一，不靠调用方自觉。
    实测会漏的一类是盘符绝对路径（`C:/repo/...`）：它既不以 `/` 开头也不含反斜杠（当写法
    为 posix 分隔时），必须单独拒——否则真实主机路径会直接跟进报告。
    """
    if not value:
        raise ValueError("path must be a non-empty repo-relative posix path")
    if value.startswith("/") or "\\" in value or _has_drive_prefix(value):
        raise ValueError("path must be repo-relative, not absolute or backslash-separated")
    if ".." in value.split("/"):
        raise ValueError("path must not contain parent-directory segments")
    return value


class ERef(BaseModel):
    """指向原始字节的区间引用。"""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(pattern=SOURCE_ID_PATTERN)
    source_path: str
    byte_start: int = Field(ge=0)
    byte_len: int = Field(gt=0)
    digest: str = Field(pattern=SHA256_HEX_PATTERN)
    line_no: int | None = Field(default=None, ge=1)

    @field_validator("source_path")
    @classmethod
    def _validate_source_path(cls, value: str) -> str:
        return _require_source_relative(value)


class SourceEntry(BaseModel):
    """`IntegrityManifest` 的条目形状；容器与构建流程属 T1.8。"""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(pattern=SOURCE_ID_PATTERN)
    path: str
    sha256: str = Field(pattern=SHA256_HEX_PATTERN)
    size: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        return _require_source_relative(value)


HostId = Literal["claude", "codex", "cursor", "qoder"]


class EventKind(StrEnum):
    """data-model §1 的七种 kind；未知行不在此枚举内，走 `ParseStats.unparsed`。"""

    USER_PROMPT = "user_prompt"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PERMISSION_DECISION = "permission_decision"
    HOOK_EVENT = "hook_event"
    LIFECYCLE = "lifecycle"


class RawEvent(BaseModel):
    """L0 归一化事件（适配器唯一产出）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: HostId
    session_id: str
    seq: int = Field(ge=1)
    ts: datetime
    kind: EventKind
    cwd: str
    evidence_ref: ERef
    fingerprint: str = Field(pattern=r"^[0-9a-f]{16}$")
    tool_name: str | None = None
    target_paths: tuple[str, ...] = ()
    command_text: str | None = None
    model: str | None = None
    permission: Literal["routine", "prompted", "denied", "blocked"] | None = None
    result_ok: bool | None = None


class SessionRef(BaseModel):
    """一个宿主会话文件；`path` 仅本机有效，出机数据一律用 `source_id`。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: HostId
    source_id: str = Field(pattern=SOURCE_ID_PATTERN)
    path: str
    size: int = Field(ge=0)
    content_hash: str = Field(pattern=SHA256_HEX_PATTERN)
    format_version: str | None = None


class AdapterHealth(BaseModel):
    """探测到的宿主版本是否在支持矩阵内。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: HostId
    support: Literal["ok", "unknown", "degraded"]
    detected_versions: tuple[str, ...] = ()


class ParseStats(BaseModel):
    """行级去向。`ignored` 与 `unparsed` 不得合并（后者才是格式漂移信号）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lines_total: int = Field(ge=0)
    parsed: int = Field(ge=0)
    ignored: int = Field(ge=0)
    unparsed: int = Field(ge=0)
    not_ours: int = Field(ge=0)
    malformed_json: int = Field(ge=0)
    excluded_self_artifact: int = Field(ge=0)
    outside_path_count: int = Field(ge=0)
    reasons: Mapping[str, int] = Field(default_factory=dict)


def source_id_for(host: str, source_root: str) -> str:
    """按 data-model §0.1 派生源标识：输出永不包含路径。

    先剥 HOME 前缀再哈希，是为了让同一目录结构在不同用户名下得到同一个 id——
    否则纵向比较（T4.4）会在换机器时整片断链。
    """
    normalized = source_root.replace("\\", "/")
    home = os.path.expanduser("~").replace("\\", "/")
    if home and home != "~" and (normalized == home or normalized.startswith(f"{home}/")):
        normalized = f"~{normalized[len(home) :]}"
    return hashlib.sha256(f"{host}\0{normalized}".encode()).hexdigest()[:12]
