#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Geocode place names and verify coordinates via Nominatim (OpenStreetMap).

Usage:
    python geocode.py "Place A, Country" "Place B, Country"
    python geocode.py --reverse 48.8566,2.3522
    python geocode.py --check path/to/trip.json

Design notes:
  - Sends a User-Agent as Nominatim's usage policy requires.
  - Sleeps between requests to stay polite.
  - Prints the administrative area for each hit so you can spot a name
    that resolves to the wrong district.
  - --check reverse-geocodes every place in a trip.json and prints the
    resolved display name next to the configured one.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

NOMINATIM = "https://nominatim.openstreetmap.org"
UA = "trip-docs/1.0"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def forward(query, limit=3):
    q = urllib.parse.urlencode({"q": query, "format": "json", "limit": limit})
    hits = _get(f"{NOMINATIM}/search?{q}")
    for h in hits:
        print(f"  {h['lat']}, {h['lon']}  {h['display_name']}")
    if not hits:
        print("  (no results)")
    return hits


def reverse(lat, lon):
    q = urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "json"})
    h = _get(f"{NOMINATIM}/reverse?{q}")
    print(f"  {h.get('display_name')}")
    return h


def check_trip(path):
    cfg = json.load(open(path, encoding="utf-8"))
    for key, p in cfg["places"].items():
        print(f"{key}: configured name = {p.get('name')!r} "
              f"({p['lat']:.4f}, {p['lon']:.4f})")
        reverse(p["lat"], p["lon"])
        time.sleep(1.1)


def main(argv):
    if argv[0] == "--reverse":
        lat, lon = (float(x) for x in argv[1].split(","))
        reverse(lat, lon)
        return
    if argv[0] == "--check":
        check_trip(argv[1])
        return
    for i, q in enumerate(argv):
        if i:
            time.sleep(1.1)
        print(f'"{q}"')
        forward(q)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
