# -*- coding: utf-8 -*-
"""
Kleinberg 突现检测（两状态自动机，γ=1.0，最短持续 2 年）
数据：最终分析集 6178 条的关键词逐年计数（同义词归并沿用 35 号脚本规则）
输出：outputs/cnki_raw/cn_analysis/cn_bursts_kleinberg.csv + 更新图3
参考：Kleinberg J. Bursty and hierarchical structure in streams. KDD 2002.
"""
import csv
import math
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
CNKI = os.path.join(ROOT, "cnki_raw")
ANA = os.path.join(CNKI, "cn_analysis")

MERGE = {
    "危化品": "危险化学品", "高校实验室安全": "实验室安全", "大学实验室": "高校实验室",
    "高等学校实验室": "高校实验室", "安全教育培训": "安全教育", "安全教育培训体系": "安全教育",
    "高校": "高校实验室",
}
STOP = {"对策", "问题", "管理", "建设", "改革", "创新", "实践", "思考", "研究", "探索", "安全", "高校", "应用", "分析", "探讨"}
YEARS = list(range(2000, 2027))
GAMMA = 1.0
S = 2.0          # 突现态速率倍数
MIN_DUR = 2


def kleinberg(counts, totals):
    """counts/totals: 逐年列表。返回 [(start_idx, end_idx, strength)]（state=1 的区间）"""
    T = len(counts)
    N = sum(counts)
    if N < 5:
        return []
    p0 = max(N / sum(totals), 1e-10)
    p1 = min(p0 * S, 0.99)

    def cost(state, d, n):
        p = p1 if state == 1 else p0
        if n == 0:
            return 0.0
        if d == 0:
            ll = (n) * math.log(1 - p) if p < 1 else -1e10
        elif d == n:
            ll = d * math.log(p) if p > 0 else -1e10
        else:
            ll = (d * math.log(p) + (n - d) * math.log(1 - p)
                  + math.lgamma(n + 1) - math.lgamma(d + 1) - math.lgamma(n - d + 1))
        return -ll

    # DP：dp[t][s]，转移代价 tau = gamma * ln(n_t)（0→1 上升才有代价）
    INF = float("inf")
    dp = [[INF, INF] for _ in range(T + 1)]
    dp[0][0] = 0.0
    parent = [[None, None] for _ in range(T + 1)]
    for t in range(T):
        d, n = counts[t], totals[t]
        tau = GAMMA * math.log(max(n, 1))
        for s in (0, 1):
            if dp[t][s] == INF:
                continue
            # 保持
            c = dp[t][s] + cost(s, d, n)
            if c < dp[t + 1][s]:
                dp[t + 1][s] = c
                parent[t + 1][s] = (t, s)
            # 上升
            if s == 0:
                c2 = dp[t][s] + tau + cost(1, d, n)
                if c2 < dp[t + 1][1]:
                    dp[t + 1][1] = c2
                    parent[t + 1][1] = (t, 0)
            # 下降无代价
            if s == 1:
                c3 = dp[t][s] + cost(0, d, n)
                if c3 < dp[t + 1][0]:
                    dp[t + 1][0] = c3
                    parent[t + 1][0] = (t, 1)
    # 回溯
    end_state = 0 if dp[T][0] <= dp[T][1] else 1
    states = [0] * T
    t, s = T, end_state
    while t > 0 and parent[t][s] is not None:
        pt, ps = parent[t][s]
        states[pt] = s if ps != s else s  # 当前年 t-1 的状态 = s（回溯前状态为 ps）
        states[pt] = s
        t, s = pt, ps
    # 修正：states[i] 应记录第 i 年所处状态
    # 重新回溯（标准做法）
    t, s = T, end_state
    path = [s]
    while t > 0 and parent[t][s] is not None:
        t, s = parent[t][s]
        path.append(s)
    path.reverse()  # path[i] = 第 i-1 年状态
    states = path[1:]  # path[0] 是初始状态
    bursts = []
    i = 0
    while i < T:
        if states[i] == 1:
            j = i
            strength = 0.0
            while j < T and states[j] == 1:
                strength += cost(0, counts[j], totals[j]) - cost(1, counts[j], totals[j])
                j += 1
            if j - i >= MIN_DUR and strength > 0:
                bursts.append((YEARS[i], YEARS[j - 1], round(strength, 2)))
            i = j
        else:
            i += 1
    return bursts


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


def main():
    rows = list(csv.DictReader(open(os.path.join(CNKI, "final_analysis_set.csv"), encoding="utf-8-sig")))
    totals = Counter(r["year"] for r in rows if r["year"])
    kw_year = defaultdict(Counter)
    kw_total = Counter()
    for r in rows:
        if not r["year"]:
            continue
        for t in set(kws_of(r)):
            kw_year[t][r["year"]] += 1
            kw_total[t] += 1
    tot_list = [totals.get(str(y), 0) for y in YEARS]
    out = []
    for kw, c in kw_total.items():
        if c < 30:
            continue
        cnt_list = [kw_year[kw].get(str(y), 0) for y in YEARS]
        for (y0, y1, strength) in kleinberg(cnt_list, tot_list):
            out.append([kw, c, y0, y1, strength])
    out.sort(key=lambda x: -x[4])
    with open(os.path.join(ANA, "cn_bursts_kleinberg.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "works", "burst_start", "burst_end", "strength"])
        w.writerows(out)
    print(f"Kleinberg bursts: {len(out)} 段（词数 {len(set(o[0] for o in out))}）")
    for o in out[:15]:
        print(f"  {o[0]}: {o[2]}-{o[3]}, strength={o[4]}, n={o[1]}")


if __name__ == "__main__":
    main()
