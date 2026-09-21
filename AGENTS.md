# AGENTS.md — AfterMatter 开发规范

面向 AI 辅助开发的行为准则与项目约束。与各任务的临时指示合并使用；冲突时本文件优先。

**取舍说明**：以下规范偏向谨慎而非速度。琐碎任务（改错别字、加一行日志）可自行裁量，
但拿不准时按规范执行。

---

## 一、项目总体定位（每次会话先对齐）

**AfterMatter 是什么**：Evidence-based review of AI coding agent workflows——读取编码 Agent
本地会话（Claude Code/Codex/Cursor/Qoder）与仓库证据，按五维 Agent Work Loop 产出
"每条断言可指回原始字节"的改进发现，并以有界修复 + 纵向统计验证闭环。

**不是什么**（防 scope 漂移，评审时对照）：
- ❌ LLM tracing / observability 大盘（红海，明确放弃）
- ❌ 编码 Agent 框架本身（我们是审查者，不是执行者）
- ❌ 模型能力评测榜单

**三条产品级铁律**（任何实现不得违背）：
1. 诚实呈现：没有证据的断言不写，证据缺口显式标注 `Unobserved`，不臆断评分；
2. 模型提议、工具裁决：LLM 只能产出 candidate，severity/分数/状态迁移由确定性代码判定；
3. 双大脑同契约：大脑①（宿主寄生）与大脑②（自带引擎）消费同一 EvidenceBundle、
   产出同一 Finding schema——契约不可因实现便利而分叉。

命名：品牌展示体 **AfterMatter**；一切技术标识符小写 **aftermatter**（包名/import/CLI/目录）。

## 二、行为规范

### 1. Think Before Coding —— 先想清楚再动手

不假设，不隐藏困惑，主动暴露权衡。

- 实现前先陈述假设；不确定就问。多种解读并存时摆出选项，**不要默默替用户选**。
- 有更简单的做法就直说；认为方案有问题就提出反对意见，即使用户已经"定了"。
- 有不清楚的地方就停下来，指明困惑点，提问。
- 契约类改动（数据模型、状态机、消息协议）**先改文档，代码跟随**——顺序不可反。

### 2. Simplicity First —— 简单优先

用解决问题的最少代码，不做任何投机性设计。

- 不写超出要求的功能；单次使用的代码不做抽象。
- 不做未被要求的"灵活性/可配置性"；不为不可能发生的场景写错误处理。
- 写了 200 行而 50 行能解决的，重写。
- 自问："资深工程师会觉得这里过度设计吗？" 会，就简化。

### 3. Surgical Changes —— 外科手术式修改

只动必须动的，只清理自己制造的。

- 不"顺手改进"相邻代码、注释、格式；不重构没坏的东西。
- 跟随既有风格，即使你有不同偏好；发现无关死代码：**提出来，不要删**。
- 你的修改产生的孤儿 import/变量：清理；既有死代码除非被要求否则不动。
- 目录内文件怎么拆由实现者自定，但**禁止 `utils/`、`common/`、`helpers/` 兜底目录**
  （`core/` 只收时间/哈希/路径/日志/异常五类真基础件）。
- 检验标准：**每一行改动都能直接追溯到当前任务编号（T-x.x）或用户指令。**

### 4. Goal-Driven Execution —— 目标驱动执行

先定义成功标准，循环到验证通过。

- "加校验" → "先写非法输入的测试，再让它通过"；"修 bug" → "先写复现测试，再修"。
- 多步任务先给计划：`1. [步骤] → 验证: [检查方式]`。
- 每个任务对照 `docs/aftermatter-开发计划.md` 第 3 章的验收列自证完成，
  **不接受"看起来能跑"作为完成证据**。

### 5. Decision Capture —— 关键决策动手前留痕

**触发清单**（任一命中即必须先写决策记录，再动手）：

1. 改变数据契约 / 状态机 / 消息协议（同时适用"先改 data-model.md"规则，两者并存：
   ADR 记"为什么改"，data-model 记"改成什么样"）
2. 技术或依赖选型变更（含 overview.md §5 选型表）
3. 砍单或范围变更（启用开发计划 §3 砍单预案、PRD 需求调整）
4. 实现与文档矛盾，需要现场裁决
5. 发现文档之间的不一致（裁决结果必须回写修正两处文档）

**规矩**：动手前在 `docs/adr/` 写一页记录（`NNNN-标题.md` 递增编号，模板见其 README）；
一页装不下升 `docs/specs/`（日期命名）。后续对应 commit footer 必须带 `Refs ADR-NNNN`。
**未留痕的此类改动，评审直接打回。**历史决策见 `docs/adr/0001–0006` 与 `docs/specs/`。

## 三、文档地图（开发前按任务路由，未读架构文档禁止改核心模块）

| 要做的事 | 必读（按序） |
|---------|-------------|
| 任何任务开工前 | `docs/aftermatter-开发计划.md`（本任务行 + 第 1 章执行协议） |
| 改数据模型/状态机 | `docs/architecture/data-model.md`（契约源头）→ 先改文档并递增版本号 |
| 新增/修改采集适配器 | `docs/architecture/collectors.md` → `modules.md` §2 → `data-model.md` §1 → fixture 目录 |
| 改分析引擎/多 Agent | `docs/architecture/analysis.md` → `overview.md` §1/§6 → `modules.md` §5 |
| 改修复/沙箱/纵向验证 | `docs/architecture/repair.md` / `sandbox.md` / `longitudinal.md` → `overview.md` §4.2 |
| 其他模块 | 同名内部设计篇，12 篇一览见 `docs/architecture/INDEX.md` |
| 放不进上面任何一行 | 先在 `docs/adr/` 写一条轻量决策，再动手 |

