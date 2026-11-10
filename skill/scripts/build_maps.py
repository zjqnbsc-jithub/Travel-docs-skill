#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the two itinerary maps from trip.json.

Outputs (into the out_dir next to trip.json):
    plan-{slug}-final.png        traveller version: map + day/cost panel
    map-{slug}-route-only.png    driver/company version: no dates, no costs

Usage:
    python build_maps.py path/to/trip.json

Data contract (see references/maps.md):
  - places: keyed lon/lat + kind (origin|overnight|visit|waypoint)
  - days:   one entry per travel day; "stay" names the overnight place
  - legs:   road segments; real geometry comes from routes_geom.json
            (run route.py first). Straight lines are the fallback.
  - basemap: country.geojson / admin1.geojson from fetch_basemap.py.

Never hardcode coordinates: every lon/lat comes from trip.json, which
must be geocoded first (geocode.py --check trip.json).
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.patches import FancyBboxPatch, Polygon as MplPolygon
import matplotlib.patheffects as pe

plt.rcParams["font.family"] = ["Microsoft YaHei", "Noto Sans CJK SC",
                               "PingFang SC", "Hiragino Sans GB",
                               "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.facecolor"] = "white"

# ---------------------------------------------------------------- 配色
LAND, LAND_EDGE = "#f5efdd", "#9a8f6b"
SEA, DIST, SEA_TXT = "#d7e9f4", "#ded2b4", "#6f9dbb"
ROUTE, HOME, TXT, MUTED = "#e2542c", "#7a1f2b", "#22303c", "#6b7a88"

HALO = [pe.withStroke(linewidth=2.8, foreground="white")]
RAMP = mcolors.LinearSegmentedColormap.from_list(
    "dayramp", ["#2b3a8f", "#6a3d9a", "#b12a90", "#e2542c"])


# ---------------------------------------------------------------- 工具
def day_color(i, n):
    return RAMP(0.08 + 0.62 * (i / max(n - 2, 1)))


def lab(ax, x, y, s, **kw):
    kw.setdefault("path_effects", HALO)
    return ax.text(x, y, s, **kw)


def draw_polys(g, ax, polys, **kw):
    for poly in polys:
        for ring in poly:
            ax.add_patch(MplPolygon(g.pts(ring), closed=True, **kw))


def polys_of(geom):
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def load_features(path):
    """GeoJSON FeatureCollection / Feature / bare geometry -> feature list."""
    if not path or not os.path.exists(path):
        return []
    data = json.load(open(path, encoding="utf-8"))
    t = data.get("type")
    if t == "FeatureCollection":
        return data.get("features", [])
    if t == "Feature":
        return [data]
    return [{"properties": {}, "geometry": data}]


class Geo:
    """Projection + bounds for one trip."""

    def __init__(self, cfg, base, routes):
        self.cfg = cfg
        b = cfg.get("bounds")
        if not b:
            pts = [(p["lon"], p["lat"]) for p in cfg["places"].values()]
            for lg in routes.get("legs", {}).values():
                pts.extend(lg.get("geometry", []))
            lons = [p[0] for p in pts]
            lats = [p[1] for p in pts]
            lon0, lon1 = min(lons), max(lons)
            lat0, lat1 = min(lats), max(lats)
            padx = max((lon1 - lon0) * 0.12, 0.15)
            pady = max((lat1 - lat0) * 0.12, 0.15)
            b = [lon0 - padx, lat0 - pady, lon1 + padx, lat1 + pady]
        self.lon0, self.lat0, self.lon1, self.lat1 = b
        self.W = self.lon1 - self.lon0
        self.H = self.lat1 - self.lat0
        self.latm = (self.lat0 + self.lat1) / 2
        self.KX = math.cos(math.radians(self.latm))

        bm = cfg.get("basemap", {})
        self.country = [polys_of(f.get("geometry"))
                        for f in load_features(
                            os.path.join(base, bm["country"]))
                        ] if bm.get("country") else []
        self.admin1 = [polys_of(f.get("geometry"))
                       for f in load_features(
                           os.path.join(base, bm["admin1"]))
                       ] if bm.get("admin1") else []
        self.ref_places = bm.get("ref_places", [])
        self.sea_labels = bm.get("sea_labels", [])
        self.legend_pos = bm.get("legend_pos")

    def proj(self, lon, lat):
        return lon * self.KX, lat

    # 把「点」投影成绘图坐标
    def pts(self, coords):
        return [self.proj(c[0], c[1]) for c in coords]

    def pt(self, lon, lat):
        return self.proj(lon, lat)

    def pt_size(self, w_pt, h_pt, frac_w, frac_h):
        """Convert a size in points to data units for the given axes rect."""
        fig = plt.gcf()
        fi = fig.get_size_inches()
        map_w_pt = frac_w * fi[0] * 72
        map_h_pt = frac_h * fi[1] * 72
        s = min(map_w_pt / (self.W * self.KX), map_h_pt / self.H)
        return w_pt / s, h_pt / s


