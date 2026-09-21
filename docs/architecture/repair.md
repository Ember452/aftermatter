# repair 内部设计

状态: 草稿（T4.1–T4.2 落地时升定稿） | 对应: modules §6、overview §4.2

## 职责边界

`Finding.repair` → 可审 diff → （确认后）落盘 + 台账。LLM **只参与起草 plan**，
apply 阶段是纯确定性代码——"模型提议、工具裁决"在写路径上的体现。

## 内部流程（两阶段 + 事务）

```
plan(finding):
  1 目标解析: finding.repair.targets × 白名单模板（AGENTS.md、CI 配置、测试骨架占位…）
    路径展开后逐条校验：glob 命中白名单 ∧ 非 symlink 逃逸 ∧ diff 行数 ≤ 上限
    任一不过 → RepairPlanRejected(越界清单)     # plan 期即拒，不留到 apply
  2 起草: LLM(证据 ERef + 目标文件现文) → 候选 diff（仅此步用 LLM）
  3 自检: 候选 diff 复过第 1 步全部校验（LLM 输出不可信原则）

apply(plan, *, yes):
  a journal 写入 pending 记录（plan 哈希 + 目标清单）
  b 快照: 每个被改文件 {sha256, 内容副本} 存 run-dir（revert 依据）
  c 落盘: 逐文件写；任一失败 → 按快照回滚全部 → journal 标 aborted
  d 记账: longitudinal.ledger.commit(intervention) 成功 → journal 标 committed
    记账失败 → 回滚 c（两阶段：先能记账才允许落盘生效）
  e 非交互模式无 --yes → 拒（ConfigError），dry-run 永远先行

revert(intervention_id): 按快照还原 + ledger 追加 revert 事件（不删账，只追加）
```

## 白名单引擎

声明式规则表（路径 glob + 每类目标的 diff 上限 + 禁改清单如 `src/**`、`schemas/**`），
规则表版本进 plan 哈希——白名单变更 = 关键决策（ADR 触发条件 3）。

## 测试要点

越界 diff 注入全拒（plan 期与自检期各一套）；symlink 逃逸用例；
崩溃注入（b/c/d 各步骤 kill）后无半成品状态；revert 往返一致（内容哈希复原）；
记账失败触发落盘回滚的联动测试。
