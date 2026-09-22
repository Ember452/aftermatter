"""evidence 契约层：跨层数据模型的唯一定义处 + 引用闸（T1.2 起）。

依赖方向的例外只认 `aftermatter.evidence.models` 这一条子路径（overview §3、evidence.md），
因此采集层必须写 `from aftermatter.evidence.models import ERef`，不能从本包的公共出口拿——
从 `aftermatter.evidence` 导入会连带把 `integrity`（L1 的引用闸）拉进采集层，守卫会拒绝。
"""

from __future__ import annotations

from aftermatter.evidence.integrity import VerifyOutcome, verify_ref
from aftermatter.evidence.models import ERef, SourceEntry

__all__ = ["ERef", "SourceEntry", "VerifyOutcome", "verify_ref"]
