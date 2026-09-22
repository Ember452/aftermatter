# adr/ — 轻量决策记录（编号式）

命名：`NNNN-<短标题>.md`（四位递增，如 `0001-brand-casing.md`）。

模板 v2（一页以内；自 ADR-0009 起生效，0001–0008 为历史记录不回改）：

```
# ADR-NNNN: <决定标题>

状态: Proposed | Accepted | Superseded by NNNN   日期: YYYY-MM-DD
Related: <关联 ADR / spec / T 任务号 / FR 编号>
## 背景      一两句话：遇到什么岔路口
## 决定      我们选了什么
## 影响      对代码/文档/契约的连锁修改点（改哪几篇、schema 版本是否递增）
## 被否备选  列被否决方案各一句 why（无则写"无"）
```

适用：技术选型表变更、目录规则微调、命名与流程约定、跨文档口径裁决等小决策。
长到一页装不下 → 升级进 `../specs/`。

## 索引

| 编号 | 标题 | 状态 |
|:---:|------|:---:|
| [0001](0001-brand-name-aftermatter.md) | 项目命名 AfterMatter | Accepted |
| [0002](0002-casing-convention.md) | 品牌驼峰展示体与小写技术标识符 | Accepted |
| [0003](0003-dual-brain-architecture.md) | 双大脑架构（同一证据内核，两个可插拔推理前端） | Accepted |
| [0004](0004-comparison-boundary-mandatory.md) | 比较边界强制声明（F4，P0） | Accepted |
| [0005](0005-inspector-mechanism-prelude.md) | Harness Inspector 只做机制预埋，一期不做 UI（F5，P2） | Accepted |
| [0006](0006-milestone-tag-naming.md) | 里程碑 tag 命名规则 | Accepted |
| [0007](0007-host-vs-provider-naming.md) | 数据契约 host 与 provider 命名分离 | Accepted |
| [0008](0008-finding-frozen-hash.md) | Finding revision 增加 frozen_hash 字段 | Accepted |
| [0009](0009-original-experiment-system-calibration.md) | 原版全库对照后的主张校准与四项设计吸收 | Accepted |
| [0010](0010-tests-src-mirror-layout.md) | tests/ 保持 src 镜像布局，不采用领域分组 | Accepted |
| [0011](0011-doc-language-and-standards.md) | 文档语言分层与写作规范 | Accepted |
| [0012](0012-m0-toolchain-and-dependency-baseline.md) | M0 工程化工具链与依赖基线 | Accepted |
| [0013](0013-docs-tests-chinese-filename-exemption.md) | docs/tests/ 中文文件名豁免与实测目录语言定位 | Accepted |
| [0014](0014-milestone-reports-directory.md) | 里程碑收口报告独立目录 docs/reports/ | Accepted |
| [0015](0015-readme-chinese-default.md) | 门面 README 默认中文，英文版镜像 | Accepted |
| [0016](0016-reference-source-identity.md) | 证据引用携带 source_id（多源根与主机路径不入库） | Accepted |

维护约定：新增 ADR **必须在本表补一行**（编号连续由 `adr_checker` 强制，但"漏登记索引行"目前
是人工评审项；表内链接失效会被 `link_checker` 拦下，所以改名/删除不会悄悄通过）。
若本表与实际文件长期不同步，再将其机器化进 `adr_checker` 并补一条 ADR。
