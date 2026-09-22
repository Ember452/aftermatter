# M0 骨架阶段完成报告（T0.1–T0.5）

状态: 定稿（一次性收口记录，写完不追改） | 日期: 2026-09-22
对应: `docs/DEVELOPMENT-PLAN.md` 的「§3 任务分解 / §5 里程碑验收清单」、ADR-0012 M0 工程化工具链与依赖基线、
[ROADMAP.md](../plans/ROADMAP.md) 的「§1 当前阶段快照」

> **定位**：本报告是 M0 出口的一次性收口证据，不承担时效性状态。**"现在走到哪了"的唯一来源仍是
> ROADMAP §1**（§7 规定历史快照靠 tag 回溯、不另存副本）。后续事实变化不回改本文，如需修正请新起一份并互相引用。

---

## 0. 一句话结论

M0 把仓库从"只有设计文档"变成"有门禁、有依赖方向守卫、三平台 CI 全绿的可开发骨架"。
交付 **17 个新文件 + 10 个修改文件，10 个可独立回滚的 commit，tag 链第一环 `v0.1.0-m0-skeleton`**；
**没有交付任何产品功能**（这是 M0 的定义，不是缺口）。

---

## 1. 任务对照：计划 → 实际 → 验收

| ID | 计划内容（开发计划 §3 原文摘要） | 实际交付 | 验收命令与结果 |
|----|---|---|---|
| T0.1 | pyproject：src layout、依赖最小集、ruff/pyright/pytest 配置 | `pyproject.toml` 5 行 → 64 行完整配置；`uv.lock` 入库 | `uv sync --frozen` 成功，解析 12 包 ✅ |
| T0.2 | 包骨架：只建当期有代码的子包，`__init__` 导出公共 API | `src/aftermatter/__init__.py`（docstring + `__version__`）+ `py.typed`；**未建任何空子包** | `uv run python -c "import aftermatter"` → `0.1.0` ✅ |
| T0.3 | `tests/architecture/` import 方向守卫（依赖方向硬规则） | `test_import_direction.py` 257 行，5 条规则 + 注入自证 | `uv run pytest tests/architecture -q` → **14 passed** ✅；注入违规样例必红由 `tmp_path` 测试证明 |
| T0.4 | `.github/`：ci.yml（3.12/3.13 × 三平台）、dependabot、issue/PR 模板 | `workflows/ci.yml` 88 行、`dependabot.yml`、3 个 issue 模板、PR 模板 | 远端 `ci` run **35674200907**：`lint + typecheck` + 6 格 pytest 矩阵全 `success` ✅ |
| T0.5 | `.pre-commit-config.yaml`、`.gitignore`、LICENSE、CHANGELOG/CONTRIBUTING/SECURITY 骨架 | 全部落地 + 最小英文 `README.md`（M0 决策点 4） | `uvx pre-commit run --all-files` → 8 个钩子全 `Passed` ✅ |

**开发计划 §5「M0」四项验收：4/4 已勾选**（前 3 项本地证据，第 4 项远端 run 证据）。

计划外的两项必要工作（不属于任何 T 编号，但被验收命令要求）：

- **T0.1'：把既有 `scripts/doc_lint/` 拉进新门禁**。它是 Phase 0 的产物，在新配置下报 8 处违规 + 2 文件需重排，不修就 `ruff check .` 必红。
- **T0.2'：最小英文根 README**。`pyproject` 的 `readme`/`license` 元数据要求这两个文件存在，否则构建阶段直接失败。

---

## 2. 提交序列（每个 commit = 一个逻辑变更）

