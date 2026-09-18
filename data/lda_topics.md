# LDA 数据驱动主题互证（sklearn LatentDirichletAllocation，random_state=42）

## 中文（n=5 888，题名+关键词，k=10）

- 主题0: 安全、生物、课程、医学、研究生、实验、调查、标准化、动物、生物学、培训、探索
- 主题1: 安全、化学、科研、化工、环保、专业、实验、工程、探索、浅谈、基础、化工类
- 主题2: 实验教学、中心、共享、技术、仪器设备、大型、示范、开放、平台、仪器、数据、规范化
- 主题3: 信息化、实验、管理模式、平台、环境、开放、创新、为例、探索、学院、安全、专业
- 主题4: 系统、应急、设计、管理系统、消防安全、危化品、智能、联网、技术、理论、优化、实现
- 主题5: 安全、教育、模式、探索、智慧、路径、高等学校、人工智能、培训、构建、校园、创新
- 主题6: 安全、管理体系、构建、文化、探索、准入、制度、安全检查、一流、背景、学科、责任
- 主题7: 安全、化学品、危险、风险、评价、评估、管控、危险源、分级、分析法、综合、模型
- 主题8: 安全、计算机、废弃物、实验、事故、规范、模型、处置、处理、维护、化学试剂、安全事故
- 主题9: 安全、措施、地方、策略、预防、院校、防护、治理、火灾、安全隐患、应对、改进

## 英文（n=33 200，题名+摘要，k=12）

- 主题0: education, learning, students, engineering, development, higher, educational, course, research, virtual, technology, new
- 主题1: university, laboratory, china, engineering, department, science, research, technology, institute, sciences, key, school
- 主题2: system, management, laboratory, information, control, design, network, university, data, systems, technology, model
- 主题3: water, soil, quality, food, samples, nigeria, state, university, collected, health, assessment, land
- 主题4: safety, laboratory, university, laboratories, students, chemical, health, research, risk, chemistry, assessment, waste
- 主题5: health, report, care, review, new, covid, animal, international, conference, first, public, virus
- 主题6: laboratory, management, teaching, construction, universities, colleges, university, experimental, practice, college, laboratories, system
- 主题7: risk, factors, disease, cancer, effects, associated, women, children, treatment, acute, cell, effect
- 主题8: energy, high, power, experimental, nuclear, gas, safety, systems, low, performance, building, water
- 主题9: management, laboratory, effect, agricultural, conducted, experiment, university, field, rice, plant, different, control
- 主题10: dan, pada, laboratorium, drug, universitas, dna, yang, imaging, driving, terhadap, nursing, dalam
- 主题11: research, management, university, project, data, scientific, development, laboratory, resource, laboratories, universities, resources

## 互证结论

双侧 LDA 主题中均未出现以电气安全/线路老化/设备老化为核心的数据驱动主题（各主题 Top12 词经词边界精确匹配无命中；英文主题10 的"d​NA"系印尼语残留记录，imaging 子串误报已排除），与词典标注的"双语空白"结论一致。英文侧检出少量印尼语等非英文记录（约 0.82%，S2 未限定语种所致），已在局限性声明。
