# -*- coding: utf-8 -*-
"""协同演化版新增图：图1框架、图2事故类型、图3危险因素、图6主题热力图、图7中英文突现、图9四象限、图10优先级矩阵"""
import csv
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs")))
FIG = os.path.join(ROOT, "figures")
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ---------- 图1 三流框架 ----------
fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=300)
ax.axis("off")
boxes = {"风险流\n（事故事件集合）": (0.18, 0.62), "制度流\n（政策法规响应）": (0.82, 0.62), "知识流\n（安全研究生产）": (0.5, 0.18)}
for label, (x, y) in boxes.items():
    ax.add_patch(mpatches.FancyBboxPatch((x - 0.14, y - 0.10), 0.28, 0.20,
                 boxstyle="round,pad=0.02", fc="#DEEBF7", ec="#2E75B6", lw=1.5))
    ax.text(x, y, label, ha="center", va="center", fontsize=11)
def arrow(p1, p2, label, off=0.0, curved=0.0):
    ax.annotate("", xy=p2, xytext=p1,
                arrowprops=dict(arrowstyle="->", lw=1.6, color="#C00000",
                                connectionstyle=f"arc3,rad={curved}"))
    mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2 + off
    ax.text(mx, my, label, fontsize=9.5, color="#C00000", ha="center")
arrow((0.32, 0.62), (0.44, 0.30), "H1 事故驱动议程", -0.06, -0.2)
arrow((0.56, 0.30), (0.70, 0.55), "H2 循证决策", -0.04, -0.2)
arrow((0.68, 0.66), (0.32, 0.66), "H3 政策落地重塑风险", 0.05)
ax.annotate("", xy=(0.70, 0.60), xytext=(0.30, 0.52),
            arrowprops=dict(arrowstyle="->", lw=1.3, color="#7F7F7F", ls="--",
                            connectionstyle="arc3,rad=-0.35"))
ax.text(0.5, 0.47, "反馈通道：重大事故直触立法", fontsize=9, color="#7F7F7F", ha="center")
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_title("高校实验室安全治理“风险流—知识流—制度流”协同演化分析框架", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "cf_fig1_framework.png")); plt.close(fig)

# ---------- 图2 事故类型构成与时段 ----------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=300)
types = [("火灾", 87), ("爆炸", 57), ("毒害", 25), ("生物感染", 4), ("腐蚀", 4), ("其他", 6)]
a1.bar([t[0] for t in types], [t[1] for t in types], color="#2E75B6")
for i, (k, v) in enumerate(types):
    a1.text(i, v + 1, f"{v}\n({v/183*100:.1f}%)", ha="center", fontsize=9)
a1.set_title("事故类型构成（n=183）"); a1.set_ylabel("起数")
periods = ["1984—2003", "2004—2015", "2016—2026"]
fire = [24.0, 46.8, 62.5]
a2.plot(periods, fire, "-o", color="#C00000", lw=2, label="火灾占比")
a2.plot(periods, [8.0, None, None], "")  # 占位
for i, v in enumerate(fire):
    a2.text(i, v + 2, f"{v}%", ha="center", fontsize=10, color="#C00000")
a2.set_title("火灾占比分期演变（P=0.0019）"); a2.set_ylabel("占比 / %"); a2.set_ylim(0, 75)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "cf_fig2_accident_types.png")); plt.close(fig)

# ---------- 图3 危险因素 ----------
fig, ax = plt.subplots(figsize=(7.5, 4), dpi=300)
factors = [("危险化学品", 110, 62.5), ("仪器设备", 38, 21.6), ("线路安全", 16, 9.1), ("生物因素", 4, 2.3), ("其他及未知", 8, 4.5)]
ax.barh([f[0] for f in factors][::-1], [f[1] for f in factors][::-1], color="#2E75B6")
for i, (k, v, p) in enumerate(factors[::-1]):
    ax.text(v + 1.5, i, f"{v} 起（{p}%）", va="center", fontsize=9)
ax.set_title("危险因素分布（危险因素/环节/原因结构均为叶文 176 起库口径）")
ax.set_xlabel("起数")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "cf_fig3_factors.png")); plt.close(fig)

# ---------- 图6 主题—时期热力图 ----------
mat = {}
with open(os.path.join(ROOT, "keep", "theme_year_matrix.csv"), encoding="utf-8-sig") as f:
    rdr = csv.reader(f)
    header = next(rdr)
    years = header[1:]
    for row in rdr:
        mat[row[0]] = [int(x) for x in row[1:]]
year_idx = {y: i for i, y in enumerate(years)}
periods_def = [("≤2015", 2000, 2015), ("2016—2018", 2016, 2018), ("2019—2022", 2019, 2022), ("2023—2026", 2023, 2026)]
themes = [t for t in mat if t != "其他"]
data = np.zeros((len(themes), 4))
for ti, t in enumerate(themes):
    for pi, (_, y0, y1) in enumerate(periods_def):
        idx = [year_idx[str(y)] for y in range(y0, y1 + 1) if str(y) in year_idx]
        tot = sum(sum(mat[th][i] for i in idx) for th in themes)
        data[ti, pi] = sum(mat[t][i] for i in idx) / tot * 100 if tot else 0
