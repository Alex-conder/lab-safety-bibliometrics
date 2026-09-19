# -*- coding: utf-8 -*-
"""图2（中文关键词共现网络）与图3（中文突现词时间轴）——基于最终分析集 6178 真实数据"""
import csv
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

ROOT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs")))
ANA = os.path.join(ROOT, "cnki_raw", "cn_analysis")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ---------- 图2：共现网络 ----------
freq = {}
with open(os.path.join(ANA, "cn_kw_top50.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        freq[r["keyword"]] = int(r["works"])
pairs = []
with open(os.path.join(ANA, "cn_copairs_top100.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        pairs.append((r["kw1"], r["kw2"], int(r["co_works"])))

TOP_N = 35          # 节点数
top_nodes = [k for k, _ in sorted(freq.items(), key=lambda x: -x[1])[:TOP_N]]
G = nx.Graph()
for n in top_nodes:
    G.add_node(n, w=freq[n])
for a, b, c in pairs:
    if a in G and b in G:
        G.add_edge(a, b, weight=c)

fig, ax = plt.subplots(figsize=(9.5, 7), dpi=300)
pos = nx.spring_layout(G, k=1.4, iterations=120, seed=42)
sizes = [G.nodes[n]["w"] * 1.6 for n in G.nodes]
widths = [max(0.4, G.edges[e]["weight"] / 45) for e in G.edges]
nx.draw_networkx_edges(G, pos, width=widths, alpha=0.35, edge_color="#888888", ax=ax)
nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color="#2E75B6", alpha=0.85, ax=ax)
nx.draw_networkx_labels(G, pos, font_size=8.5, font_family="Microsoft YaHei", ax=ax)
ax.set_title("中文关键词共现网络（Top 35，最终分析集 n=6 178）")
ax.axis("off")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig2_cn_cooccurrence.png"))
plt.close(fig)

# ---------- 图3：中文突现词时间轴（简化 z-score 法） ----------
bursts = []
with open(os.path.join(ANA, "cn_bursts.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        bursts.append((r["keyword"], int(r["works"]), int(r["burst_start"]), int(r["burst_end"]), float(r["max_z"])))
bursts.sort(key=lambda x: (x[2], -x[4]))
bursts = bursts[:15]

fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
ylabels = []
for i, (kw, n, y0, y1, z) in enumerate(bursts):
    ax.plot([2000, 2026], [i, i], color="#cccccc", lw=6, solid_capstyle="butt", zorder=1)
    ax.plot([y0, max(y1, y0 + 0.4)], [i, i], color="#C00000", lw=6, solid_capstyle="butt", zorder=2)
    ylabels.append(f"{kw}（{n} 篇）")
ax.set_yticks(range(len(bursts)))
ax.set_yticklabels(ylabels, fontsize=9)
ax.invert_yaxis()
ax.set_xlim(1999.5, 2026.5)
ax.set_xlabel("年份")
ax.set_title("中文关键词突现时间轴（简化 z-score 法，正式稿以 CiteSpace Kleinberg 复跑）")
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig3_cn_bursts.png"))
plt.close(fig)
print("fig2, fig3 saved")
