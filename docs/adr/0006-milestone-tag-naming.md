# ADR-0006: 里程碑 tag 命名规则

日期: 2026-09-21 | 状态: accepted

## 背景
开发计划 §1 收尾仪式要求里程碑出口询问打 tag，但 tag 命名无约定；
原版用日期目录组织 run 产物，不适用于版本发布场景。

## 决定
tag 格式 `v0.N.0-<milestone>`，milestone 用 kebab-case 短名：
如 `v0.1.0-m0-skeleton`、`v0.2.0-m1-evidence-kernel` …… `v0.7.0-m6-distribution`。
打 tag 与 commit 同样必须经用户明确允许。

## 影响
CHANGELOG.md 按 tag 分组（Keep a Changelog）；简历/README 可用 tag 链展示进度；
一期发布正式版（v1.0.0）时脱离此序列，走正常 SemVer。
