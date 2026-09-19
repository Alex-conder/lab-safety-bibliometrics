# -*- coding: utf-8 -*-
"""《中国安全科学学报》格式终版 docx 构建：
- 0 引言编号体系（1 引言→0 引言，其后顺延）
- 全部表格转三线表
- 作者拼音行、单位英文占位、CSSJ 首页脚注（基金项目/作者简介/通讯作者）
- 中图分类号 X913.4；G647，文献标志码 A
"""
import re
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC_MD = 'outputs/paper_coevolution_v2.md'
OUT = 'outputs/paper_final_CSSJ.docx'

# ---------- 编号体系转换 ----------
RENUM_HEAD = {
    '## 1 引言': '## 0 引言',
    '## 2 资料与方法': '## 1 数据与方法',
    '## 3 结果': '## 2 结果',
    '## 4 讨论': '## 3 讨论',
    '## 5 结论': '## 4 结论',
}
SUBMAP = {'2.1': '1.1', '2.2': '1.2', '2.3': '1.3',
          '3.1': '2.1', '3.2': '2.2', '3.3': '2.3',
          '4.1': '3.1', '4.2': '3.2', '4.3': '3.3', '4.4': '3.4', '4.5': '3.5', '4.6': '3.6'}

FIG_EN = {
    '图 1': 'Fig. 1  Co-evolution framework of risk-knowledge-institution streams',
    '图 2': 'Fig. 2  Composition of 183 accidents and period evolution of fire share',
    '图 3': 'Fig. 3  Distribution of hazard factors in 183 accidents',
    '图 4': 'Fig. 4  Annual publication trends in Chinese and English (2000—2026)',
    '图 5': 'Fig. 5  Co-occurrence network of Chinese keywords (Top 35)',
    '图 6': 'Fig. 6  Period evolution heatmap of Chinese research themes',
    '图 7': 'Fig. 7  Burst detection in Chinese and English keywords (Kleinberg)',
    '图 8': 'Fig. 8  Timeline of risk events, knowledge production and policy responses',
    '图 9（左）': 'Fig. 9 (left)  Mismatch quadrant between accident risk and research attention; Fig. 10 (right)  Intervention priority matrix',
}


def renumber(md):
    for k, v in RENUM_HEAD.items():
        md = md.replace(k, v)
    # 三级标题换号（### 2.1 xxx → ### 1.1 xxx；先 4.x 再 3.x 再 2.x 防串号）
    for old in ['2.1', '2.2', '2.3', '3.1', '3.2', '3.3', '4.1', '4.2', '4.3', '4.4', '4.5', '4.6']:
        md = re.sub(r'^(### )' + re.escape(old) + ' ', r'\g<1>' + SUBMAP[old] + ' ', md, flags=re.M)
    return md


def set_font(run, cn='宋体', en='Times New Roman', size=10.5, bold=None):
    run.font.name = en
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), cn)


def add_runs(p, text):
    for part in re.split(r'(\*\*.+?\*\*)', text):
        if not part:
            continue
        if part.startswith('**'):
            r = p.add_run(part[2:-2])
            r.bold = True
        else:
            p.add_run(part)


def three_line(table, n_rows, n_cols):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge, sz in [('top', 12), ('bottom', 12), ('insideH', 4)]:
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), str(sz))
        borders.append(e)
    for edge in ['left', 'right', 'insideV']:
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'), 'none')
        borders.append(e)
    tblPr.append(borders)
    # 表头行下加中粗线：直接给首行单元格底边
    for cell in table.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcB = OxmlElement('w:tcBorders')
        b = OxmlElement('w:bottom')
        b.set(qn('w:val'), 'single')
        b.set(qn('w:sz'), '8')
        tcB.append(b)
        tcPr.append(tcB)


