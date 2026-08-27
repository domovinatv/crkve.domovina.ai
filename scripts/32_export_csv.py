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
        SELECT p.id, p.slug, p.name AS naziv, p.short_name AS kratki_naziv,
               p.kind AS vrsta, p.titular, p.oib, p.diocese AS biskupija,
               p.community AS zajednica,
               p.religion AS religija, p.denomination AS konfesija,
               p.address AS adresa, p.city AS mjesto, p.county AS zupanija,
               p.lat, p.lng, p.geocode_source AS izvor_koordinata,
               p.registry_no AS evidencijski_broj, p.registry_status AS status,
               p.duplicate_of AS duplikat_od,
               p.registered_at AS datum_upisa, p.leader_title AS sluzba,
               p.phone AS telefon, p.email, p.website AS web,
               p.google_maps_uri AS google_karta,
               (SELECT COUNT(*) FROM churches c WHERE c.parish_id = p.id)
                   AS broj_gradjevina,
               pc.name AS zupna_crkva, pc.slug AS zupna_crkva_slug,
               p.source AS izvori
        FROM parishes p
        LEFT JOIN churches pc ON pc.id = (
            SELECT c2.id FROM churches c2
            WHERE c2.parish_id = p.id AND c2.is_parish_church = 1
            ORDER BY c2.id LIMIT 1)
        ORDER BY p.diocese, p.name
    """,
    "biskupije.csv": """
        SELECT d.id, d.slug, d.name AS naziv, d.kind AS vrsta,
               d.religion AS religija, d.denomination AS konfesija, d.oib,
               d.seat AS sjediste, d.parish_count AS broj_zupa,
               a.area_km2 AS povrsina_km2, a.population AS stanovnika_na_podrucju,
               a.settlement_count AS broj_naselja, a.church_count AS broj_crkava,
               a.osm_agreement AS slaganje_s_osm_posto,
               d.source AS izvori
        FROM dioceses d LEFT JOIN diocese_areas a ON a.diocese_id = d.id
        ORDER BY d.name
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
