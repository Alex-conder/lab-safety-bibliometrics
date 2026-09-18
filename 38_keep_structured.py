# -*- coding: utf-8 -*-
"""
阶段2：keep 集（最终分析集 6178 条）结构化提取与主题编码
输出：outputs/keep/keep_structured.csv, theme_year_matrix.csv, zero_theme_list.md, theme_cn_en_mapping.csv
规则：主题多选≤3（按命中词数排序取前3）；电气/线路/老化类单独标记供"供给不足型错位"分析
"""
import csv
import os
from collections import Counter, defaultdict

CNKI = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "cnki_raw"))
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "keep"))
os.makedirs(OUT, exist_ok=True)

THEMES = [
    ("危化品", ["危险化学品", "危化品", "化学品安全", "剧毒", "易制爆", "气瓶", "易制毒"]),
    ("生物安全", ["生物安全", "病原微生物", "生物实验室", "动物实验", "实验动物"]),
    ("辐射", ["辐射", "放射", "核"]),
    ("设备", ["仪器设备", "设备管理", "大型仪器", "设备安全", "仪器管理"]),
    ("电气", ["电气安全", "用电安全", "线路老化", "电路", "配电", "电气火灾"]),
    ("消防", ["消防", "火灾", "防火", "灭火"]),
    ("安全教育", ["安全教育", "安全培训", "安全意识", "安全准入", "准入制度", "准入体系"]),
    ("安全文化", ["安全文化", "安全价值观"]),
    ("风险评估", ["风险评估", "风险评价", "风险分级", "风险辨识", "风险管控", "风险管理"]),
    ("双重预防", ["双重预防", "隐患排查", "隐患治理", "隐患排查治理"]),
    ("信息化", ["信息化", "智慧实验室", "智能实验室", "物联网", "数字化", "智能化", "大数据"]),
    ("安全管理", ["安全管理", "实验室安全", "安全管理体系", "管理制度", "管理体制"]),
]
ELEC_TERMS = ["电气安全", "用电安全", "线路老化", "电气火灾", "设备老化", "老化", "电气", "线路"]

OBJ_RULES = [("高校", ["大学", "学院", "高校", "高等"]), ("科研院所", ["研究院", "研究所", "科学院", "中心实验室"])]
METHOD_RULES = [
    ("计量", ["文献计量", "计量分析", "bibliometric", "citespace", "vosviewer", "可视化分析", "知识图谱"]),
    ("综述", ["综述", "述评", "研究进展", "现状与", "现状分析"]),
    ("案例", ["事故案例", "案例分析", "个案", "事故为", "事故分析", "起事故", "起实验室"]),
    ("实证", ["问卷", "调查", "实证", "统计分析", "数据分析", "影响因素", "满意度", "访谈"]),
]
ACCIDENT_TERMS = ["事故", "爆炸", "火灾", "中毒", "泄漏", "伤亡", "爆燃", "灼伤"]


def text_of(r):
    return (r["title"] or "") + " " + (r["keywords"] or "") + " " + (r["abstract"] or "")


def main():
    rows = list(csv.DictReader(open(os.path.join(CNKI, "final_analysis_set.csv"), encoding="utf-8-sig")))
    theme_year = defaultdict(Counter)
    elec_hits = Counter()
    out = []
    for r in rows:
        t = text_of(r)
        # 研究对象
        obj = "其他"
        aff = (r["affiliations"] or "") + (r["title"] or "")
        for label, kws in OBJ_RULES:
            if any(k in aff for k in kws):
                obj = label
                break
        # 主题（多选≤3）
        scored = []
        for name, kws in THEMES:
            hits = sum(t.count(k) for k in kws)
            if hits:
                scored.append((hits, name))
        scored.sort(reverse=True)
        themes = [n for _, n in scored[:3]] or ["其他"]
        # 电气/老化专项
        elec = [k for k in ELEC_TERMS if k in t]
        for k in elec:
            elec_hits[k] += 1
        # 事故相关
        acc = "是" if any(k in t for k in ACCIDENT_TERMS) else "否"
        # 研究方法
        meth = "其他"
        for m, kws in METHOD_RULES:
            if any(k in t.lower() for k in kws):
                meth = m
                break
        out.append({
            "title": r["title"], "journal": r["journal"], "year": r["year"],
            "研究对象": obj, "主题标签": "|".join(themes),
            "事故相关": acc, "研究方法": meth,
            "电气老化专项": "|".join(elec), "keywords": r["keywords"],
        })
        if r["year"]:
            for th in themes:
                theme_year[th][r["year"]] += 1
    with open(os.path.join(OUT, "keep_structured.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    # 主题×年份矩阵
    years = sorted({r["year"] for r in out if r["year"]})
    with open(os.path.join(OUT, "theme_year_matrix.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["theme"] + years)
        for th, _ in THEMES:
            w.writerow([th] + [theme_year[th].get(y, 0) for y in years])
        w.writerow(["其他"] + [theme_year["其他"].get(y, 0) for y in years])

    # 零主题词清单
    with open(os.path.join(OUT, "zero_theme_list.md"), "w", encoding="utf-8") as f:
        f.write("# 零/近零主题词清单（供'供给不足型错位'分析）\n\n")
        f.write("| 专项词 | 命中篇数（n=6178） |\n|---|---|\n")
        for k in ELEC_TERMS:
            f.write(f"| {k} | {elec_hits.get(k, 0)} |\n")
        f.write("\n说明：'老化''电气''线路'为全文宽泛匹配，含非安全语境；其余为精确词。\n")

    # 中英文主题对照（语义对应）
    mapping = [
        ("危化品", "hazardous chemicals / chemical safety"),
        ("生物安全", "biosafety / biosecurity"),
        ("辐射", "radiation safety"),
        ("设备", "instrument & equipment safety / facility management"),
        ("电气", "electrical safety / wiring aging（文献侧近零）"),
        ("消防", "fire safety / fire protection"),
        ("安全教育", "safety education / safety training / safety access"),
        ("安全文化", "safety culture / safety climate"),
        ("风险评估", "risk assessment / risk management"),
        ("双重预防", "dual prevention mechanism / hazard identification & risk grading"),
        ("信息化", "smart laboratory / digital & IoT-based management"),
        ("安全管理", "safety management / laboratory safety management system"),
    ]
    with open(os.path.join(OUT, "theme_cn_en_mapping.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["中文主题", "英文对应主题（语义对应，非逐字翻译）"])
        w.writerows(mapping)

    # 摘要
    tc = Counter()
    for r in out:
        for th in r["主题标签"].split("|"):
            tc[th] += 1
    print("主题分布:", dict(tc.most_common()))
    print("事故相关:", Counter(r["事故相关"] for r in out))
    print("研究方法:", dict(Counter(r["研究方法"] for r in out)))
    print("研究对象:", dict(Counter(r["研究对象"] for r in out)))
    print("电气老化专项命中:", dict(elec_hits))


if __name__ == "__main__":
    main()
