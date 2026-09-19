# -*- coding: utf-8 -*-
"""英文锚定词 Kleinberg 突现（全量 33 200 集，全文匹配）→ en_bursts_kleinberg.csv"""
import csv
import math
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "outputs", "en_analysis", "full", "en_screened_full.csv")
OUT = os.path.join(ROOT, "outputs", "en_analysis", "full")
YEARS = list(range(2000, 2027))
GAMMA = 1.0
S = 2.0
MIN_DUR = 2
ANCHOR_EN = ["laboratory safety","laboratory accident","safety management","safety culture",
             "safety climate","safety education","biosafety","biosecurity","risk assessment",
             "risk management","hazardous chemicals","chemical safety","laboratory waste",
             "emergency management","occupational health","personal protective equipment",
             "human factors","unsafe behavior","hazard identification","inherent safety",
             "smart laboratory","accident causation","electrical safety","fire safety",
             "laboratory fire","equipment safety","aging equipment","wiring"]


def kleinberg(counts, totals):
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
            return -(n * math.log(1 - p)) if p < 1 else 1e10
        if d == n:
            return -(d * math.log(p)) if p > 0 else 1e10
        ll = (d * math.log(p) + (n - d) * math.log(1 - p)
              + math.lgamma(n + 1) - math.lgamma(d + 1) - math.lgamma(n - d + 1))
        return -ll

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
            c = dp[t][s] + cost(s, d, n)
            if c < dp[t + 1][s]:
                dp[t + 1][s] = c
                parent[t + 1][s] = (t, s)
            if s == 0:
                c2 = dp[t][s] + tau + cost(1, d, n)
                if c2 < dp[t + 1][1]:
                    dp[t + 1][1] = c2
                    parent[t + 1][1] = (t, 0)
            else:
                c3 = dp[t][s] + cost(0, d, n)
                if c3 < dp[t + 1][0]:
                    dp[t + 1][0] = c3
                    parent[t + 1][0] = (t, 1)
    end_state = 0 if dp[T][0] <= dp[T][1] else 1
    t, s = T, end_state
    path = [s]
    while t > 0 and parent[t][s] is not None:
        t, s = parent[t][s]
        path.append(s)
    path.reverse()
    states = path[1:]
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


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    totals = Counter(r["year"] for r in rows if r["year"])
    tot_list = [totals.get(str(y), 0) for y in YEARS]
    texts = [(r["title"] + " " + r["abstract"] + " " + r["keywords"]).lower() for r in rows]
    out = []
    for term in ANCHOR_EN:
        t = term.lower()
        yc = Counter()
        total = 0
        for r, text in zip(rows, texts):
            if t in text:
                total += 1
                if r["year"]:
                    yc[r["year"]] += 1
        if total < 5:
            continue
        cnt_list = [yc.get(str(y), 0) for y in YEARS]
        for (y0, y1, strength) in kleinberg(cnt_list, tot_list):
            out.append([term, total, y0, y1, strength])
    out.sort(key=lambda x: -x[4])
    with open(os.path.join(OUT, "en_bursts_kleinberg.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["term", "works", "burst_start", "burst_end", "strength"])
        w.writerows(out)
    print(f"EN Kleinberg bursts: {len(out)} 段")
    for o in out[:12]:
        print(f"  {o[0]}: {o[2]}-{o[3]}, strength={o[4]}, n={o[1]}")


if __name__ == "__main__":
    main()
