# -*- coding: utf-8 -*-
"""
暴露量分母分析：万室事故率
锚点（真实公开数据）：
  2007 年 24 731 个（普通本科高校，教育部实验室信息统计，浙大培训讲稿/新华网引）
  2018 年 36 953 个（同口径，新华网 2021-12 报道/《实验科学与技术》论文引）
  2021 年 66 600 个（口径扩大：含本科层次职业学校，叶元兴等 2025/郭战胜等 2026 引）
方法：锚点间几何插值；2000—2006 按 2007—2018 CAGR 外推；2022—2026 两种口径情景
  （窄口径=2018 口径外推；宽口径=2021 后持平 66 600）
事故数（大陆，台湾 1 起单列）：P1 1984—2003 年均 1.32（叶文，仅背景）；
  P2 2004—2015：109 起/12 年；P3 2016—2026：48 起/11 年（含本研究增量）
检验：Poisson 率比的精确二项检验（scipy.stats.binomtest）
"""
import csv
import math
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
from scipy import stats

ROOT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs")))
OUT = os.path.join(ROOT, "exposure")
os.makedirs(OUT, exist_ok=True)

# ---- 实验室数量序列（两种口径情景） ----
CAGR = (36953 / 24731) ** (1 / 11) - 1  # 2007→2018，约 3.73%
def labs_narrow(y):
    if y < 2007:
        return 24731 / (1 + CAGR) ** (2007 - y)
    if y <= 2018:
        return 24731 * (1 + CAGR) ** (y - 2007)
    return 36953 * (1 + CAGR) ** (y - 2018)  # 2018 口径外推
def labs_wide(y):
    if y < 2021:
        return labs_narrow(y)
    return 66600  # 2021 口径扩大后持平（保守）

years = list(range(2000, 2027))
narrow = {y: round(labs_narrow(y)) for y in years}
wide = {y: round(labs_wide(y)) for y in years}

# ---- 分期事故数与暴露量 ----
PERIODS = [("2004—2015", 2004, 2015, 109), ("2016—2026", 2016, 2026, 48)]  # 起数，大陆
rows = []
rates = {}
for label, y0, y1, acc in PERIODS:
    yrs = y1 - y0 + 1
    for tag, series in [("窄口径", narrow), ("宽口径", wide)]:
        mean_labs = sum(series[y] for y in range(y0, y1 + 1)) / yrs
        exposure = mean_labs * yrs  # 室·年
        rate = acc / exposure * 10000  # 起/万室·年
        rates[(label, tag)] = (acc, yrs, mean_labs, rate)
        rows.append([label, tag, acc, yrs, round(mean_labs), round(exposure), round(rate, 3)])

# ---- Poisson 率比精确检验（窄口径主口径，宽口径敏感性） ----
def rate_test(acc2, e2, acc3, e3):
    """H0: 两期率相等；条件二项检验"""
    total = acc2 + acc3
    p0 = e2 / (e2 + e3)
    pval = stats.binomtest(acc2, total, p0).pvalue
    rr = (acc3 / e3) / (acc2 / e2)
    # 率比 95% CI（对数法）
    se = math.sqrt(1 / acc2 + 1 / acc3)
    lo, hi = math.exp(math.log(rr) - 1.96 * se), math.exp(math.log(rr) + 1.96 * se)
    return rr, lo, hi, pval

res = {}
for tag in ["窄口径", "宽口径"]:
    a2, y2, ml2, r2 = rates[("2004—2015", tag)]
    a3, y3, ml3, r3 = rates[("2016—2026", tag)]
    e2, e3 = ml2 * y2, ml3 * y3
    rr, lo, hi, pval = rate_test(a2, e2, a3, e3)
    res[tag] = (r2, r3, rr, lo, hi, pval)
    print(f"{tag}: P2 率 {r2:.2f} → P3 率 {r3:.2f} 起/万室·年；率比 {rr:.2f}（95%CI {lo:.2f}—{hi:.2f}），P={pval:.4f}")

with open(os.path.join(OUT, "exposure_rate.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["时期", "口径情景", "事故起数", "年数", "实验室均值（个）", "暴露量（室·年）", "事故率（起/万室·年）"])
    w.writerows(rows)
with open(os.path.join(OUT, "lab_series.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["year", "labs_narrow", "labs_wide", "anchor"])
    for y in years:
        anchor = {2007: "官方 24731", 2018: "官方 36953", 2021: "官方 66600（口径扩大）"}.get(y, "")
        w.writerow([y, narrow[y], wide[y], anchor])
with open(os.path.join(OUT, "exposure_notes.md"), "w", encoding="utf-8") as f:
    f.write("# 暴露量分母分析说明\n\n")
    f.write("- 锚点：2007 年 24 731、2018 年 36 953（普通本科高校口径）；2021 年 66 600（含本科层次职业学校，口径扩大）。\n")
    f.write(f"- 2007—2018 年 CAGR = {CAGR*100:.2f}%；锚点间几何插值，2000—2006 外推、2022—2026 两种情景。\n")
    f.write("- 事故数：大陆口径（台湾 1 起单列）；P2=2004—2015 年 109 起，P3=2016—2026 年 48 起（含本研究增量）。\n")
    f.write("- 检验：Poisson 率比的条件二项检验；率比 CI 用对数法。\n\n")
    for tag in ["窄口径", "宽口径"]:
        r2, r3, rr, lo, hi, pval = res[tag]
        f.write(f"**{tag}**：P2 {r2:.2f} → P3 {r3:.2f} 起/万室·年（下降 {(1-rr)*100:.0f}%）；率比 {rr:.2f}（95%CI {lo:.2f}—{hi:.2f}），P={pval:.2e}\n")
print("done")
