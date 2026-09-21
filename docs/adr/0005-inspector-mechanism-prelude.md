# ADR-0005: Harness Inspector 只做机制预埋，一期不做 UI（F5，P2）

日期: 2026-09-21 | 状态: accepted

## 背景
原版有交互式会话取证界面（Harness Inspector：时间线 + 证据抽屉 + Continuation packet）。
单人项目做前端会显著挤占三项深化（纵向统计/沙箱重放/反作弊）的预算。

## 决定
一期不做证据浏览器 UI，列入非目标；仅做机制预埋：
ERef 必须可从浏览器反解析回原始文件位置；run-dir 数据足以离线重建 Episode 时间线。
验收降级为"用 fixture 手工渲染一页静态时间线原型"（可选，不进关键路径）。

## 影响
PRD FR-F5（P2）与 §7 非目标同步；不新增前端依赖；
二期若做 Inspector，数据层零返工（决策依据：run-dir 契约不变）。
