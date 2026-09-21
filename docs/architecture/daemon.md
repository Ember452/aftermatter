# daemon 内部设计

状态: 草稿（T6.5 落地时升定稿） | 对应: modules §10

## 职责边界

本地常驻：定时驱动"采集→分析→（可选）上传"。自身**零业务逻辑**——
全部动作是调用 cli/kernel 公共 API，daemon 只拥有"何时、对哪个 workspace、失败怎么办"。

## 组件

```
Scheduler   asyncio 定时循环（APScheduler 或自研 tick，选型表内可换）：
            每 workspace 一个 job（interval / cron 表达式），支持 pause/resume
JobRunner   单 job 执行体：freeze→analyze→落 run-dir→（配置了 upload 则）入队
            同 job 不重叠（上轮未完即跳过并记日志）
UploadQ     本地磁盘队列（掉电不丢）：脱敏(≥standard)→ POST →
            失败指数退避（上限封顶），Idempotency-Key = bundle 内容哈希
State       ~/.aftermatter/daemon/state.toml：各 workspace 的 offset checkpoint、
            最近 run 摘要、队列水位（与 collectors 的 checkpoint 机制同一套键）
Lifecycle   优雅退出：完成当前 job 或超时截断→ journal 落盘；重启后从 state 续
```

## 边界与失败姿态

无服务端配置 = 纯本地模式（上传整条链路可关）；连续 N 次同因失败 → job 自动暂停 +
doctor 提示（不无限重试烧钱）；daemon 永不执行 repair/apply（写操作只能来自人驱动的 CLI）。

## 测试要点

重传幂等（fake server 收两次同 key）；掉电恢复（队列与 state 重建后无重复 run 记录）；
job 重叠保护；失败退避序列正确；关闭上传时全链路零外呼（网络 spy 断言）。
