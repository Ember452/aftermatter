"""防自污染清单（跨宿主共用）：AfterMatter 自己的产物不能被当成宿主证据。

放在 collectors 顶层共享模块而不是某个宿主子包里，是因为宿主子包之间禁止互相 import
（守卫规则④）；每家宿主都要用同一份清单，抄两份必然漂移。
"""

from __future__ import annotations

SELF_ARTIFACT_MARKERS: tuple[str, ...] = (".aftermatter/", ".aftermatter\\")


def is_self_artifact(path: str) -> bool:
    """路径是否指向 AfterMatter 自己的产物（运行目录、报告、台账导出）。"""
    return any(marker in path for marker in SELF_ARTIFACT_MARKERS)
