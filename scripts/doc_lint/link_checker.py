"""相对链接可解析性检查（``.md`` 内部 ``[text](relative/path.md#anchor)``）。

规则：
- 跳过 ``http(s)://``、``mailto:``、``#anchor`` 与内联代码/围栏内的伪链接；
- 目标文件必须存在；
- 锚点 ``#heading-slug`` 校验：GitHub 风格 slug 化后必须匹配目标文件的某个标题。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from ._core import Finding, iter_markdown_docs, strip_code

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)


def _iter_links(stripped_text: str) -> Iterator[tuple[int, str, str]]:
    """在已剥离代码的文本上产出 ``(line_no, text, target)``。"""
    for lineno, line in enumerate(stripped_text.splitlines(), start=1):
        for match in _LINK_RE.finditer(line):
            yield lineno, match.group(1), match.group(2)


def _slugify(heading: str) -> str:
    """GitHub anchor slug：小写、空格→连字符、剥掉非 ``[\\w\\s\\u4e00-\\u9fff-]``。"""
    lowered = heading.strip().lower()
    no_marks = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", lowered)
    return re.sub(r"\s+", "-", no_marks).strip("-")


def _collect_anchors(md_text: str) -> set[str]:
    """从**原文**（不剥代码）提取标题的锚点集合；标题不会出现在代码块内。"""
    return {_slugify(m.group(2)) for m in _HEADING_RE.finditer(md_text)}


def _is_external(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:", "ftp://", "//"))


def check(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    anchor_cache: dict[Path, set[str]] = {}
    for doc in iter_markdown_docs(repo_root):
        raw = doc.read_text(encoding="utf-8")
        stripped = strip_code(raw)
        for lineno, _text, target in _iter_links(stripped):
            if _is_external(target) or target.startswith("#"):
                continue
            file_part, _, anchor = target.partition("#")
            if not file_part:
                continue
            file_part_norm = file_part.replace("\\", "/")
            resolved = (doc.parent / file_part_norm).resolve()
            try:
                rel = resolved.relative_to(repo_root.resolve())
            except ValueError:
                findings.append(
                    Finding(
                        path=doc,
                        rule="link.outside_repo",
                        line=lineno,
                        message=f"链接目标跳出仓库: {target}",
                        hint="使用仓库内相对路径或 http(s) 外链",
                    )
                )
                continue
            if not resolved.exists():
                findings.append(
                    Finding(
                        path=doc,
                        rule="link.broken",
                        line=lineno,
                        message=f"链接目标不存在: {rel.as_posix()}",
                        hint="确认路径拼写；若文件已改名请同步更新本链接",
                    )
                )
                continue
            if anchor and resolved.suffix == ".md":
                if resolved not in anchor_cache:
                    anchor_cache[resolved] = _collect_anchors(
                        resolved.read_text(encoding="utf-8")
                    )
                anchors = anchor_cache[resolved]
                if anchor.lower() not in anchors:
                    findings.append(
                        Finding(
                            path=doc,
                            rule="link.anchor_missing",
                            line=lineno,
                            message=(
                                f"锚点 #{anchor} 在 {rel.as_posix()} 中未找到对应标题；"
                                f"可用锚点样本: {sorted(anchors)[:5]}"
                            ),
                            hint="校对标题文字；GitHub 锚点为 slug 化（小写、空格→-）",
                        )
                    )
    return findings