# ---------------------------------------------------------------- 路线
def route_points(g, cfg, routes, warn=True):
    order = cfg.get("leg_order") or sorted(routes.get("legs", {}))
    legs = routes.get("legs", {})
    if not order or not any(k in legs for k in order):
        if warn:
            print("warning: no routes_geom.json - drawing straight lines "
                  "(run route.py trip.json for real road geometry)")
        seq, seen = [], None
        for d in cfg["days"]:
            for key in (d.get("from"), d.get("stay")):
                if key and key != seen:
                    seq.append(key)
                    seen = key
        seq = [cfg["places"][k] for k in seq]
        return [g.pt(p["lon"], p["lat"]) for p in seq]
    pts = []
    for i, name in enumerate(order):
        if name not in legs:
            continue
        seg = g.pts(legs[name]["geometry"])
        pts.extend(seg if not pts else seg[1:])
    return pts


def draw_route(ax, g, cfg, routes, accent, lw):
    pts = route_points(g, cfg, routes)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color="white", lw=6.0, solid_capstyle="round",
            solid_joinstyle="round", zorder=5, alpha=0.85)
    ax.plot(xs, ys, color=accent, lw=lw, solid_capstyle="round",
            solid_joinstyle="round", zorder=6)

    # 方向箭头：沿折线累计长度等距放置
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.hypot(pts[i][0] - pts[i - 1][0],
                                        pts[i][1] - pts[i - 1][1]))
    total, step, t = cum[-1], 0.62, 0.33
    while t < total - 0.15:
        j = min(range(len(cum)), key=lambda k: abs(cum[k] - t))
        a, b = max(j - 5, 0), min(j + 5, len(pts) - 1)
        if math.hypot(pts[b][0] - pts[a][0], pts[b][1] - pts[a][1]) > 0.012:
            ax.annotate("", xy=pts[b], xytext=pts[a],
                        arrowprops=dict(arrowstyle="-|>", color=accent, lw=2.1,
                                        mutation_scale=19), zorder=7)
        t += step


# ---------------------------------------------------------------- 住宿统计
def stay_map(cfg):
    """place key -> [1-based day numbers staying there]"""
    m = {}
    for i, d in enumerate(cfg["days"], start=1):
        m.setdefault(d["stay"], []).append(i)
    return m


def origin_key(cfg):
    for k, p in cfg["places"].items():
        if p.get("kind") == "origin":
            return k
    return next(iter(cfg["places"]))


# ---------------------------------------------------------------- 底图绘制
def draw_base(ax, g, cfg, variant):
    ax.set_facecolor(SEA)
    for polys in g.country:
        draw_polys(g, ax, polys, facecolor=LAND, edgecolor=LAND_EDGE,
                   lw=1.1, zorder=2)
    for polys in g.admin1:
        draw_polys(g, ax, polys, facecolor="none", edgecolor=DIST, lw=0.55,
                   ls=(0, (3, 2)), zorder=3)
    if not g.country:
        print("warning: no basemap loaded - set cfg[basemap][country] "
              "(fetch_basemap.py) for a proper outline")

    for rp in g.ref_places:
        x, y = g.pt(rp["lon"], rp["lat"])
        ax.scatter([x], [y], s=24, facecolor="#aab4bd", edgecolor="white",
                   lw=1.0, zorder=4)
        lab(ax, x + 0.08, y + 0.06, rp["name"], fontsize=7.8,
            color="#98a3ac", ha="center", va="center", zorder=5,
            clip_on=True)

    for sl in g.sea_labels:
        x, y = g.pt(sl["lon"], sl["lat"])
        ax.text(x, y, sl["name"], fontsize=7.4, color=SEA_TXT,
                style="italic", ha="center", va="center", zorder=4,
                linespacing=1.35, clip_on=True)


