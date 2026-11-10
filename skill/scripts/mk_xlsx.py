#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the three spreadsheets from trip.json.

Outputs (into the out_dir next to trip.json):
    司机行程单-Driver-Schedule-{date_suffix}.xlsx   1 sheet, English
    游客手册-{date_suffix}.xlsx                    8 sheets, bilingual
    行程中英对照-{date_suffix}.xlsx                1 sheet, CN/EN commands

Usage:
    python mk_xlsx.py path/to/trip.json

Audience split (see references/deliverables.md):
  - the driver sheet and the bilingual command sheet carry route and
    timing only - never budget, never passenger personal details;
  - the guest handbook carries everything, including the budget.
"""
import json
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

HDR = PatternFill("solid", fgColor="1F4E5F")
WRAP = Alignment(wrap_text=True, vertical="top")


def load(path):
    cfg = json.load(open(path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(path))
    out = os.path.join(base, cfg.get("out_dir", "out"))
    os.makedirs(out, exist_ok=True)
    return cfg, out


def place_name(cfg, key, en=False):
    p = cfg["places"][key]
    if en:
        return p.get("name_en") or p["name"]
    return p["name"]


def route_of(cfg, d, en=False):
    if en:
        return d.get("route_en") or (f"{place_name(cfg, d['from'], True)} "
                                     f"-> {place_name(cfg, d['to'], True)}")
    return d.get("route_cn") or (f"{place_name(cfg, d['from'])}"
                                 f"→{place_name(cfg, d['to'])}")


# ---------------------------------------------------------------- 游客手册
def sheet(wb, name, rows, widths=None, title=None):
    ws = wb.create_sheet(name)
    start = 1
    if title:
        ws["A1"] = title
        ws["A1"].font = Font(bold=True, size=14)
        start = 3
    for i, row in enumerate(rows, start=start):
        for j, v in enumerate(row, start=1):
            ws.cell(row=i, column=j, value=v).alignment = WRAP
    for j in range(1, len(rows[0]) + 1):
        c = ws.cell(row=start, column=j)
        c.font = Font(bold=True, color="FFFFFF", size=12)
        c.fill = HDR
    if widths:
        from openpyxl.utils import get_column_letter
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w
    return ws


def build_guest(cfg, out):
    g = cfg["guest"]
    fx = cfg.get("fx", {})
    code = fx.get("code", "Rs")
    wb = Workbook()
    wb.remove(wb.active)

    # 1 封面
    ws = sheet(wb, "封面", [["项目", "内容"]],
               title=g.get("cover_title", cfg.get("title", "")))
    for row in g.get("cover_rows", []):
        ws.append(list(row))

    # 2 行程总览（由 days 派生）
    rows = [["日", "日期", "路线", "km", "车时", "出发", "住"]]
    for d in cfg["days"]:
        rows.append([d["day"], d.get("date", ""), route_of(cfg, d),
                     d.get("km", 0), d.get("drive", "-"),
                     d.get("depart", "-"), place_name(cfg, d["stay"])])
    sheet(wb, "行程总览", rows, widths=[6, 10, 26, 8, 10, 24, 10],
          title="行程总览 Itinerary")

    # 3 每日行程（由 days 派生）
    rows = [["天", "中文", "ENGLISH"]]
    for d in cfg["days"]:
        cn = d.get("daily_cn")
        if cn is None:
            cn = "；".join(d.get("items_cn", [])) or d.get("note_cn", "")
        en = d.get("daily_en")
        if en is None:
            en = "; ".join(d.get("items_en", [])) or d.get("note_en", "")
        rows.append([f"{d['day']} {d.get('date', '')}", cn, en])
    sheet(wb, "每日行程", rows, widths=[12, 70, 70],
          title="每日行程 Day by Day")

    # 4 酒店
    hot = g.get("hotels", {"rows": [["晚", "候选", "档", "房型要求", "备注"]]})
    sheet(wb, "酒店", hot["rows"], widths=[20, 55, 8, 40, 45],
          title=hot.get("title", "酒店候选（自行按日期查实时房态，"
                                 "或让旅行社拿B2B价）"))

    # 5 费用
    fxcode = fx.get("code", "Rs")
    cost = g.get("costs", {"rows": [["项目", fxcode, "约人民币", "说明"]]})
    title = cost.get("title") or (
        f"费用明细（估算，¥1≈{fxcode} {fx.get('cny', '')}，{fx.get('as_of', '')}）")
    sheet(wb, "费用", cost["rows"], widths=[22, 16, 14, 60], title=title)

    # 6 专项活动（原蓝本为 Safari）
    act = g.get("activity")
    if act:
        sheet(wb, act.get("sheet", "专项活动"), act["rows"],
              widths=[12, 90], title=act.get("title", ""))

    # 7 天气打包
    wpack = g.get("weather_pack",
                  {"rows": [["日", "降水", "最高温", "穿带"]]})
    sheet(wb, "天气打包", wpack["rows"], widths=[10, 26, 22, 45],
          title=wpack.get("title", "天气与打包"))

    # 8 待办
    todo = g.get("todo", {"rows": [["何时", "事项", "状态"]]})
    sheet(wb, "待办", todo["rows"], widths=[12, 70, 10],
          title=todo.get("title", "待办清单"))

    path = os.path.join(out, f"游客手册-{cfg['date_suffix']}.xlsx")
    wb.save(path)
    print("saved", path)


# ---------------------------------------------------------------- 司机行程单
def build_driver(cfg, out):
    wb = Workbook()
    ws = wb.active
    ws.title = "Driver Schedule"
    rows = [["Day", "Date", "Route", "km", "Drive", "Depart", "Arrive",
             "Stops / Parking / Notes"]]
    for d in cfg["days"]:
        km = d.get("km", 0)
        rows.append([
            d["day"], d.get("date_en", d.get("date", "")),
            route_of(cfg, d, en=True), km,
            d.get("drive") or "-", d.get("depart") or "-",
            d.get("arrive") or "-", d.get("driver_notes", ""),
        ])
    for i, r in enumerate(rows, start=1):
        for j, v in enumerate(r, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.alignment = WRAP
            if i == 1:
                c.font = Font(bold=True, color="FFFFFF", size=11)
                c.fill = HDR
    from openpyxl.utils import get_column_letter
    for j, w in enumerate([8, 10, 34, 8, 10, 10, 10, 70], start=1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    path = os.path.join(
        out, f"司机行程单-Driver-Schedule-{cfg['date_suffix']}.xlsx")
    wb.save(path)
    print("saved", path)


# ---------------------------------------------------------------- 中英对照
def build_bilingual(cfg, out):
    b = cfg["bilingual"]
    wb = Workbook()
    ws = wb.active
    ws.title = b.get("sheet", "指令")
    rows = b["rows"]
    for i, r in enumerate(rows, start=1):
        for j, v in enumerate(r, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.alignment = WRAP
            if i == 1:
                c.font = Font(bold=True, color="FFFFFF", size=11)
                c.fill = HDR
    from openpyxl.utils import get_column_letter
    for j, w in enumerate([55, 60], start=1):
        ws.column_dimensions[get_column_letter(j)].width = w
    path = os.path.join(out, f"行程中英对照-{cfg['date_suffix']}.xlsx")
    wb.save(path)
    print("saved", path)


def main(path):
    cfg, out = load(path)
    for key in ("places", "days", "guest", "bilingual", "date_suffix"):
        if key not in cfg:
            sys.exit(f"fatal: trip.json missing required key {key!r}")
    build_driver(cfg, out)
    build_guest(cfg, out)
    build_bilingual(cfg, out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
