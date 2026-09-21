# longitudinal 内部设计

状态: 草稿（T4.3–T4.5/T5.5–T5.7 落地时升定稿） | 对应: modules §8、data-model §4

## 职责边界

历史存储 + 干预台账 + 可比性判定 + 统计裁决 + **状态机唯一驱动者**。
统计代码零 LLM、纯函数；一切状态迁移结论必须能回溯到 comparisons 表行。

## store（SQLite WAL）

```
表: bundles(id PK, scope_json, manifest_hash, created_at)
    episodes(id PK, bundle_id FK, workspace, window, features_json)
    findings(finding_id + revision 复合 PK, status, severity, evidence_json, frozen_hash)
    interventions(id PK, finding_id, applied_at, diff_digest_json, env_json, checks_json)
    comparisons(id PK, finding_id, intervention_id, method, verdict, effect, ci_json,
                excluded_json, missing_n, created_at)
    state_transitions(自增 PK, finding_id, from, to, actor, adr_ref, at)   # 审计流水
迁移: 顺序 SQL 脚本 + schema_version 表；启动时校验版本，不匹配拒开（不做猜测兼容）
```

finding 更新 = 插入新 revision 行（不改旧行），当前状态视图 = 每 finding 最大 revision。

## match（可比 Episode 检索）

```
1 硬过滤(SQL): 同 workspace ∧ 与目标 check 相关行为存在 ∧ 难度桶相同 ∧ 干预时间窗两侧
2 软排序: tool_shape 相似度 (+ embedding 余弦，若 EmbeddingProvider 可用)
3 输出: Comparability{candidates[], confidence, exclusions[{episode_id, reason_code}]}
```

## confound（混杂否决，先于统计）

EnvSnapshot 等值比较：model_versions 集合、host、llm_provider、关键依赖哈希（ADR-0007 消歧）。
任一不一致 → 该候选 excluded（reason=`confound:<字段>`），**不进入统计样本**。
否决是硬门不是加权项——这是"报告趋势 ≠ 因果证明"的机制化（ADR-0004）。

## stats（裁决）

```
指标定义: 每 check 一个 MetricSpec（如 relevant-check → 验证配对率，逐 Episode 取值）
方法选择: 样本 < 阈值 → 直接 insufficient(missing_n=功效近似所需)
         前后窗对比 → bootstrap 置信区间(差值)；序列漂移 → CUSUM 变点
Verdict: {improved | flat | worsened | insufficient, effect, ci, method, missing_n}
判定规则: improved ∧ ci 下界 > 最小效应 → 支持 verified；worsened/复发信号 → regressed
```

## driver（状态机唯一入口）

`transition(finding_id, to, actor)`：校验 data-model §4.2 白名单 → 写 revision 行 +
审计流水 → 失败抛 ContractViolation。verified 仅可由 comparisons 显著结论触发；
regressed 自动重开（引用旧台账）。**其他模块想改状态只有这一条路。**

## 测试要点

迁移双向兼容（v1 库升 v2 可读）；混杂注入 100% 排除；无改进仿真序列 1000 轮
误判 ≤50（假阳性门禁）；missing_n 单调性（样本增加缺口不减）；
白名单外迁移全拒 + 审计行完整。
