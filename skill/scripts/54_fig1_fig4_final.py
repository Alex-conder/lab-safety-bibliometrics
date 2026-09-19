# -*- coding: utf-8 -*-
"""图1/图4 最终版：CN 实线 + 英文双源筛选集 + 英文未筛选总量灰线 + 事故年均值 + 政策节点"""
import csv
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs")))
FIG = os.path.join(ROOT, "figures")
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

years, cn, en, en_raw, acc, pol = [], {}, {}, {}, {}, {}
with open(os.path.join(ROOT, "policy_timeline.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        y = int(r["year"])
        years.append(y)
        cn[y] = int(r["cn_works_final6178"] or 0)
        en[y] = int(r["en_works_dual_source_screened"] or 0)
        acc[y] = float(r["accidents_ye_period_mean"]) if r["accidents_ye_period_mean"] else None
        if r["policy_event"]:
            pol[y] = r["policy_event"]
with open(os.path.join(ROOT, "bibliometric_openalex", "en_yearly.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        en_raw[int(r["year"])] = int(r["works"])

# 图1：CN + 英文双源
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
ax.plot(years, [cn[y] for y in years], "-o", ms=3, lw=1.5, label="中文发文量（CNKI，n=6 178）")
ax.plot(years, [en[y] for y in years], "--s", ms=3, lw=1.2, label="英文发文量（OpenAlex+S2 双源，n=33 200）")
ax.plot(years, [en_raw.get(y) for y in years], ":", lw=1.2, color="#999999", label="英文未筛选总量（含临床噪声）")
ax.set_xlabel("年份"); ax.set_ylabel("发文量 / 篇")
ax.set_title("2000—2026 年中英文高校实验室安全研究年度发文量趋势")
ax.legend(); ax.grid(alpha=0.3); ax.set_ylim(0, 3600)
ax.annotate("2026 年截至 9 月", xy=(2026, cn[2026]), xytext=(2021.5, 60),
            arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1_publication_trend.png")); plt.close(fig)

# 图4：四线（CN、英文筛选集、英文未筛选、事故）+ 政策节点
fig, ax1 = plt.subplots(figsize=(9, 5), dpi=300)
l1, = ax1.plot(years, [cn[y] for y in years], "-o", ms=3, lw=1.5, color="#1f77b4", label="中文发文量")
l2, = ax1.plot(years, [en[y] for y in years], "--s", ms=3, lw=1.2, color="#2ca02c", label="英文发文量（双源筛选集）")
l4, = ax1.plot(years, [en_raw.get(y) for y in years], ":", lw=1.2, color="#999999", label="英文未筛选总量（含临床噪声）")
ax1.set_xlabel("年份"); ax1.set_ylabel("发文量 / 篇"); ax1.set_ylim(0, 3600)
ax2 = ax1.twinx()
l3, = ax2.plot(years, [acc[y] for y in years], ":^", ms=4, lw=1.2, color="#d62728", label="事故数量（年均值）")
ax2.set_ylabel("事故数量 / 起"); ax2.set_ylim(0, 10)
short = {2004: "病原微生物条例", 2015: "天津港8·12后整治", 2019: "教育部36号文",
         2021: "生物安全法", 2023: "高校实验室安全规范", 2026: "北京市若干措施"}
for i, (y, label) in enumerate(sorted(pol.items())):
    ax1.axvline(y, color="gray", ls=":", lw=0.8)
    ax1.annotate(short[y], xy=(y, 3450 if i % 2 == 0 else 3050), xytext=(3, 0),
                 textcoords="offset points", rotation=90, fontsize=7.5, va="top", color="dimgray")
ax1.legend(handles=[l1, l2, l4, l3], loc="center left")
ax1.set_title("政策—发文量—事故数量时间轴（2000—2026）")
ax1.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig4_policy_timeline.png")); plt.close(fig)
print("fig1/fig4 final saved")
