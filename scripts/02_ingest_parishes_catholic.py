"""Ingest katoličkih pravnih osoba (župe, samostani, biskupije) s data.gov.hr.

Izvor: "Evidencija pravnih osoba Katoličke Crkve u RH" (Ministarstvo
pravosuđa i uprave). ~2100 zapisa s OIB-om, sjedištem i (nad)biskupijom —
od toga ~1560 župa. To je JEDINI potpuni službeni popis župa u RH; crkveni
šematizmi su per-biskupija, u PDF-u, i nisu strojno čitljivi.

Zapisi se dijele na:
  kind='zupa'        NAZIV počinje sa "ŽUPA"           (~1563)
  kind='samostan'    SAMOSTAN / REZIDENCIJA / KARMEL   (~110)
  kind='biskupija'   (NAD)BISKUPIJA — ide i u `dioceses`
  kind='provincija'  redovničke provincije i družbe
  kind='caritas'     Caritas ustanove
  kind='ostalo'      škole, sjemeništa, zaklade…

Statusom PRESTANAK označene osobe (13) se uvoze ali se filtriraju u exportu.

  uv run python scripts/02_ingest_parishes_catholic.py
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
from src.datagovhr import KATOLICKE_PRAVNE_OSOBE, fetch, split_sjediste  # noqa: E402
from src.db import connect, mark_duplicates, merge_source, upsert_diocese, upsert_parish  # noqa: E402
from src.normalize import slugify, title_case_hr  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("zupe-kat")

_KIND_RULES: list[tuple[str, re.Pattern]] = [
    ("zupa", re.compile(r"^\s*ŽUPA\b", re.I)),
    ("biskupija", re.compile(r"^\s*(NAD)?BISKUPIJA\b|\bNADBISKUPIJA\s*$|\bBISKUPIJA\s*$", re.I)),
    ("samostan", re.compile(r"\bSAMOSTAN|\bREZIDENCIJA\b|\bKARMEL\b|\bOPATIJA\b", re.I)),
    ("provincija", re.compile(r"\bPROVINCIJA\b|\bDRUŽBA\b|\bKUSTODIJA\b|\bRED\b", re.I)),
    ("caritas", re.compile(r"\bCARITAS\b", re.I)),
    ("svetiste", re.compile(r"\bSVETIŠTE\b", re.I)),
]


def classify(naziv: str) -> str:
    for kind, pat in _KIND_RULES:
        if pat.search(naziv or ""):
            return kind
    return "ostalo"


def short_name(naziv: str) -> str:
    """"ŽUPA SV. MARKA EVANĐELISTA, ZAGREB" → "sv. Marko Evanđelist, Zagreb"."""
    core = re.sub(r"^\s*ŽUPA\s+", "", naziv or "", flags=re.I)
    return title_case_hr(core)


def run() -> None:
    rows = fetch(KATOLICKE_PRAVNE_OSOBE)
    log.info("zapisa u evidenciji: %d", len(rows))

    stats = Counter()
    with connect() as conn:
        for r in rows:
            naziv = (r.get("NAZIV") or "").strip()
            if not naziv:
                stats["bez_naziva"] += 1
                continue

            kind = classify(naziv)
            street, city = split_sjediste(r.get("SJEDISTE"))
            oib = (r.get("OIB") or "").strip() or None
            sbt = r.get("SBT_ID")

            # Slug: naziv+grad je čitljiv dio, ali NIJE jedinstven — 723 zapisa
            # nema OIB, a "ŽUPA SV. MARKA EVANĐELISTE, Zagreb" postoji dvaput
            # (Jakuševec i Trg sv. Marka). Zato sufiks: OIB ako ga ima, inače
            # SBT_ID (interni id evidencije, uvijek prisutan i stabilan).
            suffix = oib[-4:] if oib else (str(sbt) if sbt else None)
            slug = slugify(naziv, city, suffix=suffix)

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

            diocese = (r.get("BISKUPIJA_NADBISKUPIJA") or "").strip() or None

            parish_id = upsert_parish(
                conn,
                slug,
                naziv,
                short_name=short_name(naziv) if kind == "zupa" else title_case_hr(naziv),
                kind=kind,
                religion="christian",
                denomination="roman_catholic",
                titular=titular.parse(naziv) if kind in ("zupa", "svetiste") else None,
                oib=oib,
                diocese=title_case_hr(diocese) if diocese else None,
                address=street,
                city=city,
                registry_no=(r.get("EVIDENCIJSKI_BROJ") or "").strip() or None,
                registry_id=sbt,
                registry_status=(r.get("STATUS") or "").strip() or None,
                registered_at=(r.get("DATUM_UPISA") or "")[:10] or None,
                leader_title=(r.get("SLUZBA_OSOBE") or "").strip() or None,
                source=merge_source(existing["source"] if existing else None,
                                    "datagovhr:katolicke-pravne-osobe"),
            )
            stats[kind] += 1
            stats["ok"] += 1

            if kind == "biskupija":
                is_arch = "NADBISKUPIJA" in naziv.upper()
                upsert_diocese(
                    conn,
                    slugify(naziv),
                    title_case_hr(naziv),
                    kind="nadbiskupija" if is_arch else "biskupija",
                    religion="christian",
                    denomination="roman_catholic",
                    oib=oib,
                    seat=city,
                    source='["datagovhr:katolicke-pravne-osobe"]',
                )

        # Biskupije koje se pojavljuju samo kao strani ključ u BISKUPIJA_
        # NADBISKUPIJA (a nemaju vlastiti zapis) — dodaj ih da popis bude pun.
        mark_duplicates(conn)
        for row in conn.execute(
            "SELECT diocese, COUNT(*) n FROM parishes "
            "WHERE diocese IS NOT NULL AND kind = 'zupa' "
            "AND (registry_status IS NULL OR registry_status LIKE 'AKTIV%') "
            "AND duplicate_of IS NULL GROUP BY diocese"
        ).fetchall():
            d = row["diocese"]
            upsert_diocese(
                conn,
                slugify(d),
                d,
                kind="nadbiskupija" if "nadbiskupija" in d.lower() else "biskupija",
                religion="christian",
                denomination="roman_catholic",
                parish_count=row["n"],
                source='["datagovhr:katolicke-pravne-osobe"]',
            )

        conn.commit()
        n_par = conn.execute("SELECT COUNT(*) FROM parishes").fetchone()[0]
        n_dio = conn.execute("SELECT COUNT(*) FROM dioceses").fetchone()[0]

    log.info("gotovo: %s", dict(stats))
    log.info("pravnih osoba u bazi: %d | biskupija: %d", n_par, n_dio)


if __name__ == "__main__":
    run()
