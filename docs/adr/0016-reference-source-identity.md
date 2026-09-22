# ADR-0016: 证据引用必须携带源标识

状态: Accepted | 日期: 2026-09-22
Related: T1.2、T1.3、FR-A1、data-model §0.1/§1.1、evidence.md §verify_ref、overview §8

## 背景

T1.2 落地的 `verify_ref(eref, entries, *, root)` 只接受**一个** root，默认所有证据都在同一
目录下。真实宿主会话打破了这个默认：本机探雷实测 Claude 会话住在 `~/.claude/projects`，
与被分析仓库根不在同一棵树，而 Bundle 的三条 lane 必然同时引用会话文件与仓库文件。
更要紧的是，该目录名本身就是主机路径的编码（实测 slug 形如 `C--Users-<user>`，含用户名），
绝不能进跨边界数据。

## 决定

每条引用携带 `source_id`——证据源根的稳定别名（12 位小写 hex），派生规则为
`sha256(f"{host}\0{源根去 HOME 前缀}").hexdigest()[:12]`；跨边界数据只出现 `source_id`，
不出现源根路径。引用闸按 `source_id → 源根` 的映射定位原始字节，该映射由本机 run 上下文
提供，主机路径永不进模型。

## 影响

- `data-model.md` §0.1：`ERef` 增加 `source_id`，`source_path` 语义由"仓库相对"改为
  "相对其 `source_id` 所指源根"；新增 §1.1 采集侧类型（`SessionRef`/`AdapterHealth`/`ParseStats`）。
- schema 基线 `event` 3→4（新增必填字段，非兼容变更）。
- `evidence`：`SourceEntry` 增加 `source_id`，`verify_ref` 第三参由 `root` 改为 `roots` 映射
  （趁其尚无下游消费者时改，只影响本包测试）。
- `collectors.md`：原文"工作区外路径标记 `outside`"与 `RawEvent` 契约（无对应字段）冲突，
  改口径为本期只计数（`ParseStats.outside_path_count`）；Episode 侧的 outside 语义留待 T1.7
  真正需要时再入契约。
- 同时落定：`unparsed_count` 与 `ignored` 拆成两个计数器，`SessionRef` 的 `path` 标注为仅本机有效。

## 被否备选

- `source_path` 直接存主机绝对路径、出机前 redact：把隐私安全寄托在"脱敏每次都执行正确"上，
  违背 overview §2"结构把关优于 prompt 自觉"。
- 保持单一 `root`：会话源根与仓库根不同目录，物理上做不到，混源即错。
- 给 `RawEvent` 加 `outside_paths` 字段：`collectors.md` 那句要求本期只计数即可满足，无 Episode 侧消费者。