| # | commit | 类型 | 内容 | 依赖关系 |
|---|---|---|---|---|
| 0 | `2359e37` | `ci(docs)` | 把维护者手写的 4 处 YAML 注释移到所属键上一行，逻辑零改动 | 无 |
| 1 | `a0cf7c1` | `docs(adr)` | ADR-0012：工具链与依赖基线决策 | **先于一切依赖变更**（AGENTS §4.2） |
| 2 | `3c838cb` | `chore(m0)` | pyproject + uv.lock + 包骨架 + README + LICENSE | pyproject 元数据 ↔ 门面文件必须同批 |
| 3 | `a0e1652` | `style(scripts)` | doc_lint 过 ruff 门禁（纯风格） | **先于 commit 6**，否则 CI 必红 |
| 4 | `fe657a3` | `test(architecture)` | 依赖方向守卫 + 自证测试 | 依赖 commit 2（需可安装包） |
| 5 | `cf5d0c4` | `chore(m0)` | 社区文档 + pre-commit + .gitignore | 无 |
| 6 | `d1900d8` | `ci(m0)` | 三平台矩阵 + dependabot + 模板 | 依赖 2/3/4 全绿 |
| 7 | `4601546` | `docs` | 勾选 M0 前 3 项，第 4 项**留空并写明原因** | 推送前只声称本地证据 |
| 8 | `388526f` | `docs` | 远端跑绿后补第 4 项与 run id | 依赖 run 35674200907 结果 |
| 9 | `ace723d` | `docs` | tag 打点后闭合 ROADMAP §1 与 CHANGELOG 分组 | 依赖 tag 真实存在 |

**两段式勾选（7→8）是刻意的**：先推送拿证据，再据实记录，避免文档出现"承诺式已完成"。
tag 打在 `388526f`（M0 代码尖端），记录该 tag 的 commit 在其后——否则 tag 自引用。

---

## 3. 选型与理由（含被否方案）

完整决策链见 [ADR-0012](../adr/0012-m0-toolchain-and-dependency-baseline.md)，此处摘要对照：

