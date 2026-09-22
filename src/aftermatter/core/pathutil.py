"""路径归一：纯字符串操作，输出仓库相对 posix 路径（契约见 docs/architecture/core.md）。"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from aftermatter.core.errors import ContractViolation, PathOutsideWorkspace

_CURRENT_DIR_MARKER = "."


def _style(windows: bool) -> str:
    """异常 context 用的风格标记（只写枚举，不写路径）。"""
    return "win" if windows else "posix"


def _drive(text: str) -> str:
    """`C:/x` → `c:`；非盘符输入返回空串（盘符统一小写）。"""
    if len(text) >= 2 and text[1] == ":" and text[0].isalpha():
        return text[0].lower() + ":"
    return ""


def _looks_windows(text: str) -> bool:
    """按**输入串自身的特征**判定风格，而不是按运行主机：三平台 CI 必须对同一输入
    得到同一结果，否则指纹会随平台漂移。"""
    return "\\" in text or bool(_drive(text)) or text.startswith("\\\\")


def _expand_user(text: str, *, windows: bool) -> str:
    if text != "~" and not text.startswith(("~/", "~\\")):
        return text
    home = os.environ.get("USERPROFILE") if windows else os.environ.get("HOME")
    if not home:
        raise ContractViolation("path_home_unknown", context={"style": _style(windows)})
    return home + text[1:]


def _split(text: str, *, windows: bool) -> tuple[str, list[str]]:
    """拆成 (root_key, 原始段)。root_key 是盘符 / UNC 前缀 / posix 的 `/` / 空串（相对）。"""
    normalized = text.replace("\\", "/") if windows else text
    raw: list[str]
    if windows and normalized.startswith("//"):
        parts = normalized[2:].split("/")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ContractViolation("path_malformed_unc", context={"depth": len(parts)})
        # 主机名与共享名按 Windows 语义大小写不敏感；共享下的段保留原样。
        root_key = f"//{parts[0].lower()}/{parts[1].lower()}"
        raw = parts[2:]
    elif windows and _drive(normalized):
        root_key = _drive(normalized)
        raw = normalized[2:].split("/")
    else:
        root_key = "/" if normalized.startswith("/") else ""
        raw = normalized.split("/")
    return root_key, [segment for segment in raw if segment not in ("", _CURRENT_DIR_MARKER)]


def _collapse(segments: Sequence[str]) -> list[str]:
    """折叠 `..`（纯词汇，不跟随 symlink）。

    多余的 `..` 原样留在结果里：它必然与前缀比较失败，由包含性判定统一拒绝，
    因此不需要额外的"越界层数"状态。
    """
    out: list[str] = []
    for segment in segments:
        if segment == "..":
            if out:
                out.pop()
            else:
                out.append(segment)
        else:
            out.append(segment)
    return out


def _same(first: str, second: str, *, windows: bool) -> bool:
    return first.casefold() == second.casefold() if windows else first == second


def norm_path(p: str | Path, root: str | Path) -> str:
    """把 `p` 归一为相对 `root` 的 posix 路径；越出 `root` 抛 PathOutsideWorkspace。

    全程不碰文件系统：`resolve()` 会 stat/symlink 且结果随主机变化，既违反事件循环
    内不阻塞的纪律，也会让同一输入在不同平台产生不同指纹。
    相对输入按 workspace 相对处理——采集层同时存在绝对路径与仓库相对路径两种来源，
    归一必须给同一结果。root 自身返回 `"."`（对齐 git 约定）。
    """
    root_text = os.fspath(root)
    p_text = os.fspath(p)
    if not root_text:
        raise ContractViolation("path_root_not_absolute", context={"length": len(root_text)})
    if not p_text:
        raise ContractViolation("path_empty", context={"length": len(p_text)})

    windows = _looks_windows(root_text)
    root_key, root_segments = _split(root_text, windows=windows)
    if not root_key:
        raise ContractViolation("path_root_not_absolute", context={"style": _style(windows)})
    root_segments = _collapse(root_segments)

    p_windows = _looks_windows(p_text)
    expanded = _expand_user(p_text, windows=p_windows)
    p_key, p_segments = _split(expanded, windows=p_windows)
    if not p_key and p_segments:
        p_key, p_segments = root_key, [*root_segments, *p_segments]
    p_segments = _collapse(p_segments)

    if p_key != root_key:
        raise PathOutsideWorkspace("path_outside_root", context={"depth": len(p_segments)})
    if len(p_segments) < len(root_segments) or not all(
        _same(a, b, windows=windows) for a, b in zip(root_segments, p_segments, strict=False)
    ):
        raise PathOutsideWorkspace("path_outside_root", context={"depth": len(p_segments)})
    return "/".join(p_segments[len(root_segments) :]) or _CURRENT_DIR_MARKER
