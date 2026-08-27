"""Premjesti župe koje su sjele na krivi homonim naselja.

Ide POSLIJE Placesa (13), a ne prije: Places je zadnji korak koji dira
koordinate, pa bi ranija korekcija bila pregažena. Vidi `src/parish_geo.py`
za razlog zašto homonim uopće prolazi kroz geokodiranje.

Korekcija je namjerno konzervativna — pomiče samo kad je odredište
**jednoznačno**: ili je u `OVERRIDES` (s izvorom), ili biskupija reže
kandidate na točno jedan. Sve ostalo se prijavljuje i ostavlja na miru.

Jedna iznimka od „ostavlja na miru": točka udaljena od SVAKOG naselja koje
evidencija imenuje (`MAX_SJEDISTE_KM`) briše se i kad se odredište ne zna.
Prazna koordinata je poštena, a izmišljena na karti izgleda jednako
uvjerljivo kao i sve ostale.

Nova koordinata je crkva istog titulara u tom naselju ako postoji (razina
zgrade), inače težište naselja (razina mjesta). `geocode_source` to razlikuje,
pa se u exportu i dalje zna koliko je koja točka precizna.

  uv run python scripts/14_fix_parish_locations.py --dry-run
  uv run python scripts/14_fix_parish_locations.py
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import geo_hr, parish_geo  # noqa: E402
from src.db import connect  # noqa: E402
from src.normalize import slugify  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fix-lokacije")

PARISH_SQL = """
SELECT id, name, titular, city, county, diocese, lat, lng, registry_id, geocode_source
FROM parishes
WHERE kind = 'zupa' AND (registry_status IS NULL OR registry_status LIKE 'AKTIV%')
  AND duplicate_of IS NULL
ORDER BY id
"""


def _seat_in(conn, s: parish_geo.Settlement, titular: str | None):
    """Koordinate crkve istog titulara u TOM naselju, ako je ima.

    Ime naselja nije dovoljno — „Sesvete" i „Sveti Martin" su i sami homonimi,
    pa bi filtar po imenu vratio crkvu iz krivog. Presuđuje geometrija.
    """
    if not titular:
        return None
    want = slugify(titular)
    rows = conn.execute(
        "SELECT lat, lng, titular FROM churches "
        "WHERE settlement = ? AND lat IS NOT NULL",
        (s.name,),
    ).fetchall()
    for r in rows:
        if (r["titular"] and slugify(r["titular"]) == want
                and parish_geo.contains(s, r["lat"], r["lng"])):
            return r["lat"], r["lng"]
    return None


def run(dry_run: bool = False) -> None:
    stats = Counter()
    with connect() as conn:
        rows = conn.execute(PARISH_SQL).fetchall()
        counties = parish_geo.settled_counties(rows)
        log.info("župa: %d | biskupija sa sigurnim uporištem: %d",
                 len(rows), len(counties))

        for r in rows:
            fix = parish_geo.resolve(r, counties)
            if not fix:
                stats["ostaje"] += 1
                continue

            if isinstance(fix, parish_geo.Drop):
                log.info("%s → BEZ KOORDINATE | %s", r["name"][:44], fix.reason)
                stats["obrisano"] += 1
                if not dry_run:
                    conn.execute(
                        "UPDATE parishes SET lat = NULL, lng = NULL, county = NULL, "
                        "geocode_source = NULL, notes = ?, "
                        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (f"koordinata odbačena: {fix.reason}", r["id"]),
                    )
                continue

            hit = _seat_in(conn, fix.target, r["titular"])
            if hit:
                lat, lng, src = hit[0], hit[1], "church"
            else:
                lat, lng, src = fix.target.lat, fix.target.lng, "naselje-centroid"

            moved = (parish_geo.km(r["lat"], r["lng"], lat, lng)
                     if r["lat"] is not None else None)
            log.info("%s → %s/%s (%s) %s | %s",
                     r["name"][:44], fix.target.name, fix.target.county, src,
                     f"{moved:.0f} km" if moved is not None else "prvi put",
                     fix.reason)
            stats["premjesteno"] += 1

            if not dry_run:
                conn.execute(
                    "UPDATE parishes SET lat = ?, lng = ?, county = ?, "
                    "geocode_source = ?, notes = ?, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ?",
                    (lat, lng, fix.target.county, src,
                     f"lokacija ispravljena: {fix.reason}", r["id"]),
                )
        if not dry_run:
            conn.commit()

    log.info("gotovo%s: %s", " (dry-run)" if dry_run else "", dict(stats))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(**vars(ap.parse_args()))
