# cli 内部设计

状态: 草稿（T0.1 起持续演进，M1 出首个命令） | 对应: modules §11

## 职责边界

typer 应用树，只做三件事：参数解析与校验 → 装配调用 kernel 公共 API → 输出格式化。
**零业务逻辑**（架构测试禁止 cli 内出现算法/判断代码）；退出码是对外协议的一部分。

## 命令树（一期）

```
aftermatter | aftm
├── analyze   --target --host(claude|codex|cursor|qoder) --depth(quick|normal) --engine(deterministic|llm|host)
│             --since --until --json --run-dir --budget-usd
├── repair    plan <finding-id> / apply <plan-id> --yes / revert <intervention-id>
├── history   findings|trends [--repo]（读本地 SQLite；比较块自动带边界声明）
├── upload    手动触发 daemon 上传队列（或 --enable 配置）
├── doctor    环境自检：宿主会话发现、格式版本矩阵、docker、provider key、DB 迁移状态
└── mcp       stdio server（大脑①入口，供宿主挂载）
```

## 输出契约（agent-friendly，对齐 modules §11）

- `--json`：stdout 纯 JSON（模型 dump，parser-safe），人类诊断全走 stderr；
  非 json 模式 rich 渲染
- 退出码：0 成功 / 1 用户错误 / 2 证据不足（normal 拒发报告）/ 3 环境缺依赖 / 4 内部错误；
  每码有稳定 machine code 供 CI 分支
- 计划/变更分离：repair apply 必须 `--yes` 且非交互模式强制；所有写操作先 plan
- 全局 flag：`--no-input --quiet --timeout --no-color`

## 装配规则

config 优先级：flag > 环境变量（AFTERMATTER_*）> `~/.aftermatter/config.toml` > 默认；
合并逻辑在 cli 层完成，kernel 只收显式参数对象（kernel 不读环境，保证可测）。

## 测试要点

退出码逐一路径覆盖（含 2 与 3 的真实触发场景）；`--json` 输出 stdout 零污染断言；
config 优先级矩阵；`doctor` 对每种缺失依赖的机器可读输出；help/unknown-command 契约。
