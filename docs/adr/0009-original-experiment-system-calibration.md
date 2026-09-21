# ADR-0009: 原版全库对照后的主张校准与四项设计吸收

状态: Accepted | 日期: 2026-09-21
Related: ADR-0003/0004（背景勘误）、PRD §1/§4/§5.2/§5.3/E4/E5/D3、
specs/2026-09-21-dual-brain-and-deepening.md、data-model.md §4.3（bundle=3）、
longitudinal.md、sandbox.md、adr/README.md（模板 v2）

## 背景
对照 better-harness **完整仓库**（此前仅研读 Qoder 插件缓存子集）新发现：
原版 `docs/adrs/` 含 10 篇 ADR，其中 ADR-0004（harness-checkpoint-experiment-compare）、
ADR-0005（checkpoint-backed-compare-sources）对应 `packages/harness/src/experiment|compare/`
**已有实现代码**——原版已具备"主动受控实验"系统：多车道 checkpoint 重放、
derived 单轴归因（恰一轴不同才可归因）、matched-pair 规则证据地板、identical-pair
噪声地板、checkpoint 完整性收据。我们文档中"无执行级复跑 / 止步于报告"等三处表述过强。
同时 roadmap.md / roadmap-2026.md 关键词扫描（statistic/bootstrap/longitudinal/
standalone/headless/cron/unattended）零命中——无人值守与统计纵向不在其路线上。

## 决定
1. **口径修正**：差异化重定位为——被动工作流的统计纵向验证（bootstrap/CUSUM/CI）
   vs 原版主动受控实验（规则地板）；报告链路 claimed→replay 沙箱核验 vs 实验室
   lane 重放；无人值守（大脑②）原版无此方向。三条主张校准后依然成立。
2. **吸收四项设计**：噪声地板（无干预期可比对构造 run-to-run 变异基线）、
   单轴归因三态（single 可归因 / multi 仅描述 / none 记噪声测量）、
   工作树完整性收据（无收据的复跑不得回填 replay_ok）、ADR 模板 v2
   （状态生命周期 + Traceability + 被否备选）。
3. **登记不实施**：受控实验形态列 ROADMAP P2-7；test/ 领域分组与读者视角
   样式模板列 D-7/D-8 决策点。

## 影响
PRD 四处 + specs 两处措辞校准；data-model Comparison 增 `axis_diff` 字段
（只增，schema bundle 版本 2→3）；longitudinal confound 节改三态、stats 节增
噪声地板；sandbox 增收据门；ADR-0003/0004 加勘误引用（正文不改）；adr/README 模板升级。

## 被否备选
- 照搬原版 experiment/compare 整套进一期：属 Studio 产品面，依赖驱动 fresh agents
  的 ACP 基础设施，与报告链路是两个产品。
- 因原版有实验系统而收缩差异化：路线与场景均不同，校准后主张更可信而非更弱。
- 只改 PRD 措辞不留痕：违反 AGENTS §二.5 触发 5（跨文档不一致裁决必须留痕）。
- 回改 ADR-0001–0008 正文：历史决策写完不追改，以勘误引用代替。
