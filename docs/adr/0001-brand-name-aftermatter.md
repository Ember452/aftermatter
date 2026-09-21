# ADR-0001: 项目命名 AfterMatter

日期: 2026-09-21 | 状态: accepted

## 背景
需要一个独立开源品牌：不与 Better Harness 同家族（避免"衍生品"定位）、避开 2026 年
语义已被"执行框架"占用的 harness 一词、PyPI/npm/GitHub 可注册。直觉候选全部实测撞车：
looplens / proofloop（含同名 agent 质量评估插件）/ reverify（942★ 趋势项目）/
groundproof / retroscope（Android 取证框架）均被占用。

## 决定
命名 **AfterMatter**。双关：字面 after + matter（事后留下的成果是否经得起验证）；
词典义"实质的分量"，对治"AI 编码只求能跑"。实测 PyPI 404、npm 404、同领域 GitHub 无冲突。
tagline：*Harness engineering, with evidence.*（harness 只进描述，不进名字）。

## 影响
仓库/包/CLI 标识符见 ADR-0002；README、CONTRIBUTING 以该品牌展开；
名称风险（与 aftermath 的口播混淆）已知并接受，靠 tagline 断词消歧。
