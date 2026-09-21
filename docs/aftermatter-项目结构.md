# AfterMatter 项目结构

状态: 定稿 | 层级: 目录级契约（本文档只锁"目录与职责"，**不锁文件名**）

> 定位：阶段 2 文档，回答"仓库长什么样、新代码放哪里"。
> 模块内部职责见 architecture/modules.md；依赖方向硬规则见 architecture/overview.md §3。
> **文件级布局由实现者自定**：只要目录职责不越界、依赖方向不违规，目录内怎么拆文件
> 不需要回来改本文档——这是防止"文档写死实现"的边界约定。

---

## 1. 顶层布局（对标成熟 Python 开源大项目：src layout + uv + 单一 pyproject）

```
aftermatter/
├── pyproject.toml               # 唯一的项目元数据 + 依赖 + 全部工具配置（ruff/pyright/pytest）
├── uv.lock                      # 锁文件（uv 管理，提交入库）
├── LICENSE                      # MIT
├── README.md                    # 英文主 readme（获客面）
├── README.zh-CN.md              # 中文 readme（预留，与主 readme 同步维护）
├── CHANGELOG.md                 # Keep a Changelog 格式，Unreleased 区常开
├── CONTRIBUTING.md              # 贡献流程：环境→分支→commit 规范→测试要求→PR
├── SECURITY.md                  # 漏洞报告渠道 + 沙箱/隐私边界声明
├── AGENTS.md                    # 阶段 4 文档：AI 参与开发的行为规范
├── .gitignore
├── .pre-commit-config.yaml      # ruff + ruff-format + 基础检查，本地与 CI 同源
├── .github/                     # CI workflows / issue & PR 模板 / dependabot
├── docs/                        # 文档体系（§4）
├── src/aftermatter/             # 唯一发布包（§2）
├── tests/                       # 测试（§3）
├── scripts/                     # 仓库维护脚本，不进 wheel、不含产品逻辑
├── schemas/                     # 版本化对外契约（JSON Schema，由模型导出生成）
└── skill/                       # 大脑①寄生入口资产（SKILL.md 等，随包作为 package data 分发）
```

**顶层不设**：`examples/`（并入 docs）、`benchmarks/`（需要时进 tests/ 旁挂）、
根级散落脚本、`src/` 下的第二个包。

## 2. src/aftermatter 模块骨架（目录级，内部文件自由）

```
src/aftermatter/
├── core/            # 基础设施：时间、哈希指纹、路径归一、日志与 TraceId、异常基类
├── collectors/      # L0 采集。每个宿主一个子包（claude/ codex/ cursor/ qoder/），
│                    #   仓库证据扫描独立子包（repo/）
├── episodes/        # L1 重建：Episode 切分、事件分类、可比性特征
├── evidence/        # L2 契约：全部跨层 pydantic 模型的唯一定义处；
│                    #   Bundle 冻结、完整性清单、脱敏管道
├── analysis/        # 判断层（大脑）
│   ├── deterministic/   # 零 LLM 基线评分器
│   ├── engine/          # 大脑②多 Agent 编排（专家/裁决/预算等子包自定）
│   ├── mcp/             # 大脑① MCP 只读工具面
│   └── providers/       # LLM 客户端薄封装与错误分类
├── repair/          # 有界修复：方案校验、白名单引擎、dry-run/apply
├── sandbox/         # 执行级证据：容器环境、重放策略、限额
├── longitudinal/    # 纵向验证：历史库、Ledger、Episode 匹配、单轴归因、统计
├── report/          # 渲染：报告模型校验、HTML/Markdown 输出
├── serve/           # 服务端（一期骨架）：API、模型、迁移
├── daemon/          # 本地常驻：定时驱动、上传管道
├── cli/             # 命令行入口（typer app，只做参数解析与装配调用）
└── migrations/      # schema/DB 版本迁移
```

目录规则：

- **新增顶层功能域 = 新子包 + `__init__.py` 公共 API + docs/architecture/ 一篇内部设计**，
  三者同 PR 落地；
- 子包内部结构（拆几个文件、文件叫什么）不设约束，跟随职责命名；
- 禁止 `utils/`、`common/`、`helpers/`、`base/`（core 除外，且 core 只收
  时间/哈希/路径/日志/异常五类真基础件）；
- 宿主适配器子包之间不得互相 import（防格式逻辑串味）。

## 3. tests 布局（镜像 + 特殊区）

```
tests/
├── unit/                  # 镜像 src 包结构；LLM/FS/网络全 fake
├── integration/           # 跨模块链路（collector→bundle→report 等）
├── architecture/          # 依赖方向、模型不可变性、白名单完备性等结构守卫
├── adversarial/           # 反作弊/反幻觉注入集（只增不减，CI 门禁）
└── fixtures/              # 黄金会话、标注数据、期望产物（按宿主与场景分目录）
```

