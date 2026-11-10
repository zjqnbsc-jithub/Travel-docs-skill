---
name: Travel Docs
description: Plan a multi-day trip anywhere in the world - by self-drive, rail, ferry, chartered car or mixed transport, free independent travel or organized - and produce a fixed pack of 6 deliverables - tourist plan map, route-only map, weather-comparison PDF, driver schedule xlsx, guest handbook xlsx, and bilingual command sheet. Use when the user asks to plan a trip, itinerary, route, or multi-day travel plan, especially when they want final documents (maps, PDF, Excel) in a consistent format. The weather step climbs a three-rung legibility ladder (destination chart - small-area regional excerpt - location base with officially-sampled fill) when no small-area chart exists for the destination.
---

# Travel Docs

Plan a multi-day trip that holds up on the ground — anywhere in the
world, by self-drive, rail, ferry, chartered car, or a mix (free
independent travel and organized tours alike) — then emit
**exactly six deliverables** in a fixed format — two maps, one
weather-comparison PDF, three spreadsheets. The format is a contract:
same count, same file names, same sheet structure every time. See
`references/deliverables.md` for the exact spec and
`references/example.md` for the anonymized reference pack.

## Non-negotiables

1. **Never state coordinates from memory.** Geocode every stop and
   reverse-check it (`geocode.py --check trip.json`). A place name
   shared by two districts is the classic failure.
2. **Never estimate road distance by hand.** Straight-line plus a
   fudge factor is wrong by 40%+. Run `route.py` (OSRM) before any map
   or document quotes a kilometre.
3. **Never invent prices.** Search for real figures, label estimates as
   estimates, and state the exchange rate with its as-of date.
4. **Ask about mobility before routing.** Stairs, hiking, walking
   tolerance and heat change which stops are viable. Constraints
   discovered late invalidate earlier work.
5. **Never read a forecast colour from memory.** Sample the pixel under
   each stop against the chart's own legend, and write the verdict from
   that. See `references/weather.md`.
6. **Never ship personal data.** Home addresses, exact home
   coordinates, passenger health/mobility details and private booking
   references stay in working files only. They must never appear in
   this skill, its references, or any driver-facing document — the
   driver pack (map 2, driver sheet, bilingual sheet) carries route and
   timing only, never budget or personal notes. Examples in
   `references/` are anonymized: no real coordinates, no specific
   private locations.
7. **Never ship an unreadable forecast chart.** If the destination is
   only a few pixels wide on the only chart available, do not upscale
   it and do not guess the colour: climb the legibility ladder in
   `references/weather.md` — destination-readable chart → small-area
   regional excerpt → location base with officially-sampled fill —
   and keep the source chain stated at every rung.

## Workflow

### Step 0 — Frame the trip

Collect, or infer then confirm: start/end point (same or different),
dates (or month + trip length), party size and room configuration,
budget band, transport mode (chartered car / self-drive / rail), and
**physical constraints** — stairs, hiking, walking tolerance, heat.

### Step 1 — Verify every location

```
python scripts/geocode.py "Place A, Country" "Place B, Country"
python scripts/geocode.py --reverse 48.8566,2.3522
python scripts/geocode.py --check trip.json
```

Compare the returned administrative area against what the user
described. Report mismatches to the user rather than silently
correcting — disagreement means one of you is wrong, and it is cheaper
to find out now.

### Step 2 — Build `trip.json` and fetch real geometry

Copy `scripts/trip.example.json` to `trip.json` and fill it (see the
`_note` fields; every coordinate comes from Step 1). Then:

```
python scripts/fetch_basemap.py "Country English Name"
python scripts/route.py trip.json
```

Check the loop before presenting: total km plausible for the days
available? Any single day over 4 h of driving? Does the route retrace
itself? Would a different order be shorter? Report the total distance
change whenever an earlier version existed.

### Step 3 — Size each day honestly

Assign nights from what the day actually contains, not to fill a
calendar. Estimate queues, transfers and meals. If the trip is short,
cut days — say plainly that a stop is not worth the extra night rather
than inventing filler.