# ---------------------------------------------------------------- 主图（游客版）
def draw_map(ax, g, cfg, routes):
    accent = cfg.get("accent", ROUTE)
    stays = stay_map(cfg)
    n_stops = len(cfg["days"]) + 1

    draw_base(ax, g, cfg, "tourist")
    draw_route(ax, g, cfg, routes, accent, lw=2.5)

    # ---- 住宿点标记
    for key, p in cfg["places"].items():
        kind = p.get("kind", "overnight")
        if kind in ("waypoint", "visit"):
            continue
        x, y = g.pt(p["lon"], p["lat"])

        if kind == "origin":
            ax.scatter([x], [y], marker="D", s=200, facecolor=HOME,
                       edgecolor="white", lw=2.2, zorder=11)
            dx, dy, ha, va = _label_of(p, (-0.07, -0.16, "right", "top"))
            ax.text(x + dx, y + dy, p["name"], fontsize=9.0, color=HOME,
                    ha=ha, va=va, fontweight="bold",
                    path_effects=HALO, zorder=13, clip_on=True)
            continue
        if key not in stays:
            continue

        days = stays.get(key, [])
        labels = [cfg["days"][i - 1]["day"] for i in days]
        txt = "/".join(labels)
        col = day_color(days[0], n_stops)
        ox, oy = p.get("offset", [0, 0])
        mx, my = x + ox, y + oy
        if ox or oy:
            ax.plot([x, mx], [y, my], color=MUTED, lw=0.9, ls=(0, (2, 2)),
                    zorder=8)
            ax.scatter([x], [y], s=22, facecolor=MUTED, edgecolor="white",
                       lw=1.0, zorder=9)

        if len(labels) == 1:
            ax.scatter([mx], [my], s=900, facecolor=col, edgecolor="white",
                       lw=2.4, zorder=10)
            fs = 11.0
        else:
            w, h = _pill_wh(g, txt, 0.325, 0.855)
            ax.add_patch(FancyBboxPatch(
                (mx - w / 2, my - h / 2), w, h,
                boxstyle=f"round,pad=0,rounding_size={g.W * 0.04:.4f}",
                facecolor=col, edgecolor="white", lw=2.3, zorder=10))
            fs = 9.8
        ax.text(mx, my + 0.004, txt, fontsize=fs, color="white", ha="center",
                va="center", fontweight="bold", zorder=12, clip_on=True)
        if len(labels) > 1:
            _, h = _pill_wh(g, txt, 0.325, 0.855)
            ax.text(mx, my - h / 2 - g.H * 0.028, f"{len(labels)} 晚",
                    fontsize=7.4, color="white", ha="center", va="center",
                    zorder=15, clip_on=True,
                    bbox=dict(boxstyle="round,pad=0.26,rounding_size=0.3",
                              facecolor=MUTED, edgecolor="none"))

        # 地名白框 + 引线（整体锚定，日期不参与，避免错位）
        dx, dy, ha, va = _label_of(p, (0.30, 0.20, "left", "center"))
        lx, ly = mx + dx, my + dy
        ax.plot([mx, lx], [my, ly], color=TXT, lw=0.9, alpha=0.55, zorder=12,
                solid_capstyle="round")
        ax.text(lx, ly, p["name"], fontsize=10.2, color=TXT, ha=ha, va=va,
                fontweight="bold", zorder=14, clip_on=True,
                bbox=dict(boxstyle="round,pad=0.36,rounding_size=0.14",
                          facecolor="white", edgecolor=TXT,
                          linewidth=0.9, alpha=0.97))

    # ---- 途经城镇（灰色小点，仅游客版）
    for key, p in cfg["places"].items():
        if p.get("kind") != "waypoint":
            continue
        x, y = g.pt(p["lon"], p["lat"])
        ax.scatter([x], [y], s=30, facecolor=MUTED, edgecolor="white",
                   lw=1.1, zorder=8)
        dx, dy, ha, va = _label_of(p, (0.08, 0.12, "center", "center"))
        lab(ax, x + dx, y + dy, p["name"], fontsize=8.2, color=MUTED,
            ha=ha, va=va, zorder=9, clip_on=True)

    # ---- 拍照 / 参观点：橙色空心圈
    for key, p in cfg["places"].items():
        if p.get("kind") != "visit":
            continue
        x, y = g.pt(p["lon"], p["lat"])
        ax.scatter([x], [y], s=110, facecolor="white", edgecolor=accent,
                   lw=2.2, zorder=9)
        ax.scatter([x], [y], s=16, facecolor=accent, zorder=10)
        dx, dy, ha, va = _label_of(p, (0.16, 0.12, "left", "center"))
        lab(ax, x + dx, y + dy, p["name"], fontsize=8.6, color=accent,
            ha=ha, va=va, fontweight="bold", zorder=11, clip_on=True)

    draw_legend(ax, g, cfg, stays, accent)
    draw_scale(ax, g)


