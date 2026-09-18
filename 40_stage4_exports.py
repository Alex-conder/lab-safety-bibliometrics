# -*- coding: utf-8 -*-
"""
阶段4：CiteSpace 可读格式导出 + 政策—发文量—事故三线时间轴数据
输出：outputs/citespace/cn_refworks.txt、en_openalex_note.md、outputs/policy_timeline.csv
"""
import csv
import os
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
CNKI = os.path.join(ROOT, "cnki_raw")
OUT = os.path.join(ROOT, "citespace")
os.makedirs(OUT, exist_ok=True)

POLICIES = {
    2004: "《病原微生物实验室生物安全管理条例》",
    2015: "天津港8·12后全国危化品安全整治",
    2019: "教育部《关于加强高校实验室安全工作的意见》",
    2021: "《中华人民共和国生物安全法》",
    2023: "教育部《高等学校实验室安全规范》",
    2026: "北京市《关于进一步强化北京地区高校实验室安全管理主体责任的若干措施》",
}
# 叶文三期年均 + 本研究增量（2025—2026）
ACCIDENTS = {**{y: 1.32 for y in range(2000, 2004)},
             **{y: 8.38 for y in range(2004, 2016)},
             **{y: 4.67 for y in range(2016, 2025)},
             2025: 3, 2026: 4}


def main():
    # 1) CN Refworks 导出
    rows = list(csv.DictReader(open(os.path.join(CNKI, "final_analysis_set.csv"), encoding="utf-8-sig")))
    with open(os.path.join(OUT, "cn_refworks.txt"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write("RT Journal Article\n")
            f.write(f"A1 {r['authors']}\n")
            if r["affiliations"]:
                f.write(f"AD {r['affiliations']}\n")
            f.write(f"T1 {r['title']}\nJF {r['journal']}\nYR {r['year']}\n")
            if r["issue"]:
                f.write(f"IS {r['issue']}\n")
            if r["pages"]:
                f.write(f"OP {r['pages']}\n")
            if r["keywords"]:
                f.write(f"K1 {r['keywords']}\n")
            if r["abstract"]:
                f.write(f"AB {r['abstract']}\n")
            f.write("\n")
    # 2) EN 说明（OpenAlex 无全记录导出，正式 WoS 待机构检索）
    with open(os.path.join(OUT, "en_openalex_note.md"), "w", encoding="utf-8") as f:
        f.write("# 英文侧 CiteSpace 数据说明\n\n英文全记录需 WoS 机构订阅导出（Full Record and Cited References 纯文本）。\n当前英文侧计量基于 OpenAlex API 聚合数据（outputs/bibliometric_openalex/），不含逐条题录，无法直接生成 CiteSpace 输入文件。\n待 WoS 导出后放入本目录命名 en_wos.txt 即可。\n")
    # 3) 政策三线时间轴
    cn_year = Counter(r["year"] for r in rows if r["year"])
    en_year = {}
    with open(os.path.join(ROOT, "bibliometric_openalex", "en_yearly.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            en_year[int(r["year"])] = int(r["works"])
    with open(os.path.join(ROOT, "policy_timeline.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["year", "cn_works_final6178", "en_works_openalex_unscreened", "accidents_ye_period_mean", "policy_event"])
        for y in range(2000, 2027):
            w.writerow([y, cn_year.get(str(y), 0), en_year.get(y, ""), ACCIDENTS.get(y, ""), POLICIES.get(y, "")])
    print("citespace exports + policy_timeline done; cn records:", len(rows))


if __name__ == "__main__":
    main()
