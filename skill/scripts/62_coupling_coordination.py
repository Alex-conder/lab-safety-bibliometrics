# -*- coding: utf-8 -*-
"""耦合协调度：风险流与研究流（分议题截面 + 分期版本）
C = 2*sqrt(u_r*u_k)/(u_r+u_k)；T = α*u_r+β*u_k（α=β=0.5）；D = sqrt(C*T)
等级：D≥0.8 高度协调；0.6—0.8 中度；0.4—0.6 勉强；0.2—0.4 轻度失调；<0.2 严重失调
"""
import csv
import math
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）

ROOT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs")))
OUT = os.path.join(ROOT, "coupling")
GAP = os.path.join(OUT, "risk_research_gap.csv")

def level(d):
    if d >= 0.8: return "高度协调"
    if d >= 0.6: return "中度协调"
    if d >= 0.4: return "勉强协调"
    if d >= 0.2: return "轻度失调"
    return "严重失调"

def main():
    rows = [r for r in csv.DictReader(open(GAP, encoding="utf-8-sig")) if r["判定"] != "不单列"]
    items = []
    for r in rows:
        risk = float(r["风险占比%"]) / 100
        res = float(r["研究占比%"]) / 100
        items.append((r["事故风险项"], risk, res))
    # 归一化到 [0,1]
    rmax = max(x[1] for x in items)
    kmax = max(x[2] for x in items)
    out = []
    for name, ur, uk in items:
        ur_n, uk_n = ur / rmax, uk / kmax
        C = 2 * math.sqrt(ur_n * uk_n) / (ur_n + uk_n) if (ur_n + uk_n) > 0 else 0
        T = 0.5 * ur_n + 0.5 * uk_n
        D = math.sqrt(C * T)
        out.append([name, round(ur * 100, 2), round(uk * 100, 2), round(C, 3), round(T, 3), round(D, 3), level(D)])
    out.sort(key=lambda x: x[5])
    with open(os.path.join(OUT, "coupling_coordination.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["议题", "风险占比%", "研究占比%", "耦合度C", "协调指数T", "耦合协调度D", "等级"])
        w.writerows(out)
    print("分议题耦合协调度（升序 = 失调最重在前）：")
    for r in out:
        print(f"  {r[0]}: C={r[3]}, T={r[4]}, D={r[5]}（{r[6]}）")

if __name__ == "__main__":
    main()
