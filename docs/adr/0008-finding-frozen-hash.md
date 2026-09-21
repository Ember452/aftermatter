# ADR-0008: Finding revision 增加 frozen_hash 字段

日期: 2026-09-21 | 状态: accepted

## 背景
"裁决冻结"不变量（Lead 六阶段之 freeze）要求定稿结果不可变且可追溯；
longitudinal.md 存储层已出现 `frozen_hash` 列、analysis.md 描述了定稿哈希入表，
但 data-model.md 的 Finding 契约没有对应字段——存储层发明了契约之外的列，违反
"契约唯一来源"纪律。

## 决定
`Finding` 增加 `frozen_hash: str | None`：Lead freeze 阶段写入该 revision
canonical JSON 的 sha256；冻结前恒为 None。

## 影响
data-model.md §4.1 补字段；longitudinal.md 表列合法化；report/serve 校验
"已定稿 findings 必须 frozen_hash 非空"；schema 基线 finding 版本号递增（finding=2）。