| 议题 | 选择 | 理由 | 被否方案 |
|---|---|---|---|
| 构建后端 | **hatchling** + src layout | 与 `REPO-LAYOUT.md` 的「§1 顶层布局」一致；`[tool.hatch.version]` 支持从包内读版本 | setuptools（需手写 packages 发现）；uv_build（当期无收益） |
| 版本号来源 | `dynamic = ["version"]` + `src/aftermatter/__init__.py` | **单一来源**，杜绝 pyproject 与包内双写漂移 | 两处各写 `0.1.0` |
| 依赖声明 | PEP 735 `[dependency-groups].dev` | `uv sync` 默认安装，与"pre-commit 与 CI 同源"一致 | `[project.optional-dependencies].dev`（要 `--extra dev`） |
| 运行时依赖 | **保持为空 `[]`** | pydantic/typer/rich/httpx 等推迟到首次真正 import 的任务；技术选型表不是提前声明清单 | 现在照 overview §5 抄一张依赖表 |
| lint 规则集 | `E,F,I,UP,B,SIM`，`line-length = 100` | 规则集是 AGENTS §4.1 既定；取 100 因 ruff 按**码点**计宽，既有中文 docstring 在 88 下大面积误报 | 默认 88；关闭 E501 |
| Markdown 代码块 | `[tool.ruff] extend-exclude = ["docs"]` | **实测发现**：ruff 0.16 会格式化 ```python 围栏，要重写 `data-model.md`/`modules.md` 的示意代码，等于篡改契约文档 | 让 ruff 改文档；把门禁命令缩到 `src/ tests/`（破坏 DoD 一致性） |
| 类型检查强度 | pyright `standard` | 满足"公共 API 零错误"即可 | `strict`（成本花在 `reportUnknown*` 噪声上） |
| 依赖方向守卫 | **自建 stdlib `ast`** | 5 条规则数十行覆盖，可与注入样例同文件自证；零新依赖 | import-linter（多一个依赖 + 一份配置，modules §0 列为可选但非必选） |
| CI 结构 | `quality` 单实例 + `test` 六格矩阵 | lint/type 与平台无关，只有测试需要跨平台 | 每格跑全套（×3 倍额度换不到信号） |
| 锁文件 | 提交 `uv.lock`（11.7 KB / 12 包） | `REPO-LAYOUT.md` 的「§1 顶层布局」要求；CI 用 `--frozen` 锁死可复现 | 只锁 `pyproject` 区间 |
| pre-commit 依赖 | 用 `uvx pre-commit`，**不进 dev 组** | 避免与 `uv.lock` 形成工具版本双写 | 加入 dev 组 |
| 门面文件 | 英文，README 最小版 + pre-alpha 声明 | ADR-0011 语言分层；不放 badge、不放任何能力宣称 | 复制原版 README 结构（会吹出没有的功能） |

**工具实际版本**（`uv.lock` 固化）：ruff 0.16.8、pyright 1.1.414、pytest 9.1.1、pytest-asyncio 1.4.0；
运行时 uv 0.11.19 / CPython 3.13.7 / node v24.14.1（pyright 依赖 node）。

---

## 4. 文件清单与职责

### 新增（17）

| 文件 | 职责 |
|---|---|
| `docs/adr/0012-m0-toolchain-and-dependency-baseline.md` | 本阶段全部选型决策与被否备选（4 段模板 v2） |
| `pyproject.toml` | 唯一的项目元数据 + 工具配置（修改性质上是"扩展"，此处列作对照） |
| `uv.lock` | 依赖锁文件，CI `--frozen` 的锚点 |
| `src/aftermatter/__init__.py` | 包级 docstring（定位 + 分层规则指向）+ `__version__` 单一来源 |
| `src/aftermatter/py.typed` | PEP 561 类型标记 |
| `tests/architecture/test_import_direction.py` | **本阶段唯一的"功能"**：依赖方向守卫（详见 §5） |
| `README.md` | 英文门面：定位 + pre-alpha 诚实声明 + 文档入口表 + 非目标 |
| `LICENSE` | MIT |
| `CONTRIBUTING.md` | 环境 → DoD 四条命令 → 代码放哪（指向三份契约文档）→ commit/PR → 决策记录 → 语言分层 |
| `SECURITY.md` | 私有漏洞报告入口 + 隐私/沙箱边界 + **实现状态段（明确哪些还是契约不是保障）** |
| `CHANGELOG.md` | Keep a Changelog：`[Unreleased]` 常开 + `[0.1.0]` 按 tag 分组 |
| `.pre-commit-config.yaml` | 6 个基础钩子 + ruff(`--fix`) + ruff-format，rev 与 lock 主版本对齐 |
| `.github/workflows/ci.yml` | `quality`（ruff check / format / pyright）+ `test`（2×3 矩阵），paths 过滤与 docs 工作流互补 |
| `.github/dependabot.yml` | `uv` + `github-actions` 两生态，weekly |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | 版本/环境/复现/**期望须引用文档出处**/脱敏证据 |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | 含"是否改契约"下拉（把 ADR 触发条件前置到提需求时） |
| `.github/ISSUE_TEMPLATE/config.yml` | 关空白 issue + 两个导流链接 |
| `.github/PULL_REQUEST_TEMPLATE.md` | DoD 勾选 + `Refs T-x.x` + 契约/文档同步 + 隐私与诚实自查 |

### 修改（10）

`pyproject.toml`、`.gitignore`（+`doc-lint-report.json`）、`.github/workflows/docs.yml`（注释位置）、
`scripts/doc_lint/{_core,cli,adr_checker,link_checker,metadata_checker}.py`（过门禁）、
`docs/DEVELOPMENT-PLAN.md`（§5 M0 勾选）、`docs/plans/ROADMAP.md`（§1 快照）、
`CHANGELOG.md`/`README.md` 属新增不重复计。

---

## 5. 实现了什么功能

严格说，M0 交付的是**工程能力**而非产品功能。可验证的能力清单：

**① 依赖方向守卫（T0.3，本阶段唯一的实质代码）**

`tests/architecture/test_import_direction.py` 用 `ast` 解析 `src/aftermatter/**/*.py`，机器化五条原本只活在文档里的规则：

| 规则 | 来源 | 违规形态 |
|---|---|---|
| R1 分层秩 | overview 的「§3 分层与依赖方向」 | `core`(L0) import `analysis`(L2) 等 |
| R2 采集不可越过证据层 | overview §3 第 2 条 | `analysis` 直连 `collectors`（防二次采集造成证据漂移） |
| R3 装配层不可被依赖 | `REPO-LAYOUT.md` 的「§8 反模式清单」 | 任何模块 import `serve`/`daemon`（含 `cli`，放宽需另开 ADR） |
| R4 适配器隔离 | `REPO-LAYOUT.md` 的「§2 目录规则」 | `collectors.claude` ↔ `collectors.codex` 互 import |
| R5 顶层目录白名单 | overview §3 + REPO-LAYOUT §2 | import 或**存在**清单外的顶层子包（把"禁止 `utils/`、`common/`、`helpers/`、`base/`"从口头约束变成红灯） |

工程设计要点：

- **可注入根路径的纯函数**（`_violations_for_source(module, source)` / `_collect_violations(root)`），使"注入违规必红"能自动化：负向用例走 `tmp_path`，**违规文件不入库**；
- 相对导入按所在包展开（`from ..analysis import x` 会被抓），绝对导入不再拼前缀；
- 层级表把 `migrations` 标为不参与分层秩比较（版本化脚本序列，非架构层），避免 M4 落地时误报。

为什么这条最重要：M0 的 `src/` 只有一个 `__init__.py`，"零违规"是**必然**的——守卫必须先证明自己有牙齿，否则它是假绿的核心来源。

**② 门禁闭环**：本地四条 DoD 命令 = CI 命令 = pre-commit 命令，同一套配置单一来源（`pyproject.toml`）。
**③ 可复现环境**：`uv sync` → 12 包装好、包可 import、`--frozen` 保证 CI 与本地一致。
**④ 文档一致性门禁未被破坏**：doc-lint 在本阶段全部改动后仍 0 违规（ADR-0012 满足 adr_checker 的编号/字段/四段要求）。

**明确没有实现的东西**（防误读）：任何 CLI 命令、任何宿主会话解析、EvidenceBundle/ERef、评分与状态机、报告渲染、LLM 调用、修复与台账、沙箱、服务端。铁律 1（M2 前不写任何 LLM 代码）保持完好。

---

## 6. 验证证据

### 本地（PowerShell，全部实际执行）

```
uv run ruff check .            → All checks passed!                 (exit 0)
uv run ruff format --check .   → 18 files already formatted         (exit 0)
uv run pyright                 → 0 errors, 0 warnings, 0 informations
uv run pytest tests/architecture -q → 14 passed in 0.04s
uv run python -m doc_lint --root .  → doc-lint: OK (no violations)  (exit 0)
uvx pre-commit run --all-files → 8 钩子全 Passed                    (exit 0)
uv sync --frozen               → Resolved 12 packages, Built aftermatter 0.1.0
```

行为不变的附加证据：doc_lint 改动前后 `--json` 报告均 `violation_count: 0`（证明 §1 的 T0.1' 是纯风格改动）。

### 远端（GitHub REST API 实测）

```
ci   run 35674200907 @ main/4601546  completed / success
     lint + typecheck                            success
     pytest (ubuntu|windows|macos × 3.12|3.13)   6 格全 success
