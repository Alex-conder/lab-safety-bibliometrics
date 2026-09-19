# -*- coding: utf-8 -*-
"""
合并去重：outputs/cnki_raw/seg_*.txt + relevance_top6000/pages_*.txt（Refworks 格式）
去重键：题名(规范化) + 第一作者 + 年份
输出：outputs/cnki_raw/merged_records.csv（含字段：题名/作者/机构/期刊/年/期/页/关键词/摘要/来源文件）
     outputs/cnki_raw/merge_report.md
"""
import csv
import glob
import os
# BIBLIO_ROOT: 输出根目录环境变量（默认脚本上两级 outputs/）
import re
from collections import Counter

OUT = os.path.abspath(os.path.join(os.environ.get("BIBLIO_ROOT", os.path.dirname(__file__) + "/../../outputs"), "cnki_raw"))


def parse_refworks(path):
    recs = []
    cur = {}
    tag = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            m = re.match(r"^([A-Z][A-Z0-9]) (.*)$", line)
            if m:
                tag, val = m.group(1), m.group(2)
                if tag == "RT":
                    if cur:
                        recs.append(cur)
                    cur = {"_file": os.path.basename(path)}
                if tag in ("A1",):
                    cur.setdefault(tag, []).append(val)
                elif tag in ("AB",):
                    cur[tag] = cur.get(tag, "") + val
                else:
                    cur[tag] = val
            elif tag == "AB" and cur is not None:
                cur["AB"] = cur.get("AB", "") + line.strip()
    if cur:
        recs.append(cur)
    return recs


def norm_title(t):
    return re.sub(r"\W+", "", (t or "").lower())


def main():
    files = sorted(glob.glob(os.path.join(OUT, "seg_*.txt"))) + \
            sorted(glob.glob(os.path.join(OUT, "relevance_top6000", "pages_*.txt")))
    all_recs = []
    per_file = {}
    for fp in files:
        rs = parse_refworks(fp)
        per_file[os.path.basename(fp)] = len(rs)
        all_recs.extend(rs)
    seen = {}
    dups = 0
    for r in all_recs:
        a1 = r.get("A1", [""])[0].split(";")[0] if r.get("A1") else ""
        key = (norm_title(r.get("T1")), a1, r.get("YR", ""))
        if key in seen:
            dups += 1
            continue
        seen[key] = r
    rows = []
    for r in seen.values():
        rows.append({
            "title": r.get("T1", ""),
            "authors": ";".join(r.get("A1", [])),
            "affiliations": r.get("AD", ""),
            "journal": r.get("JF", ""),
            "year": r.get("YR", ""),
            "issue": r.get("IS", ""),
            "pages": r.get("OP", ""),
            "keywords": r.get("K1", ""),
            "abstract": r.get("AB", ""),
            "source_file": r.get("_file", ""),
        })
    rows.sort(key=lambda x: (x["year"], x["title"]))
    csv_path = os.path.join(OUT, "merged_records.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    year_cnt = Counter(r["year"] for r in rows)
    rep = os.path.join(OUT, "merge_report.md")
    with open(rep, "w", encoding="utf-8") as f:
        f.write("# CNKI 合并去重报告\n\n")
        f.write(f"- 文件数：{len(files)}（分段 {len(glob.glob(os.path.join(OUT, 'seg_*.txt')))} + 归档 {len(glob.glob(os.path.join(OUT, 'relevance_top6000', 'pages_*.txt')))}）\n")
        f.write(f"- 原始记录：{len(all_recs)}\n- 重复剔除：{dups}\n- **去重后：{len(rows)}**\n\n")
        f.write("## 各文件记录数\n")
        for k, v in per_file.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n## 去重后年度分布\n\n| 年 | 篇数 |\n|---|---|\n")
        for y in sorted(year_cnt):
            f.write(f"| {y} | {year_cnt[y]} |\n")
    print(f"merged: {len(all_recs)} raw -> {len(rows)} unique; report: {rep}")


if __name__ == "__main__":
    main()
