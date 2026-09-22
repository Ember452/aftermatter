"""AfterMatter — harness engineering, with evidence.

Evidence-based review of AI coding agent workflows: read agent sessions and repository
evidence, emit findings whose every assertion resolves back to original bytes, and only
claim improvement when bounded repairs survive longitudinal validation.

设计文档见仓库 `docs/`（内部设计中文、门面文档英文，分层规则见 ADR-0011）；
分层与依赖方向硬规则见 `docs/architecture/overview.md` 的「§3 分层与依赖方向」，
由 `tests/architecture/test_import_direction.py` 强制。

包级公共 API 目前只有版本号；各子包的 `__init__` 导出随 M1 起有代码时增量加入
（REPO-LAYOUT「未用先建」反模式）。
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
