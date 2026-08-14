"""Eksportiraj katalog u GeoJSON (data/exports/) — ulaz za karte i third-party.

Dva FeatureCollectiona:

  crkve.geojson   sve građevine s koordinatama (Point). Properties su trimani
                  na ono što karta treba za marker, popup i filtriranje.
  zupe.geojson    pravne osobe s koordinatama (Point) — župni uredi.

`poklonac` ostaje u exportu (dio je sakralne baštine) ali je zaseban `kind`
pa ga karta može gasiti — vidi src/kinds.py MINOR_KINDS.

Datoteke idu u data/exports/, a scripts/33_sync_karta.py ih preslikava u
../karta-hrvatske. Namjerno razdvojeno: export ne smije ovisiti o tome je li
susjedni repo kloniran.

  uv run python scripts/31_export_geojson.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import connect  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("export-geojson")

OUT_DIR = ROOT / "data" / "exports"

CHURCH_SQL = """
SELECT c.id, c.slug, c.name, c.kind, c.religion, c.denomination, c.titular,
       c.address, c.city, c.settlement, c.municipality, c.county,
       c.lat, c.lng, c.geom_kind,
       c.parish_id, c.is_parish_church,
       c.osm_type, c.osm_id, c.wikidata_id, c.wikipedia_url, c.commons_image,
       c.heritage_id, c.heritage_status, c.year_built, c.architect, c.style,
       c.phone, c.email, c.website, c.source,
       p.name AS parish_name, p.slug AS parish_slug, p.diocese AS diocese
FROM churches c
LEFT JOIN parishes p ON p.id = c.parish_id
WHERE c.lat IS NOT NULL AND c.lng IS NOT NULL
ORDER BY c.id
"""

PARISH_SQL = """
SELECT id, slug, name, short_name, kind, religion, denomination, titular,
       oib, diocese, community, address, city, county, lat, lng,
       geocode_source, registry_no, registry_status, leader_title,
       phone, email, website, source
FROM parishes
WHERE lat IS NOT NULL AND lng IS NOT NULL
  AND (registry_status IS NULL OR registry_status LIKE 'AKTIV%')
ORDER BY id
"""


def _fc(rows) -> dict:
    feats = []
    for r in rows:
        props = {}
        for k in r.keys():
            if k in ("lat", "lng"):
                continue
            v = r[k]
            if k == "source" and isinstance(v, str):
                try:
                    v = json.loads(v)
                except json.JSONDecodeError:
                    pass
            if v is None or v == "":
                continue          # izostavi prazno — GeoJSON je i tako velik
            props[k] = v
        feats.append({
            "type": "Feature",
            "id": r["id"],
            "geometry": {
                "type": "Point",
                "coordinates": [round(r["lng"], 6), round(r["lat"], 6)],
            },
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": feats}


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        churches = conn.execute(CHURCH_SQL).fetchall()
        parishes = conn.execute(PARISH_SQL).fetchall()

    for fname, rows in [("crkve.geojson", churches), ("zupe.geojson", parishes)]:
        fc = _fc(rows)
        path = OUT_DIR / fname
        path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")))
        log.info("%s: %d feature-a (%.1f MB)",
                 fname, len(fc["features"]), path.stat().st_size / 1e6)


if __name__ == "__main__":
    run()
