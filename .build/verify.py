#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立核对：class.doc(经Word转HTML) ↔ calendar.html 内嵌数据"""
import re, json, sys
from datetime import date, timedelta
from collections import Counter

WEEK1_MON = date(2026, 9, 7)  # 公共周1 周一（用户锚点）
PUBLIC = {"新时代中国特色社会主义理论与实践", "自然辩证法", "英语（学硕）", "论文写作指导（学硕）",
          "现代生物医学前沿", "分子生物学", "高级医学免疫学"}

# ---- A. 解析 Word 转出的 HTML 表格（含 rowspan）----
html = open('/mnt/c/Users/Public/class.html', 'rb').read().decode('gb18030', 'replace')
table = re.findall(r'<table.*?</table>', html, re.S | re.I)[0]
rows_html = re.findall(r'<tr.*?</tr>', table, re.S | re.I)

# 展开成占用矩阵 occupied[r][c] = text（仅首格保留文本，延续格标记为 MERGED）
grid, occ = [], {}
for r, row in enumerate(rows_html):
    cells = re.findall(r'<t[dh][^>]*>.*?</t[dh]>', row, re.S | re.I)
    c = 0
    for cell in cells:
        while (r, c) in occ: c += 1
        attrs = re.match(r'<t[dh]([^>]*)>', cell, re.I).group(1)
        rs = re.search(r'rowspan\s*=\s*"?(\d+)', attrs, re.I)
        cs = re.search(r'colspan\s*=\s*"?(\d+)', attrs, re.I)
        span_r = int(rs.group(1)) if rs else 1
        span_c = int(cs.group(1)) if cs else 1
        txt = re.sub(r'<[^>]+>', '', cell)
        txt = txt.replace('&nbsp;', ' ').replace('&amp;', '&')
        occ[(r, c)] = txt
        for dr in range(span_r):
            for dc in range(span_c):
                if dr or dc: occ[(r + dr, c + dc)] = '\x00MERGED'
        c += span_c

n_cols = max(c for _, c in occ) + 1
def cell(r, c): return occ.get((r, c), '').strip()

# 节次行 -> 起止时间（直接取 col1 文本）
def row_time(r):
    t = cell(r, 1)
    m = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', t)
    return (m.group(1), m.group(2)) if m else None

# ---- B. 抽取全部教学条目: (weekday, start, end, course, weeks, teacher, room) ----
TOK = re.compile(r'([^\[\]\r\n]+?)\[(\d+)(?:-(\d+))?周\]([^\[\]]+)\[([^\]]+)\]')
entries, raw_cells = [], 0
for (r, c), txt in occ.items():
    if txt in ('\x00MERGED', '') or c < 2 or c > 8 or r < 2: continue
    course_bits = TOK.findall(txt)
    if not course_bits: continue
    raw_cells += 1
    st_en = row_time(r)
    assert st_en, f"row {r} col {c} 有课程但无时间: {txt}"
    span_last = r
    while (span_last + 1, c) in occ and occ[(span_last + 1, c)] == '\x00MERGED': span_last += 1
    end = row_time(span_last)[1]
    for name, w1, w2, teacher, room in course_bits:
        name = re.sub(r'\d+班$', '', name.strip())
        entries.append(dict(weekday=c - 2, start=st_en[0], end=end, course=name,
                            wlo=int(w1), whi=int(w2 if w2 else w1),
                            teacher=teacher.strip(), room=room.strip()))
print(f"class.doc 解析出 {raw_cells} 个课格、{len(entries)} 条「课程×周次×教师」原始条目")

# 专业课不允许出现第1周（双轨自洽检查）
bad = [e for e in entries if e['course'] not in PUBLIC and e['wlo'] == 1]
print("专业课第1周条目(应为0):", len(bad), bad)

# ---- C. 展开成具体日期，并把相邻时段做区间并集 ----
def to_date(e, w):  # doc周次 -> 具体日期
    pub = w - 1 if e['course'] in PUBLIC else w - 2
    return WEEK1_MON + timedelta(weeks=pub, days=e['weekday'])
def mins(t): h, m = t.split(':'); return int(h) * 60 + int(m)

# WPS 导出会把同一节长课在每行重复标注，因此按「同日同课同师同室」收集区间后取并集
blocks = {}
for e in entries:
    for w in range(e['wlo'], e['whi'] + 1):
        d = to_date(e, w).isoformat()
        blocks.setdefault((d, e['course'], e['teacher'], e['room']), set()).add((e['start'], e['end']))

merged = Counter()
for (d, co, te, ro), ivs in blocks.items():
    cur_s, cur_e = sorted(ivs)[0]
    for s, e2 in sorted(ivs)[1:]:
        if mins(s) - mins(cur_e) <= 20:   # 相邻（<=20min 间隔）视为同一节长课
            cur_e = max(cur_e, e2)
        else:
            merged[(d, cur_s, cur_e, co, te, ro)] += 1
            cur_s, cur_e = s, e2
    merged[(d, cur_s, cur_e, co, te, ro)] += 1

# ---- D. 读取 calendar.html 内嵌数据 ----
cal = open('/home/alex/project/kecheng/calendar.html', encoding='utf-8').read()
data = json.loads(re.search(r'const DATA = (\{.*?\});\n', cal, re.S).group(1).replace('<\\/', '</'))
actual = Counter((e['date'], e['start'], e['end'], e['course'], e['teacher'], e['room'])
                 for e in data['events'])

print(f"\nclass.doc 展开并合并后: {sum(merged.values())} 次课")
print(f"calendar.html 内嵌:    {sum(actual.values())} 次课")

only_doc = merged - actual
only_cal = actual - merged
print("\n== class.doc 有而 calendar 没有 ==", len(only_doc))
for k, n in sorted(only_doc.items()): print("  -", k, "x", n)
print("\n== calendar 有而 class.doc 没有 ==", len(only_cal))
for k, n in sorted(only_cal.items()): print("  +", k, "x", n)

per = Counter()
for (d, st, en, co, te, ro) in merged.elements(): per[co] += 1
print("\n逐门课次(class.doc 口径):")
for co, n in sorted(per.items(), key=lambda x: -x[1]): print(f"  {co}: {n}")

ok = not only_doc and not only_cal
print("\n" + ("✅ 核对通过：calendar.html 与 class.doc 完全一致" if ok else "❌ 存在差异，见上"))
sys.exit(0 if ok else 1)
