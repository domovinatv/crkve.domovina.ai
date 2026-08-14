"""Ingest crkava iz Wikidate (SPARQL). Sadržaj Wikidate je CC0.

Wikidata je manja od OSM-a (~850 objekata) ali nosi sliku (Commons),
poveznicu na hrvatsku Wikipediju, arhitekta i godinu gradnje. Spaja se na
postojeće OSM zapise, redom:

  1. `churches.wikidata_id` (OSM `wikidata` tag) — egzaktno, najjače
  2. prostorno: najbliži zapis unutar 150 m s kompatibilnim titularom

Ako nema para, zapis ulazi kao nova građevina (Wikidata zna za crkve koje u
OSM-u fale, tipično porušene ili one bez tagiranog objekta).

  uv run python scripts/05_ingest_wikidata.py
"""
from __future__ import annotations

import logging
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import geo_hr, kinds, titular, wikidata  # noqa: E402
from src.db import connect, merge_source  # noqa: E402
from src.normalize import slugify  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wikidata")

# Radijus za prostorno spajanje. 150 m je kompromis: crkveni tlocrt je
# desetak metara, ali OSM centroid tlocrta i Wikidata točka znaju odstupati,
# a susjedne crkve su rijetko bliže od 150 m (osim u starim gradskim jezgrama
# — zato uz radijus ide i provjera titulara).
RADIUS_M = 150


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def run() -> None:
    rows = wikidata.query()
    log.info("Wikidata redaka: %d", len(rows))

    # SPARQL vraća jedan redak po kombinaciji OPTIONAL vrijednosti — grupiraj
    # po itemu i uzmi prvu ne-praznu vrijednost svakog polja.
    by_item: dict[str, dict] = {}
    for r in rows:
        q = wikidata.qid(r.get("item"))
        if not q:
            continue
        cur = by_item.setdefault(q, {})
        for k, v in r.items():
            if v and not cur.get(k):
                cur[k] = v

    log.info("jedinstvenih objekata: %d", len(by_item))

    stats = Counter()
    with connect() as conn:
        existing_wd = {
            r["wikidata_id"]: r["id"]
            for r in conn.execute(
                "SELECT id, wikidata_id FROM churches WHERE wikidata_id IS NOT NULL"
            ).fetchall()
        }
        # Prostorni indeks: koordinate svih građevina, grubo blokirane po
        # 0.01° ćeliji (~1.1 km) da izbjegnemo O(n·m) usporedbu.
        grid: dict[tuple[int, int], list[tuple[int, float, float, str | None]]] = {}
        for r in conn.execute(
            "SELECT id, lat, lng, titular FROM churches WHERE lat IS NOT NULL"
        ).fetchall():
            cell = (int(r["lat"] * 100), int(r["lng"] * 100))
            grid.setdefault(cell, []).append((r["id"], r["lat"], r["lng"], r["titular"]))

        for q, r in by_item.items():
            coord = wikidata.parse_point(r.get("coord"))
            if not coord:
                stats["bez_koordinata"] += 1
                continue
            lat, lng = coord
            name = r.get("itemLabel") or q
            if name == q:
                stats["bez_naziva"] += 1

            fields = dict(
                wikidata_id=q,
                wikipedia_url=r.get("article"),
                commons_image=wikidata.commons_url(r.get("image")),
                year_built=wikidata.year_of(r.get("inception")),
                architect=r.get("architectLabel"),
                style=r.get("styleLabel"),
            )

            church_id = existing_wd.get(q)
            if church_id:
                stats["spojeno_po_wikidata_tagu"] += 1
            else:
                church_id = _nearest(grid, lat, lng, titular.key(name))
                if church_id:
                    stats["spojeno_prostorno"] += 1

            if church_id:
                row = conn.execute(
                    "SELECT source FROM churches WHERE id = ?", (church_id,)
                ).fetchone()
                sets = ", ".join(f"{k} = COALESCE({k}, ?)" for k in fields)
                conn.execute(
                    f"UPDATE churches SET {sets}, source = ?, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [*fields.values(), merge_source(row["source"], "wikidata"), church_id],
                )
                continue

            # Nema para — nova građevina samo iz Wikidate.
            kind = kinds.classify({}, name)
            place = geo_hr.locate(lat, lng)
            slug = slugify(name, r.get("adminLabel") or place.settlement, suffix=q.lower())
            conn.execute(
                """
                INSERT INTO churches
                  (slug, name, kind, religion, titular, city, settlement,
                   municipality, county,
                   lat, lng, geom_kind, wikidata_id, wikipedia_url, commons_image,
                   year_built, architect, style, source)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,'node',?,?,?,?,?,?,?)
                ON CONFLICT(slug) DO NOTHING
                """,
                (
                    slug, name, kind, kinds.religion_of({}, kind), titular.parse(name),
                    r.get("adminLabel"), place.settlement, place.municipality,
                    place.county, lat, lng,
                    q, r.get("article"), wikidata.commons_url(r.get("image")),
                    wikidata.year_of(r.get("inception")), r.get("architectLabel"),
                    r.get("styleLabel"), '["wikidata"]',
                ),
            )
            stats["novo_iz_wikidate"] += 1

        conn.commit()
        n_img = conn.execute(
            "SELECT COUNT(*) FROM churches WHERE commons_image IS NOT NULL"
        ).fetchone()[0]
        n_wiki = conn.execute(
            "SELECT COUNT(*) FROM churches WHERE wikipedia_url IS NOT NULL"
        ).fetchone()[0]

    log.info("gotovo: %s", dict(stats))
    log.info("građevina sa slikom: %d | s Wikipedijom: %d", n_img, n_wiki)


def _nearest(grid, lat: float, lng: float, tkey: str | None) -> int | None:
    """Najbliža građevina unutar RADIUS_M, uz uvjet da titular ne proturječi."""
    best: tuple[float, int] | None = None
    c_lat, c_lng = int(lat * 100), int(lng * 100)
    for dlat in (-1, 0, 1):
        for dlng in (-1, 0, 1):
            for cid, clat, clng, ctit in grid.get((c_lat + dlat, c_lng + dlng), []):
                d = haversine_m(lat, lng, clat, clng)
                if d > RADIUS_M:
                    continue
                if tkey and ctit:
                    from src.titular import key as tk

                    if tk(ctit) and tk(ctit) != tkey:
                        continue
                if best is None or d < best[0]:
                    best = (d, cid)
    return best[1] if best else None


if __name__ == "__main__":
    run()