### Step 4 — Budget

Line items → total → per-person, in local currency and ¥ at a stated
rate. Include transport (fuel/tolls?), accommodation with room
configuration, meals noting breakfast, tickets, tips/contingency. Every
figure either sourced or labelled an estimate.

### Step 5 — Produce the pack

```
python scripts/build_maps.py trip.json     # files 1 + 2
python scripts/mk_xlsx.py trip.json        # files 4 + 5 + 6
```

Specs: `references/deliverables.md` (structure), `references/maps.md`
(cartography). Verify against the checklist at the end of
`maps.md` — read each PNG as someone who has never seen the
itinerary, and confirm the route-only map leaks no dates, prices or
personal notes.

### Step 6 — Weather overlay (when dates are inside a forecast window)

Fetch the official NWP charts yourself, render to PNG, calibrate
pixels, sample colours, then:

```
python scripts/build_weather_pdf.py trip.json   # file 3, last
```

Full method: `references/weather.md`. Produce the PDF only after the
user confirms the dates are final — bundle one PDF per scenario if
comparing date shifts.

**Chart legibility (no small-area chart for the destination?):** look
for a chart covering the destination's region first (destination or
provincial/region chart). If the only official chart covering the
dates is a large-area one — a national chart, as in the reference
case — and the destination reads as a few pixels on it, do not ship
the blurred crop and do not guess: climb the three-rung ladder in
`references/weather.md`:

1. the chart as-is, when the destination is readable;
2. a **small-area regional excerpt** (crop of the large chart around
   the destination, upscaled only while coastlines/legend stay
   resolvable);
3. a **location base with officially-sampled fill** — a sharp
   vector basemap of the trip region, land filled with the colour
   actually sampled from the official chart at the destination,
   official legend shown, provenance line kept in the banner.

The verdicts are sampled the same way at every rung; only the base
changes. If you cannot state the source chain in one sentence, you
have gone too far.

## Presenting the plan

Lead with the route and total distance, then the day-by-day table,
then budget; flag constraints and open decisions at the end. State
uncertainties plainly — "I could not confirm whether a permit is needed"
beats a confident guess. When correcting earlier work, say so directly
and give the corrected figure.

Once a pack is accepted, copy `out/` to a dated folder before any
regeneration; see `references/deliverables.md` for version discipline.

## Common pitfalls

| Pitfall | Consequence |
|---|---|
| Coordinates from memory | entire route in the wrong part of the country |
| Hand-estimated distances | days sized wrongly, drive times 40% off |
| One document for everyone | driver sees budget and medical notes |
| Invented or stale prices | budget unusable for booking |
| Ignoring mobility limits | planned stops cannot be completed |
| Weather verdict from a weather app | go/no-go call with no evidence |
| Destination unreadable on the only available chart | upscaled mush → guessed verdict; climb the legibility ladder |
| Badge/label drift on the map | date labels the wrong town |
| Overwriting an approved pack | no record of what was agreed |

## Scripts

- `scripts/geocode.py` — forward/reverse geocoding via Nominatim, plus
  `--check` for a whole trip.json
- `scripts/route.py` — road distance, duration and geometry via OSRM
- `scripts/fetch_basemap.py` — Natural Earth country + admin-1 GeoJSON
- `scripts/build_maps.py` — both PNG maps from one trip.json
- `scripts/mk_xlsx.py` — all three spreadsheets from one trip.json
- `scripts/build_weather_pdf.py` — annotate forecast charts, bundle PDF
- `scripts/trip.example.json` — annotated config template

## References

- `references/deliverables.md` — the 6-file contract: names, sheets,
  columns, styles, audience split
- `references/maps.md` — basemap, projection, badges, panels, checklist
- `references/weather.md` — official-chart sourcing, pixel calibration,
  verdict writing, PDF assembly
- `references/example.md` — anonymized reference pack (structure only)

Requires: Python 3 with `matplotlib`, `openpyxl`, `pillow`; network
access to OSRM, Nominatim and the Natural Earth mirror.
