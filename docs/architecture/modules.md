# AfterMatter 模块设计

状态: 定稿（设计阶段） | 对应 [overview.md](overview.md) / [data-model.md](data-model.md)

> 每个模块给出：职责一句话、公共接口（Protocol）、允许依赖、测试要求。
> **新代码必须放对模块；放不进去就先来改这份文档。**
> 本文档只约束模块职责与接口，**不约束目录内文件名**；仓库级目录契约见
> [../REPO-LAYOUT.md](../REPO-LAYOUT.md)。

---

## 0. 模块划分

目录树契约唯一来源：[../REPO-LAYOUT.md](../REPO-LAYOUT.md) 的“§2 src/aftermatter 模块骨架”，
本文档不再维护副本（消除双写漂移）；各模块内部设计见 INDEX 所列 12 篇。
模块职责总序：core（基础）→ collectors/episodes/evidence（证据内核）→
analysis/repair/sandbox/longitudinal/report（判断与产物）→ serve/daemon/cli（装配暴露）。

依赖方向遵守 [overview.md](overview.md) §3，由 `tests/architecture/`（import-linter 或自建 AST 检查）强制。

---

## 1. core — 基础设施

| 项 | 内容 |
|----|------|
| 职责 | 时间戳规范化、sha256/稳定指纹、路径归一（Windows 盘符→仓库相对）、日志与 TraceId、异常基类层次 |
| 接口 | `fingerprint(obj)->str`、`norm_path(p, root)->str`、`AfterMatterError(code, retryable)` 异常基类树（见 core.md） |
| 依赖 | 仅标准库 |
| 测试 | 纯函数全分支覆盖 |

## 2. collectors — L0 采集

| 项 | 内容 |
|----|------|
| 职责 | 把宿主私有会话文件解析为 `RawEvent[]`；扫描仓库产出 `RepositoryEvidence` |
| 接口 | `class SessionAdapter(Protocol)`: `discover(workspace)->list[SessionRef]`（找文件+识别格式版本）、`parse(ref, since_offset)->AsyncIterator[RawEvent]`（流式、可断点）、`healthcheck()->AdapterHealth`（版本是否在支持矩阵内） |
| 关键设计 | ① 版本探测先行：文件头/字段特征识别宿主版本，未知版本 → `unparsed_count` + 显式降级，**绝不猜测映射**；② 剔除自身产物路径（防自我污染）；③ 增量：`since_offset` 配合内容哈希缓存（A5） |
| 依赖 | core |
| 测试 | 每家 ≥20 条黄金 fixture（含畸形行、截断文件、编码陷阱）；解析正确率进 CI |

## 3. episodes — L1 重建

| 项 | 内容 |
|----|------|
| 职责 | RawEvent → TaskEpisode：双规则切分、行为/验证/摩擦分类、可比性特征计算 |
| 接口 | `segment(events, cfg)->list[TaskEpisode]`；`classify(e)->FactKind|None`；`comparability(ep)->Features` |
| 关键设计 | ① 分类器纯规则先行（命令正则库：pytest/npm test/cargo/make...，NFKC 归一），embedding 只做特征不做事实；② `claimed_ok` 只来自转述，`replay_ok` 只允许 sandbox.Verifier 回填（写入走唯一入口函数）；③ 切分配置化（gap 时长）但规则组合固定，防指标被调参调没 |
| 依赖 | core, collectors(模型) |
| 测试 | 黄金样例集（多会话交错、30min 边界、纠错续接）逐 Episode 断言；property-based 测切分不变量（不重叠、时间有序） |

## 4. evidence — L2 契约层

| 项 | 内容 |
|----|------|
| 职责 | 全部跨层数据模型的**唯一定义处**（[data-model.md](data-model.md) 的代码化身）；Bundle 冻结、IntegrityManifest、脱敏管道 |
| 接口 | `freeze(scope, lanes, ...) -> EvidenceBundle`（写 run-dir，内容寻址）；`redact(model, level)->model`；`verify_ref(bundle, eref)->bool`（引用闸的确定性核心） |
| 关键设计 | ① Lane 模型互斥：`SessionLane/ProjectLane/AssetsLane` 无交叉字段，专家输入类型即隔离；② 脱敏分级管道 raw/standard/minimal 为纯函数 + 属性测试（secret 正则库必过）；③ JSON Schema 由模型导出版本化入 `schemas/`，报告/服务端复用 |
| 依赖 | core |
| 测试 | 冻结幂等、哈希篡改必被 verify_ref 拒绝（对抗夹具）、脱敏泄漏扫描 |