order = np.argsort(-data[:, 0])
data = data[order]; themes = [themes[i] for i in order]
fig, ax = plt.subplots(figsize=(7.5, 5.5), dpi=300)
im = ax.imshow(data, cmap="Reds", aspect="auto")
ax.set_xticks(range(4)); ax.set_xticklabels([p[0] for p in periods_def])
ax.set_yticks(range(len(themes))); ax.set_yticklabels(themes, fontsize=9)
for ti in range(len(themes)):
    for pi in range(4):
        ax.text(pi, ti, f"{data[ti,pi]:.0f}", ha="center", va="center",
                color="white" if data[ti, pi] > data.max() * 0.55 else "black", fontsize=9)
ax.set_title("中文文献主题占比的时期演化热力图（%，列内归一）")
fig.colorbar(im, label="占比 %")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "cf_fig6_theme_heatmap.png")); plt.close(fig)

# ---------- 图7 中英文突现对照 ----------
def load_bursts(path, kcol, top=8):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append((r[kcol], int(r["burst_start"]), int(r["burst_end"]), float(r["strength"])))
    rows.sort(key=lambda x: -x[3])
    return rows[:top]
cn_b = load_bursts(os.path.join(ROOT, "cnki_raw", "cn_analysis", "cn_bursts_kleinberg.csv"), "keyword")
en_b = load_bursts(os.path.join(ROOT, "en_analysis", "full", "en_bursts_kleinberg.csv"), "term")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6), dpi=300)
for ax, bl, title in [(a1, cn_b, "中文（n=6 178）"), (a2, en_b, "英文（n=33 200）")]:
    for i, (kw, y0, y1, s) in enumerate(bl):
        ax.plot([2000, 2026], [i, i], color="#dddddd", lw=5, solid_capstyle="butt", zorder=1)
        ax.plot([y0, y1 + 0.9], [i, i], color="#C00000", lw=5, solid_capstyle="butt", zorder=2)
    ax.set_yticks(range(len(bl))); ax.set_yticklabels([b[0] for b in bl], fontsize=9)
    ax.invert_yaxis(); ax.set_xlim(1999, 2027); ax.set_title(title, fontsize=11)
    ax.grid(axis="x", alpha=0.3)
fig.suptitle("中英文关键词突现检测对照（Kleinberg，γ=1.0，最短 2 年）", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "cf_fig7_bursts.png")); plt.close(fig)

# ---------- 图9 四象限 + 图10 优先级矩阵 ----------
pts = [("危化品", 62.5, 52.8), ("火灾/消防", 47.5, 42.2), ("违规操作", 22.7, -4.4),
       ("仪器设备", 21.6, 12.0), ("管理缺陷(储存不规范)", 13.1, 3.4), ("设备老化", 11.4, 1.8),
       ("线路/电气", 9.1, 8.2), ("生物因素", 2.3, -3.2)]
tiers = {"危化品": 1, "火灾/消防": 1, "仪器设备": 1, "线路/电气": 1,
         "违规操作": 2, "管理缺陷(储存不规范)": 2, "设备老化": 2, "生物因素": 3}
colors = {1: "#C00000", 2: "#ED7D31", 3: "#2E75B6"}
fig, (a9, a10) = plt.subplots(1, 2, figsize=(11.5, 4.8), dpi=300)
for ax, title, tiered in [(a9, "错位四象限（缺口分级）", False), (a10, "干预优先级矩阵", True)]:
    ax.axhline(0, color="gray", lw=1)
    ax.axhline(5, color="gray", lw=0.6, ls="--"); ax.axhline(-5, color="gray", lw=0.6, ls="--")
    for name, x, y in pts:
        c = colors[tiers[name]] if tiered else ("#C00000" if y > 5 else "#ED7D31" if y > -5 else "#2E75B6")
        ax.scatter(x, y, s=120, color=c, zorder=3)
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(6, 6), fontsize=9)
    ax.set_xlabel("事故侧风险占比 / %"); ax.set_ylabel("研究缺口 / pp")
    ax.set_title(title); ax.grid(alpha=0.3)
    ax.set_xlim(0, 70)
if True:
    handles = [mpatches.Patch(color=colors[1], label="Ⅰ级 优先干预"),
               mpatches.Patch(color=colors[2], label="Ⅱ级 重点关注"),
               mpatches.Patch(color=colors[3], label="Ⅲ级 常规监测")]
    a10.legend(handles=handles, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "cf_fig9_10_quadrant_priority.png")); plt.close(fig)
print("co-evolution figures done:", sorted(os.listdir(FIG)))
