"""引用闸：把 ERef 解析回原始字节并与入册内容比对（`evidence.md` §verify_ref）。

只读操作，永不修复、永不写回。核验失败是**返回值**不是异常——引用失败必须能进报告
`rejected` 附录被审计，抛出去会被上层吞成一次静默丢弃。
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path

from aftermatter.evidence.models import ERef, SourceEntry


class VerifyOutcome(StrEnum):
    """四态结论，语义见 data-model.md §0.1。"""

    OK = "ok"
    NOT_FOUND = "not_found"
    HASH_MISMATCH = "hash_mismatch"
    OUT_OF_MANIFEST = "out_of_manifest"


def _entry_for(
    entries: Sequence[SourceEntry], source_id: str, source_path: str
) -> SourceEntry | None:
    """按 (源标识, 源根相对路径) 查条目；两侧路径都是 `norm_path` 输出，精确串比较即可。"""
    for entry in entries:
        if entry.source_id == source_id and entry.path == source_path:
            return entry
    return None


def verify_ref(
    eref: ERef,
    entries: Sequence[SourceEntry],
    *,
    roots: Mapping[str, str | Path],
) -> VerifyOutcome:
    """核验一条引用。

    `roots` 是 `source_id -> 源根目录` 的映射，由本机 run 上下文提供（主机路径不进模型）；
    `eref.source_path` 与 `entry.path` 都是相对各自源根的 posix 串。
    符号链接逃逸不在本层判定：`core.norm_path` 是纯字符串归一（三平台一致性优先），
    真实的容器/沙箱边界属 T5.8 对抗线，这里不偷偷引入 `realpath` 语义。
    """
    root = roots.get(eref.source_id)
    if root is None:
        return VerifyOutcome.OUT_OF_MANIFEST
    entry = _entry_for(entries, eref.source_id, eref.source_path)
    if entry is None:
        return VerifyOutcome.OUT_OF_MANIFEST

    path = Path(root) / eref.source_path
    try:
        raw = path.read_bytes()
    except OSError:
        # 不带异常文本：OSError 的 message 含主机绝对路径。
        return VerifyOutcome.NOT_FOUND

    if len(raw) != entry.size or hashlib.sha256(raw).hexdigest() != entry.sha256:
        return VerifyOutcome.HASH_MISMATCH

    end = eref.byte_start + eref.byte_len
    if end > len(raw):
        return VerifyOutcome.NOT_FOUND
    if hashlib.sha256(raw[eref.byte_start : end]).hexdigest() != eref.digest:
        return VerifyOutcome.HASH_MISMATCH
    return VerifyOutcome.OK
