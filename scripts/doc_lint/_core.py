"""共享类型与遍历工具：Breaking 潜在 ``__init__ ↔ checker`` 循环 import。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

_SKIP_PARTS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    }
)


@dataclass(frozen=True)
class Finding:
    """单条违规。``rule`` 用于 CI 分类，``hint`` 提供修复建议。"""

    path: Path
    rule: str
    line: int | None
    message: str
    hint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "rule": self.rule,
            "line": self.line,
            "message": self.message,
            "hint": self.hint,
        }


def iter_markdown_docs(repo_root: Path) -> Iterator[Path]:
    """产出需要被 lint 的全部 .md：docs/**、根 AGENTS.md/CLAUDE.md。"""
    for name in ("AGENTS.md", "CLAUDE.md"):
        candidate = repo_root / name
        if candidate.is_file():
            yield candidate
    docs = repo_root / "docs"
    if not docs.is_dir():
        return
    for path in docs.rglob("*.md"):
        if any(part in _SKIP_PARTS for part in path.parts):
            continue
        yield path


_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_INLINE_CODE_RE = re.compile(r"(`+)(?:[^`]|(?!\1)`)*?\1")


def strip_code(text: str) -> str:
    """把代码围栏与内联代码内容替换为空格，保持行数与列数不变，方便 checker
    按位置匹配而不误伤示例。围栏标记行本身也替换为等长空格。
    """
    out_lines: list[str] = []
    inside_fence = False
    for raw in text.splitlines():
        if _FENCE_RE.match(raw):
            inside_fence = not inside_fence
            out_lines.append(" " * len(raw))
            continue
        if inside_fence:
            out_lines.append(" " * len(raw))
            continue
        # 替换内联代码；保留长度
        out_lines.append(_INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), raw))
    return "\n".join(out_lines)


__all__ = ["Finding", "iter_markdown_docs", "strip_code"]
