"""collectors：宿主会话与仓库证据 → L0 事实。

这里只导出跨宿主公共符号；宿主实现（`ClaudeAdapter` 等）从各宿主子包自己的出口取，
避免公共出口把一个具体宿主变成所有调用方的隐式依赖。
"""

from __future__ import annotations

from aftermatter.collectors.protocol import ParseTally, SessionAdapter

__all__ = ["ParseTally", "SessionAdapter"]
