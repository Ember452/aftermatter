# ADR-0003: 双大脑架构（同一证据内核，两个可插拔推理前端）

日期: 2026-09-21 | 状态: accepted

## 背景
勘误注记（ADR-0009）：原版另有面向 harness 开发的主动受控实验系统（其 ADR-0004/0005），
本文"无法自动复验"限定于用户报告链路，不含该实验产品面。

源码核实原版 Better Harness 全仓库零 LLM API 调用——其"智能"寄生于宿主 Agent，
导致无法无人值守运行，修复与纵向验证只能人驱动。纯自带引擎方案失去零成本宿主入口；
纯寄生复刻则差异化塌缩为"Python 重写"。

## 决定
确定性证据内核（collectors/episodes/evidence，零 LLM）之上挂两个大脑，
消费同一 EvidenceBundle、产出同一 Finding schema：
① 寄生宿主（Skill + MCP 只读工具，借宿主模型，零 API 成本）；
② 自带多 Provider LLM 引擎（cron/CI 无人值守，支撑有界修复与纵向验证闭环）。
完整论证与竞品校准见 `../specs/2026-09-21-dual-brain-and-deepening.md`。

## 影响
契约成为硬约束（AGENTS 铁律 3）：任何为实现便利而分叉 schema 的做法打回；
analysis 模块双实现（engine/ 与 mcp/）；report/longitudinal/serve 对大脑无感知。
