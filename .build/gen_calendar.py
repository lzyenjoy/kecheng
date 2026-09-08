#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从课表规则生成自包含 HTML 课表日历（2026-09-07 当周 = 公共周1 = 专业周2）"""
import json
from datetime import date, timedelta

WEEK1_MON = date(2026, 9, 7)          # 公共周1 的周一 / 专业周2
SEM_START, SEM_END = date(2026, 9, 1), date(2027, 1, 31)

def public_week(d):                    # 公共周次；非学期内返回 None
    if d < WEEK1_MON: return 0
    return (d - WEEK1_MON).days // 7 + 1

CATS = {
    "politics": {"name": "政治理论",  "courses": ["新时代中国特色社会主义理论与实践", "自然辩证法"]},
    "lang":     {"name": "外语与写作", "courses": ["英语（学硕）", "专业英语", "论文写作指导（学硕）"]},
    "med":      {"name": "医学基础",  "courses": ["分子生物学", "高级医学免疫学", "现代生物医学前沿"]},
    "core":     {"name": "药学核心",  "courses": ["药理学选论", "药理学实验方法", "药学研究进展", "体内药物分析"]},
    "other":    {"name": "药学其他",  "courses": ["药事法规实务", "天然药物实用技术", "高级临床药学实践教程", "医药知识产权"]},
}
SHORT = {"新时代中国特色社会主义理论与实践": "新时代中特理论", "论文写作指导（学硕）": "论文写作指导",
         "天然药物实用技术": "天然药物", "高级临床药学实践教程": "高级临床药学"}

# (course, cat, wd, start, end, [(wlo, hi, teacher), ...], room, track)  wd: 0=周一
# track: "pub" -> 周次=公共周 ; "prof" -> 周次=专业周(=公共周+1)
RULES = [
    ("新时代中国特色社会主义理论与实践", "politics", 1, "08:30", "11:50", [(1, 8, "王驰")],  "博济-东101", "pub"),
    ("新时代中国特色社会主义理论与实践", "politics", 3, "08:30", "11:50", [(1, 2, "王驰")],  "博济-东101", "pub"),
    ("英语（学硕）",       "lang",     1, "19:00", "21:20", [(1, 13, "袁昌万")], "博济-东102", "pub"),
    ("分子生物学",         "med",      2, "08:30", "11:00", [(1, 8, "汤建才")],  "德启-西101", "pub"),
    ("分子生物学",         "med",      3, "19:00", "21:20", [(1, 8, "汤建才")],  "德启-西101", "pub"),
    ("分子生物学",         "med",      5, "08:30", "11:00", [(1, 6, "汤建才")],  "德启-西101", "pub"),
    ("高级医学免疫学",     "med",      2, "19:00", "21:20", [(1, 8, "胡为民")],  "德启-西101", "pub"),
    ("高级医学免疫学",     "med",      3, "08:30", "11:00", [(3, 8, "胡为民")],  "德启-西101", "pub"),
    ("自然辩证法",         "politics", 5, "19:00", "21:20", [(9, 14, "王廷龙")], "德启-西102", "pub"),
    ("论文写作指导（学硕）","lang",     2, "08:30", "11:00", [(10, 15, "钟晓武")], "德启-西101", "pub"),
    ("现代生物医学前沿",   "med",      1, "08:30", "11:50", [(10, 18, "曾梅")],  "德启-西101", "pub"),
    ("药理学选论",         "core",     0, "08:30", "11:50", [(2, 8, "胥正敏")],          "科技楼17楼药物研究所会议室", "prof"),
    ("药理学选论",         "core",     0, "08:30", "11:50", [(9, 9, "李勇")],            "科技楼17楼药物研究所会议室", "prof"),
    ("药理学选论",         "core",     4, "14:00", "17:20", [(2, 9, "胥正敏")],          "科技楼17楼药物研究所会议室", "prof"),
    ("药理学实验方法",     "core",     4, "08:30", "11:50", [(9, 17, "于春雷")],         "松林书院2号楼南408", "prof"),
    ("药学研究进展",       "core",     3, "14:00", "16:30", [(2, 15, "张帆")],           "松林书院2号楼南106", "prof"),
    ("体内药物分析",       "core",     2, "14:50", "17:20", [(2, 4, "苏蓉川"), (5, 5, "魏莹"), (7, 8, "魏莹")], "松林书院2号楼南309", "prof"),
    ("体内药物分析",       "core",     2, "14:00", "18:10", [(9, 9, "苏蓉川"), (10, 10, "魏莹")],               "松林书院2号楼南309", "prof"),
    ("体内药物分析",       "core",     2, "14:00", "17:20", [(11, 11, "魏莹"), (12, 12, "苏蓉川")],             "松林书院2号楼南309", "prof"),
    ("药事法规实务",       "other",    0, "14:00", "17:20", [(2, 2, "袁斌"), (4, 4, "李毅"), (7, 7, "韩彬")],   "博济-东509", "prof"),
    ("药事法规实务",       "other",    0, "14:00", "16:30", [(3, 3, "袁斌"), (5, 5, "李毅")],                   "博济-东509", "prof"),
    ("专业英语",           "lang",     1, "14:00", "16:30", [(2, 14, "赵鹏")],           "博济-东509", "prof"),
    ("天然药物实用技术",   "other",    0, "14:00", "16:30", [(8, 13, "李毅")],           "松林书院2号楼南307", "prof"),
    ("高级临床药学实践教程","other",    4, "14:50", "18:10", [(13, 13, "何梅"), (14, 14, "李婷婷"), (16, 16, "何梅"), (17, 17, "黎风")], "博济-东509", "prof"),
    ("高级临床药学实践教程","other",    4, "14:50", "16:30", [(15, 15, "李婷婷")],        "博济-东509", "prof"),
    ("医药知识产权",       "other",    0, "19:00", "21:20", [(15, 17, "袁斌")],          "科技楼17楼药物研究所会议室", "prof"),
    ("医药知识产权",       "other",    4, "19:00", "21:20", [(15, 17, "袁斌")],          "科技楼17楼药物研究所会议室", "prof"),
]

