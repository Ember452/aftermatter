# analysis 内部设计

状态: 草稿（T2.x/T3.x 落地时升定稿） | 对应: modules §5、overview §1/§6

## 职责边界

输入 EvidenceBundle，输出 `Finding[] + DimensionScores + EvidenceBrief`。
四个子包：deterministic（基线）、engine（大脑②）、mcp（大脑①）、providers（LLM 客户端）。
**判断层不得生成证据**：一切对 bundle 之外的读取都视为违约（架构测试强制）。

## deterministic/ —— 基线评分器（零 LLM）

```
SignalRegistry: check_id → [SignalExtractor]     # 声明式注册，15 检查逐一挂信号
  例 relevant-check:  验证配对率(改后同窗有验证)、测试共变率、replay_ok 占比
  例 scope-boundary:  edits 路径 ∩ 意图提及路径 比例
BaselineScorer: Bundle → {per_check: SignalValue, per_dimension: 0-100 基线分}
```

- 纯函数 + 表驱动，输出稳定幂等；每个信号带 `strength`（该信号最高能支撑的证据状态），
  维度基线分自动被天花板截断
- 双重角色：M2 主评分器；M3 后的"基线闸"（LLM 分冲突源）

## engine/ —— 大脑②多 Agent 编排

### 专家（三实例同构，配置差异）

```
ContextAssembler: 本 lane 切片 → 有界上下文（Episode 摘要卡 × N + 信号表），
                  超预算先裁 Episode 数（coverage 如实记录裁了什么）
PromptContract:   system(角色+lane 边界+禁越界声明) + 证据块 + 输出 JSON Schema
CallAndParse:     LLM → ExpertReport 模型校验；失败带错误信息重试 1 次；
                  再失败 → status=unavailable(reason_code)（不产半成品）
```

- 专家工具面：只读本 lane（类型系统保证拿不到别的 lane）
- golden set：固定 Bundle → 断言 candidate 的 check 归属/severity 一致率（防 prompt 静默劣化）

### lead/ —— 裁决流水线（顺序固定，不可逆）

```
1 verify    全部 candidate ERef 过 evidence.verify_ref → 不过者入 rejected(带原因码)
2 merge     四元组一致(目标+后果+责任人+修复路径)才合并；保留各自证据并集
3 dissent   专家冲突不折中：输出低置信 finding + conflict_source 标注
4 grade     severity 判定表（后果×影响面×可逆性），仅此处可赋值
5 score     维度分 = f(基线分, LLM 断言) → 天花板截断 → 与 finding 数量解耦
6 freeze    定稿哈希入 Ledger 前置表；此后 repair/report 只读此快照
```

### budget/ + orchestrator

- `BudgetLedger`：每角色 token/费用上限，实时记账（providers 回写）；
  超限动作序列：裁 Episode → 减重试 → 整 run 降级 deterministic-only（报告全份标注）
- `Orchestrator`：TaskGroup 三专家并发 → 收集 ExpertReport → Lead；
  失败隔离按 overview §6.2 矩阵执行（normal 遇非 ok → 抛 `EvidenceInsufficient`，CLI 退出码 2）

## mcp/ —— 大脑①寄生入口

四个只读/受控工具：`build_bundle`（触发内核冻结，返回 bundle_id+摘要）、
`query_lane`（按 lane+分页取 Episode 摘要卡，永不返回原文 prompt）、
`verify_refs`（宿主 Agent 自检引用）、`submit_findings`（宿主产出的 candidate
过**与大脑②完全相同**的 verify+merge+grade 流水线，origin=host）。
实现即薄壳：全部逻辑 import 自 deterministic/lead/evidence，零复制。

## providers/ —— LLM 客户端

- 协议适配：openai-compat / anthropic / ollama，统一 `generate(schema, messages) -> T`
  （强制 JSON Schema 输出）
- 错误分类映射到 core.ProviderError 子类；重试仅幂等调用、指数退避、上限 2
- 成本计量：每调用回写 (role, tokens_in/out, cost) 至 BudgetLedger
- `FakeLLM`：从对话录像 fixture 重放，接口同真客户端——单测/CI 全程使用

## 测试要点

Lead 六阶段逐阶段注入测试（乱序调用拒绝）；lane 越界 candidate 降权用例；
预算超限→deterministic-only 可复现；双大脑 parity：同 Bundle 两路产出过同一 schema 校验；
FakeLLM 录像回放一致性。
