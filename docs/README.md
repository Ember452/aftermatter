# AfterMatter 文档总导航

> **Harness engineering, with evidence.**
> 本文档体系按七阶段规划组织；每份文档顶部标注 `状态: 定稿/评审中/草稿`。

## 阅读地图（按序）

| 阶段 | 文档 | 回答什么问题 | 状态 |
|:---:|------|------------|------|
| 1 | [PRD.md](PRD.md) | 做什么？PRD、功能需求（FR-A~H）、里程碑、指标、风险 | ✅ 定稿 |
| 1 | [architecture/](architecture/INDEX.md) | 系统怎么分层？数据契约是什么？模块边界在哪？ | ✅ 定稿（随代码维护） |
| 2 | [REPO-LAYOUT.md](REPO-LAYOUT.md) | 仓库目录长什么样？新代码放哪里？ | ✅ 定稿 |
| 3 | [DEVELOPMENT-PLAN.md](DEVELOPMENT-PLAN.md) | 按什么顺序做、怎么验收？（M0–M6 任务级分解 + 验收清单） | ✅ 定稿 |
| 4 | [../AGENTS.md](../AGENTS.md) | AI 参与开发时的行为规范 | ✅ 定稿 |
| 5 | [architecture/](architecture/INDEX.md) 各模块篇 | 每个模块的内部设计 | ✅ 12 篇设计稿已入（随实现升定稿） |
| 6 | [specs/](specs/README.md) + [adr/](adr/README.md) | 关键决策为什么这么做 | ✅ 持续增补（索引见 adr/README.md 与 specs/README.md） |
| 7 | [plans/ROADMAP.md](plans/ROADMAP.md) | 演进路线与当前阶段 | ✅ active（随里程碑出口更新） |

## 目录规约

```
docs/
├── README.md                    # 本导航
├── PRD.md                       # 阶段 1：PRD/需求/指标（曾用名：aftermatter-项目设计文档.md）
├── REPO-LAYOUT.md               # 阶段 2：目录级契约（不锁文件名）（曾用名：aftermatter-项目结构.md）
├── DEVELOPMENT-PLAN.md          # 阶段 3：Phase 划分与验收（曾用名：aftermatter-开发计划.md）
├── architecture/                # 架构与契约（overview / data-model / modules / INDEX
│                                #   + 12 篇模块内部设计，随实现升定稿）
├── specs/                       # 带日期的专题决策与设计文档（较大粒度，时效性强）
├── adr/                         # 编号轻量决策记录（一页式：背景/决定/影响）
├── plans/                       # 演进计划与阶段快照
├── reports/                     # 里程碑收口报告（一次性记录，ADR-0014）
├── development/                 # 开发专题教程（按模块编号，随代码成熟补写）
├── tests/                       # 量化指标实测文档（需人工实测的场景）
├── benchmarks/                  # 基准测试报告（命名含日期）
└── api/                         # API 参考（模型导出 JSON Schema 后逐步生成）
```

**specs/ 与 adr/ 的分工**：specs/ 放"日期前缀的专题文档"（一次决策一份，含背景与边界，
如 `2026-09-21-dual-brain-and-deepening.md`）；adr/ 放"编号一页式轻量记录"（`NNNN-标题.md`，
只写 决定/理由/影响面）。拿不准放哪 → 先写 adr/，长到一页装不下再升 specs/。
**里程碑收口报告两者都不是**：写完了做了什么的那份去 `reports/`（ADR-0014）。

## 文档纪律

- **契约唯一来源**：数据模型以 `architecture/data-model.md` + `schemas/` 为准，其他文档只引用不复述；
- **变更顺序不可反**：契约/选型先改文档（specs/adr 记录）→ 代码跟随；
- 技术选型表（architecture/overview.md §5）变更必须先落 ADR；
- 命名约定：品牌展示体 **AfterMatter**；技术标识符一律小写 **aftermatter**。

## 文档规范

> 本节与 `scripts/doc_lint/` 同源于 **ADR-0011**，自动约束执行。新增文档前对照本检查项；
> `docs/**`、`AGENTS.md`、`CLAUDE.md` 任一改动都会触发 CI 门禁。

### 1. 语言分层（ADR-0011 决定 1）

| 层级 | 内容语言 | 文件名 | 适用位置 |
|------|---------|--------|---------|
| 门面 | 英文 | 英文 | `README.md`、`CONTRIBUTING.md`、`SECURITY.md`、`CHANGELOG.md` |
| AI 规范 | 双语镜像（例外） | 英文（约定俗成） | `AGENTS.md` + `CLAUDE.md` |
| 用户向 | 英文 | 英文 | `docs/development/*.md`、`docs/api/*.md` |
| 内部设计 | 中文 | 英文 | `docs/architecture/`、`docs/adr/`、`docs/specs/`、`docs/plans/`、`docs/reports/`、三份顶层规划文档 |
| 实测记录 | 中文 | 英文；`docs/tests/` 豁免中文文件名（ADR-0013） | `docs/tests/`、`docs/benchmarks/` |
| 目录索引 | 中文 | `README.md`（约定俗成） | 各子目录 README |