def wlabel(wlo, hi, track):
    if wlo == hi: return ("公共第%d周" % wlo) if track == "pub" else ("专业第%d周" % wlo)
    return ("公共第%d-%d周" % (wlo, hi)) if track == "pub" else ("专业第%d-%d周" % (wlo, hi))

events = []
d = SEM_START
while d <= SEM_END:
    p = public_week(d)
    if p >= 1:
        for course, cat, wd, st, en, spans, room, track in RULES:
            if d.weekday() != wd: continue
            for wlo, hi, teacher in spans:
                w = p if track == "pub" else p + 1
                if wlo <= w <= hi:
                    events.append({
                        "date": d.isoformat(), "start": st, "end": en,
                        "course": course, "short": SHORT.get(course, course),
                        "cat": cat, "teacher": teacher, "room": room,
                        "track": "公共课" if track == "pub" else "专业课",
                        "weeks": wlabel(wlo, hi, track),
                    })
    d += timedelta(days=1)

events.sort(key=lambda e: (e["date"], e["start"]))
HOLIDAYS = [
    {"start": "2026-09-25", "end": "2026-09-25", "name": "中秋节"},
    {"start": "2026-10-01", "end": "2026-10-07", "name": "国庆节"},
    {"start": "2027-01-01", "end": "2027-01-01", "name": "元旦"},
]

# ---- sanity checks ----
from collections import Counter
per_course = Counter(e["course"] for e in events)
print("total sessions:", len(events))
for c, n in per_course.items(): print(f"  {c}: {n}")
def show(ds):
    rows = [e for e in events if e["date"] == ds]
    print(f"\n{ds} ({len(rows)}):")
    for e in rows: print(f"  {e['start']}-{e['end']} {e['course']} {e['teacher']} {e['room']} [{e['weeks']}]")
show("2026-09-08"); show("2026-10-30"); show("2026-12-25"); show("2026-09-07")
print("\nfirst:", events[0]["date"], "last:", events[-1]["date"])

json.dumps  # noqa
open("/home/alex/project/kecheng/.build/events.json", "w", encoding="utf-8").write(
    json.dumps({"events": events, "holidays": HOLIDAYS, "cats": CATS}, ensure_ascii=False))
print("\nwritten events.json")
