# -*- coding: utf-8 -*-
"""
文献计量数据调取（OpenAlex 版，无需账号）v2
用途：为论文《高校实验室安全研究热点与事故特征演变》文献计量部分提供真实预演数据。
说明：OpenAlex 覆盖 WoS/Scopus 绝大部分文献，但非 WoS 本体；论文方法部分须如实写
     "英文数据经 OpenAlex 获取"或将其作为 WoS 正式检索前的预演数据。
输出：outputs/bibliometric_openalex/ 下 CSV 若干 + summary_notes.md
v2 修正：年度键 str->int；关键词分"全量 Top200（含学科泛词）"与"锚定主题词逐年序列"两套。
"""
import csv
import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://api.openalex.org/works"
MAILTO = "lab-safety-biblio@example.org"
OUT = os.path.join(os.path.dirname(__file__), "..", "outputs", "bibliometric_openalex")
os.makedirs(OUT, exist_ok=True)

EN_SEARCH = '((university OR college OR "higher education") AND laboratory AND (safety OR accident OR incident OR risk OR hazard OR management))'
ZH_SEARCH = "((高校 OR 大学 OR 高等学校) AND 实验室 AND (安全 OR 事故 OR 风险 OR 管理))"

# 论文 25 对锚定词表的英文主题词（剔除检索式本身的限定词）
ANCHOR_TERMS = [
    "laboratory safety", "laboratory accident", "safety management", "safety culture",
    "safety climate", "safety education", "biosafety", "biosecurity", "risk assessment",
    "risk management", "hazardous chemicals", "chemical safety", "laboratory waste",
    "emergency management", "occupational health", "personal protective equipment",
    "human factors", "unsafe behavior", "hazard identification", "inherent safety",
    "smart laboratory", "accident causation",
]

YEARS = list(range(2000, 2027))


