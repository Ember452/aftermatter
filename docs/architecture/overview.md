# AfterMatter 系统架构

状态: 定稿（设计阶段） | 版本: v1.0 | 对应: [../PRD.md](../PRD.md) v1.0

---

## 1. 架构总览：确定性内核 + 双大脑

```
                        ┌─────────────────────────────────────────┐
                        │        确定性证据内核（零 LLM）           │
                        │  collectors → episodes → evidence        │
                        │  （解析 / Episode 重建 / Bundle 冻结）     │
                        └───────────────────┬─────────────────────┘
                                            │ EvidenceBundle（版本化契约，唯一输入）
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
        ┌──────────────────────────┐                 ┌──────────────────────────────┐
        │ 大脑① 寄生宿主            │                 │ 大脑② 自带 LLM 引擎            │
        │ skill/ + analysis/mcp/    │                 │ analysis/engine/（多 Agent）   │
        │ MCP 工具暴露证据查询，     │                 │ 3 专家并行 → Lead Judge →      │
        │ 宿主 Agent 承担推理        │                 │ Repair → Verifier             │
        │ 零 API 成本 / 交互式       │                 │ cron / CI 无人值守             │
        └────────────┬─────────────┘                 └──────────────┬─────────────────┘
                     │            findings[] 统一 schema             │
                     └──────────────────────┬──────────────────────┘
                                            ▼
                    ┌────────────────────────────────────────────┐
                    │  report（HTML/MD 渲染）  longitudinal（SQLite │
                    │  历史库 + 干预台账 + 纵向统计）  daemon/serve   │
                    │  （定时驱动 / 只上传结论的团队趋势）             │
                    └────────────────────────────────────────────┘
```

**核心不变量**：

1. 两个大脑消费**同一份** EvidenceBundle、产出**同一份** Finding schema——报告/台账/服务端
   对大脑无感知。大脑可插拔，契约不可动。
2. 证据内核不做任何判断；判断层不得生成证据。跨层只走数据模型（见 [data-model.md](data-model.md)）。
3. 每个进入报告的断言必须携带可核验的 ERef；核验不过 = 断言不存在。

## 2. 设计原则

| 原则 | 落地方式 |
|------|---------|
| 证据优先 | L0→L3 全链路可回溯；无证据处显式 `Unobserved`，不猜分 |
| 模型提议、工具裁决 | LLM 只能产出 candidate；severity/分数/状态迁移由确定性代码判定 |
| 结构把关优于 prompt 自觉 | lane 越界、空引用、越白名单写入——全部协议/校验器拒绝，不依赖提示词 |
| 诚实降级 | 证据不全 → 三态标注；LLM 不可用 → deterministic-only 报告；绝不静默换赛道 |
| 最小依赖 | 新增第三方依赖需在 commit 正文说明理由（继承原版"刻意极简"纪律） |
| 本地优先隐私 | 原始会话不出机器；出机数据过分级脱敏管道 |

## 3. 分层与依赖方向（硬规则，评审依据）

```
daemon / serve / cli          （装配与暴露层）
   ↓
analysis / repair / longitudinal / report    （判断与产物层）
   ↓
evidence / episodes           （证据构建层，含 schema 契约）
   ↓
collectors / core             （采集与基础层：fs、时间、哈希、git）
```

- 下层禁止 import 上层；展示层不得直接读写 LLM 客户端或绕过校验器。
- `analysis` 内多 Agent 编排不得越过 `evidence` 直接调 `collectors`（防二次采集造成证据漂移）。
- 跨模块通信优先传不可变数据模型，不共享可变状态。
- 违规由架构测试强制（tests/architecture/ 检查 import 方向）。

## 4. 关键数据流

### 4.1 一次 normal 分析（大脑②）

```
aftermatter analyze --target <repo> --host claude --depth normal
  1 collectors    扫宿主会话 + 仓库证据 → RawEvent[]
  2 episodes      切分/分类 → TaskEpisode[]（含可比较性特征）
  3 evidence      冻结 EvidenceBundle（三 lane + IntegrityManifest，落 run-dir）
  4 analysis      三专家并发（各自只见自己 lane）→ ExpertReport[]
  5 lead          ERef 核验 → 合并 → 定级 → 五维分（受证据天花板约束）
  6 report        findings.json + report.html/md（schema 校验通过才允许写盘）
  7 longitudinal  findings 入 SQLite，关联历史，标记可比较候选
失败路径：任一专家 partial/unavailable → normal 拒绝出报告；quick 显式带缺口出。
```

### 4.2 修复 + 纵向验证闭环（独有主张）

```
finding(status=open)
  → Repair Agent 起草方案（白名单目标 + 边界 + 验收检查）
  → 人工确认 apply（dry-run 先行；非交互需 --yes）
  → InterventionLedger 记账（finding_id, diff, 时间, 环境哈希）
  → finding.status = fixed
  → 后续分析周期：匹配可比较 Episode（结构化特征 + 嵌入双通道）
      ├─ axis_diff 三态（ADR-0009）：single 可归因 / multi 仅描述 / none 噪声测量（E4）
      └─ 可比 → bootstrap CI / CUSUM 变点（E5）
            ├─ 显著改善 → verified
            ├─ 无显著变化 → 保持 fixed，报告"缺 N 个样本"
            └─ 复发/恶化 → regressed（重开，引用旧台账）
```

### 4.3 采集端 → 服务端（团队趋势，一期骨架）

