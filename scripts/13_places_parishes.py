"""Google Places: precizne koordinate župa + NEZAVISNA provjera matchera.

Jedini korak u pipelineu koji treba API ključ — zato nije u `make all` nego u
`make places`. Bez ključa cijeli katalog i dalje radi.

Dvije uloge iz jednog poziva po župi (vidi src/places.py):

  PRECIZIRANJE  Župa koja nema koordinate svoje crkve leži na težištu naselja
                (točnost sela). Places nad "ŽUPA SV. X, Mjesto" vraća točku na
                razini zgrade + telefon + web, kojih u državnoj evidenciji nema.

  PROVJERA      Župa KOJA JEST spojena na crkvu (scripts/11) ne treba nove
                koordinate — ali usporedba s Placesom je nezavisna potvrda da
                je spojena na PRAVU crkvu. Places nije sudjelovao u matchanju,
                pa je to stvarni drugi izvor, ne kružna provjera.
                  ≤ 300 m  → churches.geo_verified = 1
                  > 750 m  → zapis u `geo_conflicts` (ne dira se automatski)
                  između   → ni potvrda ni konflikt (gradske jezgre, veliki
                             kompleksi, župni ured odvojen od crkve)

Rezultat se NE primjenjuje slijepo: Places mora vratiti sakralni tip objekta
(ili naziv vrlo sličan župi) i mora pasti u istu županiju, inače se odbacuje.

  uv run python scripts/13_places_parishes.py              # sve aktivne župe
  uv run python scripts/13_places_parishes.py --limit 50   # probni run
  uv run python scripts/13_places_parishes.py --verify-only  # bez pisanja koordinata
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import geo_hr  # noqa: E402
from src.db import connect, merge_source  # noqa: E402
from src.places import (  # noqa: E402
    PlacesClient,
    PlacesError,
    haversine_m,
    pick,
    queries_for,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("places")

# Vrste pravnih osoba koje imaju fizički objekt koji Places može znati.
PARISH_KINDS = ("zupa", "svetiste", "samostan", "parohija", "crkvena-opcina", "dzemat")

VERIFY_OK_M = 300.0      # ispod ovoga: potvrda
CONFLICT_M = 750.0       # iznad ovoga: konflikt za ručni pregled


def run(limit: int | None = None, verify_only: bool = False) -> None:
    stats = Counter()
    with connect() as conn:
        placeholders = ", ".join("?" * len(PARISH_KINDS))
        rows = conn.execute(
            f"""
            SELECT p.*, c.id AS church_id, c.name AS church_name,
                   c.lat AS church_lat, c.lng AS church_lng
            FROM parishes p
            LEFT JOIN churches c ON c.parish_id = p.id AND c.is_parish_church = 1
            WHERE p.kind IN ({placeholders})
              AND (p.registry_status IS NULL OR p.registry_status LIKE 'AKTIV%')
            ORDER BY (c.id IS NULL) DESC, p.id
            """,
            PARISH_KINDS,
        ).fetchall()
        if limit:
            rows = rows[:limit]
        log.info("župa za obradu: %d (prvo one bez matchirane crkve)", len(rows))

        try:
            with PlacesClient() as client:
                for i, p in enumerate(rows, 1):
                    # Sidro = već poznata pozicija župe. Bez njega Places zna
                    # vratiti istoimenu crkvu s druge strane države (mjereno:
                    # 24 % preciziranih završi >5 km od vlastitog naselja).
                    anchor = _anchor(p)
                    hit = None
                    for q in queries_for(p["name"], p["city"], p["address"]):
                        res = client.search_text(q)
                        hit = pick(res, p["name"], p["county"], anchor=anchor)
                        if hit:
                            break
                    if not hit:
                        stats["bez_pogotka"] += 1
                        continue
                    stats["pogodak"] += 1

                    # Kontakt je čist dobitak neovisno o koordinatama.
                    if not verify_only:
                        conn.execute(
                            "UPDATE parishes SET "
                            "  phone = COALESCE(phone, ?), website = COALESCE(website, ?), "
                            "  google_place_id = COALESCE(google_place_id, ?), "
                            "  google_maps_uri = COALESCE(google_maps_uri, ?), "
                            "  source = ?, updated_at = CURRENT_TIMESTAMP "
                            "WHERE id = ?",
                            (hit["phone"], hit["website"], hit["place_id"],
                             hit["google_maps_uri"], merge_source(p["source"], "places"),
                             p["id"]),
                        )
                        if hit["phone"]:
                            stats["telefon"] += 1
                        if hit["website"]:
                            stats["web"] += 1

                    if p["church_id"] is not None:
                        _verify(conn, p, hit, stats, verify_only)
                    elif not verify_only:
                        _precise(conn, p, hit, stats)

                    if i % 100 == 0:
                        conn.commit()
                        log.info("… %d/%d | poziva: %d, iz keša: %d | %s",
                                 i, len(rows), client.calls, client.cache_hits, dict(stats))
                log.info("Places poziva: %d (novih), iz keša: %d",
                         client.calls, client.cache_hits)
        except PlacesError as e:
            conn.commit()
            log.error("%s", e)
            log.error("Prekinuto — dosad obrađeno: %s", dict(stats))
            sys.exit(1)

        conn.commit()
        verified = conn.execute(
            "SELECT COUNT(*) FROM churches WHERE geo_verified = 1"
        ).fetchone()[0]
        conflicts = conn.execute("SELECT COUNT(*) FROM geo_conflicts").fetchone()[0]
        by_src = conn.execute(
            "SELECT geocode_source, COUNT(*) n FROM parishes WHERE lat IS NOT NULL "
            "GROUP BY geocode_source"
        ).fetchall()

    log.info("gotovo: %s", dict(stats))
    log.info("koordinate župa po izvoru: %s", {r["geocode_source"]: r["n"] for r in by_src})
    log.info("crkava s potvrđenom lokacijom: %d | konflikata za pregled: %d",
             verified, conflicts)


def _anchor(p) -> tuple[float, float] | None:
    """Najbolja poznata pozicija župe, po padajućoj točnosti."""
    if p["church_lat"] is not None:
        return p["church_lat"], p["church_lng"]
    if p["lat"] is not None:
        return p["lat"], p["lng"]
    return geo_hr.settlement_centroid(p["city"], p["county"])


def _verify(conn, p, hit, stats, verify_only: bool) -> None:
    """Župa ima matchiranu crkvu — usporedi je s Placesom."""
    d = haversine_m(p["church_lat"], p["church_lng"], hit["lat"], hit["lng"])
    if d <= VERIFY_OK_M:
        stats["potvrdjeno"] += 1
        if not verify_only:
            conn.execute(
                "UPDATE churches SET geo_verified = 1, geo_verify_m = ?, "
                "google_place_id = COALESCE(google_place_id, ?), "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (round(d, 1), hit["place_id"], p["church_id"]),
            )
        return
    if d > CONFLICT_M:
        stats["konflikt"] += 1
        conn.execute(
            """
            INSERT INTO geo_conflicts
              (parish_id, church_id, parish_name, church_name, place_name,
               place_address, distance_m, our_lat, our_lng, place_lat, place_lng)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (p["id"], p["church_id"], p["name"], p["church_name"], hit["name"],
             hit["address"], round(d, 1), p["church_lat"], p["church_lng"],
             hit["lat"], hit["lng"]),
        )
        return
    stats["neodlucno"] += 1
    if not verify_only:
        conn.execute(
            "UPDATE churches SET geo_verify_m = ? WHERE id = ?",
            (round(d, 1), p["church_id"]),
        )


def _precise(conn, p, hit, stats) -> None:
    """Župa bez matchirane crkve — Places daje bolju točku od težišta naselja."""
    if p["geocode_source"] == "places":
        stats["vec_precizna"] += 1
        return
    place = geo_hr.locate(hit["lat"], hit["lng"])
    conn.execute(
        "UPDATE parishes SET lat = ?, lng = ?, geocode_source = 'places', "
        "address = COALESCE(address, ?), county = COALESCE(county, ?), "
        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (hit["lat"], hit["lng"], hit["address"], place.county, p["id"]),
    )
    stats["precizirano"] += 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--verify-only", action="store_true",
                    help="samo provjeri i prijavi, ne piši koordinate/kontakte")
    run(**vars(ap.parse_args()))
