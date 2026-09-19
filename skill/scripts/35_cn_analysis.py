# -*- coding: utf-8 -*-
"""
中文计量分析（keep 集）：关键词频次（同义词归并）、锚定词逐年趋势、简化突现检测、共现对。
输出：outputs/cnki_raw/cn_analysis/ 下若干 CSV + notes.md
方法声明：突现为简化算法（年度占比 z>2 连续段），非 Kleinberg 状态机；正式稿可用 CiteSpace 复跑。
"""
import csv
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
import re
from collections import Counter, defaultdict

OUT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs"), "cnki_raw"))
ANA = os.path.join(OUT, "cn_analysis")
os.makedirs(ANA, exist_ok=True)

# 同义词归并（保守，只并确定等价者）
MERGE = {
    "危化品": "危险化学品", "高校实验室安全": "实验室安全", "大学实验室": "高校实验室",
    "高等学校实验室": "高校实验室", "安全教育培训": "安全教育", "安全教育培训体系": "安全教育",
    "高校": "高校实验室",  # 在 keep 集中“高校”均为高校实验室语境
}
# 无实义停用词
STOP = {"对策", "问题", "管理", "建设", "改革", "创新", "实践", "思考", "研究", "探索", "安全", "高校", "应用", "分析", "探讨"}

ANCHOR_CN = ["高校实验室", "实验室安全", "安全管理", "危险化学品", "实验室事故", "风险评估",
             "安全教育", "安全文化", "生物安全", "实验室建设", "精细化管理", "信息化管理",
             "隐患排查", "应急管理", "实验教学", "开放实验室", "职业健康", "个人防护",
             "废弃物处理", "不安全行为", "人机工程学", "双重预防机制", "本质安全",
             "安全准入", "智慧实验室", "事故致因", "实验室安全管理体系", "安全检查", "信息化"]

YEARS = list(range(2000, 2027))


def load():
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "prescreen_keep.csv"
    rows = []
    with open(os.path.join(OUT, src), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    print("input:", src, len(rows))
    return rows


def kws_of(r):
    out = []
    for t in re.split(r"[;；]", r["keywords"] or ""):
        t = t.strip()
        if not t:
            continue
        t = MERGE.get(t, t)
        if t not in STOP:
            out.append(t)
    return out


def text_of(r):
    return (r["title"] or "") + " " + (r["keywords"] or "") + " " + (r["abstract"] or "")


def main():
    rows = load()
    per_year_total = Counter(r["year"] for r in rows if r["year"])

    # 1) 关键词频次 Top50
    kw = Counter()
    kw_year = defaultdict(Counter)
    for r in rows:
        ks = kws_of(r)
        for t in set(ks):
            kw[t] += 1
            if r["year"]:
                kw_year[t][r["year"]] += 1
    with open(os.path.join(ANA, "cn_kw_top50.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "works"])
        for t, c in kw.most_common(50):
            w.writerow([t, c])

    # 2) 锚定词趋势（标题+关键词+摘要全文匹配）
    anchor_rows = []
    for term in ANCHOR_CN:
        yc = Counter()
        total = 0
        for r in rows:
            if term in text_of(r):
                total += 1
                if r["year"]:
                    yc[r["year"]] += 1
        early = sum(yc.get(str(y), 0) for y in YEARS if y <= 2012)
        mid = sum(yc.get(str(y), 0) for y in YEARS if 2013 <= y <= 2020)
        late = sum(yc.get(str(y), 0) for y in YEARS if y >= 2021)
        te = sum(per_year_total.get(str(y), 0) for y in YEARS if y <= 2012)
        tl = sum(per_year_total.get(str(y), 0) for y in YEARS if y >= 2021)
        se, sl = (early / te if te else 0), (late / tl if tl else 0)
        ratio = round(sl / se, 2) if se > 0 else None
        first = next((y for y in YEARS if yc.get(str(y), 0) >= 3), None)
        anchor_rows.append([term, total, early, mid, late, first, round(se * 100, 2), round(sl * 100, 2), ratio])
    with open(os.path.join(ANA, "cn_anchor_trends.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["term", "total", "w_2000_2012", "w_2013_2020", "w_2021_2026", "first_year_ge3", "share_early_pct", "share_late_pct", "late_vs_early_ratio"])
        w.writerows(sorted(anchor_rows, key=lambda x: -(x[1] or 0)))

    # 3) 简化突现检测（频次≥30 的词）
    bursts = []
    all_years = [str(y) for y in YEARS]
    for t, c in kw.items():
        if c < 30:
            continue
        shares = []
        for y in all_years:
            pt = per_year_total.get(y, 0)
            shares.append(kw_year[t].get(y, 0) / pt if pt else 0)
        mean = sum(shares) / len(shares)
        sd = (sum((s - mean) ** 2 for s in shares) / len(shares)) ** 0.5
        if sd == 0:
            continue
        zs = [(s - mean) / sd for s in shares]
        # 找最长连续 z>2 段
        best, cur = None, None
        for i, z in enumerate(zs):
            if z > 2:
                if cur is None:
                    cur = [i, i, z]
                else:
                    cur[1] = i
                    cur[2] = max(cur[2], z)
            else:
                if cur and (best is None or cur[2] > best[2]):
                    best = cur
                cur = None
        if cur and (best is None or cur[2] > best[2]):
            best = cur
        if best:
            bursts.append([t, c, all_years[best[0]], all_years[best[1]], round(best[2], 2)])
    bursts.sort(key=lambda x: -x[1])
    with open(os.path.join(ANA, "cn_bursts.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "works", "burst_start", "burst_end", "max_z"])
        w.writerows(bursts[:25])

    # 4) 共现对（Top60 词）
    top60 = [t for t, _ in kw.most_common(60)]
    co = Counter()
    for r in rows:
        ks = [t for t in set(kws_of(r)) if t in top60]
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                co[tuple(sorted((ks[i], ks[j])))] += 1
    with open(os.path.join(ANA, "cn_copairs_top100.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["kw1", "kw2", "co_works"])
        for (a, b), c in co.most_common(100):
            w.writerow([a, b, c])

    # 5) notes
    with open(os.path.join(ANA, "cn_analysis_notes.md"), "w", encoding="utf-8") as f:
        f.write("# 中文计量分析（机器预筛 keep 集，n=5745）\n\n")
        f.write("方法：同义词保守归并；突现为简化 z-score 法（正式稿可 CiteSpace 复跑）；锚定词为全文匹配。\n\n")
        f.write("## 关键词 Top 20\n")
        for t, c in kw.most_common(20):
            f.write(f"- {t}: {c}\n")
        f.write("\n## 锚定词趋势（按总量）\n\n| 词 | 总量 | 00-12 | 13-20 | 21-26 | 近期/早期比 |\n|---|---|---|---|---|---|\n")
        for r in sorted(anchor_rows, key=lambda x: -(x[1] or 0)):
            f.write(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[8]} |\n")
        f.write("\n## 突现词（简化法 Top15）\n\n| 词 | 频次 | 突现起 | 突现止 | 最大z |\n|---|---|---|---|---|\n")
        for b in bursts[:15]:
            f.write(f"| {b[0]} | {b[1]} | {b[2]} | {b[3]} | {b[4]} |\n")
    print("analysis done:", ANA)


if __name__ == "__main__":
    main()
