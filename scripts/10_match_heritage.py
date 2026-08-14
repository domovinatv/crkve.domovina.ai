"""Spoji zaštićenu sakralnu baštinu (Registar kulturnih dobara) na građevine.

Ulaz: `heritage_unmatched` (iz scripts/04) + `churches` (iz scripts/01/05).
Izlaz: popunjeni `heritage_id`, `heritage_status`, `heritage_desc`,
`year_built` na građevinama; spojeni zapisi se brišu iz `heritage_unmatched`
pa preostatak tablice = mjera nepokrivenosti.

Matching je u src/match.py — blokiranje po mjestu, tvrdi filtar po titularu,
pa rapidfuzz uz prag i marginu. Registar nema koordinate, pa je ovo jedini
način; svjesno radije ostavi nespojeno nego pogriješi.

  uv run python scripts/10_match_heritage.py            # spoji
  uv run python scripts/10_match_heritage.py --dry-run  # samo izvijesti
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import connect, merge_source  # noqa: E402
from src.match import best_match, build_index, place_key  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("match-bastina")


def run(dry_run: bool = False) -> None:
    stats = Counter()
    with connect() as conn:
        churches = conn.execute(
            "SELECT id, name, kind, city, settlement, municipality FROM churches"
        ).fetchall()
        index = build_index(churches)
        log.info("građevina u indeksu: %d | blokova po mjestu: %d",
                 len(churches), len(index))

        taken: set[int] = {
            r["id"] for r in conn.execute(
                "SELECT id FROM churches WHERE heritage_id IS NOT NULL"
            ).fetchall()
        }

        rows = conn.execute("SELECT * FROM heritage_unmatched").fetchall()
        log.info("baštinskih zapisa za spajanje: %d", len(rows))

        for h in rows:
            # Naselje prvo (Mjesto_smjestaja), općina (Opcina_grad) kao šira
            # razina — vidi src/match.py zašto redoslijed nije svejedno.
            hit = best_match(
                index, h["name"],
                place_key(h["settlement"]),
                place_key(h["municipality"]),
            )
            if not hit:
                stats["nespojeno"] += 1
                continue
            cand, score = hit
            if cand.id in taken:
                # Jedna građevina ne može nositi dvije oznake zaštite — druga
                # je gotovo sigurno drugi objekt u istom mjestu.
                stats["kandidat_vec_zauzet"] += 1
                continue
            taken.add(cand.id)
            stats["spojeno"] += 1
            stats[f"score_{score // 10 * 10}"] += 1

            if dry_run:
                continue

            src_row = conn.execute(
                "SELECT source, year_built FROM churches WHERE id = ?", (cand.id,)
            ).fetchone()
            conn.execute(
                """
                UPDATE churches SET
                  heritage_id = ?, heritage_status = ?, heritage_class = ?,
                  heritage_desc = ?, year_built = COALESCE(year_built, ?),
                  settlement = COALESCE(settlement, ?),
                  county = COALESCE(county, ?),
                  source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    h["heritage_id"], h["status"], h["klasifikacija"],
                    h["description"], h["period"], h["settlement"],
                    _county_full(h["county"]),
                    merge_source(src_row["source"], "kulturna-dobra"),
                    cand.id,
                ),
            )
            conn.execute(
                "DELETE FROM heritage_unmatched WHERE heritage_id = ?", (h["heritage_id"],)
            )

        if not dry_run:
            conn.commit()
        left = conn.execute("SELECT COUNT(*) FROM heritage_unmatched").fetchone()[0]
        with_h = conn.execute(
            "SELECT COUNT(*) FROM churches WHERE heritage_id IS NOT NULL"
        ).fetchone()[0]

    log.info("gotovo%s: %s", " (dry-run)" if dry_run else "", dict(stats))
    log.info("građevina sa zaštitom: %d | nespojene baštine: %d", with_h, left)


def _county_full(name: str | None) -> str | None:
    """Registar piše "Krapinsko-zagorska"; isti oblik koristi i geo_hr."""
    return name.strip() if name else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(**vars(ap.parse_args()))
