#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Featured-tour exporter (ETT-11).

Reads the curated list in data/featured/manifest.json (slug + tour id) and
exports each tour from the production database into data/featured/<slug>.json,
the record scripts/build_featured.py renders. Read-only: it only issues GET
requests, signing in as a normal user (no service keys, no DB changes).

Required environment variables (never commit these):
  FEATURED_SUPABASE_URL       e.g. https://luiytextfhajminczddl.supabase.co
  FEATURED_SUPABASE_ANON_KEY  the project's public anon key
  FEATURED_EMAIL              reader account email
  FEATURED_PASSWORD           reader account password

Run from the repo root:  python scripts/export_featured.py
Then:                    python scripts/build_featured.py
"""
import json, os, sys, glob
import urllib.request, urllib.parse, urllib.error
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "featured")
MEDIA = os.environ.get("FEATURED_MEDIA_BASE", "https://media.steepmap.eu").rstrip("/")
GRADE = {0: "Easy", 10: "Medium", 20: "Hard", 30: "Very Hard"}


def env(name):
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit(f"Missing environment variable {name}")
    return v


class Db:
    def __init__(self):
        self.base = env("FEATURED_SUPABASE_URL").rstrip("/")
        self.anon = env("FEATURED_SUPABASE_ANON_KEY")
        body = json.dumps({"email": env("FEATURED_EMAIL"), "password": env("FEATURED_PASSWORD")}).encode()
        req = urllib.request.Request(f"{self.base}/auth/v1/token?grant_type=password", data=body,
                                     headers={"apikey": self.anon, "Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            self.token = json.load(r)["access_token"]

    def get(self, table, params, schema="tours"):
        url = f"{self.base}/rest/v1/{table}?{urllib.parse.urlencode(params, safe='.,()*')}"
        req = urllib.request.Request(url, headers={
            "apikey": self.anon, "Authorization": f"Bearer {self.token}", "Accept-Profile": schema})
        with urllib.request.urlopen(req) as r:
            return json.load(r)


def build_record(db, slug, tour_id):
    rows = db.get("locations", {"select": "*,waypoints(lat,lng,elevation,sequence)", "id": f"eq.{tour_id}"})
    if not rows:
        sys.exit(f"[{slug}] tour {tour_id} not found")
    d = rows[0]
    if not d.get("is_public") or not d.get("approved") or d.get("deleted"):
        sys.exit(f"[{slug}] tour {tour_id} is not public and approved - refusing to export")

    wp = sorted(d.get("waypoints") or [], key=lambda p: p["sequence"])
    coords = [[round(p["lng"], 6), round(p["lat"], 6)] for p in wp]
    gain, prev = 0.0, None
    for p in wp:
        e = p.get("elevation")
        if e is None:
            continue
        if prev is not None and e > prev:
            gain += e - prev
        prev = e

    users = db.get("users", {"select": "display_name,username,auth_uid", "id": f"eq.{d['user_id']}"})
    author = users[0] if users else {"display_name": None, "username": "", "auth_uid": None}
    author_name = author.get("display_name") or author.get("username") or ""

    trs = db.get("tour_description_translations", {"select": "lang,title,description",
                                                   "location_id": f"eq.{tour_id}"})
    src = d.get("source_lang") or "en"
    desc = {src: d.get("description") or ""}
    title = {src: d["title"]}
    for r in trs:
        desc[r["lang"]] = (r.get("description") or "").strip() or desc[src]
        title[r["lang"]] = (r.get("title") or "").strip() or d["title"]

    dt = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
    center = [round((d["long_min"] + d["long_max"]) / 2, 6), round((d["lat_min"] + d["lat_max"]) / 2, 6)]
    aspect = ", ".join(s.strip() for s in (d.get("aspect") or "").split(",") if s.strip()) or "-"

    rec = {
        "id": d["id"], "slug": slug, "title": d["title"], "title_i18n": title, "source_lang": src,
        "author": {"name": author_name, "auth_uid": author.get("auth_uid"),
                   "avatar": f"{MEDIA}/profile_pictures/{author['auth_uid']}/avatar.jpg" if author.get("auth_uid") else ""},
        "created_date": f"{dt.day} {dt.strftime('%b %Y')}",
        "stats": {
            "grade": GRADE.get(d["grade"], str(d["grade"])),
            "max_steep": round(d["max_steep"]),
            "exposure": f"E{d['exposure']}" if d.get("exposure") is not None else "n/a",
            "aspect": aspect,
            "distance_km": round(d["distance_m"] / 1000, 1),
            "elev_gain_m": round(gain),
            "alt_min_m": round(d["altitude_min"]),
            "alt_max_m": round(d["altitude_max"]),
        },
        "description": desc,
        "photos": [f"{MEDIA}/figures/{k}" for k in (d.get("photo_keys") or [])],
        "center": center, "zoom": 13,
        "track": {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords}},
    }
    return rec


def main():
    manifest = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))
    db = Db()
    for entry in manifest["tours"]:
        rec = build_record(db, entry["slug"], entry["id"])
        out = os.path.join(DATA, f"{entry['slug']}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        print(f"  exported {entry['slug']}: {rec['title']} ({len(rec['photos'])} photos, {len(coords_of(rec))} points)")
    print(f"Exported {len(manifest['tours'])} tour(s).")


def coords_of(rec):
    return rec["track"]["geometry"]["coordinates"]


if __name__ == "__main__":
    main()