def _label_of(p, default):
    lbl = p.get("label")
    if not lbl:
        return default
    dx, dy, ha = lbl[0], lbl[1], lbl[2]
    va = lbl[3] if len(lbl) > 3 else "center"
    return dx, dy, ha, va


def _pill_wh(g, txt, frac_w=0.325, frac_h=0.855):
    """Pill size in data units ≈ fixed point size (15 + 8/char × 31 pt)."""
    return g.pt_size(15 + 8.2 * len(txt), 31.0, frac_w, frac_h)


def draw_legend(ax, g, cfg, stays, accent):
    # pill 样例最宽：整列右移半个 pill 宽，文字统一排在 pill 右侧
    pill_w = _pill_wh(g, "D1/D2", 0.325, 0.855)[0]
    pos = g.legend_pos or (g.lon0, g.lat1 - 0.045 * g.H)
    x0, y0 = pos[0] + 0.02 * g.W + pill_w / 2, pos[1]
    tx = x0 + pill_w / 2 + 0.012 * g.W
    tx_proj = tx * g.KX  # 图例文字 x 在投影前的图面坐标系，需乘横轴比例
    step = g.pt_size(0, 34, 0.325, 0.855)[1]
    entries = []
    ok = origin_key(cfg)
    multi = any(len(v) > 1 for v in stays.values())
    if ok:
        entries.append(("d", HOME, "起 / 终"))
    if stays:
        entries.append(("o", accent, "当天住宿地"))
    if multi:
        entries.append(("p", accent, "连住多晚"))
    if any(p.get("kind") == "visit" for p in cfg["places"].values()):
        entries.append(("hollow", accent, "拍照 / 参观点"))
    if any(p.get("kind") == "waypoint" for p in cfg["places"].values()):
        entries.append(("o", MUTED, "途经城镇"))
    for i, (glyph, col, txt) in enumerate(entries):
        lx, ly = x0, y0 - i * step
        x, y = g.pt(lx, ly)
        if glyph == "p":
            w, h = _pill_wh(g, "D1/D2")
            ax.add_patch(FancyBboxPatch(
                (x - w / 2, y - h / 2), w, h,
                boxstyle=f"round,pad=0,rounding_size={g.W * 0.04:.4f}",
                facecolor=col, edgecolor="white", lw=1.2, zorder=14))
        elif glyph == "d":
            ax.scatter([x], [y], s=62, marker="D", facecolor=col,
                       edgecolor="white", lw=1.2, zorder=14)
        else:
            hollow = glyph == "hollow"
            ax.scatter([x], [y], s=54 if hollow else 46,
                       facecolor="white" if hollow else col,
                       edgecolor=col, lw=1.6, zorder=14)
            if hollow:
                ax.scatter([x], [y], s=10, facecolor=col, zorder=15)
        ax.text(tx_proj, y, txt, fontsize=8.0, color=TXT,
                ha="left", va="center", zorder=14, clip_on=True,
                path_effects=HALO)


def draw_scale(ax, g):
    km_per_deg = 111.32 * g.KX
    width_km = g.W * km_per_deg
    target = width_km * 0.12
    nice = [10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000]
    km = min(nice, key=lambda v: abs(v - target))
    seg = km / km_per_deg
    bx, by = g.lon0 + 0.015 * g.W, g.lat0 + 0.045 * g.H
    x, y = g.pt(bx, by)
    x2, _ = g.pt(bx + seg, by)
    ax.plot([x, x2], [y, y], color=TXT, lw=2.8, zorder=13,
            solid_capstyle="butt")
    for xx in (x, x2):
        ax.plot([xx, xx], [y - g.H * 0.011, y + g.H * 0.011], color=TXT,
                lw=1.5, zorder=13)
    ax.text((x + x2) / 2, y + g.H * 0.02, f"{km} km", fontsize=8.0,
            color=TXT, ha="center", va="bottom", zorder=13, clip_on=True,
            path_effects=HALO)


