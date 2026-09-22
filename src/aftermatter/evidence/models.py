"""L0 契约模型：证据引用与证据源条目（`data-model.md` §0.1 的一比一化身）。

本模块是依赖方向的例外：它按 L0 参与判定（见 overview §3），因为所有层都需要这里的
模型。字段语义只在 data-model.md 定义，此处不复述。
"""

from __future__ import annotations

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
