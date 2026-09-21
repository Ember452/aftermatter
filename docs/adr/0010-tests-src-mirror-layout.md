# ADR-0010: tests/ 保持 src 镜像布局，不采用领域分组

状态: Accepted | 日期: 2026-09-21
Related: ADR-0009（D-7 决策点来源）、项目结构 §3、开发计划 §1 DoD、ROADMAP §6 D-7

## 背景
D-7 提出是否借鉴原版 test/ 的领域分组（agents/cli/governance/learning/reporting…）
替代我们 unit 层按 src 包镜像的布局。原版如此组织源于其产品形态：逻辑长在
script + SKILL.md + docs 的能力链上，无稳定模块概念，能力测试即主测试层。
我们是 L0–L3 类型化数据管道，模块边界即契约边界，前提不同。

## 决定
保持现有混合布局：unit 镜像 src 包（对齐契约先行与 DoD 的
`uv run pytest tests/unit/<路径>` 直接映射）；跨模块场景测试归 integration
（按领域命名：bundle_freeze / dual_brain_parity / repair_ledger）；
architecture 与 adversarial 为专区。不整体改领域分组。
同时吸收原版意图：未来打包/发布验证类测试（pip install smoke、schema 导出一致性）
落 integration/release_*.py，不新增顶层目录（YAGNI）。

## 影响
零文档改动（结构 §3、开发计划 DoD 维持现状）；ROADMAP D-7 关闭并引用本 ADR。
反向触发条件：M2–M3 期间若 ≥3 个 unit 测试文件需 mock 相邻模块才能运行，
视为模块切分信号，重开本决策并优先审视架构而非先改目录。

## 被否备选
- 整体领域分组：需重写 DoD 命令与结构文档，失去"测试失败→模块"直接映射；
  照搬源于异质产品形态的布局属 cargo cult。
- 双轨制（unit 镜像 + 另建领域目录）：多一套分类而无当期消费者。
