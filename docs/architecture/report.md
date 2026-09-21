# report 内部设计

状态: 草稿（T2.6–T2.7 落地时升定稿） | 对应: modules §9、PRD FR-F

## 职责边界

`ReportModel`（findings + 分数 + 证据简报 + coverage + rejected + 成本附录）→
质量门禁 → HTML/Markdown 落盘。**渲染器没有创作权**：只呈现，不推断、不改写文案
（读者文案归 analysis 产出所有）。

## 流水线

```
1 assemble   从 Lead 冻结快照 + longitudinal 视图组装 ReportModel（纯读取）
2 quality    report-quality 校验器，错误码制：
               E1 无证据断言  E2 分数越天花板  E3 Unobserved 处出现具体断言
               E4 比较块缺 Comparability+Verdict（F4 门禁）  E5 severity×lifecycle 矛盾
             任一命中 → 拒绝渲染（不是警告降级）
3 render     Jinja2 模板；HTML 自包含（内联 CSS + 内联 SVG 趋势图，零外链）；
             Markdown 同结构镜像；输出确定性（排序固定、除 run 元数据块外无时间戳）
             ——同输入两次渲染字节级一致，可 diff 审阅
4 validate   渲染产物过 schema/链接完整性自检（HTML 内锚点、SVG 转义）后原子写 run-dir
```

## 版式契约（对应原版四件套卡片）

发现卡固定区块：标题+severity+dimension → WHY IT MATTERS(consequence) →
EXPECTED OUTPUT(expected_outcome) → AI FIX 区块(repair 边界+步骤) → Acceptance checks；
rejected 附录逐条带原因码；报告头部横幅呈现 lane 三态与 deterministic-only/partial 标注。

## 测试要点

五类质量错误各一组注入必拒；双渲染字节一致（幂等）；无证据处渲染为 `Unobserved`
而非省略；自包含性扫描（外链正则零命中）；长文本/中文/代码块在 HTML 与 MD 双路径的转义正确。