def finish_axes(ax, g):
    # 扩展 bounds 使数据纵横比与坐标轴一致：set_aspect 只会缩小数据框留白，
    # 等量扩展则是把白边换成地图内容（内容大小不变）。
    rect = ax.get_position()
    fi = plt.gcf().get_size_inches()
    target = (rect.width * fi[0]) / (rect.height * fi[1])
    cur = (g.W * g.KX) / g.H
    if cur < target:  # 太窄：扩经度
        new_w = g.H * target / g.KX
        c = (g.lon0 + g.lon1) / 2
        g.lon0, g.lon1 = c - new_w / 2, c + new_w / 2
        g.W = new_w
    else:  # 太矮：扩纬度
        new_h = g.W * g.KX / target
        c = (g.lat0 + g.lat1) / 2
        g.lat0, g.lat1 = c - new_h / 2, c + new_h / 2
        g.H = new_h
    ax.set_xlim(g.lon0 * g.KX, g.lon1 * g.KX)
    ax.set_ylim(g.lat0, g.lat1)
    ax.set_aspect(g.KX)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


# ---------------------------------------------------------------- 侧栏（游客版）
def draw_panel(ax, g, cfg):
    ax.axis("off")
    days = cfg["days"]
    places = cfg["places"]
    ok = origin_key(cfg)
    fx = cfg.get("fx", {})
    code = fx.get("code", "Rs")
    cny = fx.get("cny", 42)
    party = cfg.get("party", 2)

    rows = [("origin", 0, "起点与终点为同一处", None)]
    for d in days:
        rows.append((d["stay"], d.get("km", 0),
                     d.get("panel_cn") or d.get("note_cn", ""),
                     d.get("cost")))
    n = len(rows)
    n_stops = n

    ax.text(0.0, 1.055, cfg.get("title", ""), fontsize=15.2, color=TXT,
            fontweight="bold", va="top", transform=ax.transAxes)
    ax.text(0.0, 0.988, cfg.get("subtitle", ""), fontsize=9.9, color=MUTED,
            va="top", transform=ax.transAxes)

    top = 0.935
    row_h = 0.083 if n <= 9 else 0.72 / n
    for i, (key, km, note, cost) in enumerate(rows):
        y = top - i * row_h
        col = HOME if i == 0 else day_color(i, n_stops)
        ax.add_patch(FancyBboxPatch(
            (0.005, y - 0.025), 0.060, 0.050,
            boxstyle="round,pad=0.004,rounding_size=0.010",
            transform=ax.transAxes, facecolor=col, edgecolor="none"))
        badge = "★" if i == 0 else days[i - 1]["day"]
        ax.text(0.035, y, badge, fontsize=9.6, color="white", ha="center",
                va="center", fontweight="bold", transform=ax.transAxes)

        if i == 0:
            line1 = f"出发 · {places[ok]['name']}"
        else:
            line1 = f"{days[i - 1].get('date_cn', '')}　→　{places[key]['name']}"
        ax.text(0.088, y + 0.013, line1, fontsize=10.4, color=TXT,
                ha="left", va="center", fontweight="bold",
                transform=ax.transAxes)
        km_txt = "—" if not km else f"{km} km"
        ax.text(0.088, y - 0.024, f"{km_txt}　｜　{note}", fontsize=8.8,
                color=MUTED, ha="left", va="center", transform=ax.transAxes)

        if cost:
            ax.text(1.0, y, f"{code} {cost:,}", fontsize=9.8, color=TXT,
                    ha="right", va="center", fontweight="bold",
                    transform=ax.transAxes)
            ax.text(1.0, y - 0.024, f"≈ ¥{round(cost / cny):,}",
                    fontsize=8.6, color=ROUTE, ha="right", va="center",
                    transform=ax.transAxes)
        elif i == 0:
            ax.text(1.0, y, "起 · 终", fontsize=9.2, color=HOME, ha="right",
                    va="center", fontweight="bold", transform=ax.transAxes)

        if 0 < i < n - 1:
            tag, tcol = "住", ROUTE
        elif i == n - 1:
            end = cfg.get("panel_end_tag")
            if end is None:
                end = "到家" if key == ok else "结束"
            tag, tcol = end, (HOME if end == "到家" else ROUTE)
        else:
            tag = None
        if tag:
            ax.text(1.0, y - 0.049, tag, fontsize=8.6, color=tcol, ha="right",
                    va="center", fontweight="bold", transform=ax.transAxes)
        ax.plot([0.005, 1.0], [y - 0.058, y - 0.058], color="#e6e9ec",
                lw=0.7, transform=ax.transAxes)

    # ---- 汇总
    total_km = sum(d.get("km", 0) for d in days)
    total_cost = sum(d.get("cost") or 0 for d in days)
    nights = sum(1 for d in days if d["stay"] != ok)
    if cfg.get("summary_rows") is not None:
        summary = cfg["summary_rows"]
    else:
        summary = [("行程天数", f"{len(days)} 天 {nights} 晚"),
                   ("车程合计", f"约 {total_km} km")]
        if total_cost:
            summary += [
                ("总预算", f"{code} {total_cost:,}　≈ ¥{round(total_cost / cny):,}"),
                ("人均", f"约 ¥{round(total_cost / cny / party):,} / {party} 人"),
                ("含小费弹性", f"合计约 ¥{round(total_cost / cny * 1.22):,}"),
            ]
        if cfg.get("vehicle"):
            summary.append(("交通方式", cfg["vehicle"]))
    ys = top - n * row_h - 0.025
    ax.text(0.005, ys, "汇总", fontsize=11.4, color=TXT, fontweight="bold",
            va="top", transform=ax.transAxes)
    strong_keys = {"总预算", "人均", "含小费弹性"}
    for j, (k, v) in enumerate(summary):
        yy = ys - 0.045 * (j + 1) - 0.006
        st = k in strong_keys
        ax.text(0.005, yy, k, fontsize=9.3, color=MUTED, va="center",
                transform=ax.transAxes)
        ax.text(0.235, yy, v, fontsize=10.0 if st else 9.3, color=TXT,
                va="center", ha="left", fontweight="bold" if st else "normal",
                transform=ax.transAxes)
    ax.text(0.005, ys - 0.045 * len(summary) - 0.030,
            cfg.get("panel_note", "里程与路线取自真实路网（OSRM）。"),
            fontsize=8.0, color="#9aa5ae", va="center",
            transform=ax.transAxes)