## 5. analysis — 大脑（最重模块）

### 5.1 消息契约（analysis 包内集中定义的 protocol 模型）

```python
class Candidate(BaseModel):
    claim: str
    evidence: tuple[ERef, ...]           # 空元组直接 ValidationError
    dimension: DimensionId | None        # 仅建议
    strength: Literal["observed", "inferred"]

class ExpertReport(BaseModel):
    lane: Literal["session", "project", "assets"]
    status: Literal["ok", "partial", "unavailable"]
    reason_code: str | None              # status != ok 时必填
    candidates: tuple[Candidate, ...]
    coverage: CoverageStats              # 读了多少、跳了什么
```

### 5.2 deterministic/ — 基线评分器（零 LLM）

- 输入 Bundle，输出 `BaselineScores`（五维）+ `BaselineSignals`（每项检查的确定性证据：
  CI 文件存在、测试-源码共变率、AGENTS.md 覆盖率、Episode 内验证配对率…）
- **M2 里程碑不接任何 LLM 就能出完整报告**，靠的就是它 + 状态机 + 渲染器；
- 同时充当"基线闸"：LLM 分与它冲突超阈值 → confidence=low + `needs_human` 标记。

### 5.3 engine/ — 大脑②多 Agent 编排

```
编排入口          三专家并发（asyncio）；失败隔离与降级矩阵执行者
experts/          每个专家 = 受限上下文组装器 + 单轮/少轮 LLM 调用 + 输出解析
                  工具面：只读（查询自己 lane 的 Episode/信号），无 write、无 bash
lead/             裁决流水线：核验→合并(四元组)→异议保留→定级→分数截断
budget/           每角色 token/费用上限；超限策略：裁剪 Episode 数 → 仍失败则
                  整run降级为 deterministic-only
```

- 专家间**永不共享中间结论**；Lead 是唯一合并点（防锚定污染的架构表达）；
- LLM 全部注入 `FakeLLM`（接口同 providers），单测不碰网络；
- 每个专家 + Lead 都有 golden set：输入固定 Bundle，断言 candidate 集合的
  check 归属与 severity 一致率 ≥80%（回归基线，防 prompt 改动静默劣化）。

### 5.4 mcp/ + skill/ — 大脑①寄生入口

- MCP server 暴露只读工具：`build_bundle` / `query_lane` / `verify_refs` / `submit_findings`
  （宿主 Agent 产出的 findings 也要过同一个引用闸——**两个大脑共享同一套门禁代码**）；
- SKILL.md 编排宿主走五步流程（采证→单 lane 简报→裁决→渲染→落盘），文档里明确
  "本宿主模式下 Repair 与 Longitudinal 仅记录不执行"——能力边界诚实化。

### 5.5 providers/ — LLM 客户端

- OpenAI 兼容 / Anthropic / Ollama 三协议薄封装；错误分类（rate/timeout/auth/schema）；
  重试仅幂等操作；成本计量每调用回写 run 指标（H2 的落点）。

## 6. repair — 有界修复

| 项 | 内容 |
|----|------|
| 职责 | 把 `Finding.repair` 落成可审 diff；管理 dry-run→确认→apply→记账 |
| 接口 | `plan(finding)->RepairPlan`（LLM 仅在此处可用，输入=证据+目标文件）；`apply(plan, *, yes)->ApplyResult` |
| 关键设计 | ① 白名单：目标路径模板（AGENTS.md、CI 配置、测试骨架占位）+ diff 行数上限，**白名单外路径在 plan 校验期即拒绝**；② apply 前对被改文件做内容哈希快照，提供 `aftermatter revert <intervention_id>`；③ Ledger 写入失败 → apply 回滚（先记账后落盘的两阶段） |
| 依赖 | evidence(模型), analysis/providers(可选), longitudinal(台账) |
| 测试 | 越界 diff 注入全拒绝；崩溃注入下无半成品状态 |

