#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download Natural Earth boundary GeoJSON for one country (basemap data).

Usage:
    python fetch_basemap.py "Sri Lanka" [--out basemap] [--res 10m]

Writes two files into --out:
    country.geojson   country outline (admin-0)
    admin1.geojson    first-level administrative boundaries

Global coverage notes:
  - The two source files are *worldwide* GeoJSONs from Natural Earth;
    they are downloaded once and cached (default: <temp>/travel-docs-ne),
    then filtered to the requested country. Every country after the
    first one is instant.
  - admin-1 is always fetched at 10m: that is the only resolution with
    worldwide first-level coverage (50m has 9 countries, 110m none).
  - The country outline defaults to 10m for detail on small islands;
    pass --res 50m (3 MB) for a quicker, coarser outline.

Country matching is on the Natural Earth English names (ADMIN / NAME /
SOVEREIGNT), exact first, then substring - "United States" matches
"United States of America". If nothing matches, check the English
short name and retry.
"""
import argparse
import json
import os
import sys
import tempfile
import urllib.request

UA = "trip-docs/1.0"
RAW_BASE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
            "/master/geojson/")
FILES = {
    "country": "ne_{res}_admin_0_countries.geojson",
    "admin1": "ne_10m_admin_1_states_provinces.geojson",  # only global res
}


def cached(fname, cache):
    """Return path to the raw worldwide file, downloading once."""
    path = os.path.join(cache, fname)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        print(f"using cache {path}")
        return path
    url = RAW_BASE + fname
    print(f"downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    os.makedirs(cache, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    print(f"cached {path} ({len(data) // 1024 // 1024} MB)")
    return path


def matches(props, country):
    c = country.lower()
    for field in ("ADMIN", "admin", "NAME", "name", "SOVEREIGNT"):
        v = props.get(field)
        if v and v.lower() == c:
            return True
    for field in ("ADMIN", "admin", "NAME", "name", "SOVEREIGNT"):
        v = props.get(field)
        if v and (c in v.lower() or v.lower() in c):
            return True
    return False


def filter_fc(data, country):
    feats = data.get("features", [data] if data.get("type") == "Feature"
                                 else [])
    hit = [f for f in feats if matches(f.get("properties", {}), country)]
    return {"type": "FeatureCollection", "features": hit}


def save(fc, path):
    json.dump(fc, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"saved {path} ({len(fc['features'])} feature(s))")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("country", help="English short name, e.g. 'Sri Lanka'")
    ap.add_argument("--out", default="basemap")
    ap.add_argument("--res", default="10m", choices=["110m", "50m", "10m"],
                    help="resolution of the country outline (admin-1 "
                         "is always 10m)")
    ap.add_argument("--cache",
                    default=os.path.join(tempfile.gettempdir(),
                                         "travel-docs-ne"),
                    help="where the worldwide raw GeoJSONs are cached")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)

    country = filter_fc(json.load(open(cached(
        FILES["country"].format(res=a.res), a.cache), encoding="utf-8")),
        a.country)
    if not country["features"]:
        sys.exit(f'fatal: no admin-0 match for "{a.country}" at {a.res} - '
                 "use the English short name (Natural Earth ADMIN field)")
    save(country, os.path.join(a.out, "country.geojson"))

    try:
        admin1 = filter_fc(json.load(open(cached(FILES["admin1"], a.cache),
                                          encoding="utf-8")), a.country)
    except Exception as e:  # noqa: BLE001
        print(f"admin-1 load failed ({e}); continuing without it")
        admin1 = {"type": "FeatureCollection", "features": []}
    save(admin1, os.path.join(a.out, "admin1.geojson"))
    if not admin1["features"]:
        print("note: no admin-1 boundaries for this country in Natural "
              "Earth - the map draws the outline without internal borders")


if __name__ == "__main__":
    main()
