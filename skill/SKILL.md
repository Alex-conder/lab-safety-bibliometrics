---
name: lab-safety-biblio-coupling
description: 高校实验室安全"文献计量 + 事故案例"耦合分析全流程。覆盖中英文文献获取与筛选（CNKI 人机接力、OpenAlex/Semantic Scholar 双公开源）、事故案例编码与双人复核、主题标注与突现检测（Kleinberg）、LDA 互证、耦合缺口与耦合协调度、暴露量校正事故率、政策节点分段回归（ITS）、期刊格式稿件生成。当用户需要对"研究关注 vs 实际风险"做耦合分析、文献计量、事故案例库统计时使用。
---

# 高校实验室安全：文献计量与事故案例耦合分析管线

## 何时使用

- 做"研究热点 vs 实际风险"耦合/错位分析（本 skill 的核心场景）；
- 中英文双库文献计量（发文趋势、关键词共现、突现词、主题演化）；
- 事故案例库收集、编码、统计（类型/危险因素/环节/两级原因）；
- 需要可复现、可审计的安全类实证研究管线（全部规则可追溯）。

## 输入要求

| 输入 | 说明 | 必需 |
|---|---|---|
| 检索式（中/英） | 主题词组合，见 `config.example.yaml` | 是 |
| 事故基础库 | 已发表案例库（如叶元兴等 176 起）或自建 | 是（耦合分析需要） |
| 暴露量锚点 | 实验室/机构数量年度锚点（≥2 个） | 否（率分析需要） |
| 政策节点 | 年份 + 政策名 | 否（ITS/时间轴需要） |
| 机构数据库权限 | CNKI/万方/维普（校园网 IP 或账号） | 中文全量分析需要 |

## 环境与依赖

- Python 3.10+：`pandas`、`requests/urllib`、`selenium`（CNKI 人机接力用）、`matplotlib`、`networkx`、`scikit-learn`（LDA）、`statsmodels`（ITS/GLM）、`jieba`（中文分词）、`python-docx`、`scipy`；
- R 4.x（仅 `49_trend_test.R` 趋势检验用）；
- Edge 浏览器（CNKI 人机接力导出，用户需手动完成验证码滑块）；
- 输出根目录由环境变量 `BIBLIO_ROOT` 指定（默认 `<项目根>/outputs`）。

## 工作流（按阶段）

### 阶段 0：准备
1. 复制 `config.example.yaml`，按课题改检索式、时段、政策节点；
2. 主题词典放 `assets/theme_dictionary_cn.json` / `theme_dictionary_en.json`；临床噪声规则放 `assets/clinical_noise.json`（非医学领域可清空）。

### 阶段 1：文献获取

**中文（CNKI 全量）**：CNKI 有反爬滑块，必须"人机接力"——Selenium 驱动 Edge，遇验证码由人拖动，脚本自动翻页勾选导出 Refworks 题录：
```
BIBLIO_ROOT=outputs python scripts/30_cnki_full_export_v4.py [起始页]
```
断点续跑（progress.json）；500 条选择上限、6000 条翻页上限需按年份分段（见 `32_cnki_export_v6_yearly.py` 的分段逻辑）。万方/维普只记命中数用于查全。

**英文（双公开源，无需账号）**：
```
BIBLIO_ROOT=outputs python scripts/43_openalex_full_pull.py   # OpenAlex 游标分页，断点续传；有每日配额
BIBLIO_ROOT=outputs python scripts/47_s2_pull.py              # Semantic Scholar bulk API，无配额问题，是配额耗尽时的等效替代
```

### 阶段 2：合并、去重、筛选
```
python scripts/33_merge_dedup.py            # CNKI 批次合并去重（Refworks 解析）
python scripts/34_prescreen.py              # 中文机器预筛（无安全主题词剔除）
python scripts/36_review_stage1.py          # 边界记录规则初判（E1—E10 可追溯）
python scripts/37_apply_rulings.py          # 课题组口径裁定合并最终集
python scripts/48_en_full_merge_analyze.py  # 英文双源合并去重 + 临床噪声剔除
```
**必须双人复核**：按固定种子抽样（排除 600/保留 300），报告漏筛率/误筛率/Kappa（`39_exclude_audit.py` 生成抽样包）。经仲裁确认的误筛模式（如"信息安全/网络安全"学科名误纳）应固化为规则回灌全集（见 `discipline_name_exclusion`）。

