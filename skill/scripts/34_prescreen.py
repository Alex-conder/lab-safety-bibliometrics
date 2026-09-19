# -*- coding: utf-8 -*-
"""
机器预筛（替代不了双人人工初筛，仅作预分类，供人工复核提速）
规则对应论文 2.1 纳入/排除标准：
  auto_exclude: 标题+关键词+摘要中无任何安全主题词 → 纯教学/建设/管理类（排除标准3）
  review_flag : 含 中小学/企业/公司/医院 信号（排除标准2，需人工判定）
  keep        : 其余保留
输出 outputs/cnki_raw/prescreen_*.csv 和 prescreen_report.md
"""
import csv
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
from collections import Counter

OUT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs"), "cnki_raw"))

SAFETY_TERMS = ["安全", "事故", "风险", "隐患", "危险", "危化", "防爆", "应急", "防护",
                "消防", "中毒", "爆炸", "毒害", "辐射", "生物安全", "准入", "双重预防",
                "危险品", "废弃物", "处置", "泄漏", "灼伤", "防火", "用电安全", "气瓶",
                "管制", "剧毒", "易制爆", "安全培训", "安全教育", "安全意识"]
NONUNI_TERMS = ["中学", "小学", "幼儿园", "企业", "公司", "医院", "检验科", "中职", "高职",
                "职业技术学院", "职业院校"]
VIRTUAL_TERMS = ["虚拟仿真", "网络实验室", "虚拟实验室"]


def classify(r):
    text = (r["title"] or "") + " " + (r["keywords"] or "") + " " + (r["abstract"] or "")
    has_safety = any(t in text for t in SAFETY_TERMS)
    nonuni = [t for t in NONUNI_TERMS if t in (r["title"] or "") + (r["affiliations"] or "") + (r["abstract"] or "")]
    virtual_only = any(t in text for t in VIRTUAL_TERMS) and not has_safety
    if not has_safety or virtual_only:
        return "auto_exclude", "无安全主题词" if not virtual_only else "虚拟/网络实验室非实体安全"
    if nonuni:
        return "review_flag", "含非高校信号:" + "/".join(nonuni[:2])
    return "keep", ""


def main():
    rows = []
    with open(os.path.join(OUT, "merged_records.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    for r in rows:
        r["prescreen"], r["reason"] = classify(r)
    cnt = Counter(r["prescreen"] for r in rows)
    for label in ["keep", "review_flag", "auto_exclude"]:
        sub = [r for r in rows if r["prescreen"] == label]
        with open(os.path.join(OUT, f"prescreen_{label}.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(sub)
    # 年度分布（keep 集）
    year_cnt = Counter(r["year"] for r in rows if r["prescreen"] == "keep")
    with open(os.path.join(OUT, "prescreen_report.md"), "w", encoding="utf-8") as f:
        f.write("# 机器预筛报告（供人工复核，非正式 PRISMA 数）\n\n")
        f.write(f"- 总记录：{len(rows)}\n- 保留（keep）：{cnt['keep']}\n- 待人工判定（review_flag）：{cnt['review_flag']}\n- 机器排除（auto_exclude）：{cnt['auto_exclude']}\n\n")
        f.write("## keep 集年度分布\n\n| 年 | 篇数 |\n|---|---|\n")
        for y in sorted(year_cnt):
            if y:
                f.write(f"| {y} | {year_cnt[y]} |\n")
    print("keep:", cnt["keep"], "review:", cnt["review_flag"], "exclude:", cnt["auto_exclude"])


if __name__ == "__main__":
    main()
