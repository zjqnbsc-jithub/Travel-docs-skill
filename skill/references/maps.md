# Maps — cartography spec

Both PNG maps come from one `trip.json` and one `routes_geom.json`
(produced by `route.py`). The two maps share the basemap, the projection
and the marker positions; only the panel and the amount of information
differ.

## Data contract

```jsonc
"places": {
  "start": { "lon": 0.0, "lat": 0.0, "name": "起点", "name_en": "Start",
             "kind": "origin",      // origin | overnight | visit | waypoint
             "label": [-0.07, -0.16, "right", "top"],  // dx, dy, ha[, va]
             "offset": [0, 0] },    // optional: nudge the badge, leader line back
  ...
},
"legs":    { "S1": ["start", "park"], ... },   // road segments
"leg_order": ["S1", "S2", ...],               // drawing order
"days":    [ { "day": "D1", "stay": "park", "km": 151, ... }, ... ],
"bounds":  null,               // null = auto (places+route, 12% pad)
"basemap": { "country": "basemap/country.geojson",
             "admin1":  "basemap/admin1.geojson",
             "ref_places": [ { "lon", "lat", "name" } ],
             "sea_labels": [ { "lon", "lat", "name" } ],
             "legend_pos": null }   // [lon, lat] or null = top-left
```

Rules:

- **Never hardcode coordinates.** Every lon/lat lives in `trip.json`
  and must come from geocoding (`geocode.py --check trip.json`). A
  place name shared by two districts is the classic failure.
- Day badges are derived from `days[].stay` — never drawn by hand.
  Multi-night stays automatically become one pill (`D2/D3` + `N 晚`)
  instead of overlapping circles.
- `label` offsets are in degrees of lon/lat, relative to the *badge*
  position (after `offset`). The name and its box move as one unit
  anchored by a leader line — never place name and date as separate
  text objects; independent offsets drift apart and the date ends up
  labelling the wrong place.

## Basemap

```
python fetch_basemap.py "Country English Name" [--out basemap] [--res 50m]
```

Downloads Natural Earth admin-0 (country outline) and admin-1 (dashed
first-level boundaries) filtered to one country. Store both under
`basemap/` next to `trip.json` and point `cfg["basemap"]` at them.

Without a basemap the script still runs but warns: a route on a bare
sea canvas reads as blank. Never ship that as a final map.

## Projection

Equirectangular scaled by `cos(mean latitude of bounds)` — true at
region scale for the trip area. `ax.set_aspect(KX)` keeps shapes honest.

Auto-bounds = bounding box of all places + route geometry, padded 12%.
Set `bounds: [lon0, lat0, lon1, lat1]` explicitly when the whole country
should be visible regardless of route extent.

## Route line

- Real OSRM geometry from `routes_geom.json` (simplified ~1 pt / 300 m).
  **Straight lines between stops are a fallback only** — they mislead by
  40%+ on winding roads. If `route.py` has not been run, the script
  warns and draws straight lines; do not present that as final.
- White halo (`lw 6`, alpha .85) under the accent line (`lw 2.5`
  tourist / `2.6` route-only), round caps.
- Direction arrows every ~0.62 projected units along the polyline, so
  the reading order of the loop is obvious.

## Markers

| kind | glyph | where |
|------|-------|-------|
| `origin` | diamond `#7a1f2b`, label in accent-free bold | both maps |
| overnight (single night) | filled circle, day colour ramp, day id inside | both maps |
| overnight (multi nights) | rounded pill `D2/D3` + grey `N 晚` tag below | both maps |
| `visit` | white hollow circle with accent ring + accent dot | tourist only |
| `waypoint` | small grey dot, muted label | tourist only |
| reference city (basemap) | tiny grey dot + grey label | both maps |

Day colour ramp: `["#2b3a8f", "#6a3d9a", "#b12a90", "#e2542c"]` via
`day_color(i, n_stops)` — early days blue, late days orange.

Badge numbers differ by audience: the tourist map shows the day id
(`D1`), the route-only map shows the arrival number (`1`, `2/3`).
Same circle, same position — only the text differs.

When two badges overlap (cities 20 km apart), set `offset` on the
place: the badge moves, a dashed leader line points back to the true
position. Never delete a stop to resolve overlap.

## Tourist panel (right side of file 1)

- Rows: `★` origin row, then one row per day.
- Per row: badge, `date → place`, `km ｜ note`, right side daily cost
  in local currency + `≈ ¥` at the trip's exchange rate, 住 / 到家 tag.
- 汇总 block: 行程天数, 车程合计, 总预算, 人均, 含小费弹性 (×1.22),
  交通方式 — all derived from `days` unless `summary_rows` overrides.
- Footnote: "里程与路线取自真实路网（OSRM）。"
- With more than 8 rows, `row_h` shrinks automatically; verify no
  overlap in the rendered PNG before shipping.

## Route-only right side (file 2)

Title (18 pt), subtitle (11 pt), rule line, then `highlights` rows
(accent place + one-line sight) and a 2-line `route_note`. Nothing
else: no dates, no km, no money.

## Legend & scale

- Legend (tourist only) lists only what is present: 起/终, 当天住宿地,
  连住多晚 (if any), 拍照/参观点 (if any), 途经城镇 (if any). Default
  position top-left; override with `basemap.legend_pos` when it covers
  land.
- Scale bar bottom-left: nice round km ≈ 12% of map width
  (10/20/25/50/100/200/250/500/1000/2000).

## Verification checklist

Read the finished PNG as someone who has never seen the itinerary:

1. Does every number sit next to the thing it belongs to?
2. Does the badge sit on the correct stop after any `offset`?
3. Do labels collide with each other, the legend, or the panel edge?
4. Is the route continuous (no gaps at leg boundaries)?
5. Route-only version: any date, price, or personal note visible? If
   yes, fix before it gets forwarded.
