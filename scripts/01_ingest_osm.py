"""Ingest sakralnih objekata iz OpenStreetMapa (Overpass). Bez API ključa.

OSM je PRIMARNI izvor građevina: jedini daje koordinate za sve, i to za ~5200
objekata kao tlocrt (way/relation), ne samo točku. Upit je unija širih od
`amenity=place_of_worship`, jer je HR dio OSM-a nekonzistentno tagiran:

  amenity=place_of_worship      kanonski tag (~5350)
  building=church|chapel|…      objekti bez amenity tagа (stare crkve, ruševine)
  amenity=monastery             samostanski kompleksi
  historic=church               nekadašnje crkve / ruševine
  historic=wayside_shrine       pilovi i poklonci (kind='poklonac')

Ukupno ~6840 elemenata. Dedup je po (osm_type, osm_id) — Overpass ne vraća
duplikate unutar jednog upita, ali unija tagova može isti objekt dohvatiti
više puta u budućim proširenjima upita.

Županija/općina se dodjeljuju prostorno (src/geo_hr.py) nad DGU granicama iz
../karta-hrvatske — OSM `addr:*` tagovi su prerijetki da bi bili dovoljni.

  uv run python scripts/01_ingest_osm.py
"""
from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import geo_hr, kinds, titular  # noqa: E402
from src.db import add_alias, connect, merge_source  # noqa: E402
from src.normalize import slugify  # noqa: E402
from src.overpass import latlng, query  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("osm")

OQL = """
[out:json][timeout:300];
area["ISO3166-1"="HR"][admin_level=2]->.hr;
(
  nwr["amenity"="place_of_worship"](area.hr);
  nwr["building"~"^(church|chapel|cathedral|mosque|synagogue|temple|monastery)$"](area.hr);
  nwr["amenity"="monastery"](area.hr);
  nwr["historic"="church"](area.hr);
  nwr["historic"="wayside_shrine"](area.hr);
);
out center tags;
"""


def run() -> None:
    elements = query(OQL)
    log.info("OSM elemenata: %d", len(elements))

    stats = Counter()
    kind_counts = Counter()
    with connect() as conn:
        for el in elements:
            t = el.get("tags") or {}
            osm_type, osm_id = el["type"], el["id"]

            name = t.get("name") or t.get("official_name") or t.get("alt_name")
            coords = latlng(el)
            if not coords:
                stats["bez_koordinata"] += 1
                continue
            lat, lng = coords

            kind = kinds.classify(t, name)
            religion = kinds.religion_of(t, kind)
            denomination = (t.get("denomination") or "").strip().lower() or None

            if not name:
                # Bezimeni objekti su stvarni (kapelice uz put) — imenuj ih po
                # tipu da katalog ostane upotrebljiv, ali označi u aliasima.
                stats["bez_imena"] += 1
                name = {"kapela": "Kapela", "poklonac": "Poklonac",
                        "crkva": "Crkva"}.get(kind, "Sakralni objekt")

            city = t.get("addr:city") or t.get("addr:place") or t.get("addr:suburb")
            street, hnum = t.get("addr:street"), t.get("addr:housenumber")
            address = ", ".join(
                p for p in [" ".join(x for x in [street, hnum] if x), city] if p
            ) or None

            place = geo_hr.locate(lat, lng)
            if place.county:
                stats["s_zupanijom"] += 1
            if place.settlement:
                stats["s_naseljem"] += 1

            slug = slugify(
                name, city or place.settlement or place.municipality,
                suffix=f"{osm_type[0]}{osm_id}",
            )

            existing = conn.execute(
                "SELECT id, source FROM churches WHERE osm_type = ? AND osm_id = ?",
                (osm_type, osm_id),
            ).fetchone()
            source = merge_source(existing["source"] if existing else None, "osm")

            fields = dict(
                name=name,
                name_official=t.get("official_name"),
                kind=kind,
                religion=religion,
                denomination=denomination,
                titular=titular.parse(name),
                address=address,
                city=city,
                settlement=place.settlement,
                municipality=place.municipality,
                county=place.county,
                postal_code=t.get("addr:postcode"),
                lat=lat,
                lng=lng,
                geom_kind=osm_type,
                osm_type=osm_type,
                osm_id=osm_id,
                wikidata_id=t.get("wikidata"),
                wikipedia_url=_wikipedia_url(t.get("wikipedia")),
                year_built=t.get("start_date"),
                architect=t.get("architect"),
                style=t.get("building:architecture"),
                phone=t.get("phone") or t.get("contact:phone"),
                email=t.get("email") or t.get("contact:email"),
                website=t.get("website") or t.get("contact:website"),
                source=source,
            )

            if existing:
                cols = ", ".join(f"{k} = ?" for k in fields)
                conn.execute(
                    f"UPDATE churches SET {cols}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [*fields.values(), existing["id"]],
                )
                church_id = existing["id"]
                stats["azurirano"] += 1
            else:
                cols = ["slug", *fields.keys()]
                sql = (
                    f"INSERT INTO churches ({', '.join(cols)}) "
                    f"VALUES ({', '.join(['?'] * len(cols))}) "
                    "ON CONFLICT(slug) DO NOTHING RETURNING id"
                )
                row = conn.execute(sql, [slug, *fields.values()]).fetchone()
                if row is None:
                    stats["slug_kolizija"] += 1
                    continue
                church_id = row["id"]
                stats["novo"] += 1

            for key in ("alt_name", "official_name", "old_name", "name:hr", "name:it"):
                if t.get(key) and t[key] != name:
                    add_alias(conn, church_id, t[key], f"osm:{key}")

            kind_counts[kind] += 1
            stats["ok"] += 1

        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM churches").fetchone()[0]

    log.info("gotovo: %s", dict(stats))
    log.info("po tipu: %s", dict(kind_counts.most_common()))
    log.info("ukupno građevina u bazi: %d", total)


def _wikipedia_url(tag: str | None) -> str | None:
    """OSM `wikipedia=hr:Katedrala…` → puni URL."""
    if not tag:
        return None
    if tag.startswith("http"):
        return tag
    if ":" in tag:
        lang, title = tag.split(":", 1)
        return f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
    return None


if __name__ == "__main__":
    run()
