"""Eksportiraj katalog u CSV (data/exports/) — ljudski čitljiv otvoreni podatak.

Tri datoteke: crkve.csv, zupe.csv, biskupije.csv. UTF-8 s BOM-om jer Excel
inače krivo prikaže č/ć/š/ž — a ovaj export postoji upravo zato da netko tko
ne piše kod može otvoriti katalog.

  uv run python scripts/32_export_csv.py
"""
from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import connect  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("export-csv")

OUT_DIR = ROOT / "data" / "exports"

EXPORTS = {
    "crkve.csv": """
        SELECT c.id, c.slug, c.name AS naziv, c.kind AS tip, c.titular,
               c.religion AS religija, c.denomination AS konfesija,
               c.address AS adresa, c.city AS mjesto, c.settlement AS naselje,
               c.municipality AS opcina, c.county AS zupanija,
               c.lat, c.lng,
               p.name AS zupa, p.oib AS zupa_oib, p.diocese AS biskupija,
               c.is_parish_church AS zupna_crkva,
               c.heritage_id AS oznaka_zastite, c.heritage_status AS status_zastite,
               c.year_built AS godina, c.architect AS arhitekt, c.style AS stil,
               c.phone AS telefon, c.email, c.website AS web,
               c.osm_type, c.osm_id, c.wikidata_id, c.wikipedia_url, c.commons_image,
               c.source AS izvori
        FROM churches c LEFT JOIN parishes p ON p.id = c.parish_id
        ORDER BY c.county, c.city, c.name
    """,
    "zupe.csv": """
        SELECT id, slug, name AS naziv, short_name AS kratki_naziv, kind AS vrsta,
               titular, oib, diocese AS biskupija, community AS zajednica,
               religion AS religija, denomination AS konfesija,
               address AS adresa, city AS mjesto, county AS zupanija, lat, lng,
               geocode_source AS izvor_koordinata,
               registry_no AS evidencijski_broj, registry_status AS status,
               registered_at AS datum_upisa, leader_title AS sluzba,
               phone AS telefon, email, website AS web,
               google_maps_uri AS google_karta,
               source AS izvori
        FROM parishes ORDER BY diocese, name
    """,
    "biskupije.csv": """
        SELECT id, slug, name AS naziv, kind AS vrsta, religion AS religija,
               denomination AS konfesija, oib, seat AS sjediste,
               parish_count AS broj_zupa, source AS izvori
        FROM dioceses ORDER BY name
    """,
    "geo-konflikti.csv": """
        SELECT parish_name AS zupa, church_name AS spojena_crkva,
               place_name AS google_naziv, place_address AS google_adresa,
               distance_m AS udaljenost_m,
               our_lat, our_lng, place_lat, place_lng
        FROM geo_conflicts ORDER BY distance_m DESC
    """,
    "bastina-nespojeno.csv": """
        SELECT heritage_id AS oznaka, name AS naziv, settlement AS naselje,
               municipality AS opcina, county AS zupanija, klasifikacija,
               status, period AS vrijeme_nastanka
        FROM heritage_unmatched ORDER BY county, municipality, name
    """,
}


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        for fname, sql in EXPORTS.items():
            rows = conn.execute(sql).fetchall()
            path = OUT_DIR / fname
            # utf-8-sig: Excel na Windowsu inače pojede dijakritiku.
            if not rows:
                # geo-konflikti.csv je prazan dok se ne pokrene `make places`;
                # prazan file je informativniji od nepostojećeg.
                log.info("%s: 0 redaka", fname)
                path.write_text("", encoding="utf-8-sig")
                continue
            with path.open("w", newline="", encoding="utf-8-sig") as fh:
                w = csv.DictWriter(fh, fieldnames=rows[0].keys())
                w.writeheader()
                for r in rows:
                    w.writerow(dict(r))
            log.info("%s: %d redaka", fname, len(rows))


if __name__ == "__main__":
    run()