## 7. sandbox — 执行级证据（D3–D5）

- `ReplayPolicy`：从 Episode 的 validations 重建命令序列 → 容器内按序复跑 →
  `ReplayResult{per_command: [(identity, ok, duration)]}` 回填 `replay_ok`；
- 默认 `--network none`、CPU/内存限额、超时硬杀、仓库只读挂载 + 可写 tmpfs；
- Docker 不可用 → `SandboxUnavailable`，Verifier 报告 lane 状态 `unavailable`（触发降级矩阵）；
- **一期只复跑"声称通过"的验证命令做真伪核验，不做任意命令执行**（最小攻击面）。

## 8. longitudinal — 纵向验证（技术皇冠）

| 组件（职责单元，非文件名约束） | 职责 |
|------|------|
| 历史库 | SQLite（WAL）：表结构见 [longitudinal.md](longitudinal.md) §store + 迁移 |
| Episode 匹配 | 可比 Episode 检索：结构化特征过滤（硬条件：同 check 相关行为、同难度桶）→ 向量相似度软排序 → `Comparability{confidence, exclusions[]}` |
| 单轴归因 | axis_diff 三态（single/multi/none，见 longitudinal.md §confound，ADR-0009）；multi 无 verified 资格，理由机器可读 |
| 统计检验 | bootstrap 置信区间 + CUSUM 变点；`Verdict{improved|flat|worsened|insufficient, effect, ci, missing_n}` |
| 状态机驱动 | 唯一能把 finding 迁移到 verified/regressed 的位置（白名单见 [data-model.md](data-model.md) §4.2） |

- 统计代码零 LLM、纯函数、可用模拟数据做假设检验测试（假阳性率 <5% 的口径：
  在"无真实改进"的仿真序列上跑 1000 轮，误判 verified ≤50 次）。

## 9. report — 渲染

- 输入：`ReportModel`（findings + scores + evidence brief + coverage + rejected + 成本附录）；
- 写盘前跑 `report-quality` 校验（自建，借鉴原版思想）：无证据的分数、越天花板分数、
  `Unobserved` 处出现具体断言、severity 与 lifecycle 矛盾 → **拒绝渲染**；
- 自包含 HTML（内联 CSS，零外链）+ Markdown 双格式；趋势图一期用内联 SVG。

## 10. serve + daemon — 一期骨架

- serve：FastAPI `POST /ingest/findings`（幂等键去重）、`GET /trends`、最小 token 鉴权与
  团队模型；**表结构里不存在任何原文字段**（隐私承诺的 schema 化表达）；
- daemon：定时调度（APScheduler 或自研，见 daemon.md）`analyze` → 脱敏(≥standard) → 指数退避重传；
- G4（多租户配额/队列/限流）二期，接口预留 tenant_id。

## 11. CLI 契约（agent-friendly）

- 所有命令支持 `--json`（stdout 纯 JSON，诊断走 stderr）、`--no-input`、`--dry-run`、`--timeout`；
- 计划与变更分离：任何写操作两步式（plan → apply --yes）；
- 退出码语义化：0 成功 / 1 用户错误 / 2 证据不足(normal 拒绝出报告时) / 3 环境缺依赖 / 4 内部错误。

## 12. 测试策略总表

| 层 | 范围 | 特殊要求 |
|----|------|---------|
| unit | 纯函数与模型；LLM/FS/网络全 fake | pytest-asyncio auto；不打真实文件系统（tmp_path 除外） |
| integration | collector→bundle→report 全链路（fixture 会话） | 双大脑产物过同一校验器 |
| architecture | import 方向、模型不可变性、白名单完备性 | 违规即失败，无豁免清单 |
| adversarial | 假 ERef/刷绿 CI/伪造 verified 声称/越界 diff | 拦截率 100% 门禁；用例只增不减 |
| fixtures | 各宿主黄金会话 + 手工标注期望 Episode/Finding | 标注文件与数据同目录，版本对齐 |