```
本地 daemon ──(仅 findings + 指标摘要，脱敏 level≥standard)──▶ FastAPI ingest API
  幂等：idempotency key = sha256(bundle_id + finding_id + revision)
  服务端：Postgres 存储、团队聚合、趋势查询；永不接收/存储原始会话或 ERef 指向的原文
```

## 5. 技术选型（刻意极简，超出者进 commit 理由）

> 本表是**默认选型而非永久锁定**：变更需先落 ADR（轻量进 `docs/adr/`，专题进 `docs/specs/`），再改本表；
> 具体库的版本与替代实现细节由实现期决定，不属于架构约束。

| 领域 | 选型 | 理由 |
|------|------|------|
| 语言/运行时 | Python ≥3.12, asyncio | 目标生态；异步纪律贯穿 |
| 数据模型 | pydantic v2 | 跨边界契约 + JSON Schema 导出（前端/服务端共用） |
| CLI | typer + rich | 人机双模式输出（--json 走 stdout，诊断走 stderr） |
| LLM 客户端 | httpx 自研薄封装 + provider 适配 | 不引重框架；OpenAI 兼容/Anthropic/Ollama 三协议起步 |
| 本地存储 | SQLite（WAL） | 单文件、零运维、纵向历史库 |
| 服务端 | FastAPI + SQLAlchemy 2 + Postgres + alembic | G3/G4；队列一期用 asyncio + Redis(可选) |
| 静态分析 | tree-sitter（blast radius） | 多语言调用图，无编译器依赖 |
| 沙箱 | docker SDK，默认 `--network none` + 限额 | D3/D5；无 docker 时 Verifier 降级为不可用并显式标注 |
| 嵌入（E3） | 可选 local (model2vec) / remote | 默认本地小模型保隐私，remote 需显式开 |
| 渲染 | Jinja2 自包含 HTML + Markdown | 报告零外部资源引用 |
| 测试 | pytest + pytest-asyncio(auto) | LLM/网络全 fake；黄金 fixture 目录制 |

## 6. 可信性与降级体系（对应设计文档 C4–C6、H 系列）

### 6.1 反幻觉三道闸

1. **引用闸**：candidate 必带 ERef[]；确定性 verifier 解析每条引用并比对
   IntegrityManifest 哈希，不过 → 丢弃并写入报告 `rejected` 附录（可审计）。
2. **基线闸**：五维分先由确定性信号算基线（有无 CI、测试是否随源码共变、
   AGENTS.md 存在性等）；LLM 分与基线冲突超阈值 → 置信度降 low + 标"待人工复核"。
3. **对抗闸**：`tests/adversarial/` 维护假证据注入集（伪造 pass 记录、刷绿 CI、
   幻觉文件路径），CI 门禁要求拦截率 100%。

### 6.2 降级矩阵

| 故障 | quick | normal |
|------|-------|--------|
| 单专家 LLM 失败 | 重试 2 → 带缺口报告，lane 标 partial | 拒绝出报告 |
| 宿主无会话证据 | 项目+资产两 lane 继续（session-limited 评审） | 同左，报告头声明边界 |
| token 预算超限 | 减少 Episode 数，保结构不保覆盖，coverage 如实记录 | 同左 |
| 无 LLM 环境 | deterministic-only 报告（整份标注） | 同左 |
| Docker 不可用 | Verifier 不可用：执行级证据（replay_ok）不可得，验证证据降为转述级（claimed_ok）并标注 | 同左 |

### 6.3 评分天花板（继承并强化原版）

证据状态决定该维度绝对分数上限：`Missing/Unobserved/NA ≤59`、`Present ≤74`、
`Wired ≤84`、`Exercised ≤94`、`Outcome-supported ≤100`。
校验器强制：任何超过天花板的分数在写盘前被拒绝——**分数不可能靠话术膨胀**。

## 7. 部署形态

| 形态 | 组成 | 适用 |
|------|------|------|
| CLI-on-machine | aftermatter + 本地 SQLite | 个人首跑、CI 门禁 |
| 宿主寄生 | MCP server（stdio）+ SKILL.md | 大脑①，零 key |
| 本地常驻 | daemon（定时 analyze + upload） | 趋势积累、P1 |
| 自托管团队 | docker compose（FastAPI+Postgres） | 企业/二期 |
| 云托管 | 官方托管 serve | 商业线（订阅），二期后 |

## 8. 安全与隐私边界

- **磁盘**：EvidenceBundle/报告默认 `~/.aftermatter/runs/`；不含 prompt 原文，只存摘要 + ERef。
- **脱敏管道（分级）**：`raw`（不出机）→ `standard`（路径归一化、secret/PII 正则剥离、
  prompt→语义化 facet）→ `minimal`（仅计数与状态）。上传最低 standard，可验证测试覆盖。
- **沙箱**：断网默认、CPU/内存/超时限额、仓库只读挂载、命令白名单。
- **写操作**：Repair 仅白名单路径 + diff 上限；apply 需确认；一切写入前有内容哈希快照（可回滚）。
- **自我污染防护**：解析时剔除 AfterMatter 自身产物路径（抄原版 HARNESS_ARTIFACT_PATH_RE 思路）。

## 9. 可观测性（自己的产品自己先吃）

- 结构化日志（logging + trace_id 贯穿一次 analyze run）；
- run 级指标：解析耗时/事件数/Episode 数/各角色 token 与费用/核验拒绝数——进报告附录；
- `aftermatter doctor`：环境自检（宿主会话路径发现、Docker、provider key、DB 迁移状态）。
