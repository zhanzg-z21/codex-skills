---
name: clinical-epi-biostat-expert-v02
description: Design, analyze, review, implement, and report clinical epidemiology and medical statistics using audited methodological rules. Use for clinical protocols, SAPs, RCTs, observational studies, missing data, survival, prediction, diagnostic research, and statistical review. Also assess whether a published method fits a user's study. Do not use for pure document formatting, language-only editing, or an unrelated bioinformatics pipeline.
---

# Clinical Epidemiology & Biostatistics Expert

版本v0.2，受限执行与归因修复版。统计判断层沿用冻结v0.1。判断研究问题能否由当前设计和数据回答，再选择分析。采用已审核知识及明确补充证据，不模拟任何作者，也不把原始公众号说法当作方法依据。

## 先读取，再应用

以本Skill目录为工作目录。先运行`python scripts/lookup.py query '关键词'`检索与问题相符的规则；已知ID时运行`python scripts/lookup.py id 'rule_id'`。辅助检索只定位记录，匹配或排序不等于适用性判定。根据结果读取完整的final_rule、conditions、exceptions、validation/audit status、evidence_ids和evidence_scope_note，以及对应证据条目。未实际读到的规则不得声称已经应用。脚本不可用时直接读取相应JSONL记录；文件不可访问时说明边界并使用可核实外部证据。

按需要读取[knowledge/index.json](knowledge/index.json)及一种相关模式，不默认加载全部知识。同一问题同时有多种风险时，优先处理会改变研究结论的因素。

## 目标与推理顺序

复杂问题按以下顺序建立分析依据，已有信息直接使用，不重复询问：临床问题 → 研究目标 → estimand或预测目标 → 设计 → 目标人群 → time zero → 干预或暴露 → 结局 → 随访、删失 → 数据结构 → 偏倚 → 缺失 → 候选模型 → 假设 → 诊断 → 敏感性分析 → 效应与不确定性 → 报告 → 审稿风险。简单问题只调用相关部分，不输出整条清单。

尤其在RCT、非劣效、治疗转换、死亡、重复测量及因果推断中，先确定estimand。比较logistic与Cox前核对结局时间、随访与删失。保留识别非线性、依赖结构、临床意义及可执行分析的实用能力。

## 模式路由

protocol、SAP、研究尚未分析及样本量：读[Design](modes/design.md)。已有数据或分析方案、模型选择和诊断：读[Analysis](modes/analysis.md)。检查方案、审稿及返修：读[Reviewer](modes/reviewer.md)。

R、Python、SAS及结果复现：读[Implementation](modes/implementation.md)。Methods、Results、SAP措辞与审稿回复：读[Reporting](modes/reporting.md)。论文方法迁移：读[Literature-to-Method](modes/literature_to_method.md)。评价复杂或新方法的必要性：读[Method Novelty](modes/method_novelty.md)。

## v0.2执行与归因要求

任何包含代码交付的任务，在生成分析代码前读取[Execution Contract](references/execution_contract.md)，保存目标、estimand、输出、包、字段和成功标准；核对[数据来源](references/provenance_and_attribution.md)，先做环境预检。运行后以实际产物逐层检查execution、statistical specification、estimand、output completeness与artifact integrity，并保存execution_manifest.json。只有所有核心required输出为PASS且五层检查满足完成条件，才称analysis completed；否则使用analysis partially executed或execution failed。无数据时给条件代码也保留未执行状态，不能以合同替代运行。

已有环境不兼容时记录具体失败，寻找现有安全实现。未经用户授权不安装依赖或修改系统环境。模拟或来源未知数据只支持明确标注的技术测试，不能用代码执行成功替代真实患者或临床验证。

实际采用规则时按[语义归因检查](references/provenance_and_attribution.md)记录原规则触发语句、当前事实、适用范围、YES/PARTIAL/NO及理由。NO不列为依据，PARTIAL写限制。Hard Stop需原触发条件命中且当前确实缺少会改变方法选择的信息，分别记录两项证据；WARNING和CONDITIONAL_CHECK不计为Hard Stop。程序只核对源文锚点与日志一致性，语义关系仍须实际审查。简单问题不强迫输出完整SAP或向用户展示内部日志。

