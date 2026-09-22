# Codex 适配器黄金 fixture

来源：**全部合成**，不含任何真实用户会话（REPO-LAYOUT §3、AGENTS §4.3 第 4 条）。
结构依据 2026-09-22 对本机 `~/.codex/sessions` 的五轮只读探雷：信封恒为
`{timestamp, type, payload}`；对话在 `response_item`，`event_msg` 是同一份对话的第二视图
（映射表忽略它以杜绝双计）；`arguments` 是 JSON 字符串；`function_call_output.output`
实测 24/25 不带退出码，故 `result_ok` 一律 `null`；`model` 只在 `turn_context`、
`session_id`/`cwd` 只在 `session_meta`，因此适配器跨行 carry-forward。宿主版本 `0.153.1`。

每个 `.jsonl` 配同名 `.expected.json`：`events` 为期望事件序列（顺序敏感），
`stats` 为期望 `ParseStats`。`cwd` 一律 `/repo`（纯字符串归一，三平台同结果）。