docs workflow @4601546 / @388526f / @ace723d      success
tag  refs/tags/v0.1.0-m0-skeleton → 对象 72da320, type=tag（annotated，已推送）
open PRs: 0（dependabot 跑了 4 个 update 检查任务且全绿，未产出 PR）
```

### 已知偏差（写进文档而非藏起来）

`uv run pytest tests/unit -q`（DoD 第四条）**在 M0 不可执行**：`tests/unit/` 依"未用先建"尚未创建，实测
`ERROR: file or directory not found: tests/unit / exit=4`。M0 以 `tests/architecture` 替代，M1 T1.1 起恢复原命令。
CONTRIBUTING.md 与本报告的表述均按此事实书写，未把"DoD 全绿"说成字面四条都跑过。

---

## 7. 计划外发现（三条，均已处置）

1. **ruff 0.16 会格式化 Markdown 围栏**。首次跑全仓 `ruff format --check .` 时它要重写
   `docs/architecture/data-model.md` 与 `modules.md` 里的 `python` 示意代码块（拆
   `host: str; model_versions: ...`、重排中文注释对齐）。规划阶段只按 `scripts/` 做过基线，没暴露这条 → 处置：
   `extend-exclude = ["docs"]` 并在 pyproject 注释里写明原因（docs 归 doc-lint 管）。
2. **守卫第一版有真 bug**：绝对导入 `from aftermatter.analysis import x` 被误拼上导入方的包前缀，
   导致 10 条注入用例里 7 条漏报，同时让真实 `src` 树因 `from __future__ import annotations` **假报**违规。
   两处都是测试先抓出来的——若按计划只跑"扫真实目录断言零违规"，这个 bug 会一路带到 M1 并使守卫彻底失效。
3. **新增第三方依赖会触发 AGENTS §4.2 的 ADR 前置义务**。计划评审时漏了这一条，实施前补出 ADR-0012；
   它同时成为"先改文档、代码跟随"纪律的第一次实际执行。

---

## 8. 遗留问题（发现项与处置）

1. `docs/README.md` 称 ADR 索引见 `docs/adr/README.md`，但后者实际只有命名规则与模板 v2，**没有 ADR 清单**。
2. `DEVELOPMENT-PLAN.md` §5 的 M0 验收项写成 `cmd && cmd`，本机 PowerShell 不支持 `&&`，照抄必失败。
3. **`docs/tests/README.md` 与 ADR-0011 / policy_checker 存在确定性冲突**：它规定实测文档命名为
   `指标测试-<模块>.md`（中文文件名），而 ADR-0011 决定 2 要求"文件名一律英文"，且 `policy_checker`
   会扫 `docs/` 下**所有**文件名并把中文名判违规——即"照文档写出来的文件必然让 CI 变红"。
   **本报告的同一批改动已裁决落地**：维护者选择保留中文指标名，ADR-0013 开出全仓唯一豁免并由
   `policy_checker` 机器化；实测双向验证通过（`docs/tests/` 中文名不判违规、`docs/benchmarks/`
   中文名仍判违规），并同步修订了 `docs/README.md` 的分层表与命名规则、`docs/tests/README.md`
   的依据说明和 ADR-0011 决定 2 的括注。
4. commit type 白名单（REPO-LAYOUT §5 只列 6 种）与仓库历史（`ci(docs)`、`scripts(doc-lint)`）不一致，
   已在 ADR-0012 的「影响」登记，未回写 REPO-LAYOUT。
5. ROADMAP §1 原"M0 出口后确认 D-2/D-3"与 §6 表内期限（T5.5 前 / T5.1 前）不一致，本次已按 §6 对齐并
   在文中标注原因（决策实质未变）。

---

## 9. 对 M1 的交接

| 事项 | 说明 |
|---|---|
| 起点 | T1.1 core 五件套：时间规范化、sha256 稳定指纹、路径归一、TraceId 日志、异常基类树（契约见 `docs/architecture/core.md` + `data-model.md`） |
| 目录解锁 | T1.1 落地时才能建 `src/aftermatter/core/`（守卫 R5 会拒绝任何清单外顶层包） |
| 首个 runtime 依赖 | T1.2 的 ERef/Bundle 模型需要 **pydantic v2**，届时按 AGENTS §4.2 说明加依赖的理由（overview §5 已定选型，无需新 ADR） |
| DoD 恢复 | `tests/unit/core/` 建起来后，第四条门禁命令回到 `uv run pytest tests/unit -q` 原文 |
| 已就位的基础设施 | 门禁/CI/锁文件/守卫/模板齐备，M1 无需再碰工程化 |
| 风险预警 | T1.3/T1.4 的黄金 fixture（各 ≥20 条，含畸形/截断/编码陷阱）是**关键路径且不可砍**；fixture 与标注必须先于实现（开发计划 §1 铁律 3） |
| tag 链 | 已开环 `v0.1.0-m0-skeleton`；M1 出口为 `v0.2.0-m1-evidence-kernel`（ADR-0006），打 tag 仍需批准 |
