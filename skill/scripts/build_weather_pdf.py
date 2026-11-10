#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Annotate official forecast charts with the route and bundle one PDF.

Outputs (into the out_dir next to trip.json):
    weather_annotated/{date}_{page}.png    one annotated copy per travel day
    weather_route_{start}_to_{end}.pdf    one page per day (the deliverable)

Usage:
    python build_weather_pdf.py path/to/trip.json

The "weather" object of trip.json (see references/weather.md):

    "weather": {
      "src_dir": "forecast_png",          // official charts, p04.png ...
      "banner": {"metrics": "左降水mm 右最高温C",
                 "source": "ECMWF 13OCT起报 ending对应前一日白天 红线=当天行程"},
      "cities": {"start": "起点城市", "park": "园区"},   // labels on the map
      "order": ["start", "park", "coast", "capital"],    // route skeleton
      "label_off": {"start": [-118, -12], ...},
      "panel": {"bbox_px": [170, 950, 150, 1420],
                "lat_top": 9.85, "lat_bot": 5.85,
                "lon_l": 79.65, "lon_r": 81.95},
      "xy_override": {"coast": [325, 1272]},   // coastal nudge, see weather.md
      "days": [{"date": "10-17", "title": "10-17 起点-园区",
                "page": "p04.png", "seg": ["start", "park"],
                "verdict": "黄橘15-20 上午走"}, ...]
    }

Never read a forecast colour from memory: sample the pixel under each
stop against the chart's own legend, and write the verdict from that.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]
BANNER = 200  # px strip added on top of every chart


def font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def load_cfg(path):
    cfg = json.load(open(path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(path))
    out = os.path.join(base, cfg.get("out_dir", "out"))
    os.makedirs(out, exist_ok=True)
    return cfg, base, out


def annotator(cfg, base):
    w = cfg["weather"]
    panel = w["panel"]
    X0, X1, Y0, Y1 = panel["bbox_px"]
    lat_top, lat_bot = panel["lat_top"], panel["lat_bot"]
    lon_l, lon_r = panel["lon_l"], panel["lon_r"]
    cities = w["cities"]
    order = w["order"]
    off = w.get("label_off", {})
    override = w.get("xy_override", {})

    def xy(lon, lat):
        return (int(X0 + (lon - lon_l) / (lon_r - lon_l) * (X1 - X0)),
                int(Y0 + (lat_top - lat) / (lat_top - lat_bot) * (Y1 - Y0)))

    # pixel table (pre-nudge), then apply documented overrides
    pts = {}
    for k in order:
        p = cfg["places"][k]
        pts[k] = list(override.get(k) or xy(p["lon"], p["lat"]))

    f_big, f_sub, f = font(32), font(29), font(28)
    banner = w.get("banner", {})
    metrics = banner.get("metrics", "")
    source = banner.get("source", "")
    src_dir = os.path.join(base, w["src_dir"])
    ann_dir = os.path.join(cfg.get("out_dir", "out"), "weather_annotated")
    ann_dir = os.path.join(base, ann_dir) if not os.path.isabs(ann_dir) \
        else ann_dir
    os.makedirs(ann_dir, exist_ok=True)

    def annotate(day):
        base_img = Image.open(
            os.path.join(src_dir, day["page"])).convert("RGB")
        W, H = base_img.size
        im = Image.new("RGB", (W, H + BANNER), "white")
        im.paste(base_img, (0, BANNER))
        d = ImageDraw.Draw(im)

        title = day["title"] + (f" | {metrics}" if metrics else "")
        d.text((30, 10), title, fill=(0, 60, 60), font=f_big)
        if day.get("verdict"):
            d.text((30, 62), "对照: " + day["verdict"], fill=(180, 0, 0),
                   font=f_sub)
        if source:
            d.text((30, 115), source, fill=(80, 80, 80), font=f_sub)

        p2 = {k: (x, y + BANNER) for k, (x, y) in pts.items()}
        for i in range(len(order) - 1):
            d.line([p2[order[i]], p2[order[i + 1]]], fill=(0, 0, 0, 160),
                   width=2)
        a, b = p2[day["seg"][0]], p2[day["seg"][1]]
        if day["seg"][0] == day["seg"][1]:
            d.ellipse([a[0] - 24, a[1] - 24, a[0] + 24, a[1] + 24],
                      outline=(255, 0, 0), width=6)
        else:
            d.line([a, b], fill=(255, 0, 0), width=6)
        for k in order:
            x, y = p2[k]
            today = k in day["seg"]
            r = 13 if today else 9
            d.ellipse([x - r, y - r, x + r, y + r],
                      fill=(255, 0, 0) if today else (0, 0, 0),
                      outline="white", width=3)
            dx, dy = off.get(k, (18, -10))
            d.text((x + dx, y + dy), cities.get(k, k), fill="black", font=f,
                   stroke_width=4, stroke_fill="white")
        dst = os.path.join(ann_dir, f"{day['date']}_{day['page']}")
        im.save(dst)
        return dst

    def bundle(annotated, pdf_path):
        # one page per day; page ≈ 768 x 541 pt (matches the blueprint)
        ims = []
        for p in annotated:
            im = Image.open(p).convert("RGB")
            w_px = 1067
            im = im.resize((w_px, round(im.size[1] * w_px / im.size[0])),
                           Image.LANCZOS)
            ims.append(im)
        ims[0].save(pdf_path, save_all=True, append_images=ims[1:],
                    resolution=100)
        return pdf_path

    return annotate, bundle, ann_dir


def main(path):
    cfg, base, out = load_cfg(path)
    if "weather" not in cfg:
        sys.exit("fatal: trip.json has no 'weather' object")
    w = cfg["weather"]
    start, end = cfg["date_range"]
    annotate, bundle, ann_dir = annotator(cfg, base)
    annotated = [annotate(d) for d in w["days"]]
    print(f"annotated {len(annotated)} chart(s) -> {ann_dir}")
    pdf = os.path.join(out, f"weather_route_{start}_to_{end}.pdf")
    bundle(annotated, pdf)
    print("saved", pdf)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