### 阶段 3：计量分析
```
python scripts/35_cn_analysis.py            # 词频/锚定词趋势/简化突现/共现
python scripts/46_kleinberg_bursts.py       # Kleinberg 突现检测（自实现，γ=1.0）
python scripts/51_en_kleinberg.py           # 英文版
python scripts/61_lda_topics.py             # LDA 数据驱动主题互证（k=8—14 稳健性必做）
python scripts/38_keep_structured.py        # 主题编码 + 主题×年份矩阵
```

### 阶段 4：耦合与政策分析
```
python scripts/41_coupling.py               # 风险占比−研究占比缺口矩阵
python scripts/62_coupling_coordination.py  # 耦合度 C / 耦合协调度 D（D 对双侧水平敏感，解读以 C 为主）
python scripts/60_exposure_rate.py          # 暴露量分母 + Poisson 率比精确检验
python scripts/63_its_publications.py       # 政策节点分段回归（纽结模型 + Poisson 对照）
Rscript scripts/49_trend_test.R             # Cochran–Armitage 趋势检验
```

### 阶段 5：稿件与图表
```
python scripts/45_make_fig23.py             # 共现网络 + 突现时间轴
python scripts/54_fig1_fig4_final.py        # 发文趋势 + 政策三线时间轴
python scripts/58_build_lre_final.py        # 《实验室研究与探索》格式 docx
python scripts/64_build_cssj.py             # 《中国安全科学学报》格式 docx（0 引言、三线表、X 分类号）
python scripts/md2docx.py <md> <docx>       # 通用 md→docx
```

## 事故案例编码

- 编码手册：`assets/accident_codebook.md`（类型/危险因素/环节/两级原因 + 2-4 模型分层）；
- 检索渠道优先级：官方通报 > 主流媒体 > 地方/行业媒体；AI 工具仅用于线索发现，事实以官方通报为准；
- 双人背靠背编码，逐变量报告 Cohen's Kappa；细粒度变量（事故类型、原因二级）小样本下 Kappa 偏低属正常，用"直接原因优先"仲裁并在文中声明。

## 关键陷阱（踩过的坑，别再踩）

1. **CNKI 6000 条翻页上限**：直接翻页只能取前 6000 条，必须按年份/时段分段检索；
2. **CNKI 500 条选择上限**：批量勾选满 500 触发告警，批次按记录数（≥460）触发导出；
3. **OpenAlex 每日配额**：约 100 请求/天，断点续传跨天执行；配额耗尽时用 Semantic Scholar 等效替代（S2 bulk API 支持分组布尔检索式）；
4. **S2 无关键词字段**：词频分析只能用 OpenAlex 子集；锚定词全文匹配不受影响；S2 未限语种会有少量非英文记录（需量化声明）；
5. **主题规则单字误配**：如"核"会误配"核心/考核"，规则词至少两字或加边界；
6. **"信息安全/网络安全"学科名误纳**：是预筛最大误筛源，仲裁后必须固化规则回灌；
7. **相关度排序 vs 全量**：OpenAlex 游标拉取按相关度排序，中途截断的数据只能叫"试点"，不得写进论文；
8. **图表-正文编号一致性**：任何编号/数值改动后必须全文机检（残留旧值扫描）。

## 输出清单（BIBLIO_ROOT 下）

- `final_analysis_set.csv`：中文最终分析集；
- `en_analysis/full/`：英文 PRISMA 链、筛选集、年度/关键词/锚定词/突现；
- `risk_research_gap.csv`、`coupling_coordination.csv`：耦合缺口与协调度；
- `exposure/`：实验室数量序列、万室事故率、率比检验；
- `its/`：分段回归结果；
- `lda/`：LDA 主题互证；
- `figures/`、`paper_final_*.docx`：图与期刊格式稿。

## 适配其他课题

换研究主题时只需改：检索式、主题词典、事故编码表、政策节点。全部统计/图形/稿件脚本无需改动（路径由 BIBLIO_ROOT 控制，规则由 assets 驱动）。非实验室领域请先清空 `clinical_noise.json` 的医学噪声规则，避免误剔。
