"""Ingest zaštićene sakralne baštine iz Registra kulturnih dobara RH.

Izvor: data.gov.hr, Ministarstvo kulture i medija. 7950 zapisa ukupno; nas
zanima ~2000 sakralnih (klasifikacije "sakralna graditeljska baština" i
"sakralno-profana graditeljska baština"). Nose ono što ni OSM ni Wikidata
nemaju: službenu oznaku zaštite (Z-xxxx), vrijeme nastanka i stručni opis
konzervatorskog odjela.

Nemaju koordinate — zato se ovdje SAMO pune u `heritage_unmatched`, a
spajanje na građevine radi scripts/10_match_heritage.py (mjesto + naziv).
Razdvojeno je namjerno: ingest je čist prijepis izvora, matching je
heuristika koju treba moći ponoviti/podesiti bez ponovnog dohvaćanja.

  uv run python scripts/04_ingest_heritage.py
"""
from __future__ import annotations

import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.datagovhr import KULTURNA_DOBRA, fetch  # noqa: E402
from src.db import connect  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bastina")

SAKRALNE_KLASE = {
    "sakralna graditeljska baština",
    "sakralno-profana graditeljska baština",
}


def clean(s: str | None) -> str | None:
    """Registar ima vodeće razmake i \\n\\r u gotovo svakom polju."""
    if not s:
        return None
    return " ".join(str(s).split()) or None


def run() -> None:
    rows = fetch(KULTURNA_DOBRA)
    log.info("zapisa u registru: %d", len(rows))

    stats = Counter()
    with connect() as conn:
        for r in rows:
            klasa = clean(r.get("Klasifikacija"))
            if klasa not in SAKRALNE_KLASE:
                stats["preskoceno_neklasakralno"] += 1
                continue

            oznaka = clean(r.get("Oznaka_dobra"))
            naziv = clean(r.get("Naziv"))
            if not naziv:
                stats["bez_naziva"] += 1
                continue
            if not oznaka:
                # Bez oznake nema stabilnog ključa — koristi registarski id.
                oznaka = f"ID-{r.get('id')}"

            conn.execute(
                """
                INSERT INTO heritage_unmatched
                  (heritage_id, name, settlement, municipality, county,
                   klasifikacija, status, period, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(heritage_id) DO UPDATE SET
                  name=excluded.name, settlement=excluded.settlement,
                  municipality=excluded.municipality, county=excluded.county,
                  klasifikacija=excluded.klasifikacija, status=excluded.status,
                  period=excluded.period, description=excluded.description
                """,
                (
                    oznaka,
                    naziv,
                    clean(r.get("Mjesto_smjestaja")),
                    clean(r.get("Opcina_grad")),
                    clean(r.get("Zupanija")),
                    klasa,
                    clean(r.get("Pravni_status")),
                    clean(r.get("Vrijeme_nastanka")),
                    clean(r.get("Opis_dobra")),
                ),
            )
            stats[klasa] += 1
            stats["ok"] += 1

        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM heritage_unmatched").fetchone()[0]

    log.info("gotovo: %s", dict(stats))
    log.info("sakralne baštine u bazi (još nespojeno): %d", n)


if __name__ == "__main__":
    run()
