"""Deriviraj teritorije (nad)biskupija iz sjedišta župa + izmjeri ih o OSM.

Granice biskupija u Hrvatskoj nisu javno dostupne kao geometrija (OSM ima 3 od
15, Wikidata nijednu), pa se računaju: naselje pripadne biskupiji župa koje u
njemu sjede, a naselje bez župe biskupiji najbliže župe; naselja iste
biskupije se spoje. Obrazloženje i što je izostavljeno — `src/dioceses.py`.

Skripta je u slotu 20 („derivacije") jer mora doći POSLIJE matcha i
geokodiranja župa (11–13) — bez koordinata župa nema se od čega derivirati —
a PRIJE exporta (3x).

Treba susjedni repo `../karta-hrvatske` (ili `KARTA_DATA_DIR`) zbog naselja.

  uv run python scripts/20_derive_diocese_areas.py
  uv run python scripts/20_derive_diocese_areas.py --no-validate   # bez mreže
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import dioceses as dio  # noqa: E402
from src import geo_hr  # noqa: E402
from src.db import connect  # noqa: E402
from src.overpass import query as overpass  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("derive-dioceses")

METHOD = "naselja (DGU) → biskupija sjedeće/najbliže župe, spojeno"

# Samo teritorijalne latinske (nad)biskupije. Križevačka eparhija je izuzeta u
# `dioceses.OVERLAPPING_SLUGS` — grkokatolička je i preklapa se sa svima.
DIOCESE_SQL = """
SELECT id, slug, name FROM dioceses
WHERE kind IN ('nadbiskupija', 'biskupija') AND religion = 'christian'
ORDER BY id
"""

PARISH_SQL = """
SELECT id, name, diocese, lat, lng FROM parishes
WHERE kind = 'zupa' AND lat IS NOT NULL AND lng IS NOT NULL
  AND diocese IS NOT NULL AND diocese != ''
"""

# Jedine tri hrvatske biskupije koje u OSM-u postoje kao granica. Ne koriste se
# kao izvor — samo kao mjera. Provjereno 2026-08-16.
OSM_QL = """
[out:json][timeout:120];
relation(id:19899029,19899030,21111604);
out geom;
"""


def _osm_key(name: str) -> str:
    return name.casefold().replace("-", " ").strip()


def run(validate: bool = True) -> None:
    with connect() as conn:
        rows = conn.execute(DIOCESE_SQL).fetchall()
        territorial = {r["name"]: r["id"] for r in rows
                       if r["slug"] not in dio.OVERLAPPING_SLUGS}
        skipped = [r["name"] for r in rows if r["slug"] in dio.OVERLAPPING_SLUGS]

        parishes = [
            dio.Parish(r["id"], r["name"], r["diocese"], r["lat"], r["lng"])
            for r in conn.execute(PARISH_SQL).fetchall()
            if r["diocese"] in territorial
        ]
        church_counts = {
            r["diocese"]: r["n"] for r in conn.execute(
                "SELECT p.diocese AS diocese, COUNT(*) AS n FROM churches c "
                "JOIN parishes p ON p.id = c.parish_id GROUP BY p.diocese"
            ).fetchall()
        }

    log.info("biskupija u particiji: %d, izuzeto (preklapa se): %s",
             len(territorial), ", ".join(skipped) or "—")
    log.info("župa sa sjedištem: %d", len(parishes))

    feats = geo_hr.naselja_features()
    if not feats:
        log.error("nema naselja — kloniraj ../karta-hrvatske ili postavi KARTA_DATA_DIR")
        return
    sett = dio.settlements(feats)
    log.info("naselja: %d", len(sett))

    a = dio.assign(sett, parishes)
    log.info("dodjela: %d naselja izravno (župa sjedi u njima), %d po najbližoj župi"
             " (%d naselja ima župe dviju biskupija)", a.direct, a.nearest, a.mixed)

    areas = dio.dissolve(sett, a)
    log.info("spojeno u %d teritorija", len(areas))

    agreements = {}
    if validate:
        agreements = _validate(sett, a, areas)

    stats: dict[str, dict] = {name: {"settlements": 0, "population": 0}
                              for name in areas}
    for i, name in a.by_settlement.items():
        st = stats[name]
        st["settlements"] += 1
        st["population"] += sett[i].population
    parish_counts: dict[str, int] = {}
    for p in parishes:
        parish_counts[p.diocese] = parish_counts.get(p.diocese, 0) + 1

    with connect() as conn:
        conn.execute("DELETE FROM diocese_areas")
        for name, geom in sorted(areas.items()):
            conn.execute(
                "INSERT INTO diocese_areas (diocese_id, name, geometry, area_km2,"
                " population, settlement_count, parish_count, church_count, method,"
                " osm_agreement) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (territorial[name], name, dio.to_geojson_geometry(geom),
                 round(dio.area_km2(geom), 1), stats[name]["population"],
                 stats[name]["settlements"], parish_counts.get(name, 0),
                 church_counts.get(name, 0), METHOD, agreements.get(name)),
            )
        conn.commit()

    total = sum(dio.area_km2(g) for g in areas.values())
    log.info("upisano %d teritorija, ukupno %.0f km² (kopno RH ≈ 56 594 km²)",
             len(areas), total)


def _validate(sett, a, areas) -> dict[str, float]:
    """Usporedi derivaciju s 3 biskupije koje u OSM-u postoje kao granica."""
    try:
        elements = overpass(OSM_QL)
    except Exception as exc:  # noqa: BLE001 — validacija ne smije srušiti derivaciju
        log.warning("OSM validacija preskočena (%s)", exc)
        return {}

    osm = dio.osm_boundaries(elements)
    if not osm:
        log.warning("OSM nije vratio nijednu granicu — validacija preskočena")
        return {}

    ours = {_osm_key(n): (n, g) for n, g in areas.items()}
    out: dict[str, float] = {}
    log.info("── validacija nad OSM granicama ──")
    for osm_name, osm_geom in sorted(osm.items()):
        pair = ours.get(_osm_key(osm_name))
        if not pair:
            log.warning("  %s: nemamo teritorij tog imena", osm_name)
            continue
        name, geom = pair
        hit, total = dio.agreement(sett, a, osm_geom, name)
        pct = 100 * hit / total if total else 0.0
        out[name] = round(pct, 1)
        log.info("  %-38s naselja %4d/%-4d = %5.1f%%   IoU %.3f",
                 osm_name, hit, total, pct, dio.iou(geom, osm_geom))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-validate", action="store_true",
                    help="preskoči usporedbu s OSM granicama (bez mreže)")
    args = ap.parse_args()
    run(validate=not args.no_validate)
