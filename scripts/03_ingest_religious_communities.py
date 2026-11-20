"""Ingest nekatoličkih vjerskih zajednica i njihovih organizacijskih oblika.

Izvor: "Evidencija vjerskih zajednica u RH" (Ministarstvo pravosuđa i uprave,
preko data.gov.hr). Dva resursa:

  zajednice (54)      SPC, Islamska zajednica, Evangelička crkva, Reformirana
                      kršćanska kalvinska crkva, adventisti, baptisti, Židovska
                      zajednica… → ulaze u `dioceses` (kind='zajednica')
  org. oblici (863)   crkvene općine, parohije, džemati, zborovi — pandan
                      župama → ulaze u `parishes`

Bez ovoga bi katalog imao rupu: OSM zna za ~150 pravoslavnih crkava i ~20
džamija/mesdžida, ali bez pravne osobe iza njih.

  uv run python scripts/03_ingest_religious_communities.py
"""
from __future__ import annotations

import logging
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import titular  # noqa: E402
# Naziv zajednice → (religion, denomination): pravila žive u src/denomination.py
# (ista definicija kao za OSM i audit, i testabilna — ovaj modul se ne može importati).
from src.denomination import community_denomination as denom_for  # noqa: E402
from src.datagovhr import (  # noqa: E402
    VJERSKE_ORG_OBLICI,
    VJERSKE_ZAJEDNICE,
    fetch,
    split_sjediste,
)
from src.db import connect, mark_duplicates, merge_source, upsert_diocese, upsert_parish  # noqa: E402
from src.normalize import slugify, title_case_hr  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("vjerske")

_ORG_KIND_RULES: list[tuple[str, re.Pattern]] = [
    ("parohija", re.compile(r"\bPAROHIJA\b|\bCRKVEN\w*\s+OPĆIN\w*\b.*PRAVOSLAV", re.I)),
    ("dzemat", re.compile(r"\bDŽEMAT\b|\bMEDŽLIS\b|\bMEDZLIS\b", re.I)),
    ("crkvena-opcina", re.compile(r"\bCRKVEN\w*\s+OPĆIN|\bŽUPA\b|\bZBOR\b|\bOPĆINA\b", re.I)),
    ("eparhija", re.compile(r"\bEPARHIJA\b|\bMITROPOLIJA\b", re.I)),
    ("samostan", re.compile(r"\bMANASTIR\b|\bSAMOSTAN\b", re.I)),
]


def org_kind(name: str) -> str:
    for kind, pat in _ORG_KIND_RULES:
        if pat.search(name or ""):
            return kind
    return "ostalo"


def run() -> None:
    zajednice = fetch(VJERSKE_ZAJEDNICE)
    oblici = fetch(VJERSKE_ORG_OBLICI)
    log.info("zajednica: %d | organizacijskih oblika: %d", len(zajednice), len(oblici))

    stats = Counter()
    with connect() as conn:
        for r in zajednice:
            naziv = (r.get("NAZIV") or "").strip()
            if not naziv:
                continue
            rel, den = denom_for(naziv) or (None, None)
            _, city = split_sjediste(r.get("SJEDISTE"))
            upsert_diocese(
                conn,
                slugify(naziv),
                title_case_hr(naziv),
                kind="zajednica",
                religion=rel,
                denomination=den,
                oib=(r.get("OIB") or "").strip() or None,
                seat=city,
                source='["datagovhr:vjerske-zajednice"]',
            )
            stats["zajednica"] += 1

        for r in oblici:
            naziv = (r.get("NAZIV_ORGANIZACIJSKOG_OBLIKA") or "").strip()
            if not naziv:
                stats["bez_naziva"] += 1
                continue
            zajednica = (r.get("VJERSKA_ZAJEDNICA") or "").strip() or None
            # Denominacija se izvodi iz zajednice (pouzdanije), pa iz naziva.
            rel, den = denom_for(zajednica or "") or denom_for(naziv) or (None, None)

            street, city = split_sjediste(r.get("SJEDISTE"))
            oib = (r.get("OIB_ORGANIZACIJSKOG_OBLIKA") or "").strip() or None
            sbt = r.get("SBT_ID")
            # Isti razlog kao u scripts/02: bez OIB-a slug nije jedinstven,
            # SBT_ID je fallback ključ evidencije.
            slug = slugify(naziv, city, suffix=oib[-4:] if oib else (str(sbt) if sbt else None))

            existing = None
            if oib:
                existing = conn.execute(
                    "SELECT id, slug, source FROM parishes WHERE oib = ?", (oib,)
                ).fetchone()
            elif sbt:
                existing = conn.execute(
                    "SELECT id, slug, source FROM parishes WHERE registry_id = ?", (sbt,)
                ).fetchone()
            if existing:
                slug = existing["slug"]

            kind = org_kind(naziv)
            upsert_parish(
                conn,
                slug,
                naziv,
                short_name=title_case_hr(naziv),
                kind=kind,
                religion=rel,
                denomination=den,
                titular=titular.parse(naziv),
                oib=oib,
                diocese=title_case_hr(zajednica) if zajednica else None,
                community=title_case_hr(zajednica) if zajednica else None,
                address=street,
                city=city,
                registry_no=(r.get("EVIDENCIJSKI_BROJ") or "").strip() or None,
                registry_id=sbt,
                registry_status=(r.get("STATUS") or "").strip() or None,
                registered_at=(r.get("DATUM_UPISA") or "")[:10] or None,
                leader_title=(r.get("SLUZBA_OSOBE_OVLASTENE_ZA_ZASTUPANJE") or "").strip() or None,
                source=merge_source(existing["source"] if existing else None,
                                    "datagovhr:vjerske-zajednice"),
            )
            stats[kind] += 1
            stats["ok"] += 1

        # Broj org. oblika po zajednici (za `dioceses.parish_count`).
        mark_duplicates(conn)
        for row in conn.execute(
            "SELECT diocese, COUNT(*) n FROM parishes WHERE community IS NOT NULL "
            "AND (registry_status IS NULL OR registry_status LIKE 'AKTIV%') "
            "AND duplicate_of IS NULL GROUP BY diocese"
        ).fetchall():
            conn.execute(
                "UPDATE dioceses SET parish_count = ? WHERE name = ?",
                (row["n"], row["diocese"]),
            )

        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM parishes").fetchone()[0]
        d = conn.execute("SELECT COUNT(*) FROM dioceses").fetchone()[0]

    log.info("gotovo: %s", dict(stats))
    log.info("pravnih osoba ukupno: %d | zajednica/biskupija: %d", n, d)


if __name__ == "__main__":
    run()
