# -*- coding: utf-8 -*-
"""
英文侧：OpenAlex 记录筛选（规则可追溯）+ 计量分析
输入 outputs/bibliometric_openalex/records/en_records.jsonl
输出 outputs/en_analysis/ 下 6 个文件
"""
import csv
import json
import os
import re
from collections import Counter, defaultdict

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "bibliometric_openalex", "records", "en_records.jsonl"))
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "en_analysis"))
os.makedirs(OUT, exist_ok=True)

CLINICAL = ["hospital", "clinical", "patient", "diagnos", "pathol", "medical laboratory",
            "specimen", "blood test", "clinic", "nhs", "ward", "surgery", "oncology",
            "radiology", "pharmacokinet", "therapeutic"]
RESCUE = ["laboratory safety", "lab safety", "biosafety", "biohazard", "biosecurity",
          "safety culture", "chemical safety", "laboratory accident", "lab accident",
          "safety management", "hazardous", "lab-oratory"]
GENERIC = {"medicine","internal medicine","biology","computer science","engineering","psychology",
           "surgery","political science","pathology","disease","business","intensive care medicine",
           "pediatrics","immunology","population","family medicine","cancer","medical education",
           "chemistry","genetics","geography","gastroenterology","oncology","retrospective cohort study",
           "virology","environmental science","sociology","cardiology","law","gene","endocrinology",
           "cohort","diabetes mellitus","emergency medicine","library science","physics","nursing",
           "health care","psychiatry","mathematics","microbiology","ecology","pregnancy",
           "physical therapy","incidence (geometry)","infectious disease (medical specialty)",
           "logistic regression","mathematics education","operations management","quality (philosophy)",
           "antibiotics","gerontology","economics","medical emergency","anesthesia","history",
           "public health","pedagogy","obstetrics","management","artificial intelligence","geology",
           "pharmacology","materials science","confidence interval","cancer research","radiology",
           "world wide web","gynecology","medline","china","outbreak","cohort study","public relations",
           "dermatology","medical laboratory"}

ANCHOR_EN = ["laboratory safety","laboratory accident","safety management","safety culture",
             "safety climate","safety education","biosafety","biosecurity","risk assessment",
             "risk management","hazardous chemicals","chemical safety","laboratory waste",
             "emergency management","occupational health","personal protective equipment",
             "human factors","unsafe behavior","hazard identification","inherent safety",
             "smart laboratory","accident causation","electrical safety","fire safety",
             "laboratory fire","equipment safety","aging equipment","wiring"]
YEARS = list(range(2000, 2027))


def norm(t):
    return re.sub(r"\W+", "", (t or "").lower())


def main():
    recs = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    n0 = len(recs)
    # 去重
    seen, uniq = set(), []
    for r in recs:
        key = (norm(r["title"]), r["a1"], r["year"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    # 规则筛选
    kept, excluded = [], 0
    for r in uniq:
        text = (r["title"] + " " + r["abstract"] + " " + " ".join(r["kw"])).lower()
        if any(c in text for c in CLINICAL) and not any(x in text for x in RESCUE):
            excluded += 1
            continue
        kept.append(r)
    print(f"raw {n0} -> dedup {len(uniq)} -> kept {len(kept)} (excluded clinical {excluded})")

    with open(os.path.join(OUT, "en_screened.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "year", "title", "journal", "a1", "keywords", "abstract"])
        for r in kept:
            w.writerow([r["id"], r["year"], r["title"], r["journal"], r["a1"],
                        ";".join(r["kw"]), r["abstract"][:500]])

    # 年度
    yc = Counter(r["year"] for r in kept if r["year"])
    with open(os.path.join(OUT, "en_yearly_screened.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["year", "works"])
        for y in YEARS:
            w.writerow([y, yc.get(y, 0)])

    # 关键词 Top50（剔除学科泛词）
    kw = Counter()
    for r in kept:
        for k in set(r["kw"]):
            kl = k.lower()
            if kl not in GENERIC:
                kw[k] += 1
    with open(os.path.join(OUT, "en_kw_top50.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "works"])
        for k, c in kw.most_common(50):
            w.writerow([k, c])

    # 锚定词趋势（全文匹配）
    per_year_total = yc
    anchor = []
    for term in ANCHOR_EN:
        t = term.lower()
        yc_t = Counter()
        total = 0
        for r in kept:
            text = (r["title"] + " " + r["abstract"] + " " + " ".join(r["kw"])).lower()
            if t in text:
                total += 1
                if r["year"]:
                    yc_t[r["year"]] += 1
        early = sum(yc_t.get(y, 0) for y in YEARS if y <= 2012)
        mid = sum(yc_t.get(y, 0) for y in YEARS if 2013 <= y <= 2020)
        late = sum(yc_t.get(y, 0) for y in YEARS if y >= 2021)
        te = sum(per_year_total.get(y, 0) for y in YEARS if y <= 2012)
        tl = sum(per_year_total.get(y, 0) for y in YEARS if y >= 2021)
        se, sl = (early / te if te else 0), (late / tl if tl else 0)
        ratio = round(sl / se, 2) if se > 0 else None
        anchor.append([term, total, early, mid, late,
                       round(se * 100, 3), round(sl * 100, 3), ratio])
    anchor.sort(key=lambda x: -(x[1] or 0))
    with open(os.path.join(OUT, "en_anchor_screened.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["term", "total", "w_2000_2012", "w_2013_2020", "w_2021_2026",
                    "share_early_pct", "share_late_pct", "late_vs_early_ratio"])
        w.writerows(anchor)

    with open(os.path.join(OUT, "en_screen_notes.md"), "w", encoding="utf-8") as f:
        f.write("# 英文侧筛选与分析（OpenAlex 记录级，非预演聚合）\n\n")
        f.write(f"- 原始记录：{n0}（OpenAlex，检索式同论文英文式，2000—2026，article+review，English）\n")
        f.write(f"- 去重后：{len(uniq)}\n- 临床噪声剔除：{excluded}（规则：含 hospital/clinical/patient 等且不含 lab safety/biosafety 等挽救词）\n")
        f.write(f"- **最终纳入：{len(kept)}**\n\n")
        f.write("## 年度分布\n\n| 年 | 篇数 |\n|---|---|\n")
        for y in YEARS:
            f.write(f"| {y} | {yc.get(y,0)} |\n")
        f.write("\n## 关键词 Top 20（剔学科泛词）\n")
        for k, c in kw.most_common(20):
            f.write(f"- {k}: {c}\n")
        f.write("\n## 锚定词趋势\n\n| 词 | 总量 | 00-12 | 13-20 | 21-26 | 近期/早期比 |\n|---|---|---|---|---|---|\n")
        for a in anchor:
            f.write(f"| {a[0]} | {a[1]} | {a[2]} | {a[3]} | {a[4]} | {a[7]} |\n")
    print("en analysis done:", OUT)


if __name__ == "__main__":
    main()