# ---------------------------------------------------------------- 纯路线版
def draw_route_only_map(ax, g, cfg, routes):
    accent = cfg.get("accent", ROUTE)
    stays = stay_map(cfg)
    ok = origin_key(cfg)
    ndays = len(cfg["days"])

    draw_base(ax, g, cfg, "route")
    draw_route(ax, g, cfg, routes, accent, lw=2.6)

    for key, p in cfg["places"].items():
        kind = p.get("kind", "overnight")
        if kind not in ("origin", "overnight"):
            continue
        if kind == "overnight" and key not in stays:
            continue
        x, y = g.pt(p["lon"], p["lat"])
        dx, dy, ha, va = _label_of(p, (0.30, -0.26, "left", "center"))

        if kind == "origin":
            ax.scatter([x], [y], marker="D", s=210, facecolor=HOME,
                       edgecolor="white", lw=2.2, zorder=11)
        else:
            days = stays.get(key, [])
            txt = "/".join(str(i) for i in days)
            col = RAMP(0.08 + 0.62 * ((days[0] - 1) / max(ndays - 1, 1)))
            ox, oy = p.get("offset", [0, 0])
            mx, my = x + ox, y + oy
            if ox or oy:
                ax.plot([x, mx], [y, my], color=MUTED, lw=0.9,
                        ls=(0, (2, 2)), zorder=8)
                ax.scatter([x], [y], s=22, facecolor=MUTED,
                           edgecolor="white", lw=1.0, zorder=9)
                x, y = mx, my
            if len(days) == 1:
                ax.scatter([x], [y], s=880, facecolor=col, edgecolor="white",
                           lw=2.4, zorder=10)
            else:
                w, h = _pill_wh(g, txt, 0.40, 0.885)
                ax.add_patch(FancyBboxPatch(
                    (x - w / 2, y - h / 2), w, h,
                    boxstyle=f"round,pad=0,rounding_size={g.W * 0.04:.4f}",
                    facecolor=col, edgecolor="white", lw=2.3, zorder=10))
            ax.text(x, y + 0.004, txt, fontsize=10.6, color="white",
                    ha="center", va="center", fontweight="bold", zorder=12,
                    clip_on=True)
            if len(days) > 1:
                _, h = _pill_wh(g, txt, 0.40, 0.885)
                ax.text(x, y - h / 2 - g.H * 0.028, f"{len(days)} 晚",
                        fontsize=7.4, color="white", ha="center", va="center",
                        zorder=15, clip_on=True,
                        bbox=dict(boxstyle="round,pad=0.26,rounding_size=0.3",
                                  facecolor=MUTED, edgecolor="none"))

        lx, ly = x + dx, y + dy
        ax.plot([x, lx], [y, ly], color=TXT, lw=0.9, alpha=0.55, zorder=12,
                solid_capstyle="round")
        ax.text(lx, ly, p["name"], fontsize=10.4,
                color=HOME if kind == "origin" else TXT, ha=ha, va=va,
                fontweight="bold", zorder=14, clip_on=True,
                bbox=dict(boxstyle="round,pad=0.36,rounding_size=0.14",
                          facecolor="white",
                          edgecolor=HOME if kind == "origin" else TXT,
                          linewidth=1.0, alpha=0.97))

    draw_scale(ax, g)


