# -*- coding: utf-8 -*-
"""
应用课题组口径裁定，生成最终分析集：
- 高职高专（E5）→ keep（2026-09-17 裁定：高职高专纳入）
- 校企合作校内在管（E6+）→ keep（裁定：实验室在校内、安全归高校管理即纳入）；
  企业为主体的实验室 → exclude
- 纯企业（E6）、新闻体（E1）、中小学（E2）、医院检验科（E3）→ exclude
- 附属医院（E4）、非附属医院（E7）→ 暂不确定，留待课题组裁定
输出：outputs/review/review_pack_ruled.csv；outputs/cnki_raw/final_analysis_set.csv；终报
"""
import csv
import os
from collections import Counter

REV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "review"))
CNKI = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "cnki_raw"))

ENTERPRISE_LED = ["企业实验室", "公司实验室", "企业研发", "公司研发", "厂实验室", "企业技术中心的实验室"]


def main():
    rows = list(csv.DictReader(open(os.path.join(REV, "review_pack.csv"), encoding="utf-8-sig")))
    ruled = Counter()
    for r in rows:
        rid, text = r["触发规则"], (r["标题"] + " " + r["摘要"] + " " + r["关键词"])
        if rid == "E5":
            r["仲裁结果"] = "keep"
            r["不确定点"] = "已裁定：高职高专纳入（2026-09-17）"
        elif rid == "E6+":
            if any(k in text for k in ENTERPRISE_LED):
                r["仲裁结果"] = "exclude"
                r["不确定点"] = "企业主体实验室（不符合'校内在管'口径）"
            else:
                r["仲裁结果"] = "keep"
                r["不确定点"] = "已裁定：校企合作、校内在管纳入（2026-09-17）"
        elif rid in ("E1", "E2", "E3", "E6"):
            r["仲裁结果"] = "exclude"
        else:  # E4/E7 待定
            r["仲裁结果"] = ""
        ruled[(rid, r["仲裁结果"] or "pending")] += 1
    with open(os.path.join(REV, "review_pack_ruled.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # 合并最终分析集：keep 5745 + 裁定 keep 的 review 记录
    final = list(csv.DictReader(open(os.path.join(CNKI, "prescreen_keep.csv"), encoding="utf-8-sig")))
    n0 = len(final)
    # review_pack 字段名与 prescreen 字段名不同，映射回去
    src = {r["编号"]: r for r in rows}
    orig = {r["title"]: r for r in csv.DictReader(open(os.path.join(CNKI, "prescreen_review_flag.csv"), encoding="utf-8-sig"))}
    n_add = 0
    for r in rows:
        if r["仲裁结果"] == "keep":
            o = orig.get(r["标题"])
            if o:
                final.append(o)
                n_add += 1
    with open(os.path.join(CNKI, "final_analysis_set.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(final[0].keys()))
        w.writeheader()
        w.writerows(final)
    print(f"原 keep: {n0}，review 裁定并入: {n_add}，最终分析集: {len(final)}")
    for k, v in sorted(ruled.items()):
        print(f"  {k[0]} -> {k[1]}: {v}")
    print("待定（E4附属医院/E7非附属医院）:", sum(v for (rid, res), v in ruled.items() if res == "pending"))


if __name__ == "__main__":
    main()
