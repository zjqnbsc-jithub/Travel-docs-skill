# Weather — route on official forecast charts, then one PDF

Use when the trip dates fall inside a published forecast window. The
overlay is a verification loop, not decoration: it forces you to read
the colour *under each stop* instead of summarising a chart from
memory. The output is deliverable #3, `weather_route_{start}_to_{end}.pdf`
— one page per travel day.

## Sources

1. Prefer the destination Met service's NWP charts (national Met
   service, ECMWF open charts, JMA, NWS — 24 h rainfall and max
   temperature pages are the usual pair). Download the official PDF
   yourself; never reuse a generic weather-app icon for a go/no-go call
   (packing advice only).
2. Record for every chart: model name, init time, valid window,
   timezone conversion. A title like `For 24 hours ending at 03UTC
   18 OCT` does NOT mean local midnight on the 18th — convert to the
   destination timezone first (e.g. UTC+5:30 → effectively the previous
   day's daytime). Getting this off by one invalidates every verdict.
3. Render each chart page to PNG (`pymupdf`, ~150 dpi) into
   `cfg["weather"]["src_dir"]` (e.g. `forecast_png/p04.png`). Keep the
   original PDF untouched.

## Procedure

1. **Geocode every stop first** (`geocode.py --check trip.json`) — the
   overlay needs lat/lon, not names.
2. **Map lat/lon to chart pixels** with a *visual* calibration:
   - Start from the chart panel's pixel bbox and lat/lon extent
     (`weather.panel`: `bbox_px [X0,X1,Y0,Y1]`, `lat_top/lat_bot`,
     `lon_l/lon_r`), linear-map each stop.
   - Then open a zoomed crop around every coastal or border stop and
     confirm the dot sits on land. Model land–sea masks are coarse: a
     coastal dot can sample ocean one pixel away (a ~70 px offset was
     seen in practice).
   - Nudge coastal stops inland until the centre pixel matches adjacent
     land colour. Record the final pixel in `weather.xy_override`
     (e.g. `"coast": [325, 1272]`); reuse it for every page.
3. **Sample the colour programmatically**: average a small patch, drop
   black district borders and white background, match remaining RGB to
   legend swatches sampled from the same image. Report centre +
   neighbourhood range (`yellow 10-15, edge pink 30-50`). Single-pixel
   reads on a gradient lie; gradients of 10–20 km are normal.
4. **Write each day's `verdict` from the sampled colours only**
   (e.g. `深蓝<10最干`, `黄10-15 上午走`), plus the action (morning
   transfer, stay put). If the dot sits on a colour boundary, say so
   and give the range.
5. **Annotate a copy per day** (`build_weather_pdf.py` does this):
   200 px banner on top with `title | metrics`, `对照: verdict` in red,
   source line in grey; black skeleton of the whole route; that day's
   leg as a thick red line (red ring if the day does not move); red
   dots for the day's stops, black for the rest; labels with white
   stroke. Never overwrite a source PNG.
6. **Bundle last**: one PDF page per day, page ≈ 768 × 541 pt
   (annotated PNG resized to width 1067 px, `resolution=100`). A date
   shift is a data edit plus a rerun; bundle one PDF per scenario
   (original dates one PDF, shifted dates another). No polished PDF
   before the user confirms the dates are final.

## Legibility ladder — when no small-area chart exists for the destination

Prefer a chart that covers the destination's small area (city /
province / region Met service product). First record what products
actually exist for the destination and dates: the absence of a
small-area chart is a fact to report, not a gap to paper over. In the
reference case (Taihu loop), the only official chart covering all six
days was the national 24–168 h precipitation chart — no provincial
7-day chart existed — and the destination occupied ~20 px on it.

When only a large-area chart is available and the destination is not
readably on it, climb this ladder instead of shipping a blurred crop
or guessing a colour:

| Rung | Base | Use when | Provenance required |
|---|---|---|---|
| 1 | The official chart as-is | destination readable (≳ 40 px across) | chart itself |
| 2 | **Small-area regional excerpt** | a crop around the destination still resolves coastlines, labels and legend (crop + 4× NEAREST is acceptable while it stays resolvable) | banner: `区域节选` + original chart URL/init |
| 3 | **Location base with officially-sampled fill** | even the crop is mush (destination ~20 px on a national chart) | banner: `定位底 官方采样` + full source chain in `weather._note` |

Rung 3 in practice (from the reference case):

- **Base** = a sharp vector basemap of the trip region (the same
  Natural Earth data as the route maps, extent e.g.
  `118.8–122.2E / 30.2–32.2N`, 1600 × 1000), sea/land from that data,
  destination and reference cities labelled.
- **Fill** = the RGB sampled from the **official** large-area chart at
  the destination (observed: white `#FFFFFF` = 0 mm, light green
  `#A6EA90` = 0–10 mm). Take swatch values from the chart's own
  legend — never invent colours.
- **Legend** on the base = the official legend swatches plus a line
  stating how the fill was obtained (`色由{官方图名}在{目的地}上采样移植`).
- **Banner** still carries model + init + timezone conversion +
  `红线=当天行程`; `weather._note` keeps the original chart URL,
  retrieval date, init time and sampling method (centre + neighbourhood
  patch, near-black borders and white background excluded).
- **Verdicts are unchanged by the ladder** — they are sampled the same
  way at every rung; only the base changes. If you cannot state the
  source chain in one sentence, you have gone too far down the ladder.

Never: upscale a 20 px region with bilinear/NEAREST and call the
blurry result a chart; never draw fill colours from memory or from a
weather-app icon.

## Failure modes seen in practice

| What happened | Fix |
|---|---|
| Day label off by one (UTC vs local) | write the conversion in the banner source line |
| Coastal dot samples ocean | zoom-crop check, nudge inland, use adjacent land value, say so |
| Single-pixel read overstates a blob | centre + 20 px neighbourhood range |
| Black admin borders match dark legend swatches | exclude near-black pixels before matching |
| Verdict text disagrees with dot colour | re-sample after any coordinate change; never edit text without re-reading |
| Destination only a few pixels on the only available chart | climb the legibility ladder; never upscale mush |
| Rung-3 fill not traceable to a sampled official chart | you went too far; restate the source chain or stop |

## Config shape

```jsonc
"weather": {
  "src_dir": "forecast_png",
  "banner": { "metrics": "左降水mm 右最高温C", "source": "model+init+tz 红线=当天行程" },
  "cities": { "start": "起点", ... },        // labels on the chart
  "order":  ["start", "park", ...],          // skeleton order
  "label_off": { "start": [-118, -12], ... },
  "panel":  { "bbox_px": [170,950,150,1420], "lat_top": 9.85, "lat_bot": 5.85,
              "lon_l": 79.65, "lon_r": 81.95 },
  "xy_override": { "coast": [325, 1272] },
  "days": [ { "date": "11-03", "title": "...", "page": "p04.png",
              "seg": ["start","park"], "verdict": "..." }, ... ]
}
```

`seg` is the day's leg: `["park","coast"]` draws a red line,
`["coast","coast"]` (rest day) draws a red ring instead.
