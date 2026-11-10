#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch real road geometry for every leg in trip.json via OSRM.

Usage:
    python route.py path/to/trip.json

Reads the "legs" object of trip.json:

    "legs": {"S1": ["origin", "park"], "S2": ["park", "coast"], ...}

Writes routes_geom.json next to trip.json:

    {"legs": {"S1": {"via": [...], "km": 151, "min": 167,
                     "geometry": [[lon, lat], ...]}}, ...}

Geometry is simplified to roughly one point per 300 m so the file stays
small without changing the drawn shape. Leg ids are referenced by days
("leg": "S1") and by the map scripts (drawing order = "leg_order").
"""
import json
import os
import sys
import time
import urllib.request

OSRM = "https://router.project-osrm.org/route/v1/driving"
UA = "trip-docs/1.0"
SIMPLIFY = 0.004  # degrees of lon+lat, ~300 m at this latitude band


def fetch(coords):
    coord = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in coords)
    url = f"{OSRM}/{coord}?overview=full&geometries=geojson"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.load(r)
    if j.get("code") != "Ok":
        raise RuntimeError(j.get("code"))
    rt = j["routes"][0]
    pts = rt["geometry"]["coordinates"]
    keep = [pts[0]]
    for p in pts[1:-1]:
        if abs(p[0] - keep[-1][0]) + abs(p[1] - keep[-1][1]) > SIMPLIFY:
            keep.append(p)
    keep.append(pts[-1])
    return keep, round(rt["distance"] / 1000), round(rt["duration"] / 60)


def main(path):
    cfg = json.load(open(path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(path))
    places = cfg["places"]
    legs = cfg.get("legs", {})
    if not legs:
        # derive from days: every day with a "leg" id
        for d in cfg.get("days", []):
            if d.get("leg"):
                legs.setdefault(d["leg"], [d["from"], d["to"]])

    out = {"legs": {}}
    for name in cfg.get("leg_order", sorted(legs)):
        keys = legs[name]
        coords = [(places[k]["lon"], places[k]["lat"]) for k in keys]
        for attempt in range(3):
            try:
                geom, km, mn = fetch(coords)
                out["legs"][name] = {
                    "via": keys, "geometry": geom, "km": km, "min": mn,
                }
                print(f"{name}: {keys[0]} -> {keys[-1]}  "
                      f"{km} km / {mn} min / {len(geom)} pts")
                break
            except Exception as e:  # noqa: BLE001
                print(f"{name} attempt {attempt + 1} failed: {e}")
                time.sleep(3)
        else:
            sys.exit(f"fatal: could not fetch leg {name}")
        time.sleep(1.2)  # be polite to the public OSRM instance

    out["_total"] = {
        "km": sum(v["km"] for v in out["legs"].values()),
        "min": sum(v["min"] for v in out["legs"].values()),
    }
    dst = os.path.join(base, "routes_geom.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f)
    t = out["_total"]
    print(f"saved {dst}  total {t['km']} km / {t['min']} min")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
