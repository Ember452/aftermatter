# ADR-0013: docs/tests/ 中文文件名豁免与实测目录语言定位

状态: Accepted | 日期: 2026-09-22
Related: ADR-0011 文档语言分层与写作规范（局部修订其决定 1 与决定 2）、T0.1、
`docs/REPO-LAYOUT.md` 的「§4 docs 布局」、`scripts/doc_lint/policy_checker.py`

## 背景

M0 收尾核对各目录 README 时发现确定性冲突：`docs/tests/README.md` 规定实测文档命名为
`指标测试-<模块>.md`（中文文件名），而 ADR-0011 决定 2 要求"文件名一律英文"，且
`policy_checker` 会扫描 `docs/` 下**所有**文件名并把中文名判违规——照该 README 写出来的
文件必然让 CI 变红。根因是 ADR-0011 决定 1 的分层表只列了 `architecture/adr/specs/plans`
与 `development/api`，**`docs/tests/` 与 `docs/benchmarks/` 两个目录的语言与命名归属从未被定义**，
于是 README 各自发明规则。维护者裁决：保留中文指标名文件名，为其开豁免。

## 决定

1. **豁免范围**：仅 `docs/tests/` 目录（含其子目录）下的文件允许中文文件名，其余位置
   （`docs/` 其他子目录、仓库根 `tests/`、`scripts/`）规则不变。范围窄到"一个目录"，
   是为了让例外可被记住；一旦第二处开始要求豁免，即视为该约束需要整体重议而不是继续加白名单。
2. **豁免的机器化落点**：`policy_checker._check_filenames` 增加 `_CJK_NAME_EXEMPT_DIRS`，
   与 `docs/README.md` 的「§2 命名规则」保持同源（README §"文档规范"开头声明与脚本同源于 ADR）。
3. **补全分层表**：`docs/tests/`（量化指标实测文档）与 `docs/benchmarks/`（基准报告）定为
   维护者向内容——**内容中文、文件名英文，`docs/tests/` 按决定 1 例外**。`benchmarks/` 现行
   命名 `<主题>_<YYYYMMDD>.md` 已是 ASCII，无需豁免。
4. **中文名不参与链接稳定性**：这些文件被引用时仍须用相对路径 markdown 链接，`link_checker`
   会验证其可解析性；豁免只放开文件名字符集，不放开链接与元数据要求。

## 影响

- `scripts/doc_lint/policy_checker.py`：新增豁免常量与判定，模块 docstring 的规则 1 同步改写；
- `docs/README.md`：语言分层表补 `tests/` 与 `benchmarks/` 两行，「§2 命名规则」的禁用行加例外括注；
- `docs/tests/README.md`：命名规则处补一句依据（ADR-0013），使读者知道这是被裁决的例外而非疏漏；
- ADR-0011 决定 2 加括注指向本文，避免只读该 ADR 的人拿到"文件名一律英文"的过期绝对表述；
- 对未来的硬约束：`docs/tests/` 内的中文名文件在**出机数据**（README/论文/发布物）里引用时
  需保留原路径，平台差异（Windows 控制台、URL 编码）由引用方承担——这也是本豁免的唯一长期成本。

## 被否备选

- **全目录保持英文文件名，中文只放标题**（实现成本最低、跨平台最稳）：维护者裁决否掉，
  理由是实测文档按 PRD §9 的中文指标名检索更直接，一份报告对应一个指标场景时中文文件名即索引。
- **把 `policy_checker` 的中文名检查整体关掉**：会同时失去对 `src/`、`tests/`、`docs/architecture/`
  的保护，那是真实风险面；只为一处便利关掉整条规则不成立。
- **改 `docs/tests/README.md` 的命名规则为英文**（零代码改动）：同样可行，但等于推翻维护者对
  检索体验的判断，属产品口径而非技术选择。
- **豁免清单写成 `--root` 命令行参数**：把项目级约定变成每次可调的开关，反而更容易漂移。
