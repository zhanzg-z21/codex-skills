# Clinical Epidemiology & Biostatistics Expert v0.2

此版本只修复执行验收、环境预检、数据来源和规则语义归因。统计核心文件与v0.1逐字节一致，387个未审核canonical groups继续隔离。旧规则条目保留v0.1版本标签，表示其审核来源，不应伪改为重新审核。

从[SKILL.md](SKILL.md)进入七种原有模式。方法审查仍先确定目标、设计和偏倚，再选择模型。代码任务读取[执行合同](references/execution_contract.md)和[来源与归因](references/provenance_and_attribution.md)。脚本检查不能代替方法学判断，也不自动验证声明的来源真伪或自然语言推理。

原v0.1及其测试结果保存在相邻clinical_epi_biostat_expert目录，未覆盖。本版本开发回归、独立执行留出测试和升级报告保存在项目的20_v0.2_upgrade目录。开发中见过的回归案例不计为新留出评估。v0.2没有全局安装，也没有自动替换用户的默认版本。

来源仍分为SOURCE、DISTILLATION、VALIDATION和EXPERT_RULE。知识和证据索引见knowledge/index.json及knowledge/evidence_catalog.jsonl。只读取摘要的材料不能被声称已读全文，报告规范不能认证识别或算法正确性。范围外方法标注OUTSIDE_VALIDATED_SCOPE并另查原始方法依据，不激活隔离资料。

完整运行、五层核查、数据来源允许的验证称谓分别记录。技术模拟成功不等于临床验证，环境中断也不自动说明统计方法错误。升级结论和是否建议替代默认版本以本轮升级报告为准，未完成人类专家复核。