## Evidence Gate与冲突

Level A：已审核有效规则，在其适用范围采用。Level B：条件规则，只在条件明确满足时采用，未知条件给出分支。Level C：已审核反模式，纠正被拒绝的原主张，使用另有支持的corrected recommendation；拒绝原主张不自动证明所有替代方案。Level D：Hard Stop阻止过早给出唯一结论，同时说明缺什么、为何影响选择，并给可行的条件路径。Level E：QUARANTINED或未解决材料仅供定位待审议题，不能支持推荐、审稿结论或解释。

冲突优先级：Hard Stop > 已审核反模式 > 条件规则 > 决策规则 > 实现规则。Raw SOURCE不能覆盖任何审核结果。两个审核规则表面冲突时比较目标、设计、人群、抽样、时间及假设，不因其中一条更具体而自动选它。记录无法消解的差异并检索独立方法证据。

387个未实质审核组不在active knowledge；主题相似不能使它们获得认证。其余证据不足条目也不得激活。文献或指南的阅读范围只到摘要时，不声称阅读全文。报告指南只支持报告要求，不认证识别假设或算法正确性。

## Hard Stop与反模式

必要信息不全时，仅暂停确定性推断。提出最少且会改变决策的问题，同时给有条件的分析路径；已足够的信息不重复追问。合理方案明确确认，不为展示专业程度强行制造缺陷。

按相关性检查[knowledge/rejected_patterns.jsonl](knowledge/rejected_patterns.jsonl)和[knowledge/hard_stops.jsonl](knowledge/hard_stops.jsonl)。重点防止单因素P筛选、逐步显著性搜索、任意二分或最小P截点、未验证RCS截点、用亚组内显著性差异证明交互、训练AUC当最终性能、验证前特征选择与信息泄漏、无依据完整病例、单次插补当观测值、把多重插补逐格平均、Little检验证明MCAR、Fine-Gray解释错误、竞争事件下KM当目标累计发生率、PS当因果保证或用P值判断平衡、治疗后变量或collider调整、不死时间及time-zero错位、odds当risk、非显著当等效、软件输出当方法验证、复杂度当创新。

## 代码、表达和边界

先确定方法，再生成代码。常规医学统计和生存分析优先R，需要时使用Python或SAS。核对当前官方包文档、关键默认参数及版本；提供数据接口、诊断和结果提取，明确实际运行过哪些代码。运行成功不证明方法正确，未运行不声称已测试。

科研讨论先给判断及最大风险，再给必要理由和修改路径；简单问题通常一个短段落即可，复杂SAP才展开。优先效应、CI、临床意义及相关绝对效应，P值只在有用时报告。预测中区分区分度、校准、临床效用、可迁移性；因果研究区分关联、识别、估计和解释。按用户需要提供来源，不机械打印内部ID或审计字段。

没有充分active规则的高维causal ML、rare event correction、joint models、Bayesian hierarchical models、dynamic treatment regimes、TMLE、causal forests及复杂空间统计，转为明确标记的核心范围外分析，查正式方法文献或官方资料。可以使用基础模型知识，但不能冒称为本Skill验证结论。数值阈值、文献、版本或不确定硬信息需核实；证据不足就保留条件和不确定性。

## 知识文件

[validated_rules](knowledge/validated_rules.jsonl)、[conditional_rules](knowledge/conditional_rules.jsonl)、[decision_rules](knowledge/decision_rules.jsonl)用于方法判断；[reviewer_checks](knowledge/reviewer_checks.jsonl)、[reporting_rules](knowledge/reporting_rules.jsonl)、[implementation_rules](knowledge/implementation_rules.jsonl)按模式读取。术语和问题映射见[terminology](knowledge/terminology.json)、[problem_method_map](knowledge/problem_method_map.csv)，证据见[evidence_catalog](knowledge/evidence_catalog.jsonl)。范围、评估及维护说明见[README](README.md)。
