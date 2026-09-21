# ADR-0007: 数据契约 host 与 provider 命名分离

日期: 2026-09-21 | 状态: accepted

## 背景
全量文档审计发现 provider 一词在契约链中存在三义混用：`RawEvent.provider` 指编码宿主
（claude/codex/cursor/qoder），`analysis/providers/` 指 LLM 供应商，
`EnvSnapshot` 注释 "model_versions / provider / host 配置哈希" 中两者并排且语义不清。
混杂控制（E4）依赖这些字段的精确语义，实现期必然出错。

## 决定
数据契约与 CLI 中，编码宿主维度一律 **host**（`RawEvent.host`、`TaskEpisode.host`、
`Scope.hosts`、CLI `--host`）；**provider 仅指 LLM 供应商**（EnvSnapshot 需消歧处用
`llm_provider`）。

## 影响
data-model.md §1/§2/§3/§4.3 六处字段、overview.md §4.1 命令示例、cli.md 命令树、
longitudinal.md confound 段、episodes.md 输入边界、evidence.md scope 构造、
项目结构 §6 决策树 `collectors/<host>/`。零代码期执行成本最低；晚改则波及解析器、
契约导出、报告与服务端全链。
