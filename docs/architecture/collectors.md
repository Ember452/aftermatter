# collectors 内部设计

状态: 草稿（T1.3–T1.5 落地时升定稿） | 对应: modules §2、data-model §1

## 职责边界

宿主私有会话文件 → `RawEvent[]`；仓库 → `RepositoryEvidence`。**只产事实，不做判断**：
不切 Episode、不评任何分。产出物是唯一对外语言，宿主差异止步于各适配器子包内部。

依赖边界：可 import `core` 与 `evidence` 的**契约模型**（`RawEvent`、`ERef` 住在那里）；
**不可** import `evidence` 的 freezer / integrity / redaction——采集层不参与冻结与核验
（由 `tests/architecture/` 守卫强制）。

## 适配器生命周期（每宿主子包同构）

```
discover(workspace)          扫描宿主会话目录 → list[SessionRef]
  └ SessionRef = {path, format_version, size, mtime, content_hash}
healthcheck()                format_version 是否在支持矩阵 → AdapterHealth(ok/unknown/degraded)
parse(ref, since_offset)     AsyncIterator[RawEvent]，流式逐行，可断点续读
```

### 适配器内部三段流水线

1. **行读取器**：字节偏移 checkpoint（A5 增量索引的地基）；文件哈希变化则 checkpoint 失效重读
2. **行分类器**：宿主 JSON 行 → 语义 kind 映射表（每宿主一张声明式映射）；三类去向严格分开——
   映射表命中的会话事件→`parsed`；本就不属 L0 事件模型的非会话事件（宿主侧快照、标题、
   队列等）→`ignored`（带类型名 reason）；映射表外的**未知 type**→`unparsed`（保留 ERef 与
   有界摘要）。**只有 `unparsed` 是“格式漂移第一信号”**，把预期忽略塞进它会淹没信号（ADR-0016）
3. **事件构造器**：填充 RawEvent 必填面（tool_name/target_paths/permission/result_ok/model），
   每条自带指向原始行字节区间的 ERef（含 `source_id`，见 data-model §0.1）；路径经 `core.norm_path`
   归一。工作区外路径本期**不进入 `target_paths`、只计入 `ParseStats.outside_path_count`**（`RawEvent`
   无 outside 字段；Episode 侧的 outside 语义待 T1.7 真正需要时再入契约，ADR-0016）

### 防自污染

路径正则清单（`~/.aftermatter/`、`*.aftermatter.json` 类）命中即剔除——抄原版
HARNESS_ARTIFACT_PATH_RE 思路，清单集中在一个可测的纯数据单元。

## repo 扫描器（独立子包）

| 信号组 | 采集内容 | 手段 |
|--------|---------|------|
| 指令面 | AGENTS.md/CLAUDE.md 存在性、长度分桶、命令章节/边界章节有无 | 结构化解析（markdown 标题扫描），不评"写得好坏" |
| 验证面 | 测试目录布局、测试文件数、与源码目录映射 | 路径模式 |
| 交付面 | CI workflow 存在、test job 是否触发 push/PR | YAML 关键字段抽取 |
| 历史面 | 近 N 提交（有界）：作者分布、测试-源码共变率、当前工作树漂移 | `git log/diff` 只读子进程，超时必设 |

## 错误策略

行级 fail-soft（一行坏不影响流），文件级 fail-hard（编码崩溃/权限 → 该 SessionRef 标 unavailable
+ reason_code）。所有降级都进 CoverageLedger，供 normal/quick 分路判定。

## 测试要点

每宿主 ≥20 黄金 fixture（正常/畸形行/截断/编码陷阱/自污染路径/工作区外路径）；
offset 断点续读一致性；unparsed 计数准确；扫描器快照测试（对小型样例仓库）。
