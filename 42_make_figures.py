# -*- coding: utf-8 -*-
"""用真实数据生成图1（中英文年度发文趋势）与图4（政策—发文量—事故三线时间轴），300dpi"""
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

years, cn, en, acc, pol = [], {}, {}, {}, {}
with open(os.path.join(ROOT, "policy_timeline.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        y = int(r["year"])
        years.append(y)
        cn[y] = int(r["cn_works_final6178"]) if r["cn_works_final6178"] else 0
        en[y] = int(r["en_works_openalex_unscreened"]) if r["en_works_openalex_unscreened"] else 0
        acc[y] = float(r["accidents_ye_period_mean"]) if r["accidents_ye_period_mean"] else None
        if r["policy_event"]:
            pol[y] = r["policy_event"]

# 图1
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
ax.plot(years, [cn[y] for y in years], "-o", ms=3, lw=1.5, label="中文发文量（CNKI，n=6 178）")
ax.plot(years, [en[y] for y in years], "--s", ms=3, lw=1.2, label="英文发文量（OpenAlex 预分析口径）")
ax.set_xlabel("年份")
ax.set_ylabel("发文量 / 篇")
ax.set_title("2000—2026 年中英文高校实验室安全研究年度发文量趋势")
ax.legend()
ax.grid(alpha=0.3)
ax.annotate("2026 年截至 9 月", xy=(2026, cn[2026]), xytext=(2021.5, 60),
            arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig1_publication_trend.png"))
plt.close(fig)

# 图4（三线：双 y 轴）
fig, ax1 = plt.subplots(figsize=(9, 5), dpi=300)
ax1.plot(years, [cn[y] for y in years], "-o", ms=3, lw=1.5, color="#1f77b4", label="中文发文量")
ax1.plot(years, [en[y] for y in years], "--s", ms=3, lw=1.2, color="#2ca02c", label="英文发文量（预分析口径）")
ax1.set_xlabel("年份")
ax1.set_ylabel("发文量 / 篇")
ax2 = ax1.twinx()
ax2.plot(years, [acc[y] for y in years], ":^", ms=4, lw=1.2, color="#d62728", label="事故数量（年均值）")
ax2.set_ylabel("事故数量 / 起")
ax2.set_ylim(0, 10)
for y, label in pol.items():
    ax1.axvline(y, color="gray", ls=":", lw=0.8)
    ax1.annotate(label, xy=(y, ax1.get_ylim()[1] * 0.98), xytext=(4, -2),
                 textcoords="offset points", rotation=90, fontsize=7.5, va="top", color="gray")
lines = ax1.get_lines() + ax2.get_lines()
ax1.legend(lines, [l.get_label() for l in lines], loc="upper left")
ax1.set_title("政策—发文量—事故数量三线时间轴（2000—2026）")
ax1.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig4_policy_timeline.png"))
plt.close(fig)
print("figures saved:", os.listdir(FIG))
