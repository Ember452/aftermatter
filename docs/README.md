# AfterMatter 文档总导航

> **Harness engineering, with evidence.**
> 本文档体系按七阶段规划组织；每份文档顶部标注 `状态: 定稿/评审中/草稿`。

## 阅读地图（按序）

| 阶段 | 文档 | 回答什么问题 | 状态 |
|:---:|------|------------|------|
| 1 | [aftermatter-项目设计文档.md](aftermatter-项目设计文档.md) | 做什么？PRD、功能需求（FR-A~H）、里程碑、指标、风险 | ✅ 定稿 |
| 1 | [architecture/](architecture/INDEX.md) | 系统怎么分层？数据契约是什么？模块边界在哪？ | ✅ 定稿（随代码维护） |
| 2 | [aftermatter-项目结构.md](aftermatter-项目结构.md) | 仓库目录长什么样？新代码放哪里？ | ✅ 定稿 |
| 3 | [aftermatter-开发计划.md](aftermatter-开发计划.md) | 按什么顺序做、怎么验收？（M0–M6 任务级分解 + 验收清单） | ✅ 定稿 |
| 4 | [../AGENTS.md](../AGENTS.md) | AI 参与开发时的行为规范 | ✅ 定稿 |
| 5 | [architecture/](architecture/INDEX.md) 各模块篇 | 每个模块的内部设计 | ✅ 12 篇设计稿已入（随实现升定稿） |
| 6 | [specs/](specs/README.md) + [adr/](adr/README.md) | 关键决策为什么这么做 | ✅ 首批已入（adr 0001–0006 + specs 1 篇） |
| 7 | [plans/ROADMAP.md](plans/ROADMAP.md) | 演进路线与当前阶段 | ✅ active（随里程碑出口更新） |

## 目录规约

```
docs/
├── README.md                    # 本导航
├── aftermatter-项目设计文档.md    # 阶段1：PRD/需求/指标
├── aftermatter-项目结构.md        # 阶段2：目录级契约（不锁文件名）
├── aftermatter-开发计划.md        # 阶段3：Phase 划分与验收
├── architecture/                # 架构与契约（overview / data-model / modules / INDEX
│                                #   + 12 篇模块内部设计，随实现升定稿）
├── specs/                       # 带日期的专题决策与设计文档（较大粒度，时效性强）
├── adr/                         # 编号轻量决策记录（一页式：背景/决定/影响）
├── plans/                       # 演进计划与阶段快照
├── development/                 # 开发专题教程（按模块编号，随代码成熟补写）
├── tests/                       # 量化指标实测文档（需人工实测的场景）
├── benchmarks/                  # 基准测试报告（命名含日期）
└── api/                         # API 参考（模型导出 JSON Schema 后逐步生成）
```

**specs/ 与 adr/ 的分工**：specs/ 放"日期前缀的专题文档"（一次决策一份，含背景与边界，
如 `2026-09-21-dual-brain-and-deepening.md`）；adr/ 放"编号一页式轻量记录"（`NNNN-标题.md`，
只写 决定/理由/影响面）。拿不准放哪 → 先写 adr/，长到一页装不下再升 specs/。

## 文档纪律

- **契约唯一来源**：数据模型以 `architecture/data-model.md` + `schemas/` 为准，其他文档只引用不复述；
- **变更顺序不可反**：契约/选型先改文档（specs/adr 记录）→ 代码跟随；
- 技术选型表（architecture/overview.md §5）变更必须先落 ADR；
- 命名约定：品牌展示体 **AfterMatter**；技术标识符一律小写 **aftermatter**。

## 溯源声明

评估模型（五维十五检查、证据状态、评分天花板）借鉴并改造自
[QoderAI/better-harness](https://github.com/QoderAI/better-harness)（MIT License）。
差异化主张（双大脑、修复+纵向验证闭环、执行级证据引擎）为本项目独立设计。
