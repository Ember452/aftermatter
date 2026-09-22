"""文档头部元数据存在性检查。

规则（对齐 ADR-0011 §决定 3）：
- 每篇 .md（除豁免清单）在头部 12 行内必须含 `状态:` 字段（允许行首或 ` | 状态:` 形式）；
- 日期字段（`日期:` 或 `更新:`）为**推荐但非硬约束**（当前 12 篇模块设计文档尚未
  添加，加进 CI 会造成大面积红灯；随实现推进逐步补齐时再打开硬约束）；
- 豁免：任何目录导航 `README.md`、`docs/architecture/INDEX.md`（同为导航型）、
  `docs/adr/**`（由 adr_checker 独立覆盖）、`docs/specs/**`（专题设计件，头部形式
  灵活）；`docs/development/**`、`docs/tests/**`、`docs/benchmarks/**`、
  `docs/api/**` 属"占位 README + 未来实测文档"，仅 README 存在，其他文档不存在
  时无需检查。
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import Finding, iter_markdown_docs

# 兼容行首与 ` | 状态:` 管道分隔两种写法；支持全角冒号；
# 接受中文（默认内部文档）与英文 Status（镜像与未来用户向）。
_STATUS_RE = re.compile(r"(?:^|[|｜])\s*(?:状态|Status)\s*[:：]", re.MULTILINE | re.IGNORECASE)

_README_NAME = "README.md"
_EXEMPT_BASENAMES = {"README.md", "INDEX.md"}
_EXEMPT_SUBDIRS = ("adr", "specs")


def _is_exempt(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root)
    parts = rel.parts
    if path.name in _EXEMPT_BASENAMES:
        return True
    # docs/adr/*.md 与 docs/specs/*.md 由各自专属 checker 处理
    return len(parts) >= 2 and parts[0] == "docs" and parts[1] in _EXEMPT_SUBDIRS


def check(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for doc in iter_markdown_docs(repo_root):
        if _is_exempt(doc, repo_root):
            continue
        text = doc.read_text(encoding="utf-8")
        head = "\n".join(text.splitlines()[:12])
        if not _STATUS_RE.search(head):
            findings.append(
                Finding(
                    path=doc,
                    rule="metadata.missing_status",
                    line=None,
                    message=(
                        "头部 12 行内未找到 `状态:` 字段"
                        "（Draft/Proposed/Accepted/定稿/草稿/Superseded by NNNN）"
                    ),
                    hint=(
                        "在标题下第二行加：`状态: <值> | 日期/更新: YYYY-MM-DD | 对应/关联: <链接>`"
                    ),
                )
            )
    return findings