def main():
    md = renumber(open(SRC_MD, encoding='utf-8').read())
    # 作者/单位占位（中英文）
    md = md.replace('**关键词**',
        '张 三1，李 四2，王 五1\n（1. 西安医学院 某某学院，陕西 西安 710000；2. 某某大学 某某学院，陕西 西安 710000）\n\n**关键词**')
    md = md.replace('**中图分类号**：G647；X931', '**中图分类号**：X913.4；G647')
    # 英文作者行插在 Abstract 前
    md = md.replace('**Abstract**',
        'ZHANG San1, LI Si2, WANG Wu1\n(1. School of XX, Xi\'an Medical University, Xi\'an 710000, China; 2. School of XX, XX University, Xi\'an 710000, China)\n\n**Abstract**')

    lines = md.split('\n')
    doc = Document()
    st = doc.styles['Normal']
    st.font.name = 'Times New Roman'
    st.font.size = Pt(10.5)
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.first_line_indent = Cm(0.74)

    inserted_footer = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i + 1]):
            header = [c.strip() for c in line.strip().strip('|').split('|')]
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            t = doc.add_table(rows=len(rows) + 1, cols=len(header))
            for j, h in enumerate(header):
                cell = t.rows[0].cells[j]
                cell.text = ''
                r = cell.paragraphs[0].add_run(h)
                set_font(r, size=9, bold=True)
            for ri, row in enumerate(rows, 1):
                for j, c in enumerate(row[:len(header)]):
                    cell = t.rows[ri].cells[j]
                    cell.text = ''
                    r = cell.paragraphs[0].add_run(c)
                    set_font(r, size=9)
            three_line(t, len(rows) + 1, len(header))
            continue
        if line.startswith('### '):
            h = doc.add_paragraph()
            r = h.add_run(line[4:].strip())
            set_font(r, cn='黑体', size=12, bold=True)
        elif line.startswith('## '):
            h = doc.add_paragraph()
            r = h.add_run(line[3:].strip())
            set_font(r, cn='黑体', size=14, bold=True)
        elif line.startswith('# '):
            h = doc.add_paragraph()
            h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = h.add_run(line[2:].strip())
            set_font(r, cn='黑体', size=16, bold=True)
        elif line.strip() == '---':
            pass
        elif line.strip():
            p = doc.add_paragraph()
            add_runs(p, line.strip())
            for r in p.runs:
                set_font(r)
            if not inserted_footer and '中图分类号' in line:
                fp = doc.add_paragraph()
                fp.paragraph_format.first_line_indent = Cm(0)
                r = fp.add_run('收稿日期：____；修回日期：____\n基金项目：____（项目编号：____）\n作者简介：张三（19__—），____（职称/学位），研究方向：____。通讯作者：____，E-mail：____。')
                set_font(r, size=9)
                inserted_footer = True
        i += 1

    FIGS = [
        ('（图 1）', 'outputs/figures/cf_fig1_framework.png', '图 1  “风险流—知识流—制度流”协同演化分析框架'),
        ('（图 2）', 'outputs/figures/cf_fig2_accident_types.png', '图 2  事故类型构成、火灾分期演变与暴露量校正事故率'),
        ('（图 3）', 'outputs/figures/cf_fig3_factors.png', '图 3  危险因素分布（危险因素/环节/原因结构均为叶元兴等[1]176 起库口径）'),
        ('（图 4）', 'outputs/figures/fig1_publication_trend.png', '图 4  2000—2026 年中英文年度发文量趋势'),
        ('图 5）', 'outputs/figures/fig2_cn_cooccurrence.png', '图 5  中文关键词共现网络（Top 35，Q=0.109）'),
        ('图 6、', 'outputs/figures/cf_fig6_theme_heatmap.png', '图 6  中文文献主题占比的时期演化热力图'),
        ('图 7', 'outputs/figures/cf_fig7_bursts.png', '图 7  中英文关键词突现检测对照（Kleinberg，γ=1.0）'),
        ('（图 8）', 'outputs/figures/fig4_policy_timeline.png', '图 8  风险事件—知识生产—政策响应时间轴（2000—2026）'),
        ('（表 5、图 9）', 'outputs/figures/cf_fig9_10_quadrant_priority.png', '图 9（左）事故风险与研究关注的错位四象限；图 10（右）干预优先级矩阵'),
    ]
    paras = doc.paragraphs
    placed = set()
    for k, p in enumerate(paras):
        for marker, img, cap in FIGS:
            if marker in p.text and cap not in placed:
                nxt = paras[k + 1] if k + 1 < len(paras) else None
                ip = nxt.insert_paragraph_before() if nxt is not None else doc.add_paragraph()
                ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
                ip.paragraph_format.first_line_indent = Cm(0)
                ip.add_run().add_picture(img, width=Cm(15.5 if '左）' in cap else 14))
                cp = nxt.insert_paragraph_before() if nxt is not None else doc.add_paragraph()
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cp.paragraph_format.first_line_indent = Cm(0)
                r = cp.add_run(cap)
                set_font(r, cn='黑体', size=9, bold=True)
                ep = nxt.insert_paragraph_before() if nxt is not None else doc.add_paragraph()
                ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
                ep.paragraph_format.first_line_indent = Cm(0)
                encap = next((v for kk, v in FIG_EN.items() if cap.startswith(kk)), None)
                if encap:
                    re_ = ep.add_run(encap)
                    set_font(re_, size=9)
                placed.add(cap)
    doc.save(OUT)
    print('saved:', OUT, '| 图:', len(doc.inline_shapes), '| 表:', len(doc.tables), '| 段:', len(doc.paragraphs))
    print('未放置:', [c for _, _, c in FIGS if c not in placed] or '无')


if __name__ == '__main__':
    main()
