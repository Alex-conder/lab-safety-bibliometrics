# -*- coding: utf-8 -*-
"""中断时间序列（ITS）：2019 年教育部《意见》对中文发文量的水平/斜率效应
模型（Poisson GLM，稳健标准误）：
  works ~ time + post2019 + time×post2019
敏感性：节点改为 2015（天津港整治）与 2023（规范）。
数据：policy_timeline.csv 中文年度发文量（最终集 5888；2026 为非完整年，剔除）
"""
import csv
import os
import numpy as np
import statsmodels.api as sm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
OUT = os.path.join(ROOT, "its")
os.makedirs(OUT, exist_ok=True)

def load_cn():
    y, w = [], []
    with open(os.path.join(ROOT, "policy_timeline.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            yr = int(r["year"])
            if yr <= 2025:  # 2026 非完整年剔除
                y.append(yr)
                w.append(int(r["cn_works_final6178"]))
    return np.array(y), np.array(w, dtype=float)

def fit(years, works, node):
    t = years - 1999.0
    post = (years >= node).astype(float)
    X = np.column_stack([t, post, t * post, np.ones_like(t)])
    m = sm.GLM(works, X, family=sm.families.Poisson()).fit(cov_type="HC1")
    names = ["time", f"post{node}(水平)", f"time×post{node}(斜率)", "const"]
    res = []
    for nm, b, se, p in zip(names, m.params, m.bse, m.pvalues):
        res.append((nm, round(b, 4), round(b / se, 2), round(p, 4), round(np.exp(b), 3)))
    return res

def main():
    years, works = load_cn()
    lines = ["# 中断时间序列（ITS）结果：中文发文量对政策节点的响应",
             "",
             "模型：Poisson GLM（HC1 稳健标准误），works ~ time + post + time×post；2026 非完整年剔除。", ""]
    for node in [2019, 2015, 2023]:
        lines.append(f"## 节点 {node} 年")
        lines.append("| 项 | 系数 | z | P | exp(系数) |")
        lines.append("|---|---|---|---|---|")
        for nm, b, z, p, e in fit(years, works, node):
            lines.append(f"| {nm} | {b} | {z} | {p} | {e} |")
        lines.append("")
    with open(os.path.join(OUT, "its_results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    for node in [2019, 2015, 2023]:
        print(f"--- 节点 {node} ---")
        for nm, b, z, p, e in fit(years, works, node):
            print(f"  {nm}: β={b}, z={z}, P={p}, exp={e}")

if __name__ == "__main__":
    main()