**核心**：内容与文件名解耦；文件名一律英文（唯一例外见下方 §2）。

### 2. 命名规则

| 类型 | 风格 | 例 |
|------|------|---|
| 顶层规划 | `<SCOPE>.md` 全大写连字符 | `PRD.md`、`REPO-LAYOUT.md`、`DEVELOPMENT-PLAN.md`、`ROADMAP.md` |
| 架构设计 | `<module>.md` 全小写 | `overview.md`、`data-model.md`、`modules.md`、`collectors.md` |
| ADR | `NNNN-<kebab-title>.md` 四位递增 | `0011-doc-language-and-standards.md` |
| Spec | `YYYY-MM-DD-<kebab-title>.md` | `2026-09-21-dual-brain-and-deepening.md` |

**禁用**：中文文件名（历史遗留已清零）、大小写混排（除 `README.md`/`ROADMAP.md` 等约定俗成例外）。
**唯一例外**：`docs/tests/` 下的实测文档可用中文指标名（ADR-0013 豁免，`policy_checker` 已机器化）；
再出现第二处豁免需求时，按该 ADR 的约定整体重议而非继续加白名单。

### 3. 头部元数据（每篇文档顶部必带）

```
状态: <Draft | Proposed | Accepted | 定稿 | 草稿 | Superseded by NNNN>
日期: YYYY-MM-DD   或   更新: YYYY-MM-DD
对应: <相关文档 Markdown 链接>   或   Related: <ADR/spec/任务号>
```

目录导航型 `README.md`（本文件与 `docs/{adr,specs,plans,development,tests,api,benchmarks}/README.md`）
可豁免头部元数据，但需含“收录标准/命名规则”。

### 4. `architecture/<module>.md` 必需四段

一模块一篇，固定四段（现有 12 篇已遵守）：

1. **职责边界**：一句话定义 + 明确不做什么（防模块自杀式膨胀）；
2. **内部结构**（或内部流程）：子单元、关键机制、数据流；
3. **错误与边界**（或错误策略）：失败降级、异常分类、外部约束；
4. **测试要点**：验证上面三段的最小测试集。

### 5. 交叉引用规则（ADR-0011 决定 3）

- **优先“文件名 + 章节标题”**：
  ✅ `[architecture/overview.md](architecture/overview.md) 的“§3 分层与依赖方向”`
  ❌ `见 §3`（裸节号无文件名；节号在文档重组时静默漂移。注：带文件名的 `overview.md §3`
  为可接受的次级形式，doc-lint 仅禁裸节号且本期未机器化，见 ADR-0011 决定 4）
- **引用 ADR 用编号+标题**：
  ✅ `ADR-0011 文档语言分层与写作规范`
  ❌ `adr/0001–0011 全部`（计数区间在新 ADR 入库后失效）
- **区间引用仅在描述历史事实时允许**（如 `adr/README.md` 的“`0001–0008` 为历史记录不回改”、
  ADR-0009 被否备选中的“回改 `ADR-0001–0008` 正文”）。示例区间内的反引号包裹会让 doc-lint 自动跳过。

### 6. 三处地图同步约束

AGENTS.md §三、CLAUDE.md §3、本文件“阅读地图”三处存在内容重叠（任务路由 vs AI 镜像 vs 阅读导览），
本次保留三处但**任一变更需三处同步**（ADR 触发条件 5 的具体化）。doc-lint 不自动校验，
评审人仍需人工对账。未来若漂移严重，另开 ADR 决定单一来源化。

### 7. 新增文档检查清单

- [ ] 文件名英文，命名落入 §2 四类之一；
- [ ] 头部元数据齐（§3）；
- [ ] 若为 `architecture/<module>.md`，四段完整（§4）；
- [ ] 相对链接可解析（doc-lint 会验证）；
- [ ] 交叉引用不用裸节号（§5）；
- [ ] 若引入新目录/模块，同步更新 `docs/architecture/INDEX.md` 或本文件目录规约；
- [ ] 若变更契约（数据模型/状态机/协议），先改 `architecture/data-model.md` 并递增版本号，后写代码。

## 溯源声明

评估模型（五维十五检查、证据状态、评分天花板）借鉴并改造自
[QoderAI/better-harness](https://github.com/QoderAI/better-harness)（MIT License）。
差异化主张（双大脑、修复+纵向验证闭环、执行级证据引擎）为本项目独立设计。
