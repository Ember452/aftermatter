# ADR-0012: M0 工程化工具链与依赖基线

状态: Accepted | 日期: 2026-09-22
Related: T0.1–T0.5、ADR-0006 里程碑 tag 命名、ADR-0010 tests 布局、ADR-0011 文档语言分层

## 背景

M0 要把仓库从"只有文档"变成可开发骨架，一次性确定构建后端、依赖声明位置与
lint/format/type/test 四套工具的配置，并为此引入 5 个第三方工具；同时
`architecture/overview.md` 的「§3 分层与依赖方向」硬规则需要一个能进 CI 的机器化守卫，
而守卫有"引库"与"自建 AST"两条路。AGENTS §4.2 规定新增第三方依赖必须先落 ADR。

## 决定

1. **构建后端 hatchling**（src layout）；版本号单一来源：`[tool.hatch.version] path`
   指向 `src/aftermatter/__init__.py`，pyproject 侧用 `dynamic = ["version"]`。
2. **dev 工具走 PEP 735 `[dependency-groups]`**（`uv sync` 默认安装）：ruff、pyright、
   pytest、pytest-asyncio。runtime `dependencies` 保持为空——pydantic/typer/rich/httpx 等
   推迟到首次真正 import 它们的任务；技术选型表是默认选型而非提前声明清单。
3. **ruff `line-length = 100`**，规则集 `E,F,I,UP,B,SIM`。取 100 而非默认 88：CJK 字符按
   码点计宽，既有中文 docstring/注释在 88 下大面积误报（实测 8 处违规中 3 处为此类）。
4. **pyright `typeCheckingMode = "standard"`**：满足"公共 API 零错误"，不一步到 strict。
5. **import 方向守卫自建**（stdlib `ast`）：规则 = 分层秩（overview「§3 分层与依赖方向」＋
   modules「§0 模块划分」总序，`sandbox` 归判断与产物层）+ `analysis` 不得越过 evidence
   直连 `collectors` + 任何模块不得 import `serve`/`daemon`（REPO-LAYOUT「§8 反模式清单」）
   + 宿主适配器子包互不 import + 顶层子包名必须落在 REPO-LAYOUT §2 白名单内（顺带把
   "禁止 `utils/`/`common/`/`helpers/`" 机器化）。守卫用 `tmp_path` 注入违规样例自证拦截力，
   违规文件不留存仓库。
6. **CI 成本分层**：`quality` job 单实例（ubuntu 跑 ruff + ruff format + pyright），
   只有 `test` job 跑 3.12/3.13 × ubuntu/windows/macos 六格矩阵。
7. `migrations` 不参与分层秩比较（版本化脚本序列，非架构层）；`cli` 将来若确需 import
   `daemon`/`serve` 做装配，另开 ADR 放宽规则 3，不在实现期偷偷加豁免。

## 影响

- `pyproject.toml` 从 5 行扩为完整配置；新增 `src/aftermatter/`（`__init__.py` + `py.typed`）、
  `tests/architecture/`、`.github/workflows/ci.yml`、`dependabot.yml`、issue/PR 模板、
  `.pre-commit-config.yaml` 与根级英文门面文档（README/LICENSE/CHANGELOG/CONTRIBUTING/SECURITY）。
- 既有 `scripts/doc_lint/` 被新门禁追溯修正（8 处 lint + 2 处 format），纯风格改动，
  以 doc-lint `--json` 报告前后一致作为行为不变的证据。
- `pre-commit` 经 `uvx pre-commit run --all-files` 运行，不进 dev group：避免与 `uv.lock`
  形成工具版本双写；DoD 仍以本地四条命令为准（AGENTS §4.1）。
- 推迟登记（各有归属里程碑，不提前建）：`release.yml`（M6）、adversarial 独立 CI job
  （M5 T5.8）、`.python-version`、doc-lint 进 pre-commit、把 `doc_lint` 打包成
  console-script（`docs.yml` 注释里预留的未来项）。
- commit type 白名单在 `REPO-LAYOUT.md` §5 与实际历史（`ci(docs):`、`scripts(doc-lint):`）
  之间存在偏差；本次沿用历史写法，白名单待后续文档整理统一，不静默改文档。

## 被否备选

- **引入 import-linter**（modules §0 列为可选实现）：多一个依赖与一份配置，而上述规则
  用 stdlib `ast` 数十行即可覆盖，还能与注入样例同文件自证；与"刻意极简"冲突。
- **`[project.optional-dependencies].dev`**：需 `uv sync --extra dev` 才安装，与
  "pre-commit 钩子与 CI 用同一套命令"的同步性相抗。
- **M0 就建齐 13 个顶层子包**：违反 REPO-LAYOUT「未用先建」，空包还会让守卫的
  "零违规"更假。
- **pyproject 与 `__init__.py` 各写一个版本号**：双写必然漂移。
- **现在声明 pydantic/typer/rich/httpx 等 runtime 依赖**：无当期消费者，白白锁死版本面。
- **pyright 直接 strict**：成本花在 `reportUnknown*` 噪声上，M0 无收益。
- **把 doc-lint 塞进 pre-commit local hook**：需 `PYTHONPATH=scripts`，PowerShell 与
  POSIX 的环境变量注入写法不一致；CI 的 docs 工作流已是同源门禁。
