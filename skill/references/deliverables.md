# Deliverables — the fixed pack of 6

Every finished plan produces **exactly these six files**, into `out_dir`
(default `out/`) next to `trip.json`. Same count, same names, same
formats as the reference blueprint. Nothing more, nothing less: a
missing file means the pack is incomplete; a seventh file means you
invented a format.

| # | File | Format | Audience |
|---|------|--------|----------|
| 1 | `plan-{slug}-final.png` | PNG, tourist map + day/cost panel | traveller |
| 2 | `map-{slug}-route-only.png` | PNG, route only, no dates/costs | driver / company |
| 3 | `weather_route_{start}_to_{end}.pdf` | PDF, 1 forecast page per day | traveller |
| 4 | `司机行程单-Driver-Schedule-{date_suffix}.xlsx` | XLSX, 1 sheet | driver |
| 5 | `游客手册-{date_suffix}.xlsx` | XLSX, 8 sheets | traveller |
| 6 | `行程中英对照-{date_suffix}.xlsx` | XLSX, 1 sheet CN/EN | driver + traveller |

- `{slug}` = `cfg["slug"]` (file-name safe, e.g. `ahun`)
- `{date_suffix}` = `cfg["date_suffix"]` (trip end date as `MMDD`, e.g. `1022`)
- `{start}` `{end}` = `cfg["date_range"]` (`YYYY-MM-DD`)

Generation order (each step is a data edit + rerun, never a manual
redraw):

```
geocode.py --check trip.json          # verify every coordinate
fetch_basemap.py "Country"            # once per country
route.py trip.json                    # OSRM geometry -> routes_geom.json
build_maps.py trip.json               # files 1 + 2
mk_xlsx.py trip.json                  # files 4 + 5 + 6
build_weather_pdf.py trip.json        # file 3 (only after dates are final)
```

## Audience split (non-negotiable)

| Audience | Contains | Never contains |
|---|---|---|
| Traveller (files 1, 3, 5) | everything, notes addressed to them | — |
| Driver / third party (files 2, 4, 6) | route, timing, stops, parking | budget, passenger health/mobility, personal details |

A driver sheet that lists the group's budget or a passenger's mobility
limitation discloses information the traveller chose not to share. The
route-only map gets forwarded to companies — it must not leak dates,
prices, or notes either.

## 1. `plan-{slug}-final.png`

Matplotlib, figure 13.6 × 9.0 in, 200 dpi, `bbox_inches="tight"`,
`pad_inches=0.18`.

- Left axes `[0.035, 0.055, 0.325, 0.855]` — basemap, real road
  geometry, day badges, place labels, legend, scale bar.
- Right axes `[0.405, 0.055, 0.575, 0.855]` — day panel: title,
  subtitle, one row per day (badge, `date → place`, km, note, daily
  cost in local currency + ¥, 住/到家 tag), then a 汇总 block
  (nights, total km, total budget, per-person, tips buffer, vehicle),
  then the OSRM footnote.
- Top-left rounded tag (`cfg["tag"]`, accent colour), top-right footer
  (`cfg["footer"]`).

## 2. `map-{slug}-route-only.png`

Matplotlib, figure 12.6 × 8.6 in, 200 dpi.

- Left axes `[0.055, 0.055, 0.40, 0.885]` — same basemap and route,
  numbered arrival circles only (origin = diamond). **No dates, no
  costs, no daily notes, no legend of money.**
- Right side (figure text): title, subtitle, rule line, `highlights`
  (place + one-line sight), `route_note` (2 lines of route character).

## 3. `weather_route_{start}_to_{end}.pdf`

- One page per travel day, page ≈ 768 × 541 pt (landscape).
- Page = the official forecast chart with a 200 px banner on top:
  line 1 `title | metrics`, line 2 `对照: verdict` (red), line 3
  source line (model + init + timezone conversion + `红线=当天行程`).
- On the chart: black skeleton of the whole route, thick red line for
  that day's leg (red ring instead if the day does not move), red dots
  for that day's stops, black dots for the rest, labels with white
  stroke.
- Verdicts come from pixel sampling against the chart's own legend —
  see `weather.md`. Never from memory, never from a weather-app icon.

## 4. `司机行程单-Driver-Schedule-{date_suffix}.xlsx`

Single sheet `Driver Schedule`:

```
Day | Date | Route | km | Drive | Depart | Arrive | Stops / Parking / Notes
```

- Header: bold white on `#1F4E5F`, 11 pt. Cells wrap, top-aligned.
- Column widths: `8, 10, 34, 8, 10, 10, 10, 70`.
- English only; rest days get `0` km and `-` in Drive/Depart/Arrive.
- `fitToPage` on.
- Content: where to pick up, which road, where to park, how long the
  stop takes, what must be pre-booked, tomorrow's start time.
- **No budget, no passenger personal notes.**

## 5. `游客手册-{date_suffix}.xlsx`

Exactly **8 sheets, in this order** (header row styled bold white on
`#1F4E5F` 12 pt, wrap/top; sheet title in A1 bold 14 pt):

| # | Sheet | Source | Columns |
|---|-------|--------|---------|
| 1 | `封面` | `guest.cover_rows` | 项目 / 内容 |
| 2 | `行程总览` | derived from `days` | 日 / 日期 / 路线 / km / 车时 / 出发 / 住 |
| 3 | `每日行程` | derived from `days` | 天 / 中文 / ENGLISH |
| 4 | `酒店` | `guest.hotels` | 晚 / 候选 / 档 / 房型要求 / 备注 |
| 5 | `费用` | `guest.costs` | 项目 / 本币 / 约人民币 / 说明 |
| 6 | *activity sheet* | `guest.activity` | 项 / 内容 |
| 7 | `天气打包` | `guest.weather_pack` | 日 / 降水 / 最高温 / 穿带 |
| 8 | `待办` | `guest.todo` | 何时 / 事项 / 状态 |

- Column widths follow the blueprint: 封面 none, 总览 `6,10,26,8,10,24,10`,
  每日 `12,70,70`, 酒店 `20,55,8,40,45`, 费用 `22,16,14,60`,
  activity `12,90`, 天气 `10,26,22,45`, 待办 `12,70,10`.
- Sheet 6 keeps the blueprint name `Safari` when the activity is a
  safari; otherwise name it after the activity (`guest.activity.sheet`).
- 每日行程 cells are one paragraph (items joined with `；`/`; `), not
  bullet lists — the blueprint's format.
- 待办 items are prefixed with `□` so the sheet is checkable.
- Cover always carries: route, total driving (with the OSRM note),
  headline activity, weather conclusion, exchange rate + as-of date.

## 6. `行程中英对照-{date_suffix}.xlsx`

Single sheet (default `指令`), exactly two columns:

```
中文指令 | English
```

- Header bold white on `#1F4E5F`, widths `55 / 60`, wrap/top.
- One row per day instruction (pickup time, transfers, standby days),
  then standing rules (evening warning report, red-alert hold rule).
- Written as commands the driver executes, not prose.

## Version discipline

- Once a pack is accepted, copy the whole `out/` to a dated folder
  (`out_1108_final/`) before regenerating. Overwriting an approved pack
  destroys the record of what was agreed.
- Keep `trip.json`, `routes_geom.json` and the scripts: a route change
  is a data edit plus a rerun. The scripts are part of the deliverable.
- Produce the PDF (file 3) last, after the user confirms the dates —
  forecast charts go stale and a polished PDF invites the user to stop
  checking.
