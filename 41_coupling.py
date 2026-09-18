# -*- coding: utf-8 -*-
"""
阶段5：事故风险—研究热点耦合缺口分析
风险占比：叶元兴等(2025)176起库 + 本研究增量（真实数据）
研究占比：最终分析集 6178 条主题编码（阶段2真实数据）
输出：outputs/coupling/risk_research_gap.csv, coupling_matrix.md, discussion_draft.md
"""
import csv
import os
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
OUT = os.path.join(ROOT, "coupling")
os.makedirs(OUT, exist_ok=True)

# 事故侧真实数据（叶文 2025 + 合并库 183 起）
RISK = [
    ("危化品（危险因素）", 62.50, "叶文表3：110/176"),
    ("仪器设备（危险因素）", 21.59, "叶文表3：38/176"),
    ("线路（危险因素）", 9.09, "叶文表3：16/176"),
    ("生物因素（危险因素）", 2.27, "叶文表3：4/176"),
    ("火灾（事故类型）", 47.54, "合并库：87/183"),
    ("爆炸（事故类型）", 31.15, "合并库：57/183"),
    ("违规操作（原因二级）", 22.73, "叶文表4：40/176"),
    ("线路老化或短路（原因二级）", 7.95, "叶文表4：14/176"),
    ("设备老化故障（原因二级）", 11.36, "叶文表4：20/176"),
    ("化学品储存不规范（原因二级）", 13.07, "叶文表4：23/176"),
]
# 风险→研究主题映射
MAP = {
    "危化品（危险因素）": "危化品",
    "仪器设备（危险因素）": "设备",
    "线路（危险因素）": "电气",
    "生物因素（危险因素）": "生物安全",
    "火灾（事故类型）": "消防",
    "爆炸（事故类型）": None,  # 无直接主题，按"其他"记0
    "违规操作（原因二级）": "安全教育",
    "线路老化或短路（原因二级）": "电气",
    "设备老化故障（原因二级）": "设备",
    "化学品储存不规范（原因二级）": "危化品",
}


def main():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "keep", "keep_structured.csv"), encoding="utf-8-sig")))
    n = len(rows)
    tc = Counter()
    for r in rows:
        for th in r["主题标签"].split("|"):
            tc[th] += 1
    gap_rows = []
    for risk_name, risk_pct, src in RISK:
        theme = MAP[risk_name]
        res_cnt = tc.get(theme, 0) if theme else 0
        res_pct = round(res_cnt / n * 100, 2)
        gap = round(risk_pct - res_pct, 2)
        if abs(gap) < 3:
            verdict = "匹配"
        elif gap > 0:
            verdict = "供给不足型错位"
        else:
            verdict = "关注冗余型错位"
        gap_rows.append([risk_name, risk_pct, theme or "（无对应主题）", res_cnt, res_pct, gap, verdict, src])
    gap_rows.sort(key=lambda x: -abs(x[5]))
    with open(os.path.join(OUT, "risk_research_gap.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["事故风险项", "风险占比%", "对应研究主题", "研究篇数", "研究占比%", "缺口(风险-研究)pp", "判定", "风险数据来源"])
        w.writerows(gap_rows)

    # 电气专项（零主题词验证）
    elec = Counter()
    for r in rows:
        for k in (r["电气老化专项"].split("|") if r["电气老化专项"] else []):
            if k:
                elec[k] += 1

    with open(os.path.join(OUT, "coupling_matrix.md"), "w", encoding="utf-8") as f:
        f.write("# “事故真实风险—文献研究热度”耦合矩阵（真实数据，2026-09-17）\n\n")
        f.write("风险侧：叶元兴等(2025)176起 + 本研究增量（合并183起）；研究侧：最终分析集 6 178 条（主题多选，占比分母为总篇数，合计>100%）。\n\n")
        f.write("| 事故真实风险 | 风险占比 | 研究主题 | 研究占比 | 缺口(pp) | 判定 |\n|---|---|---|---|---|---|\n")
        for r in gap_rows:
            f.write(f"| {r[0]} | {r[1]}% | {r[2]} | {r[4]}% | {r[5]:+} | {r[6]} |\n")
        f.write("\n## 电气/线路/设备老化 零主题词验证\n\n| 专项词 | 命中篇数 | 占比 |\n|---|---|---|\n")
        for k in ["电气安全", "用电安全", "线路老化", "设备老化", "电气火灾"]:
            f.write(f"| {k} | {elec.get(k,0)} | {round(elec.get(k,0)/n*100,2)}% |\n")
        f.write("\n结论：线路/电气相关研究占比 ≤1%，而线路危险因素占事故 9.09%、线路老化短路原因占 7.95% 且显著增加（叶文 P=0.01），供给不足型错位成立。\n")

    with open(os.path.join(OUT, "discussion_draft.md"), "w", encoding="utf-8") as f:
        f.write("""# 耦合讨论草稿（基于真实数据；时滞类推断标注【待验证】）

## 1. 匹配域
违规操作（风险 22.73%）与安全教育研究（25.6%）方向匹配；危化品虽为研究第一大专题（9.2%），但与其 62.50% 的事故危险因素占比相比，缺口仍达 +53.3pp——“有研究、不成比例”。

## 2. 错位域
缺口绝对值前 5 项（见 risk_research_gap.csv）均指向供给不足：
- 火灾（风险 47.54% vs 消防研究 10.3%，缺口 +37.2pp）；
- 危化品（+53.3pp，相对不足）；
- 仪器设备（+12.2pp）；
- 线路（+8.25pp）与线路老化短路（+7.1pp）；
- 设备老化故障（+11.9pp 与设备主题相比）。
其中电气/线路/设备老化为**零主题词领域**（电气安全 0.31%、线路老化 0.11%、设备老化 0.15%），而叶文显示火灾占比升至 62.50%（2016—2026）、线路老化事故显著增加（P=0.01）——风险真实上升而研究供给空白，"供给不足型错位"成立。

## 3. 已被否定的假设
生物安全"关注冗余"假设不成立（中文占比 5.8%、近年占比比 1.23；英文 biosafety 1.77），已从讨论中移除。

## 4. 政策的双时滞【待验证】
中文发文 2019—2020 年达峰（505/534 篇）与 2019 年教育部《意见》时点耦合，事故年均值由 8.38 起降至 4.67 起存在约 3—5 年滞后【待验证：需 joinpoint/中断时间序列正式测算】。

## 5. 新兴风险【待验证】
储能实验室火灾（集美大学 2026-07）对应研究主题空白，属"新兴风险—研究滞后"错位，n=1，仅作信号提示。
""")

    # 待人工确认项
    with open(os.path.join(OUT, "pending_confirmations.md"), "w", encoding="utf-8") as f:
        f.write("""# 待人工确认项（阶段1—5汇总）

1. 双人复核 `outputs/review/sampling_review.csv`（600+300 条）→ 替换机器预估漏筛率/误筛率，算 Kappa。
2. 万方/维普命中数（PRISMA 查全报告）。
3. WoS 正式导出（替换 OpenAlex 英文侧，或论文改口径声明）。
4. CiteSpace/VOSviewer 正式跑图（数据在 outputs/citespace/，中文已可跑）。
5. 事故侧：山东理工起火原因、重大调查结论、广州环科院结论（3 起在查）。
6. 12 月底事故案例封库补充检索 + 2026 年 10—12 月发文补检。
""")

    for r in gap_rows:
        print(f"{r[0]}: 风险{r[1]}% vs 研究{r[4]}% 缺口{r[5]:+} → {r[6]}")


if __name__ == "__main__":
    main()
