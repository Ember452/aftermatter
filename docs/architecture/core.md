# core 内部设计

状态: 定稿（T1.1 已落地） | 对应: modules §1

## 职责边界

只收五类真基础件：时间、哈希指纹、路径归一、日志/TraceId、异常基类。
**明确不做**：任何业务语义（不知道什么是 Episode/Finding）、任何 IO 策略、任何配置加载。

## 内部结构（职责单元，非文件名）

| 单元 | 内容 |
|------|------|
| timeutil | `parse_ts`：ISO8601 解析→UTC datetime，毫秒**向下截断**（同一原始串必须只有一种指纹）；无时区输入按解析失败处理而非默默当 UTC（格式漂移要可见）；`event_millis` 容错语义：解析失败返回 None 不抛 |
| fingerprint | `fingerprint(obj)->str`：模型 → canonical JSON（key 排序、ensure_ascii=False、无空白、拒非 str key 与非有限浮点）→ sha256[:16]；字符串/字节直通哈希。**只交付 16 位宽度**；需要完整 sha256 的消费者（IntegrityManifest 字节比对）自算，core 不发明第二套宽度。识别模型用结构化协议（`model_dump`），**不 import pydantic**（modules §1：core 仅依赖标准库） |
| pathutil | `norm_path(p, root)->str`：反斜杠统一、盘符大小写归一、UNC 处理、`~` 展开后必须落在 root 内否则抛 `PathOutsideWorkspace`；输出仓库相对 posix 风格。**纯字符串归一**：不 `resolve()`、不跟随 symlink、不 stat 文件系统（既避开事件循环内阻塞 IO，也保证同一路径串在三平台得到同一结果）；仓库相对输入视为 workspace 相对 |
| logctx | logging 配置工厂 + `trace_id` contextvar（一次 analyze run 一个 id，所有日志行自动携带）；禁止 root logger 污染，库代码只 `getLogger("aftermatter.*")`；`setup_logging` 幂等，只配置 `aftermatter` 一支且 `propagate=False`，TraceId 过滤器挂在 handler 上（保证任何路由到该 handler 的记录都有 `trace_id` 字段） |
| errors | 异常树（下） |

## 异常分类树

```
AfterMatterError(code: str, retryable: bool)
├── ParseError            适配器遇到不可解行（携带 line_no、raw_digest，不携带原文）
├── EvidenceError         ERef 解析失败 / 哈希不符（引用闸的返回异常）
├── ContractViolation     状态机白名单外迁移、lane 越界、旁路写入（不可 retryable）
│   └── PathOutsideWorkspace  归一化后落点越出 root（路径沙箱边界）
├── ProviderError         LLM 客户端错误（子类 rate/timeout/auth/schema，在 providers 内细化）
├── SandboxUnavailable    docker 缺失/权限不足
└── ConfigError           装配层配置非法
```

规则：**异常只携带机器可读 code + 有界摘要**（单值渲染上限 80 字），永不携带原始会话内容（防泄漏进日志/报告）。
每类异常有类级默认 code（构造时可省略），供“code 唯一性扫描”测试与调用方按 code 分流。

## 测试要点

纯函数全分支；fingerprint 稳定性测试（dict 序不变性、unicode）；pathutil 三平台路径表驱动
（Windows 盘符大小写、UNC、symlink）；异常 code 唯一性扫描。
