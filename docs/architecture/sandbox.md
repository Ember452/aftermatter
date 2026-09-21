# sandbox 内部设计

状态: 草稿（T5.1–T5.2 落地时升定稿） | 对应: modules §7、data-model §2.2

## 职责边界

为验证类断言提供**执行级证据**：容器内复跑 Episode 声称过的验证命令，
回填 `replay_ok`。不做任意命令执行，不做修复应用（那是 repair）。

## 组件与流程

```
Probe      docker 可用性/权限探测 → 不可用抛 SandboxUnavailable（触发降级矩阵，
           验证类证据整体降回"转述级"并在报告显式标注）
ImagePick  按仓库语言标记选基础镜像（pyproject→python:3.12-slim / package.json→node…），
           一期仅覆盖声明式识别，不做镜像构建（D5 容器池二期）
SpecBuild  容器规格构造器：--network none、CPU/内存限额、pids 上限、
           仓库只读挂载 + tmpfs 可写工作副本、硬超时（超时=SIGKILL，记 timeout 不记 ok）
Replay     命令序列重建：取 Episode validations 的 identity 去重
           → 仅白名单类别（test/lint/build/typecheck）
           → 按原时序入队复跑 → ReplayResult[(identity, ok|fail|timeout, 有界输出尾)]
Receipt    复跑前工作树状态收据：clean 断言，或记录 dirty 文件清单+内容哈希
           （吸收原版 completeness receipt，ADR-0009）；无收据的复跑只能记为
           contextual，不得回填 replay_ok
回填       update_replay_ok(bundle, episode_id, identity, ok)
           ——全项目唯一写入口（其余模块只读 replay_ok；旁路 = ContractViolation）
```

## 安全姿态

默认断网、默认只读、命令白名单来自分类器产出（不接受外部直接投喂命令串）、
输出尾部截断有界（防日志爆）、容器即弃（无跨 run 状态）。
一期只复跑"声称通过"的命令做真伪核验（PRD R6 对策），完整重放环境构建留给 D5。

## 测试要点

无 docker 环境的 unavailable 路径；限额生效集成测试（fork 炸弹/内存 hog 样例被杀）；
dirty 工作树无收据 → contextual 路径（replay_ok 不写入）；
identity 去重与时序保持；回填唯一入口的旁路拒绝测试；超时语义（timeout ≠ fail ≠ ok）。
