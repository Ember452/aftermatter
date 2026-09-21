"""architecture/INDEX.md 与实际模块设计文件的一致性检查。

规则：
- INDEX.md 中列出的每篇文档必须存在；
- docs/architecture/ 下除 INDEX.md 外的每篇 .md 必须被 INDEX.md 列出（避免"失踪文件"）；
- 契约三件套（overview.md / data-model.md / modules.md）与 12 篇模块设计篇均一视同仁。
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import Finding

_LINK_RE = re.compile(r"\[([^\]]+\.md)\]\(([^)]+\.md)\)")


def _listed_targets(index_path: Path, architecture_dir: Path) -> set[str]:
    text = index_path.read_text(encoding="utf-8")
    targets: set[str] = set()
    for _, href in _LINK_RE.findall(text):
        # INDEX.md 里的链接都是同目录或 ../ 相对，本目录直接取 basename 即可
        clean = href.split("#", 1)[0]
        if not clean.endswith(".md"):
            continue
        targets.add(Path(clean).name)
    # 相对路径解析对齐 architecture_dir；basename 已足够定位本目录文档
    _ = architecture_dir
    return targets


def check(repo_root: Path) -> list[Finding]:
    arch_dir = repo_root / "docs" / "architecture"
    index_path = arch_dir / "INDEX.md"
    if not arch_dir.is_dir():
        return []
    if not index_path.is_file():
        return [
            Finding(
                path=arch_dir,
                rule="index.missing_index",
                line=None,
                message="docs/architecture/ 缺少 INDEX.md",
            )
        ]

    findings: list[Finding] = []
    listed = _listed_targets(index_path, arch_dir)

    # 1. INDEX 声明的文件必须存在
    for name in sorted(listed):
        target = arch_dir / name
        if not target.is_file():
            findings.append(
                Finding(
                    path=index_path,
                    rule="index.dangling_entry",
                    line=None,
                    message=f"INDEX.md 声明的文档不存在: architecture/{name}",
                )
            )

    # 2. 目录下 .md 文件（除 INDEX.md）必须被 INDEX 列出
    for path in sorted(arch_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        if path.name not in listed:
            findings.append(
                Finding(
                    path=index_path,
                    rule="index.unlisted_file",
                    line=None,
                    message=f"architecture/{path.name} 未在 INDEX.md 登记",
                    hint="在 INDEX.md 对应表格补一行；契约三件套在上表，模块设计在下表",
                )
            )
    return findings