def draw_route_only_side(fig, cfg):
    fig.text(0.50, 0.930, cfg.get("title", ""), fontsize=18, color=TXT,
             fontweight="bold", ha="left", va="center")
    fig.text(0.50, 0.888, cfg.get("subtitle", ""), fontsize=11.0,
             color=MUTED, ha="left", va="center")
    fig.add_artist(plt.Line2D([0.50, 0.975], [0.855, 0.855],
                              color="#dde3e8", lw=1.0))
    highlights = cfg.get("highlights", [])
    y0 = 0.805
    step = 0.098 if len(highlights) <= 5 else 0.70 / max(len(highlights), 1)
    for i, (place, desc) in enumerate(highlights):
        yy = y0 - i * step
        fig.text(0.502, yy, place, fontsize=12.0, color=ROUTE,
                 fontweight="bold", ha="left", va="center")
        fig.text(0.660, yy, desc, fontsize=10.5, color=TXT, ha="left",
                 va="center")
    note = cfg.get("route_note", "")
    if isinstance(note, list):
        note = "\n".join(note)
    yy = y0 - (max(len(highlights) - 1, 0)) * step - 0.075
    fig.text(0.502, yy, note, fontsize=10.2, color=MUTED, ha="left",
             va="center", linespacing=1.7)


# ---------------------------------------------------------------- 输出
def build_plan(cfg, base, out, routes):
    g = Geo(cfg, base, routes)
    fig = plt.figure(figsize=(13.6, 9.0))
    ax_map = fig.add_axes([0.035, 0.055, 0.325, 0.855])
    ax_panel = fig.add_axes([0.405, 0.055, 0.575, 0.855])
    finish_axes(ax_map, g)
    draw_map(ax_map, g, cfg, routes)
    draw_panel(ax_panel, g, cfg)
    fig.text(0.035, 0.968, cfg.get("tag", "行程"), fontsize=13,
             color="white", fontweight="bold", va="center", ha="left",
             bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.6",
                       facecolor=cfg.get("accent", ROUTE),
                       edgecolor="none"))
    fig.text(0.965, 0.968, cfg.get("footer", ""), fontsize=11, color=MUTED,
             va="center", ha="right")
    path = os.path.join(out, f"plan-{cfg['slug']}-final.png")
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    print("wrote", path)


def build_route_only(cfg, base, out, routes):
    g = Geo(cfg, base, routes)
    fig = plt.figure(figsize=(12.6, 8.6))
    ax = fig.add_axes([0.055, 0.055, 0.40, 0.885])
    finish_axes(ax, g)
    draw_route_only_map(ax, g, cfg, routes)
    draw_route_only_side(fig, cfg)
    path = os.path.join(out, f"map-{cfg['slug']}-route-only.png")
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    print("wrote", path)


def main(path):
    cfg = json.load(open(path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(path))
    out = os.path.join(base, cfg.get("out_dir", "out"))
    os.makedirs(out, exist_ok=True)
    rg = os.path.join(base, "routes_geom.json")
    routes = json.load(open(rg, encoding="utf-8")) if os.path.exists(rg) \
        else {"legs": {}}
    build_plan(cfg, base, out, routes)
    build_route_only(cfg, base, out, routes)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
