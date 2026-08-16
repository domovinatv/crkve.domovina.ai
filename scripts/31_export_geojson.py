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
       c.phone, c.email, c.website, c.geo_verified, c.source,
       p.name AS parish_name, p.slug AS parish_slug, p.diocese AS diocese
FROM churches c
LEFT JOIN parishes p ON p.id = c.parish_id
WHERE c.lat IS NOT NULL AND c.lng IS NOT NULL
ORDER BY c.id
"""

# `church_count` i `church_*` su jedini način da se iz zupe.geojson vidi je li
# župa uopće spojena sa svojom građevinom — bez toga sloj za župe ne može
# prikazati rupu u podacima (489 župa nema spojenu župnu crkvu, 422 nema
# nijednu). Podupit umjesto JOIN-a jer nad `is_parish_church` nema unique
# indeksa: da se invarijanta „jedna župna crkva po župi" ikad prekrši, JOIN bi
# tiho duplicirao župu u exportu.
PARISH_SQL = """
SELECT p.id, p.slug, p.name, p.short_name, p.kind, p.religion, p.denomination,
       p.titular, p.oib, p.diocese, p.community, p.address, p.city, p.county,
       p.lat, p.lng, p.geocode_source, p.registry_no, p.registry_status,
       p.leader_title, p.phone, p.email, p.website, p.google_maps_uri, p.source,
       (SELECT COUNT(*) FROM churches c WHERE c.parish_id = p.id) AS church_count,
       pc.slug AS church_slug, pc.name AS church_name, pc.kind AS church_kind,
       pc.geo_verified AS church_verified
FROM parishes p
LEFT JOIN churches pc ON pc.id = (
    SELECT c2.id FROM churches c2
    WHERE c2.parish_id = p.id AND c2.is_parish_church = 1
    ORDER BY c2.id LIMIT 1)
WHERE p.lat IS NOT NULL AND p.lng IS NOT NULL
  AND (p.registry_status IS NULL OR p.registry_status LIKE 'AKTIV%')
ORDER BY p.id
"""


# Zastavice 0/1 kod kojih je 0 isto što i "nema": karta ih čita kao
# `["==", ["get", …], 1]` odnosno JS falsy, pa se odsutne i nulte ponašaju
# identično. Izbacivanje nula štedi ~250 KB (11 700 polja) na 4 MB datoteke.
# `church_count` namjerno NIJE ovdje iako je često 0: nula nije „nema podatka"
# nego nalaz („ova župa nema nijednu spojenu građevinu"), a to je upravo ono
# što sloj za župe prikazuje. Izostavljena bi se rupa u podacima pretvorila u
# odsutno polje i postala nevidljiva potrošaču.
_DROP_IF_ZERO = {"is_parish_church", "geo_verified", "unesco", "church_verified"}


# Teritoriji biskupija su jedini poligoni u exportu i jedini DERIVIRANI sloj —
# `method` i `osm_agreement` putuju uz svaki feature da karta ne bi tvrdila
# preciznost koju podatak nema. Vidi scripts/20 i src/dioceses.py.
DIOCESE_SQL = """
SELECT a.diocese_id AS id, d.slug, a.name, d.kind, d.seat, d.oib,
       a.geometry, a.area_km2, a.population, a.settlement_count,
       a.parish_count, a.church_count, a.method, a.osm_agreement
FROM diocese_areas a JOIN dioceses d ON d.id = a.diocese_id
ORDER BY a.name
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
            if k in _DROP_IF_ZERO and not v:
                continue
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


def _diocese_fc(rows) -> dict:
    """Poligoni — geometrija je već GeoJSON string iz `diocese_areas`."""
    feats = []
    for r in rows:
        props = {k: r[k] for k in r.keys()
                 if k != "geometry" and r[k] is not None and r[k] != ""}
        feats.append({
            "type": "Feature",
            "id": r["id"],
            "geometry": json.loads(r["geometry"]),
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": feats}


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        churches = conn.execute(CHURCH_SQL).fetchall()
        parishes = conn.execute(PARISH_SQL).fetchall()
        areas = conn.execute(DIOCESE_SQL).fetchall()

    collections = [
        ("crkve.geojson", _fc(churches)),
        ("zupe.geojson", _fc(parishes)),
    ]
    if areas:
        collections.append(("biskupije.geojson", _diocese_fc(areas)))
    else:
        log.warning("biskupije.geojson preskočen — pokreni scripts/20 (make derive)")

    for fname, fc in collections:
        path = OUT_DIR / fname
        path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")))
        log.info("%s: %d feature-a (%.1f MB)",
                 fname, len(fc["features"]), path.stat().st_size / 1e6)


if __name__ == "__main__":
    run()
