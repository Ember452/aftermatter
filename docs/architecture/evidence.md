# evidence 内部设计

状态: 草稿（T1.2/T1.8/T1.9 落地时升定稿） | 对应: modules §4、data-model 全文

## 职责边界

全项目**契约唯一定义处**（所有跨层 pydantic 模型住这里）+ Bundle 冻结 + 完整性核验 +
脱敏管道。不做采集（调 collectors 公共 API）、不做分析（只提供输入）。

## 内部分区

| 单元 | 内容 | 对外性 |
|------|------|--------|
| models | L0–L3 全部模型 + ERef + 枚举（DimensionId/CheckId/LifecycleState/…），data-model.md 的一比一化身 | 全公共，被所有层 import |
| freezer | Bundle 冻结流程（下） | 公共 API |
| integrity | Manifest 构建 + `verify_ref(bundle, eref) -> VerifyOutcome` | 公共 API（引用闸核心） |
| redaction | 三级脱敏管道（下） | 公共 API |

## 冻结流程（freeze）

```
1. scope 解析（target/hosts/window/depth/locale）→ 冻结为 Scope 值对象
2. 三 lane 并行构建：session lane 经 episodes 公共 API；project/assets 经 collectors
3. IntegrityManifest：枚举全部证据源（会话文件/仓库文件/资产文件）
   {path, sha256, size}；ERef 指向的字节区间哈希一并入册
4. bundle_id = fingerprint(scope + manifest)——内容寻址，同输入必同 id（幂等）
5. 原子写 run-dir：写 tmp → fsync → rename；含 bundle.json / lanes/ / manifest.json
6. 重开校验：从磁盘 load → 与内存模型逐字段一致才返回成功（防半写）
```

lane 状态机：`available / partial(reason_code) / unavailable(reason_code)`，
reason_code 是封闭枚举（`no_session_files / host_version_unknown / parse_budget_exceeded / …`）。

## verify_ref（引用闸，被 Lead 与 MCP submit 共用）

解析 ERef → 定位原始字节 → 重算哈希 → 与 Manifest 比对。
返回 `ok | not_found | hash_mismatch | out_of_manifest`，**只读操作，永不修复**。
性能路径：Manifest 索引预载 + LRU 缓存已验证 ERef（缓存 key 含 bundle_id，无跨 bundle 污染）。

## 脱敏管道（redact(model, level)）

纯函数、按序应用、级别单调（minimal ⊆ standard ⊆ raw 信息量）：

```
raw      本机全量（默认落盘形态，含命令原文）
standard 路径归一 → secret/token 正则剥离（ghp_/AKIA/Bearer/JWT 形态库）→
         PII 模式（邮箱/手机号）→ prompt 全文替换为 IntentFacet 语义摘要 →
         session_id 哈希化          ← 上传最低级别
minimal  仅计数、状态、枚举、无引用文本
```

不变量测试：standard 输出上跑 secret 正则库必须零命中；redact 幂等。

## 测试要点

冻结幂等（同 scope 两次 freeze 同 bundle_id）；篡改任一源文件后 verify_ref 必拒；
run-dir 半写崩溃恢复（rename 原子性）；lane 类型隔离静态检查（SessionLane 无 project 字段）；
脱敏属性测试（随机注入 secret 必被剥离）。
