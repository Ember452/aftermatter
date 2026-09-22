# Claude 适配器黄金 fixture

来源：**全部合成**，不含任何真实用户会话（REPO-LAYOUT §3、AGENTS §4.3 第 4 条）。
结构依据 2026-09-22 对本机 `~/.claude/projects` 的只读探雷统计（顶层键频次、`type` 取值分布、
时间戳形态、单行字节量级），宿主版本按 `2.1.x` 标注。

每个 `.jsonl` 配同名 `.expected.json`：`events` 是期望事件序列（顺序敏感），
`stats` 是期望的 `ParseStats`。`workspace` 一律 `/repo`（纯字符串归一，三平台同结果）。

后续新增用例直接改本目录文件；这些 JSON 就是权威数据。
