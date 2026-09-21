# serve 内部设计（一期骨架）

状态: 草稿（T6.6 落地时升定稿） | 对应: modules §10、overview §4.3

## 职责边界

团队侧最小服务：接收脱敏 findings、账号/团队、趋势查询。
**隐私承诺的 schema 化表达：表结构中不存在任何原文字段**（无 prompt、无路径、无命令文本），
能存的上限 = standard 级脱敏产物。

## 组件

```
API(FastAPI):
  POST /v1/ingest/findings   header: Authorization Bearer <token>, Idempotency-Key
    去重: key = sha256(bundle_id + finding_id + revision) 唯一约束，冲突 → 200(已收)
    校验: 请求体过 evidence 契约模型（复用同一 pydantic 定义，服务端不复制 schema）
    越级检测: 字段含疑似 secret/长文本 → 拒收 422（第二道脱敏防线）
  GET  /v1/trends?repo&since  按团队维度聚合分数/finding 计数/verdict 分布
Auth   token → membership(team, repo scope) 一期单表；tenant_id 字段预留（G4 二期）
DB     Postgres + SQLAlchemy 2 + alembic；表: teams/members/repos/findings_ingest/
       comparisons_ingest（结构镜像 longitudinal 五表，无原文列）
部署   docker compose（api + postgres），一键起
```

## 一期明确不做

多租户配额、任务队列、限流、Webhook、前端面板（G4/二期，见 docs/plans/ 指针）。
接口面保持窄：二期扩展不得破坏 v1 契约（版本前缀已留位）。

## 测试要点

幂等重传不产生重复行；非 standard 级数据（含原文 prompt 样例）必被 422 拒收；
跨团队读取隔离；契约模型升级后旧版本客户端请求得到明确错误码而非 500。
