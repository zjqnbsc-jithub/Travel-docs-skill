# Reference blueprint (anonymized)

The reference pack this skill reproduces came from a real 6-day trip in
Sri Lanka. Personal information and specific location details have been
removed from this file: no home address, no exact coordinates, no
accommodation names, no dates. What remains is the *structure* — route
shape, document contents, numbers that illustrate format.

## The trip (structure only)

- **Shape**: 6 days / 5 nights, one-way loop, no backtracking. Start
  from a private address in the capital region → inland **national
  park** (1 night) → **beach town** (2 nights) → **largest city**
  (2 nights) → back to start.
- **Character**: expressway + southern coast, no mountain roads. One
  dawn activity (park entry at 06:00, ~4 h, seen entirely from the
  vehicle), everything else rest-oriented — deliberately built for a
  party that does not climb, does not walk far, and dislikes being
  rushed.
- **Party**: 3 adults, chartered van + driver (fuel and tolls
  included), triple rooms with extra bed and 3 breakfasts.
- **Distance**: legs of 151 / 168 / 99 / 21 km = **439 km total**,
  drive times from OSRM (`2h47 / 2h26 / 1h31 / 0h25`, ≈ 7 h 09 total).
  Two days have no driving at all (standby/rest days).
- **Currency**: local rupees; budget presented as local-currency total
  + ¥ conversion at a stated rate with an as-of date.

## The pack it produced (6 files)

```
out/
├── plan-{slug}-final.png                     tourist map + day/cost panel
├── map-{slug}-route-only.png                 route only, no dates/costs
├── weather_route_{start}_to_{end}.pdf        6 pages, one per day
├── 司机行程单-Driver-Schedule-{MMDD}.xlsx     1 sheet, 8 columns, EN
├── 游客手册-{MMDD}.xlsx                      8 sheets, bilingual
└── 行程中英对照-{MMDD}.xlsx                  1 sheet, 中文指令 | English
```

### What each file contained

1. **Tourist map** — left: coastline basemap with dashed district
   boundaries, sea labels, real road geometry with white halo and
   direction arrows; origin diamond; day-coloured badges (blue→orange
   ramp); the two-night stay drawn as a single pill `D2/D3 + 2 晚`;
   legend (起/终, 住宿地, 连住多晚, 参观点, 途经城镇) and a 100 km
   scale bar. Right: title, date range, one row per day
   (`date → place`, km, note, daily cost + ¥), 汇总 block
   (nights / total km / total budget / per-person / tips buffer /
   vehicle), OSRM footnote. Top-left tag: `新定版行程（南线）`.
2. **Route-only map** — same basemap and route, arrival numbers only,
   right side = three highlight lines (one per stop) + a 2-line route
   character note. No date, no price, no note about the passengers.
3. **Weather PDF** — 6 landscape pages, one per travel day. Each page:
   the official forecast chart with a banner (`day+route | 左降水mm
   右最高温C`, red `对照:` verdict, grey source line with model +
   init time + timezone note), black route skeleton, that day's leg in
   thick red, stops as red/black dots with white-stroked labels. All
   verdicts (e.g. "全窗最干", "深蓝5-10") came from pixel sampling
   against the chart's legend; coastal dots were nudged inland after a
   zoom-crop check.
4. **Driver schedule** — one sheet, English:
   `Day | Date | Route | km | Drive | Depart | Arrive | Stops / Parking /
   Notes`, rest days as `0 / - / - / -`, notes covering parking, gate
   tickets in cash, pre-booked vehicle, tomorrow's 05:15 start, and a
   standing "report warnings 19:00 daily" rule.
5. **Guest handbook** — 8 sheets: 封面 (route, total driving, headline
   activity, weather conclusion, exchange rate) · 行程总览 (7 rows) ·
   每日行程 (CN paragraph + EN paragraph per day) · 酒店 (candidates
   per stop with tier + triple-room booking note) · 费用 (line items →
   total → per-person) · Safari (activity pricing, cash formula) ·
   天气打包 (per-day precip band + what to pack) · 待办 (dated,
   `□`-checkable, ordered by urgency).
6. **Bilingual commands** — one sheet, 7 rows: one instruction per day
   (pickup time, transfers, standby days) + one standing safety rule.

## What made the pack hold together

- **Everything derived from one data file.** Day badges, panel rows,
  driver rows and handbook overview all read the same `days` list — a
  date change never desynchronises the documents.
- **Real geometry.** Every km came from OSRM, not straight-line
  estimates; the map route is the same geometry the driver sheet's
  distances come from.
- **Audience split enforced.** The three traveller-facing files carry
  budget and notes; the three driver-facing files carry route and
  timing only.
- **Weather as evidence.** Verdicts cite sampled colour bands, and the
  banner states model + init time, so a stale chart is visible.
- **Scripts kept.** The generating scripts shipped with the pack; a
  later one-day shift was a data edit plus a rerun, not a redraw.
