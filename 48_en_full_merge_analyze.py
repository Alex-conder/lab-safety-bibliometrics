# -*- coding: utf-8 -*-
"""
英文全量：OpenAlex(18.3k) + S2(51.4k) 合并去重 → 规则筛选 → 计量分析
输出 outputs/en_analysis/full/
"""
import csv
import json
import os
import re
from collections import Counter, defaultdict

REC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "bibliometric_openalex", "records"))
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "en_analysis", "full"))
os.makedirs(OUT, exist_ok=True)

CLINICAL = ["hospital", "clinical", "patient", "diagnos", "pathol", "medical laboratory",
            "specimen", "blood test", "clinic", "nhs", "ward", "surgery", "oncology",
            "radiology", "pharmacokinet", "therapeutic"]
RESCUE = ["laboratory safety", "lab safety", "biosafety", "biohazard", "biosecurity",
          "safety culture", "chemical safety", "laboratory accident", "lab accident",
          "safety management", "hazardous", "lab-oratory"]
GENERIC = set()  # 从试点脚本借（此处从44号脚本语义复制精简版）
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
    recs = []
    srcs = {}
    for fn, tag in [("en_records.jsonl", "openalex"), ("s2_records.jsonl", "s2")]:
        for line in open(os.path.join(REC, fn), encoding="utf-8"):
            r = json.loads(line)
            recs.append((tag, r))
    n_raw = len(recs)
    # 合并去重（先 OpenAlex 后 S2，OA 有摘要和关键词优先保留）
    seen = {}
    for tag, r in recs:
        key = (norm(r["title"]), r["a1"], r["year"])
        if key in seen:
            seen[key][1].add(tag)  # 记录双源命中
            continue
        seen[key] = [r, {tag}]
    merged = [(v[0], v[1]) for v in seen.values()]
    n_dedup = len(merged)
    # 类型过滤（S2 无类型者保留待查）
    type_cnt = Counter()
    typed = []
    type_excl = 0
    for r, tags in merged:
        t = (r.get("type") or "").lower()
        if "openalex" in tags:
            typed.append((r, tags))  # OA 侧已在 API 限定 article|review
            continue
        if "journalarticle" in t.replace(" ", "") or "review" in t:
            typed.append((r, tags))
        elif not t:
            typed.append((r, tags))  # 类型未标注，保留（多数为期刊）
            type_cnt["s2_type_empty"] += 1
        else:
            type_excl += 1
            type_cnt[t] += 1
    # 规则筛选
    kept, excl_clin = [], 0
    for r, tags in typed:
        text = (r["title"] + " " + r["abstract"] + " " + " ".join(r["kw"])).lower()
        if any(c in text for c in CLINICAL) and not any(x in text for x in RESCUE):
            excl_clin += 1
            continue
        kept.append((r, tags))
    n_kept = len(kept)
    print(f"raw {n_raw} -> dedup {n_dedup} -> type-excl {type_excl} -> clin-excl {excl_clin} -> kept {n_kept}")

    # PRISMA 链
    with open(os.path.join(OUT, "en_prisma.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["阶段", "数量", "说明"])
        w.writerows([
            ["拉取-OpenAlex", 18300, "API 记录级（配额中断点）"],
            ["拉取-S2", 51357, "bulk search 全量"],
            ["合并去重后", n_dedup, "题名规范化+一作+年份"],
            ["类型剔除", type_excl, "会议/书籍章节等（S2侧）"],
            ["临床噪声剔除", excl_clin, "规则：临床信号词且无安全挽救词"],
            ["最终纳入", n_kept, ""],
        ])
    # 明细
    with open(os.path.join(OUT, "en_screened_full.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "year", "title", "journal", "a1", "source", "keywords", "abstract"])
        for r, tags in kept:
            w.writerow([r["id"], r["year"], r["title"], r["journal"], r["a1"],
                        "+".join(sorted(tags)), ";".join(r["kw"]), r["abstract"][:500]])
    # 年度
    yc = Counter(r["year"] for r, _ in kept if r["year"])
    with open(os.path.join(OUT, "en_yearly_full.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["year", "works"])
        for y in YEARS:
            w.writerow([y, yc.get(y, 0)])
    # 关键词 Top50（仅有 OA 关键词的记录）
    kw = Counter()
    n_with_kw = 0
    for r, tags in kept:
        if r["kw"]:
            n_with_kw += 1
            for k in set(r["kw"]):
                if k.lower() not in GENERIC:
                    kw[k] += 1
    with open(os.path.join(OUT, "en_kw_top50_full.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "works"])
        for k, c in kw.most_common(50):
            w.writerow([k, c])
    # 锚定词（全文匹配）
    anchor = []
    te = sum(yc.get(y, 0) for y in YEARS if y <= 2012)
    tl = sum(yc.get(y, 0) for y in YEARS if y >= 2021)
    for term in ANCHOR_EN:
        t = term.lower()
        yc_t = Counter()
        total = 0
        for r, _ in kept:
            text = (r["title"] + " " + r["abstract"] + " " + " ".join(r["kw"])).lower()
            if t in text:
                total += 1
                if r["year"]:
                    yc_t[r["year"]] += 1
        early = sum(yc_t.get(y, 0) for y in YEARS if y <= 2012)
        mid = sum(yc_t.get(y, 0) for y in YEARS if 2013 <= y <= 2020)
        late = sum(yc_t.get(y, 0) for y in YEARS if y >= 2021)
        se, sl = (early / te if te else 0), (late / tl if tl else 0)
        ratio = round(sl / se, 2) if se > 0 else None
        anchor.append([term, total, round(total / n_kept * 100, 2), early, mid, late, ratio])
    anchor.sort(key=lambda x: -(x[1] or 0))
    with open(os.path.join(OUT, "en_anchor_full.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["term", "total", "share_pct", "w_2000_2012", "w_2013_2020", "w_2021_2026", "late_vs_early_ratio"])
        w.writerows(anchor)
    # 报告
    with open(os.path.join(OUT, "en_full_notes.md"), "w", encoding="utf-8") as f:
        f.write("# 英文全量筛选分析（OpenAlex 18.3k + S2 51.4k 合并）\n\n")
        f.write(f"- 合并原始 {n_raw} → 去重 {n_dedup} → 类型剔除 {type_excl} → 临床噪声剔除 {excl_clin} → **纳入 {n_kept}**\n")
        f.write(f"- 含关键词字段记录 {n_with_kw}（仅 OpenAlex 源有；S2 无关键词字段，锚定词为全文匹配不受影响）\n\n")
        f.write("## 年度分布\n\n| 年 | 篇数 |\n|---|---|\n")
        for y in YEARS:
            f.write(f"| {y} | {yc.get(y,0)} |\n")
        f.write("\n## 关键词 Top20\n")
        for k, c in kw.most_common(20):
            f.write(f"- {k}: {c}\n")
        f.write("\n## 锚定词\n\n| 词 | 总量 | 占比% | 00-12 | 13-20 | 21-26 | 近期/早期比 |\n|---|---|---|---|---|---|---|\n")
        for a in anchor:
            f.write(f"| {a[0]} | {a[1]} | {a[2]} | {a[3]} | {a[4]} | {a[5]} | {a[6]} |\n")
    print("full analysis done:", OUT)


if __name__ == "__main__":
    main()
