"""Dodijeli koordinate župama koje ih nisu naslijedile od svoje crkve.

Poredak izvora, od najtočnijeg prema najgrubljem:

  1. scripts/11 — koordinate NJEZINE župne crkve (točno na zgradu). Odrađeno prije.
  2. **težište naselja** iz DGU granica (`src/geo_hr.settlement_centroid`) —
     točnost razine mjesta, ali offline, instant i bez rate limita. Pokriva
     ~98% preostalih župa jer evidencija sjedište piše kao "Mjesto, Ulica br".
  3. Nominatim (`--nominatim`) — razina kućnog broja, ali javni endpoint u
     praksi daje ~5 s po upitu i do 5 upita po župi (ladder kandidata), što je
     preko 10 sati za ostatak. Zato je **opcionalan**, ne default.

Zapisuje `geocode_source` ('naselje-centroid' | 'nominatim') pa se u exportu
uvijek zna koliko je koja koordinata precizna.

  uv run python scripts/12_geocode_parishes.py                  # brzo, offline
  uv run python scripts/12_geocode_parishes.py --nominatim      # + fino, sporo
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import geo_hr  # noqa: E402
from src.db import connect  # noqa: E402
from src.nominatim import geocode  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("geocode-zupe")

PENDING_SQL = (
    "SELECT id, name, address, city, county FROM parishes "
    "WHERE lat IS NULL AND (address IS NOT NULL OR city IS NOT NULL) "
    "AND (registry_status IS NULL OR registry_status LIKE 'AKTIV%') "
    "ORDER BY id"
)


def run(nominatim: bool = False, limit: int | None = None) -> None:
    stats = Counter()
    with connect() as conn:
        _backfill_counties(conn, stats)

        rows = conn.execute(PENDING_SQL).fetchall()
        if limit:
            rows = rows[:limit]
        log.info("župa bez koordinata: %d", len(rows))

        for r in rows:
            hit = geo_hr.settlement_centroid(r["city"], r["county"])
            if not hit:
                stats["naselje_nepoznato_ili_visevznacno"] += 1
                continue
            lat, lng = hit
            place = geo_hr.locate(lat, lng)
            conn.execute(
                "UPDATE parishes SET lat = ?, lng = ?, geocode_source = 'naselje-centroid', "
                "county = COALESCE(county, ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (lat, lng, place.county, r["id"]),
            )
            stats["naselje_centroid"] += 1
        conn.commit()
        log.info("nakon naselja: %s", dict(stats))

        if nominatim:
            rest = conn.execute(PENDING_SQL).fetchall()
            log.info("Nominatim za preostalih %d (≈%d min, javni endpoint)",
                     len(rest), max(1, len(rest) * 5 // 60))
            with httpx.Client() as client:
                for i, r in enumerate(rest, 1):
                    full = ", ".join(p for p in [r["address"], r["city"]] if p) or None
                    hit = geocode(client, {"address": full, "city": r["city"],
                                           "county": r["county"]})
                    if not hit:
                        stats["nominatim_promasaj"] += 1
                        continue
                    lat, lng = hit
                    place = geo_hr.locate(lat, lng)
                    conn.execute(
                        "UPDATE parishes SET lat = ?, lng = ?, geocode_source = 'nominatim', "
                        "county = COALESCE(county, ?), updated_at = CURRENT_TIMESTAMP "
                        "WHERE id = ?",
                        (lat, lng, place.county, r["id"]),
                    )
                    stats["nominatim"] += 1
                    if i % 50 == 0:
                        conn.commit()
                        log.info("… %d/%d", i, len(rest))
            conn.commit()

        geo = conn.execute("SELECT COUNT(*) FROM parishes WHERE lat IS NOT NULL").fetchone()[0]
        tot = conn.execute("SELECT COUNT(*) FROM parishes").fetchone()[0]
        by_src = conn.execute(
            "SELECT geocode_source, COUNT(*) n FROM parishes WHERE lat IS NOT NULL "
            "GROUP BY geocode_source"
        ).fetchall()

    log.info("gotovo: %s", dict(stats))
    log.info("po izvoru: %s", {r["geocode_source"]: r["n"] for r in by_src})
    log.info("župa s koordinatama: %d / %d", geo, tot)


def _backfill_counties(conn, stats: Counter) -> None:
    """Popuni županiju svakoj župi koja već ima koordinate (od svoje crkve iz
    scripts/11 ili od ranijeg geokodiranja).

    Državna evidencija NE sadrži županiju — piše samo "Mjesto, Ulica". Bez
    ovog prolaza 1202 župe ostanu bez `county`, a onda i filtar po županiji u
    scripts/13 (Places) tiho ne radi ništa i propušta rezultate s druge strane
    Hrvatske.
    """
    rows = conn.execute(
        "SELECT id, lat, lng FROM parishes WHERE county IS NULL AND lat IS NOT NULL"
    ).fetchall()
    for r in rows:
        place = geo_hr.locate(r["lat"], r["lng"])
        if place.county:
            conn.execute("UPDATE parishes SET county = ? WHERE id = ?",
                         (place.county, r["id"]))
            stats["zupanija_popunjena"] += 1
    conn.commit()
    if rows:
        log.info("županija popunjena za %d župa (od %d bez nje)",
                 stats["zupanija_popunjena"], len(rows))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nominatim", action="store_true",
                    help="dodatni fini prolaz za ostatak (sporo, ~5 s po župi)")
    ap.add_argument("--limit", type=int, default=None)
    run(**vars(ap.parse_args()))
