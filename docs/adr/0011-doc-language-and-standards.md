# ADR-0011: 文档语言分层与写作规范

状态: Accepted | 日期: 2026-09-21
Related: ADR-0002（品牌/技术标识符大小写约定）、ADR-0009（模板 v2 起点）、
ROADMAP §6 D-6（本 ADR 关闭之）、`docs/README.md`（阅读地图）、
`docs/REPO-LAYOUT.md` §4（docs 目录契约）

## 背景
2026-09 全量文档审计发现三类长期漂移成本：
① 硬编码的 ADR 计数（如 "adr/0001–0006"、"adr/0001–0008"）在每次
新增 ADR 后失效，AGENTS.md、CLAUDE.md、docs/README.md、ROADMAP.md
四处同一句已过期；② 顶层三份规划文档中文命名（`aftermatter-项目
设计文档.md` 等）与 "本项目面向国际开源社区"（AGENTS §五）定位冲突，
GitHub 首页观感偏内部化；③ 交叉引用大量使用节号 `§X`（如
"见 overview.md §3"），节号在文档重组时静默漂移、无脚本可校验。
三份顶层文档与 AGENTS/CLAUDE 的"文档地图"内容重复出现，双写风险高。

## 决定
1. **分层双语**：门面文档（`README.md`/`CONTRIBUTING.md`/
   `SECURITY.md`/`CHANGELOG.md`）与面向用户文档（`docs/development/*`、
   `docs/api/*`）用英文；面向维护者的内部设计（`docs/architecture/`、
   `docs/adr/`、`docs/specs/`、`docs/plans/`）用中文；`AGENTS.md` 与
   `CLAUDE.md` 保持双语镜像例外（不同 AI 宿主读取不同文件名）。
2. **文件名一律英文**（后续例外：`docs/tests/` 实测文档的中文指标名，由 ADR-0013 豁免
   并在 `policy_checker` 机器化）：三份顶层文档改名——
   `aftermatter-项目设计文档.md` → `PRD.md`；
   `aftermatter-项目结构.md` → `REPO-LAYOUT.md`；
   `aftermatter-开发计划.md` → `DEVELOPMENT-PLAN.md`。
   改名用 `git mv` 保留 blame 连续性，头部加"曾用名"提示行。
3. **写作规范**（补进 `docs/README.md` "文档规范"章节）：
   - 头部元数据必备：`状态: <Draft|Proposed|Accepted|定稿|草稿|Superseded by NNNN>`
     + `日期` 或 `更新: YYYY-MM-DD` + `对应/关联` 链接；
   - `architecture/<module>.md` 必需四段：职责边界 / 内部结构 /
     错误与边界 / 测试要点（现有 12 篇已遵守；当前为人工评审依据，
     暂未由 doc-lint 机器化，见决定 4）；
   - 交叉引用优先 `[名称](路径)` + 章节标题（如"见 overview.md 的
     §3 分层与依赖方向"），**禁止只写节号**（如"见 §3"）；
   - 引用 ADR 用编号+标题（`ADR-0011 文档语言分层`），禁止用计数
     区间（"0001–0011 全部"）；区间引用仅在描述历史事实时允许
     （如 "0001–0008 为历史记录不回改"）。
4. **doc-lint 自动化门禁**：`scripts/doc_lint/` 检查相对链接可解析、
   ADR 编号连续与必需字段齐全、`INDEX.md` 与实际文件一致、头部元数据
   存在、政策违规（中文文件名、硬编码区间引用）。裸节号检测因误伤率高
   缓办（本期不实现，见 policy_checker 模块注释；人工评审依据决定 3）。CI 门禁化。
5. **D-6 关闭**：ROADMAP §6 D-6 状态改为 `Closed by ADR-0011`。

## 影响
- 3 份文件改名 + 20 处交叉引用同步（AGENTS.md/CLAUDE.md/docs/README.md/
  architecture/{INDEX,overview,data-model,modules}.md/docs/plans/ 全量清单
  见对应改动 commit）；
- `docs/README.md` 新增"文档规范"章节；
- `scripts/doc_lint/`（新目录，6 个检查模块 + CLI）+
  `.github/workflows/docs.yml`（新独立工作流）；
- ROADMAP §6 D-6 关闭；
- AGENTS.md §三、CLAUDE.md §3、`docs/README.md` 三处"文档地图"本次保留
  （AGENTS/CLAUDE 是 AI 任务路由表、docs/README.md 是用户阅读地图，
  语义不同），但 `docs/README.md` 新增"文档地图同步约束"段，明确任一
  变更需三处同步，作为 ADR 触发条件 5（跨文档不一致）的具体化提示；
  未来若漂移严重，另开 ADR 决定单一来源化。

## 被否备选
- **全量中英双份（80 个文件）**：Better Harness 的 `docs/specs/` 有 286
  篇全部英文单份、只有 `docs/i18n/zh-Hans/` 下 13 篇用户向文档做中文；
  CLAUDE.md 一份镜像已让人感受到同步成本；单人项目 80 文件不可持续。
- **全量改英文（内部设计也英文）**：撰写速度下降；核心读者是自己 +
  中文 AI 宿主（Qoder/Cursor），中文表达精度更高。
- **保持中文文件名不动**：与 "面向国际 OSS" 定位矛盾；现在零代码期改名
  成本最低，M0 起代码引用文档路径会引入更多改动点。
- **合并 AGENTS/CLAUDE/docs-README 三处地图为单一来源**：三者语义不同
  （AI 任务路由 / 用户阅读导览 / AI 镜像），强行合一会失去各自定位；
  且 CLAUDE.md 有"不同宿主读取不同文件名"的例外约束。
- **只写规范不写脚本**：ROADMAP D-6 明确指出这是漂移风险已知项；无脚本
  约束的规范在单人项目里等同口头协议，三个月后必然失效。
- **doc-lint 只本地 pre-commit 不进 CI**：单人项目 pre-commit 最容易被
  `--no-verify` 跳过；AGENTS §四.1 已声明 "pre-commit 与 CI 用同一套命令，
  本地全绿 ≠ 可以跳过"。
- **现在引入 Docusaurus/Sphinx 建文档站**：属二期动作（ROADMAP §3 触发制），
  一期无用户读者群，投入产出比低。