全局入口：`docs/README.md`（七阶段阅读地图）。依赖方向硬规则：`docs/architecture/overview.md` §3，
违规由 `tests/architecture/` 强制。

## 四、代码质量约束

### 4.1 质量门禁（每个任务完成的定义，DoD）

```bash
uv run ruff check .            # lint：E,F,I,UP,B,SIM 规则集（配置见 pyproject.toml）
uv run ruff format --check .   # 格式：ruff-format（black 兼容），不通过就 `ruff format .` 后重跑
uv run pyright                 # 类型：公共 API 零错误；新代码禁止新增 # type: ignore
uv run pytest tests/unit -q    # 单测：本任务测试绿 + 全量 unit 不回退
```

涉及集成/契约改动加跑：`uv run pytest tests/integration -q`；
涉及 import 方向/模型不可变性加跑：`uv run pytest tests/architecture -q`。
**pre-commit 钩子与 CI 用同一套命令，本地全绿 ≠ 可以跳过。**

### 4.2 编码纪律

- **类型注解**：公共 API 必须标注；跨边界数据一律 pydantic v2 模型，禁止裸 dict 传递。
- **异步纪律**：事件循环内禁止阻塞调用（同步 IO、`time.sleep`、同步 requests）；
  所有 IO 有超时；`asyncio.CancelledError` 必须放行，不得吞掉。
- **错误处理**：只捕获预期中的具体异常（用 `core` 的 AfterMatterError 异常树分类），不裸写 try/except；
  LLM 调用沿用 providers 层错误分类，不在业务层重复分类。
- **日志**：用 `logging` 不用 `print`；结构化字段带 `trace_id`；写"发生了什么+关键参数"，
  不写情绪化评论。
- **注释**：只写代码本身说不出来的"为什么"（约束、取舍、坑），不复述代码在做什么。
- **测试**：新功能必须带测试；fixture 与标注**先于实现**（尤其适配器/分类器/统计模块）；
  LLM/网络/文件系统全部 fake 隔离；pytest-asyncio auto 模式。
- **依赖**：新增第三方依赖前先看 pyproject 与 `overview.md` §5 选型表；
  **加依赖必须先在 docs/adr/ 落一条记录并在 commit 正文说明理由**。

### 4.3 项目特有红线

1. **M2 完成前不写任何 LLM 调用代码**（开发计划铁律）。
2. **`tests/adversarial/` 用例只增不减**；任何让对抗用例变绿的"修改用例本身"行为视为作弊。
3. `replay_ok` 只允许 sandbox 回填（唯一入口函数）；`severity` 只允许 Lead 赋值；
   `verified/regressed` 只允许状态机驱动迁移——**旁路写入 = 契约破坏，直接打回**。
4. 原始会话、prompt 全文、真实路径**永不进入**出机数据与测试 fixture。
5. 契约文档（data-model.md）与 schemas/ 是唯一事实源，其他文档只引用不复述。

## 五、Git 与 Commit 规范

**未经允许，绝对禁止 `git commit` 与 `git push`。** 阶段任务（T-x.x / 里程碑）完成后：
汇报改动清单与测试结果 → **询问**是否 commit/打 tag → 按用户指示执行；用户未答复前不提交。

Commit message 一律使用 **英文 Conventional Commits**（本项目面向国际开源社区）：

```
<type>(<scope>): <imperative, lowercase, no period, ≤72 chars>

[optional body: what changed + WHY, wrapped at 72]
[optional footer: Refs T-x.x / ADR-NNNN]
```

- type：`feat` / `fix` / `refactor` / `test` / `docs` / `chore` / `perf`
- scope：模块目录名（`collectors`、`episodes`、`evidence`、`analysis`、`repair`、
  `longitudinal`、`report`、`serve`、`daemon`、`cli`、`ci`、`docs`）
- **粒度标准**：一个 commit = 一个逻辑变更 = 可独立回滚。实现与其测试同一个 commit
  （`feat(collectors): add claude adapter with fixture coverage`）；
  禁止"改了 5 个模块攒一个巨型 commit"，也禁止"每保存一次提交一次的碎片化"。
- 描述写"为什么变"优于"改了哪个文件"；body 说明影响面与对照的任务编号。
- tag：里程碑出口时打 `v0.N.0-<milestone>`（如 `v0.1.0-m0-skeleton`、`v0.2.0-m1-evidence-kernel`，序列见 ADR-0006），打 tag 同样需询问。

示例（好 / 坏）：

```
# 好：范围清晰、说明动机、可回滚
fix(episodes): split episodes on new-task prompt even within gap window

Prompt-only continuations were merging unrelated goals into one episode,
breaking acceptance-boundary claims in Change Validation.
Refs T1.7

# 坏：巨型/含糊
update stuff
```

## 六、会话收尾自检清单

每次任务报告完成前逐项确认：

- [ ] 四条 DoD 命令实际运行过且全绿（贴输出，不转述）
- [ ] 改动行可追溯到任务编号或用户指令，无"顺手"修改
- [ ] 契约类改动：文档先改、版本号已递增
- [ ] 没有新增 print / 裸 except / 无超时的 IO / 未标注的公共 API
- [ ] 孤儿代码已清理（自己制造的），无关死代码只报告不删除
- [ ] 下一步建议（如有）写清楚，**不擅自开始下一个任务**

这些规范生效的标志：diff 里多余改动变少、因过度复杂而重写的次数变少、
澄清问题发生在实现之前而不是犯错之后。
