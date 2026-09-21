# ROADMAP — 演进路线与当前阶段

状态: active | 最后更新: 2026-09-21 | 更新时机: 仅里程碑出口与方向级变化（细则变更走 adr/）

> 本文档回答"一期之后往哪走、现在走到哪了"。一期怎么按序做见
> [DEVELOPMENT-PLAN.md](../DEVELOPMENT-PLAN.md)，此处不复述。

---

## 1. 当前阶段快照（唯一时效性章节，每个里程碑出口重写本节）

**阶段**：Phase 0 文档基线 ✅ 完成 → 下一步 M0 骨架（未开工）。

| 已完成 | 证据 |
|--------|------|
| 七阶段文档 1–6 | docs/（设计文档/结构/开发计划/AGENTS/architecture 12 篇/adr+specs 首批） |
| 立项决策留痕 | `docs/adr/` 与 `docs/specs/` 全量索引见各自 README |
| 竞品源码级校准 | specs §2（原版零 LLM 实测、Repair→Validate→Record 人驱动定性） |

**代码**：仅 pyproject 6 行 init 骨架（requires-python 已统一 >=3.12，余由 T0.1 补全）；
实现代码为零（有意为之——计划先行，M0 起以 tag 计进度）。
**下一决策点**：M0 出口后确认 D-2/D-3（见 §6）。

## 2. 一期（进行中）：M0–M6

里程碑表与验收在开发计划 §3/§5。一期 GA 定义：

- M0–M6 验收清单全绿，tag 链 `v0.1.0-m0-skeleton` … `v0.7.0-m6-distribution`（ADR-0006）
- PyPI 正式发布 + 英文 README + 4 宿主解析可用 + "发现→修复→台账→纵向复查"闭环可演示
- GA 时打 `v1.0.0`，脱离里程碑 tag 序列，此后走正常 SemVer
- 发布窗口动作（HN/Reddit/awesome-list 提交）届时按 D-1 决策

## 3. 二期候选（M6 后，全部为"触发制"而非日程制）

| ID | 方向 | 内容 | 准入触发条件 | 关联契约 |
|----|------|------|-------------|---------|
| P2-1 | 服务端做满 | G4 多租户配额、任务队列、限流、团队趋势面板前端 | ≥3 个团队真实 ingest，或出现自托管部署请求 issue | serve.md v1 契约不破 |
| P2-2 | Inspector UI | F5 证据浏览器（时间线+证据抽屉），数据层已预埋零返工 | 用户反馈中"需人工回溯证据"成为高频项（rejected 附录被反复质询） | run-dir 契约不变 |
| P2-3 | CI 门禁形态 | `aftermatter` 作为 GitHub Action：PR 上跑 quick 深度、退出码 2 拦截工作流退化 | PRD 用户场景三（CI/CD 运维）出现外部需求；竞品先例（proofloop 以 Action 分发）验证过分发路径 | cli 退出码契约 |
| P2-4 | 宿主扩展 | Qwen Code / Copilot / Pi / Kimi / Grok 适配器；同时适配器改 entry-points 插件化开放第三方贡献 | 适配器数 >6（结构 §7 既定触发线）或外部贡献者请求 | SessionAdapter Protocol 冻结 |
| P2-5 | 沙箱升级 | D5 容器池（预热/复用）+ 重放范围从"验证命令真伪"扩展到构建环境 | 沙箱复跑使用率稳定 >30% run，或复跑耗时成为体验瓶颈 | replay_ok 唯一入口不变 |
| P2-6 | 契约包独立 | schemas 被外部工具消费后发布 `aftermatter-contracts`（结构 §7） | 出现第一个非本项目消费者 | 版本化策略不变 |
| P2-7 | 受控实验形态 | 借鉴原版 harness-experiment（其 ADR-0004/0005）：同 checkpoint 双车道主动对跑（改前/改后同任务），与我们的被动统计纵向互补 | 用户明确需要"同任务对跑"能力，且驱动 fresh agent 的宿主协议基础设施就绪 | 实验结论仍经 Comparison（axis_diff 语义）入 verified，不开第二状态机 |

**二期启动判定**（何时从候选转执行）：PRD §9 三类指标至少两类达标——
① 增长（Star/下载/外部 issue 有真实用户信号）；② 可信性（对抗拦截率、引用通过率稳定）；
③ 闭环（出现外部用户的 `verified` 案例）。达标即立 `docs/plans/<THEME>_PLAN.md` 展开。

## 4. 三期 / 长期方向（只定方向，不做承诺）

- **商业线**：云托管订阅（B 端 $5–20/月，团队大盘 + 跨仓库趋势）。前置条件：
  自托管形态先被真实使用，open-core 边界（哪些永远 MIT）届时以 ADR 决策（D-5）
- **组织级洞察**：跨仓库重复模式挖掘（同类 finding 在 N 个仓库出现 → 平台级建议）、
  harness 治理报告——这是"团队视角"主张的远期形态
- **生态**：适配器 SDK 与贡献指南、脱敏 case studies（借鉴原版 case-studies 路径，
  以证据为边界的运行示例）
- **方法论输出**：纵向验证机制（单轴归因 + 噪声地板 + 小样本统计）独立成文，是差异化主张的
  学术/博客延伸，反哺获客

## 5. 永久非目标（每阶段 reaffirm，防 scope 漂移）

❌ 通用 LLM tracing / token 流水账大盘 ❌ 模型能力评测榜单
❌ 自己执行开发任务的 coding agent ❌ 原始会话全量上传形态
❌ 为多 Agent 而多 Agent 的模板角色（规划者/反思者/记忆管理者类）

## 6. 决策点清单（open questions，到期必须落 ADR）

| ID | 问题 | 决断期限 |
|----|------|---------|
| D-1 | GA 发布渠道与时机（HN/Reddit/awesome-list/飞书中文社区） | v1.0.0 前 |
| D-2 | 嵌入模型最终选型与隐私默认（model2vec 本地 vs 可配远程） | T5.5 前 |
| D-3 | 沙箱镜像策略（通用 slim vs 复用项目镜像） | T5.1 前 |
| D-4 | 服务端托管平台与成本上限 | 二期启动前 |
| D-5 | open-core 许可边界（云版哪些模块不开源） | 商业线启动前 |
| D-6 | ~~docs 一致性检查脚本（scripts/ 下校验跨文档术语/引用一致）是否进 M6~~ 已决：不等到 M6，即刻上 `scripts/doc_lint/` 与 `.github/workflows/docs.yml` | 已关闭（ADR-0011，2026-09-21） |
| D-7 | ~~tests/ 是否改按领域分组~~ 已决：保持 src 镜像 + integration 领域命名 | 已关闭（ADR-0010，2026-09-21） |
| D-8 | 报告是否借鉴原版 templates/style 读者视角模板族（executive/analyst/audit-scorecard）作二期皮肤 | 二期启动前 |
| D-9 | doc-lint P3 backlog：strip_code 反引号嵌套、Finding→TypedDict、slugify emoji 锚点、actionlint 验证、裸节号 checker（ADR-0011 缓办项） | 扩充 doc-lint 规则时 |

## 7. 维护规则

- 本文只在里程碑出口更新；§1 快照整节重写，历史快照靠 tag 回溯不另存副本
- 新方向从候选转执行 → 单开 `<THEME>_PLAN.md`，本文对应行改为一行引用
- 所有"已完成/已达标"表述必须可被 tag、issue、PR 或 benchmarks 文件验证——
  与产品自身的诚实红线同一条命