- 测试文件与被测模块同名对应（`aftermatter/episodes/segment.py` →
  `tests/unit/episodes/test_segment.py`，示意非强制）；
- fixtures 内的黄金标注数据带来源与版本说明，**不含真实用户会话**（脱敏合成或
  自产会话）。

## 4. docs 布局（对齐七阶段文档规划）

```
docs/
├── README.md                      # 总导航（阅读地图 + 文档纪律）
├── aftermatter-项目设计文档.md      # 阶段 1：PRD / 功能需求 / 里程碑 / 指标 / 风险
├── aftermatter-项目结构.md          # 阶段 2（本文档）
├── aftermatter-开发计划.md          # 阶段 3：任务分解、排期与验收清单（已定稿）
├── architecture/                  # 阶段 1+5：三契约篇 + INDEX + 12 篇模块内部设计（随实现升定稿）
├── specs/                         # 阶段 6：带日期的专题决策文档（YYYY-MM-DD-主题.md）
├── adr/                           # 阶段 6：编号一页式轻量决策（NNNN-标题.md）
├── plans/                         # 阶段 7：演进计划与阶段快照
├── development/                   # 开发专题教程（NN-主题.md，随代码补写）
├── tests/                         # 量化指标实测报告（指标测试-<模块>.md）
├── benchmarks/                    # 基准测试报告（主题_YYYYMMDD.md）
├── api/                           # API 参考（cli / mcp / server / contract）
└── assets/                        # 图片、SVG 等静态资源（按需创建）
```

文档纪律：

- 技术选型表（architecture/overview.md §5）变更必须先落 ADR（轻量进 adr/，专题进 specs/），再改表；
- 契约变更（architecture/data-model.md / schemas）先改文档并递增版本号，代码跟随——顺序不可反；
- `docs/architecture/` 只写"模块内部如何实现"，不得复述 §2 的目录契约（防双写漂移）。

## 5. .github 与工程化约定

```
.github/
├── workflows/         # ci.yml（ruff/pyright/pytest 矩阵：3.12/3.13 × ubuntu/windows/macos）
│                      # release.yml（tag 触发构建 + PyPI 发布）、adversarial 门禁独立 job
├── ISSUE_TEMPLATE/    # bug / feature / question
├── PULL_REQUEST_TEMPLATE.md
└── dependabot.yml     # uv.lock + actions
```

- 分支模型：主干 `main` 常驻可发布，短分支直接 PR（单人期）→ 有外部贡献者后引入
  `next` 集成分支；
- Commit：Conventional Commits（type 白名单 feat/fix/refactor/test/docs/chore/perf，
  scope 用 §2 目录名）；
- 版本号：SemVer + 日历信息不进 tag；`CHANGELOG.md` 随 release 更新；
- Python 支持窗口：≥3.12，每年底评估是否跟进最新 stable。

## 6. 新代码放置决策树

```
要加的东西是什么？
├─ 新宿主会话支持        → collectors/<host>/ 新子包 + tests/fixtures/<host>/（ADR-0007）
├─ 新判断/检查项         → analysis/deterministic（确定性）或对应专家 prompt（LLM）
│                          ⚠️ 永不写进 collectors/episodes/evidence
├─ 新数据契约            → evidence/（模型）+ schemas/（导出）+ architecture/data-model.md（先改文档）
├─ 新统计方法            → longitudinal/
├─ 新报告区块            → report/（且过 F4 比较边界校验）
├─ 服务端新接口          → serve/，契约模型仍从 evidence/ import
├─ 仓库维护/发布辅助脚本  → scripts/（不得被 src import）
└─ 拿不准                → 先写 docs/adr/ 一条轻量记录（装不下再升 docs/specs/）
```

## 7. 演进预留（防止未来重构式崩塌）

| 触发条件 | 演进动作 |
|---------|---------|
| serve 需要独立部署/依赖膨胀 | 拆 `packages/` monorepo（aftermatter-core / aftermatter-serve），CLI 依赖 core |
| 宿主适配器数量 >6 或需第三方写适配器 | collectors 适配器改 entry-points 插件注册 |
| schemas 被外部工具消费 | 独立发布契约包（aftermatter-contracts） |
| 沙箱镜像复杂化 | 根级 `sandbox-images/` 目录出现（Dockerfile 属构建资产，不进 scripts/） |

## 8. 反模式清单（评审时对照）

- ❌ 把本文档 / architecture/modules.md 的示意文件名当强制清单（本文档只锁目录）
- ❌ `cli/` 里写业务逻辑（只许参数解析 + 调用装配）
- ❌ 任何模块 import `serve.`/`daemon.`（装配层在最外圈）
- ❌ 未用先建（空目录/空子包占位提交）
- ❌ 文档与代码双写同一契约（契约唯一来源 = architecture/data-model.md + schemas/）
