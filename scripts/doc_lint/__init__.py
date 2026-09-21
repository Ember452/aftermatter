"""AfterMatter 文档一致性检查（ADR-0011）。

对外暴露 :class:`Finding`、:func:`check_all` 与 :func:`iter_markdown_docs`；
CLI 由 :mod:`doc_lint.cli` 消费。本包属于 ``scripts/`` 层，不引入产品依赖，
也不被 ``src/`` import。

checkers 在 :func:`check_all` 内部按需 import，避免与 :mod:`doc_lint._core` 形成
``__init__ ↔ checker`` 循环。
"""

from __future__ import annotations

from pathlib import Path

from ._core import Finding, iter_markdown_docs

__all__ = ["Finding", "check_all", "iter_markdown_docs"]


def check_all(repo_root: Path) -> list[Finding]:
    """跑全部检查器，返回汇总的违规清单（不排序，调用方按需排序）。"""
    # 局部 import：checkers 依赖 _core.Finding，不在包初始化期解析
    from . import adr_checker, index_checker, link_checker, metadata_checker, policy_checker

    findings: list[Finding] = []
    for checker in (
        link_checker.check,
        adr_checker.check,
        index_checker.check,
        metadata_checker.check,
        policy_checker.check,
    ):
        findings.extend(checker(repo_root))
    return findings
