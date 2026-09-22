# ADR-0014: 里程碑收口报告独立目录 docs/reports/

状态: Accepted | 日期: 2026-09-22
Related: ADR-0011 文档语言分层与写作规范、ADR-0013 docs/tests/ 中文文件名豁免、
[REPO-LAYOUT.md](../REPO-LAYOUT.md) 的「§4 docs 布局」、[docs/README.md](../README.md) 的目录规约、T0.1

## 背景

M0 收口报告写完后临时落在 `docs/specs/`，但 `specs/README.md` 的收录标准是"一次性的决策/
设计文档"，收口报告不属于该类；一期还会产生 6 份同类记录，混放会让 `specs/` 的检索语义
退化成"任何带日期的 md"。同时 `ROADMAP.md` §7 规定"历史快照靠 tag 回溯、不另存副本"，
因此这类文档必须与"当前阶段快照"划清职责，否则又造出第二个需要手工同步的时效性来源。

## 决定

1. 新增文档目录 **`docs/reports/`**，只收里程碑/阶段的**收口报告**：做了什么、选了什么与否掉了
   什么、文件清单、验证证据（真实命令输出）、计划外发现、遗留问题、对下一阶段的交接。
2. 命名 `m<N>-<slug>.md`（如 `m0-skeleton-completion-report.md`）：里程碑号进文件名，收口日期写在
   头部元数据；内容中文、文件名英文（承 ADR-0011，不新增豁免）。
3. **四类文档的分工锁定**，避免同一事实双写：
   `plans/ROADMAP.md` §1 = 唯一时效性快照（随里程碑出口整节重写）；
   `specs/` = 一次性决策全论证（写完不追改）；
   `reports/` = 一次性收口记录（写完不追改）；
   `adr/` = 一页式轻量决策。
4. `reports/` 内文档不得维护时效性内容：文首必须声明"当前阶段状态以 ROADMAP §1 为准"，
   本文只作历史证据。这是对 §7"不另存副本"的正面回应，而非绕过。

## 影响

- `docs/REPO-LAYOUT.md` 的「§4 docs 布局」补 `reports/` 一行；
- `docs/README.md` 的目录规约与「§1 语言分层」表各补一行（`reports/` 归内部设计类：中文内容、英文文件名）；
- `docs/specs/README.md` 补一句去向指引，避免后续再把收口报告写进 `specs/`；
- 首份文档 `docs/reports/m0-skeleton-completion-report.md` 由 `specs/` 迁入——迁移时该文件尚未提交，
  因此不存在 blame 断链，也无需 `git mv`；
- `scripts/doc_lint/` **无需改动**：`metadata_checker` 只豁免 `README.md`/`INDEX.md`/`adr/`/`specs/`，
  `reports/` 下的报告按规则自带 `状态:` 头即合规，其 README 天然豁免。

## 被否备选

- **留在 `docs/specs/`**：零改动，但一期 7 份混进"决策文档"目录，检索语义不可逆地退化。
- **放 `docs/plans/`**：`ROADMAP.md` §7 明确"历史快照不另存副本"，放那里等于正面违反既有约定。
- **建 `docs/milestones/` 并把 ROADMAP 一起搬进去**：ROADMAP 是时效性路线、reports 是一次性记录，
  性质不同；搬动还会牵动全部引用点，成本换不到清晰度。
- **每份报告沿用日期前缀 `YYYY-MM-DD-`**：与 `specs/` 命名同形，恰恰是本次要消除的混淆。
