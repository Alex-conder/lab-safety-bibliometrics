# -*- coding: utf-8 -*-
"""
阶段1：review_flag 647 条自动化初判 + 人工复核包生成
规则优先级：类型 → 对象 → 主题（逐条记录触发规则编号与触发词，保证可追溯）
输出：outputs/review/review_pack.csv, review_manual.md（终端打印建议分布）
"""
import csv
import os
import re
from collections import Counter

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "cnki_raw", "prescreen_review_flag.csv"))
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "review"))
os.makedirs(OUT, exist_ok=True)

RULES = [
    # (规则号, 建议, 不确定点, 关键词组, 判定函数说明)
    ("E1", "exclude_suggest", "类型不符：新闻/通讯/剪报体，待人工确认", ["<正>", "本报讯", "讯：", "会议通知", "征稿", "启事"], "题录为新闻通讯体"),
    ("E2", "exclude_suggest", "", ["中学", "小学", "幼儿园", "中小学", "中职", "附中"], "对象为中小学"),
    ("E3", "exclude_suggest", "", ["医院检验科", "检验科", "临床实验室"], "对象为医院检验科室"),
    ("E4", "uncertain", "附属医院/医学院实验室是否计入高校实验室口径，需课题组裁定", ["附属医院", "大学附属医院", "医学院附属"], "高校附属医疗机构"),
    ("E5", "uncertain", "高职高专属高等学校序列，是否纳入本研究'高校'口径需课题组裁定", ["高职", "职业技术学院", "职业学院", "职业院校"], "高职院校边界"),
    ("E6", "uncertain", "校企合作/共建实验室的归属判定", ["企业", "公司", "集团", "厂"], "含企业信号"),
    ("E7", "uncertain", "医院（非附属）实验室，需人工判断是否高校教学科研体系", ["医院"], "含医院信号"),
    ("E8", "exclude_suggest", "", ["虚拟仿真", "虚拟实验室", "网络实验室"], "虚拟/网络实验室（非实体安全）"),
    ("E9", "keep_suggest", "", ["研究院", "研究所", "科学院", "中科院", "农科院", "医科院", "疾控中心"], "科研院所（符合纳入标准1）"),
    ("E10", "keep_suggest", "", ["大学", "高校", "学院", "重点实验室", "重点学科"], "高校/科研院所实验室"),
]

UNI_HINTS = ["大学", "高校", "学院", "重点实验室", "研究生", "本科生", "导师"]


def judge(r):
    text = (r["title"] or "") + " " + (r["keywords"] or "") + " " + (r["abstract"] or "") + " " + (r["affiliations"] or "") + " " + (r["journal"] or "")
    for rid, sug, unc, kws, desc in RULES:
        hit = [k for k in kws if k in text]
        if hit:
            # E6 企业信号：若同时强高校信号则升 uncertain（共建情形）
            if rid == "E6" and any(u in text for u in UNI_HINTS):
                return "uncertain", "E6+", "/".join(hit[:3]), "校企合作/共建实验室归属需人工判定"
            # E9/E10 keep：若标题含明显非高校对象词则不适用（已被 E2-E7 拦截）
            return sug, rid, "/".join(hit[:3]), unc
    return "uncertain", "E0", "", "无明确对象线索，信息不足"


def main():
    with open(SRC, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out_rows = []
    cnt = Counter()
    for i, r in enumerate(rows, 1):
        sug, rid, trig, unc = judge(r)
        cnt[sug] += 1
        out_rows.append({
            "编号": f"R{i:04d}",
            "标题": r["title"], "期刊": r["journal"], "年份": r["year"],
            "关键词": r["keywords"], "摘要": r["abstract"],
            "预筛理由": r.get("reason", ""),
            "自动建议": sug, "触发规则": rid, "触发关键词": trig,
            "不确定点": unc,
            "复核人A": "", "复核人B": "", "仲裁结果": "",
        })
    with open(os.path.join(OUT, "review_pack.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    # 取边界示例（真实记录）
    examples = {}
    for r in out_rows:
        key = r["触发规则"]
        if key not in examples and r["自动建议"] == "uncertain":
            examples[key] = r["标题"]

    with open(os.path.join(OUT, "review_manual.md"), "w", encoding="utf-8") as f:
        f.write("""# 人工复核手册（review_flag 647 条）

## 复核流程
双人独立复核 `review_pack.csv`（填"复核人A/B"列：keep / exclude / uncertain），不一致处第三人仲裁填"仲裁结果"。
复核完成后用 R 计算 Cohen's Kappa（A vs B），Kappa>0.75 视为一致性可接受，写入论文 2.2 节。

## 判定优先级
研究对象 → 主题 → 文献类型。对象不符直接 exclude，不再看主题。

## 自动建议规则编号表（可追溯）

| 规则 | 建议 | 触发关键词 | 说明 |
|---|---|---|---|
| E1 | exclude_suggest | <正>/本报讯/讯：/会议通知/征稿/启事 | 新闻通讯体，类型不符 |
| E2 | exclude_suggest | 中学/小学/幼儿园/中小学/中职/附中 | 对象不符：中小学 |
| E3 | exclude_suggest | 医院检验科/检验科/临床实验室 | 对象不符：医院科室 |
| E4 | uncertain | 附属医院/大学附属医院/医学院附属 | 边界：附属医院实验室口径 |
| E5 | uncertain | 高职/职业技术学院/职业学院/职业院校 | 边界：高职高专是否算"高校" |
| E6 | uncertain | 企业/公司/集团/厂 | 边界：校企合作共建实验室 |
| E7 | uncertain | 医院 | 边界：非附属医院 |
| E8 | exclude_suggest | 虚拟仿真/虚拟实验室/网络实验室 | 非实体实验场所 |
| E9 | keep_suggest | 研究院/研究所/科学院等 | 科研院所符合纳入标准 |
| E10 | keep_suggest | 大学/高校/学院/重点实验室 | 高校实验室 |
| E0 | uncertain | — | 信息不足 |

## 边界案例示例（取自真实记录）

""")
        for k, v in sorted(examples.items()):
            f.write(f"- [{k}] 《{v}》\n")
        f.write("""
## 复核操作要点
1. 优先依据摘要判定；摘要缺失或过短时按标题+关键词从严判定为 uncertain，不强行归类。
2. "附属医院"口径建议（供仲裁参考）：高校直属附属医院教学科研实验室可计入，医院检验科/临床科室不计入。
3. "高职高专"口径建议（供仲裁参考）：高等职业教育属高等学校序列，建议计入并在论文敏感性分析中验证。
4. 复核人只填 keep/exclude/uncertain 三个值；仲裁结果为最终入库标签。
""")
    print("总数:", len(rows))
    for k in ["keep_suggest", "exclude_suggest", "uncertain"]:
        print(f"{k}: {cnt[k]}")
    print("规则分布:", dict(Counter(r["触发规则"] for r in out_rows)))


if __name__ == "__main__":
    main()
