# episodes 内部设计

状态: 草稿（T1.6–T1.7 落地时升定稿） | 对应: modules §3、data-model §2

## 职责边界

`RawEvent[]` → `TaskEpisode[]`。做**行为层重组与分类**，不做价值判断
（"好不好"属于 analysis；这里只回答"发生了什么、算哪类"）。

## 切分算法（segment）

```
输入: 单 (host, workspace) 边界内按 (ts, seq) 全序的事件流
1. 断点条件（取并集）:
   a. 时间缺口: next.ts - prev.ts > episode_gap_ms（默认 30min，配置项）
   b. 新任务 prompt: kind=user_prompt 且判定为新目标（规则见下）
2. 续接条件（不开新 Episode）: 纠错/澄清类 prompt（"不对"、revert 指令、
   针对当前目标的追问）——同目标重试与摩擦留在同一 Episode
3. 输出不变量: Episode 互不重叠、时间全序、每 Episode ≥1 个 user_prompt
```

**新目标判定规则表**（纯规则，可测；不引 LLM）：指称新文件/新功能词、上一 Episode
已出现 outcome 事件（commit/末次验证）后的首个 prompt、显式任务切换语。规则表版本化，
黄金样例回归防规则改动静默改变切分结果（改动 = ADR 触发条件 1）。

## 事件→事实分类器

| 事实 | 判定 | 归一化 |
|------|------|--------|
| EditFact | tool_name ∈ 编辑工具集（宿主子包提供集合）或 target_paths 非空写操作 | 文件去重、行数累加 |
| ValidationFact | 命令文本 × 类别正则库（test/lint/build/typecheck/security） | identity = NFKC + 空白折叠 + 去参数噪声；`claimed_ok` 取自 result_ok，**`replay_ok` 恒为 None（只允许 sandbox 回填）** |
| FrictionFact | permission ∈ {denied, blocked}；同 identity 命令在窗口内失败≥2 次（retry）；user-correction 模式；hook blocked | 计数 + 首末 ERef |
| OutcomeFact | git head_commit 变化 ∧ 与 edits 路径重叠；末次 validation 结果 | 提交缺失如实为 None |

## 可比性特征（comparability）

- `task_type`：规则枚举（feature/fix/refactor/docs/test/config）+ 置信度；置信不足则 `unknown`
- `scale`：文件数/行数分桶（对数桶）
- `tool_shape`：工具调用序列 3-gram 指纹向量（确定性，无外部依赖）
- `embedding_ref`：经 `EmbeddingProvider` 接口取本地向量（model2vec 默认）；
  **接口缺省实现 = None**，纵向匹配自动退回结构化+tool_shape 双通道（嵌入是增强不是依赖）

## 错误与边界

事件缺 ts → 按 seq 插值入最近窗口并标 `time_inferred`（该 Episode 的时序类断言降置信）；
跨 workspace 事件混入 → 拒收并计数；空 Episode（无 prompt）→ 丢弃但计入 CoverageLedger。

## 测试要点

黄金样例逐 Episode 断言（多会话交错、30min 边界两侧、纠错续接、新目标切换）；
property-based：切分不重叠/全序/无丢失不变量；分类器表驱动全覆盖；
identity 归一化的幂等与抗噪（多余空格/引号风格/管道参数）。