def resolve_keyword_id(term):
    """经 keywords 端点把主题词解析为 OpenAlex keyword id（keywords.search 过滤器不可用）"""
    url = "https://api.openalex.org/keywords?" + urllib.parse.urlencode(
        {"search": term, "per_page": 5, "mailto": MAILTO})
    req = urllib.request.Request(url, headers={"User-Agent": "lab-safety-biblio/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    results = d.get("results", [])
    if not results:
        return None
    for r in results:
        if r["display_name"].lower() == term.lower():
            return r["id"]
    return results[0]["id"]


def api(params, retries=4):
    params = dict(params)
    params["mailto"] = MAILTO
    url = BASE + "?" + urllib.parse.urlencode(params)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lab-safety-biblio/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            wait = 2 ** i * 3
            print(f"  retry {i+1}: {e}; sleep {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError("API failed: " + url[:200])


def base_filter(search, lang):
    return (f"title_and_abstract.search:{search},"
            f"publication_year:2000-2026,type:article|review,language:{lang}")


def yearly(search, lang, extra=None):
    f = base_filter(search, lang) + (("," + extra) if extra else "")
    data = api({"filter": f, "group_by": "publication_year"})
    rows = [(int(g["key"]), g["count"]) for g in data["group_by"]]
    return data["meta"]["count"], sorted(rows)


def write_csv(name, header, rows):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print("wrote", path, len(rows), "rows", flush=True)


print("=== 1. 总量与年度趋势 ===", flush=True)
en_total, en_year = yearly(EN_SEARCH, "en")
zh_total, zh_year = yearly(ZH_SEARCH, "zh")
print("EN total:", en_total, "| ZH total:", zh_total, flush=True)
write_csv("en_yearly.csv", ["year", "works"], en_year)
write_csv("zh_yearly.csv", ["year", "works"], zh_year)

print("=== 2. 全库关键词 Top200（原始，含学科泛词） ===", flush=True)
data = api({"filter": base_filter(EN_SEARCH, "en"), "group_by": "keywords.id", "per_page": 200})
raw_kw = [(g["key_display_name"], g["count"]) for g in data["group_by"]]
write_csv("en_keywords_raw_top200.csv", ["keyword", "works"], raw_kw)

print("=== 3. 锚定主题词逐年序列（突现/趋势分析用） ===", flush=True)
anchor_rows = []     # term, total, year-by-year dict
for term in ANCHOR_TERMS:
    try:
        kid = resolve_keyword_id(term)
        if kid is None:
            total, yr = 0, []
        else:
            total, yr = yearly(EN_SEARCH, "en", extra=f"keywords.id:{kid}")
    except Exception as e:
        print(f"  {term}: ERROR {e}", flush=True)
        total, yr = 0, []
    anchor_rows.append((term, total, dict(yr)))
    print(f"  {term}: {total}", flush=True)
    time.sleep(0.25)

write_csv("en_anchor_terms_summary.csv", ["term", "works_2000_2026"],
          [(t, c) for t, c, _ in sorted(anchor_rows, key=lambda x: -x[1])])

rows = []
for term, total, d in anchor_rows:
    for y in YEARS:
        rows.append([term, y, d.get(y, 0)])
write_csv("en_anchor_terms_yearly.csv", ["term", "year", "works"], rows)

# 趋势指标：早期(2000-2012)/中期(2013-2020)/近期(2021-2026) 三段的年均量与近期占比
trend = []
en_year_d = dict(en_year)
en_early = sum(en_year_d.get(y, 0) for y in YEARS if y <= 2012)
en_late = sum(en_year_d.get(y, 0) for y in YEARS if y >= 2021)
for term, total, d in anchor_rows:
    early = sum(d.get(y, 0) for y in YEARS if y <= 2012)
    mid = sum(d.get(y, 0) for y in YEARS if 2013 <= y <= 2020)
    late = sum(d.get(y, 0) for y in YEARS if y >= 2021)
    share_late = late / en_late if en_late else 0
    share_early = early / en_early if en_early else 0
    ratio = round(share_late / share_early, 2) if share_early > 0 else None
    first = next((y for y in YEARS if d.get(y, 0) >= 3), None)
    trend.append([term, total, early, mid, late, first,
                  round(share_early * 100, 3), round(share_late * 100, 3), ratio])
write_csv("en_anchor_terms_trends.csv",
          ["term", "total", "w_2000_2012", "w_2013_2020", "w_2021_2026", "first_year_ge3",
           "share_early_pct", "share_late_pct", "late_vs_early_ratio"], trend)

# 中文侧 Top200（参考）
data = api({"filter": base_filter(ZH_SEARCH, "zh"), "group_by": "keywords.id", "per_page": 200})
zh_kw = [(g["key_display_name"], g["count"]) for g in data["group_by"]]
write_csv("zh_keywords_raw_top200.csv", ["keyword", "works"], zh_kw)

with open(os.path.join(OUT, "summary_notes.md"), "w", encoding="utf-8") as f:
    f.write("# OpenAlex 文献计量结果摘要（自动生成）\n\n")
    f.write("数据源：OpenAlex API；检索式模拟论文 WoS/中文检索式；类型 article+review；2000—2026。\n\n")
    f.write("**重要提醒**：OpenAlex 非 WoS/CNKI 本体，且本检索式会命中临床医学实验室文献（医院检验科噪声），")
    f.write("正式 PRISMA 筛选会剔除。本结果用于：① 预判趋势形态；② 锚定词热度排序；③ 验证论文假设方向。")
    f.write("论文方法部分须写明实际数据源，或将本结果作为正式检索前的预演。\n\n")
    f.write(f"## 总量\n- 英文（模拟 WoS 式）：{en_total} 篇\n- 中文（模拟中文式，OpenAlex 覆盖不全）：{zh_total} 篇\n\n")
    f.write("## 锚定主题词热度与趋势（按总量排序）\n")
    f.write("| 主题词 | 总量 | 2000-2012 | 2013-2020 | 2021-2026 | 近期/早期占比比 |\n|---|---|---|---|---|---|\n")
    for r in sorted(trend, key=lambda x: -x[1]):
        f.write(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[8]} |\n")
print("done", flush=True)
