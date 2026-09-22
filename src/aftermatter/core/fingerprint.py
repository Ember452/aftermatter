"""稳定指纹：canonical JSON → sha256 前 16 位（契约见 docs/architecture/core.md）。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from aftermatter.core.errors import ContractViolation

# 契约宽度（core.md）：跨 bundle 的唯一性由各模型的 id 字段负责，这里只做去重指纹。
FINGERPRINT_HEX_WIDTH = 16


@runtime_checkable
class _HasModelDump(Protocol):
    """结构化识别 pydantic 模型。

    core 只允许依赖标准库（modules §1），所以不 import pydantic：任何提供
    `model_dump(mode="json")` 的对象都按模型处理，测试用桩类即可覆盖该分支。
    """

    def model_dump(self, **kwargs: Any) -> dict[str, Any]: ...


def _to_jsonable(obj: object) -> object:
    if isinstance(obj, str | bytes | bool | int | float) or obj is None:
        return obj
    if isinstance(obj, _HasModelDump):
        return _to_jsonable(obj.model_dump(mode="json"))
    if isinstance(obj, Mapping):
        items: dict[str, object] = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                # 强转非 str 键会让 {1: 'a'} 与 {'1': 'a'} 撞成同一指纹，宁可拒绝。
                raise ContractViolation(
                    "fingerprint_non_str_key", context={"type": type(key).__name__}
                )
            items[key] = _to_jsonable(value)
        return items
    if isinstance(obj, Sequence):
        return [_to_jsonable(item) for item in obj]
    raise ContractViolation("fingerprint_unserializable", context={"type": type(obj).__name__})


def _canonical_json(obj: object) -> str:
    try:
        return json.dumps(
            _to_jsonable(obj),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        # 断开异常链：序列化错误文本会携带取值，异常可能进日志与报告。
        raise ContractViolation(
            "fingerprint_unserializable", context={"reason": type(exc).__name__}
        ) from None


def fingerprint(obj: object) -> str:
    """返回对象的稳定指纹（16 位小写十六进制）。

    键序无关、跨进程稳定（canonical JSON 不依赖 hash 序）；`set`/`frozenset` 的迭代
    顺序由哈希决定，属不可序列化输入被显式拒绝——契约模型一律用 tuple。
    """
    if isinstance(obj, bytes):
        payload = obj
    elif isinstance(obj, str):
        payload = obj.encode("utf-8")
    else:
        payload = _canonical_json(obj).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:FINGERPRINT_HEX_WIDTH]
