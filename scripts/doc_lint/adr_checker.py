"""ADR 编号连续性与模板 v2 必需字段检查。

规则（对齐 docs/adr/README.md 模板 v2 与 ADR-0009/0011）：
- 编号从 0001 起、四位数字、无跳号；
- 0001–0008 属模板 v1 历史遗留，只要求：状态、日期、`## 背景`、`## 决定`、`## 影响`；
- 0009+ 严格执行模板 v2：状态、日期、Related、`## 背景`、`## 决定`、`## 影响`、`## 被否备选`；
- 状态字段合法值：``Accepted`` / ``Proposed`` / ``Superseded by NNNN``（大小写宽松）。
"""

from __future__ import annotations

import re
from pathlib import Path

from ._core import Finding

_ADR_FILE_RE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
# 兼容两种头部形式：`状态: xxx`（行首）与 `日期: ... | 状态: xxx`（管道分隔）
_STATUS_RE = re.compile(r"(?:^|[|｜])\s*状态[:：]\s*([^|｜\n]+)", re.MULTILINE)
_VALID_STATUS_RE = re.compile(
    r"^(accepted|proposed|superseded by \d{4})$",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"(日期|更新|Date|Updated)\s*[:|]\s*\d{4}-\d{2}-\d{2}")
_RELATED_RE = re.compile(r"^Related\s*:", re.MULTILINE)
_REQUIRED_SECTIONS_V1 = ("## 背景", "## 决定", "## 影响")
_REQUIRED_SECTIONS_V2 = _REQUIRED_SECTIONS_V1 + ("## 被否备选",)
_TEMPLATE_V2_START = 9  # 自 ADR-0009 起强制 v2 模板

_README_NAME = "README.md"


def _adr_files(adr_dir: Path) -> list[Path]:
    if not adr_dir.is_dir():
        return []
    return sorted(p for p in adr_dir.iterdir() if p.is_file() and p.name != _README_NAME)


def check(repo_root: Path) -> list[Finding]:
    adr_dir = repo_root / "docs" / "adr"
    files = _adr_files(adr_dir)
    if not files:
        return []

    findings: list[Finding] = []
    numbers: list[int] = []

    for path in files:
        match = _ADR_FILE_RE.match(path.name)
        if not match:
            findings.append(
                Finding(
                    path=path,
                    rule="adr.filename",
                    line=None,
                    message=f"ADR 文件名不符合 NNNN-<kebab-title>.md 规范: {path.name}",
                    hint="示例: 0011-doc-language-and-standards.md",
                )
            )
            continue
        num = int(match.group(1))
        numbers.append(num)

        body = path.read_text(encoding="utf-8")
        head = "\n".join(body.splitlines()[:15])  # 头部窗口，用于状态/日期/Related

        status_match = _STATUS_RE.search(head)
        if not status_match:
            findings.append(
                Finding(
                    path=path,
                    rule="adr.missing_status",
                    line=None,
                    message="头部 15 行内未找到 `状态:` 字段",
                )
            )
        else:
            status_value = status_match.group(1).strip().rstrip("。.")
            if not _VALID_STATUS_RE.match(status_value):
                findings.append(
                    Finding(
                        path=path,
                        rule="adr.bad_status",
                        line=None,
                        message=(
                            f"非法状态值: `{status_value}`；"
                            "允许: Accepted / Proposed / Superseded by NNNN"
                        ),
                    )
                )

        if not _DATE_RE.search(head):
            findings.append(
                Finding(
                    path=path,
                    rule="adr.missing_date",
                    line=None,
                    message="头部未找到 `日期: YYYY-MM-DD` 或 `更新: YYYY-MM-DD`",
                )
            )

        required = _REQUIRED_SECTIONS_V2 if num >= _TEMPLATE_V2_START else _REQUIRED_SECTIONS_V1
        for section in required:
            if section not in body:
                findings.append(
                    Finding(
                        path=path,
                        rule="adr.missing_section",
                        line=None,
                        message=(
                            f"缺少必需段落 `{section}`（模板 "
                            f"{'v2' if num >= _TEMPLATE_V2_START else 'v1'}）"
                        ),
                    )
                )

        if num >= _TEMPLATE_V2_START and not _RELATED_RE.search(head):
            findings.append(
                Finding(
                    path=path,
                    rule="adr.missing_related",
                    line=None,
                    message="ADR-0009+ 头部必须含 `Related:` 字段指向相关 ADR/spec/任务号",
                )
            )

    # 编号连续性：0001 起、无跳号
    if numbers:
        numbers_sorted = sorted(numbers)
        if numbers_sorted[0] != 1:
            findings.append(
                Finding(
                    path=adr_dir / _README_NAME,
                    rule="adr.numbering_start",
                    line=None,
                    message=f"最小 ADR 编号应为 0001，实际: {numbers_sorted[0]:04d}",
                )
            )
        # 两序列长度天然差 1，strict=True 会抛 ValueError（那就不是纯风格改动了）
        for prev, curr in zip(numbers_sorted, numbers_sorted[1:], strict=False):
            if curr != prev + 1:
                findings.append(
                    Finding(
                        path=adr_dir / f"{curr:04d}-*.md",
                        rule="adr.numbering_gap",
                        line=None,
                        message=f"ADR 编号跳号: {prev:04d} → {curr:04d}（缺失 {prev + 1:04d}）",
                        hint="确认是否有 ADR 未落盘或错编号",
                    )
                )
    return findings
