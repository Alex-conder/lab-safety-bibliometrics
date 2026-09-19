# -*- coding: utf-8 -*-
"""锚定词补丁：keyword-id 与 search 回退双策略，重算全部锚定词并覆盖三个锚定 CSV + 摘要"""
import csv, json, os, time, urllib.parse, urllib.request

BASE = "https://api.openalex.org/works"
MAILTO = "lab-safety-biblio@example.org"
OUT = os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs"), "bibliometric_openalex")
EN_SEARCH = '((university OR college OR "higher education") AND laboratory AND (safety OR accident OR incident OR risk OR hazard OR management))'
ANCHOR_TERMS = ["laboratory safety","laboratory accident","safety management","safety culture",
    "safety climate","safety education","biosafety","biosecurity","risk assessment",
    "risk management","hazardous chemicals","chemical safety","laboratory waste",
    "emergency management","occupational health","personal protective equipment",
    "human factors","unsafe behavior","hazard identification","inherent safety",
    "smart laboratory","accident causation"]
YEARS = list(range(2000, 2027))

def api(url, retries=6):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lab-safety-biblio/1.1"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"  retry {i+1}: {e}", flush=True)
            time.sleep(4 * (i + 1))
    raise RuntimeError("fail " + url[:150])

def base_filter():
    return (f"title_and_abstract.search:{EN_SEARCH},"
            "publication_year:2000-2026,type:article|review,language:en")

def resolve(term):
    u = "https://api.openalex.org/keywords?" + urllib.parse.urlencode({"search": term, "per_page": 5, "mailto": MAILTO})
    d = api(u)
    rs = d.get("results", [])
    if not rs:
        return None
    for r in rs:
        if r["display_name"].lower() == term.lower():
            return r["id"]
    return rs[0]["id"]

def yearly_by_filter(extra_params):
    p = {"group_by": "publication_year", "mailto": MAILTO}
    p.update(extra_params)
    d = api(BASE + "?" + urllib.parse.urlencode(p))
    return d["meta"]["count"], {int(g["key"]): g["count"] for g in d["group_by"]}

rows = []
for term in ANCHOR_TERMS:
    kid = resolve(term)
    time.sleep(0.3)
    if kid:
        total, yr = yearly_by_filter({"filter": base_filter() + f",keywords.id:{kid}"})
        method = "keyword_id"
    else:
        # 回退：search 参数（短语全文检索）与 filter 取交集
        total, yr = yearly_by_filter({"filter": base_filter(), "search": f'"{term}"'})
        method = "fulltext_search"
    rows.append((term, total, yr, method))
    print(f"  {term}: {total} ({method})", flush=True)
    time.sleep(0.4)

def w(name, header, data):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8-sig") as f:
        wri = csv.writer(f); wri.writerow(header); wri.writerows(data)
    print("wrote", name, len(data), flush=True)

w("en_anchor_terms_summary.csv", ["term", "works_2000_2026", "method"],
  [(t, c, m) for t, c, _, m in sorted(rows, key=lambda x: -x[1])])
w("en_anchor_terms_yearly.csv", ["term", "year", "works"],
  [(t, y, d.get(y, 0)) for t, _, d, _ in rows for y in YEARS])

# 趋势表（读 en_yearly.csv 算分母）
en_year = {}
with open(os.path.join(OUT, "en_yearly.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        en_year[int(r["year"])] = int(r["works"])
en_early = sum(en_year.get(y, 0) for y in YEARS if y <= 2012)
en_late = sum(en_year.get(y, 0) for y in YEARS if y >= 2021)
trend = []
for term, total, d, m in rows:
    early = sum(d.get(y, 0) for y in YEARS if y <= 2012)
    mid = sum(d.get(y, 0) for y in YEARS if 2013 <= y <= 2020)
    late = sum(d.get(y, 0) for y in YEARS if y >= 2021)
    se, sl = early / en_early, late / en_late
    ratio = round(sl / se, 2) if se > 0 else None
    first = next((y for y in YEARS if d.get(y, 0) >= 3), None)
    trend.append([term, total, early, mid, late, first, round(se*100, 3), round(sl*100, 3), ratio, m])
w("en_anchor_terms_trends.csv",
  ["term","total","w_2000_2012","w_2013_2020","w_2021_2026","first_year_ge3","share_early_pct","share_late_pct","late_vs_early_ratio","method"],
  trend)

with open(os.path.join(OUT, "anchor_terms_table.md"), "w", encoding="utf-8") as f:
    f.write("| 主题词 | 总量 | 2000-2012 | 2013-2020 | 2021-2026 | 近期/早期比 | 方法 |\n|---|---|---|---|---|---|---|\n")
    for r in sorted(trend, key=lambda x: -x[1]):
        f.write(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[8]} | {r[9]} |\n")
print("done", flush=True)
