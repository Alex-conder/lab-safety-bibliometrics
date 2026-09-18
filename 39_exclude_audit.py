# -*- coding: utf-8 -*-
"""
阶段3：exclude 集排除理由审计 + 抽样复核包 + 漏筛/误筛率（机器预估值，待人工复核）
输出：outputs/audit/exclude_reason_distribution.csv, sampling_review.csv, method_reliability.md
抽样：random seed=42；exclude 抽 600 条、keep 抽 300 条（供人工复核）
"""
import csv
import os
import random
from collections import Counter

CNKI = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "cnki_raw"))
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "audit"))
os.makedirs(OUT, exist_ok=True)

SAFETY_TITLE = ["安全", "事故", "隐患", "危化", "爆炸", "中毒", "火灾", "辐射", "生物安全"]
TEACH_TITLE = ["教学改革", "课程改革", "课程建设", "人才培养", "教学模式", "教学设计", "课程体系", "思政"]


def reason_code(r):
    txt = (r["title"] or "") + (r["abstract"] or "") + (r["keywords"] or "")
    if "虚拟" in (r.get("reason", "") + txt):
        return "对象不符-虚拟/网络实验室"
    if any(k in (r["title"] or "") for k in ["中学", "小学", "幼儿园"]):
        return "对象不符-中小学"
    return "非安全主题"


def main():
    exc = list(csv.DictReader(open(os.path.join(CNKI, "prescreen_auto_exclude.csv"), encoding="utf-8-sig")))
    keep = list(csv.DictReader(open(os.path.join(CNKI, "final_analysis_set.csv"), encoding="utf-8-sig")))
    # 1) 排除理由分布
    dist = Counter(reason_code(r) for r in exc)
    with open(os.path.join(OUT, "exclude_reason_distribution.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["排除理由", "条数", "占比%"])
        for k, v in dist.most_common():
            w.writerow([k, v, round(v / len(exc) * 100, 2)])
    # 2) 随机抽样（固定种子）
    random.seed(42)
    s_exc = random.sample(exc, 600)
    s_keep = random.sample(keep, 300)
    # 3) 机器预判（供对照，待人工复核）
    rows = []
    miss = 0
    for i, r in enumerate(s_exc, 1):
        suspect = any(k in (r["title"] or "") for k in SAFETY_TITLE)
        if suspect:
            miss += 1
        rows.append({"样本": f"E{i:04d}", "来源集": "exclude", "标题": r["title"], "期刊": r["journal"],
                     "年份": r["year"], "摘要": r["abstract"][:300], "排除理由": reason_code(r),
                     "机器预判": "疑似误排" if suspect else "维持排除", "人工复核": "", "复核人": ""})
    wrong_keep = 0
    for i, r in enumerate(s_keep, 1):
        t = (r["title"] or "")
        suspect = any(k in t for k in TEACH_TITLE) and not any(k in t for k in SAFETY_TITLE)
        if suspect:
            wrong_keep += 1
        rows.append({"样本": f"K{i:04d}", "来源集": "keep", "标题": r["title"], "期刊": r["journal"],
                     "年份": r["year"], "摘要": r["abstract"][:300], "排除理由": "",
                     "机器预判": "疑似误留" if suspect else "维持保留", "人工复核": "", "复核人": ""})
    with open(os.path.join(OUT, "sampling_review.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # 4) 率估算（机器预估）
    miss_rate = round(miss / 600 * 100, 2)
    wrong_rate = round(wrong_keep / 300 * 100, 2)
    with open(os.path.join(OUT, "method_reliability.md"), "w", encoding="utf-8") as f:
        f.write(f"""# 筛选可靠性评估（方法部分草稿）

## 排除理由分布（exclude 集 n=11 683）
""")
        for k, v in dist.most_common():
            f.write(f"- {k}：{v}（{round(v/len(exc)*100,2)}%）\n")
        f.write(f"""
## 抽样复核设计
随机种子 42；exclude 集抽 600 条、keep 集抽 300 条（`sampling_review.csv`），双人独立复核"机器预判"列，不一致处仲裁。

## 漏筛率与误筛率
- **机器预估值（待人工复核替换）**：漏筛率 = {miss_rate}%（exclude 样本中疑似误排 {miss}/600）；误筛率 = {wrong_rate}%（keep 样本中疑似误留 {wrong_keep}/300）。
- 机器预判规则（可追溯）：疑似误排 = 标题含 安全/事故/隐患/危化/爆炸/中毒/火灾/辐射/生物安全；疑似误留 = 标题含教学/课程/人才培养类词且无安全类词。
- 人工复核完成后：以人工标签重算两率，并计算双人 Cohen's Kappa（占位：κ = __）。

## 方法部分拟写（草稿）
"采用'机器规则预筛 + 双人人机复核'的双轨筛选流程。机器预筛依据纳入/排除标准编码规则自动分类，对边界记录（高职、校企合作、附属医院等）经课题组口径裁定后人工裁决。为评估筛选可靠性，按固定随机种子分别抽取排除集 600 条、保留集 300 条进行双人复核，漏筛率 __%、误筛率 __%，复核一致性 Cohen's Kappa = __，表明筛选流程可靠/经仲裁后可用于后续分析。"
""")
    print("排除理由分布:", dict(dist))
    print(f"机器预估 漏筛率 {miss_rate}% 误筛率 {wrong_rate}%")


if __name__ == "__main__":
    main()
