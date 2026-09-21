# architecture/ 索引

> 架构与契约文档区。**随代码维护**：代码变了这里必须同 PR 更新；
> 模块内部实现设计（阶段 5）也落这里，一模块一篇。

| 文档 | 内容 | 状态 |
|------|------|------|
| [overview.md](overview.md) | 系统架构：双大脑总览、设计原则、依赖方向硬规则、关键数据流、技术选型、降级与可信体系、部署与隐私边界 | ✅ 定稿 |
| [data-model.md](data-model.md) | 四层数据契约（RawEvent/TaskEpisode/EvidenceBundle/Finding）、状态机、五维15检查、证据状态与评分天花板、schema 版本化 | ✅ 定稿（契约源头） |
| [modules.md](modules.md) | 模块划分与职责：各子系统接口契约、关键设计、允许依赖、测试要求 | ✅ 定稿 |

## 模块内部设计（阶段 5，实现前设计稿，随对应任务落地时升定稿）

| 文档 | 模块 | 锚定任务 |
|------|------|---------|
| [core.md](core.md) | 基础设施与异常树 | T1.1 |
| [collectors.md](collectors.md) | 适配器流水线、repo 扫描器 | T1.3–T1.5, T6.1–T6.3 |
| [episodes.md](episodes.md) | 切分算法、分类器、可比性特征 | T1.6–T1.7 |
| [evidence.md](evidence.md) | 冻结流程、verify_ref、脱敏 | T1.2/T1.8/T1.9 |
| [analysis.md](analysis.md) | 基线评分器、三专家、Lead 六阶段、预算、MCP、providers | T2.1–T3.8 |
| [repair.md](repair.md) | plan/apply 两阶段事务、白名单引擎、revert | T4.1–T4.2 |
| [sandbox.md](sandbox.md) | 探测/容器规格/重放策略/replay_ok 唯一入口 | T5.1–T5.2 |
| [longitudinal.md](longitudinal.md) | 表结构、匹配、混杂否决、统计裁决、状态机驱动 | T4.3–T4.5, T5.5–T5.7 |
| [report.md](report.md) | 质量门禁错误码、确定性渲染、四件套版式 | T2.6–T2.7 |
| [serve.md](serve.md) | ingest 幂等、无原文表结构、v1 契约 | T6.6 |
| [daemon.md](daemon.md) | 调度、磁盘上传队列、掉电恢复 | T6.5 |
| [cli.md](cli.md) | 命令树、退出码、输出契约、配置优先级 | 持续演进 |

**边界**：本目录只写"设计与契约"；"为什么这样选"的一次性决策记录去 `../specs/` 与 `../adr/`；
"目录长什么样"的仓库级契约在 `../aftermatter-项目结构.md`，此处不复述。
