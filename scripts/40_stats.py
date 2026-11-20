"""Izvještaj o pokrivenosti i kvaliteti kataloga.

Ovo je mjerni instrument projekta — ono što ide u README tablicu i ono po
čemu se vidi je li novi run pipelinea nešto pokvario. Piše i
data/exports/stats.json da frontend/karta mogu prikazati brojke.

  uv run python scripts/40_stats.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import connect  # noqa: E402
from src.stats import scalars  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stats")

OUT = ROOT / "data" / "exports" / "stats.json"


def run() -> None:
    with connect() as conn:
        stats = scalars(conn)

        stats["zupe_po_izvoru_koordinata"] = {
            (r["geocode_source"] or "?"): r["n"] for r in conn.execute(
                "SELECT geocode_source, COUNT(*) n FROM parishes WHERE lat IS NOT NULL "
                "GROUP BY geocode_source ORDER BY n DESC"
            )
        }
        stats["po_tipu"] = {
            r["kind"] or "?": r["n"] for r in conn.execute(
                "SELECT kind, COUNT(*) n FROM churches GROUP BY kind ORDER BY n DESC"
            )
        }
        stats["po_zupaniji"] = {
            r["county"] or "?": r["n"] for r in conn.execute(
                "SELECT county, COUNT(*) n FROM churches GROUP BY county ORDER BY n DESC"
            )
        }
        stats["po_konfesiji"] = {
            r["denomination"] or "?": r["n"] for r in conn.execute(
                "SELECT denomination, COUNT(*) n FROM churches "
                "GROUP BY denomination ORDER BY n DESC LIMIT 15"
            )
        }
        stats["zupe_po_biskupiji"] = {
            r["diocese"] or "?": r["n"] for r in conn.execute(
                "SELECT diocese, COUNT(*) n FROM parishes WHERE kind = 'zupa' "
                "GROUP BY diocese ORDER BY n DESC"
            )
        }
        stats["najcesci_titulari"] = {
            r["titular"]: r["n"] for r in conn.execute(
                "SELECT titular, COUNT(*) n FROM churches WHERE titular IS NOT NULL "
                "GROUP BY titular ORDER BY n DESC LIMIT 20"
            )
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2))

    def pct(a: int, b: int) -> str:
        return f"{100 * a / b:.1f}%" if b else "—"

    n = stats["crkve_ukupno"]
    print()
    print("═" * 62)
    print("  KATALOG CRKAVA I SAKRALNIH OBJEKATA U HRVATSKOJ")
    print("═" * 62)
    print(f"  Građevina ukupno            {n:>7}")
    print(f"  … s koordinatama            {stats['crkve_s_koordinatama']:>7}  {pct(stats['crkve_s_koordinatama'], n)}")
    print(f"  … s tlocrtom (ne točka)     {stats['crkve_s_tlocrtom']:>7}  {pct(stats['crkve_s_tlocrtom'], n)}")
    print(f"  … sa županijom              {stats['crkve_sa_zupanijom']:>7}  {pct(stats['crkve_sa_zupanijom'], n)}")
    print(f"  … s titularom               {stats['crkve_s_titularom']:>7}  {pct(stats['crkve_s_titularom'], n)}")
    print(f"  … sa zaštitom (MinKulture)  {stats['crkve_sa_zastitom']:>7}  {pct(stats['crkve_sa_zastitom'], n)}")
    print(f"  … sa slikom (Commons)       {stats['crkve_sa_slikom']:>7}  {pct(stats['crkve_sa_slikom'], n)}")
    print(f"  … povezano sa župom         {stats['crkve_sa_zupom']:>7}  {pct(stats['crkve_sa_zupom'], n)}")
    print(f"  … lokacija potvrđena (Places){stats['crkve_lokacija_potvrdjena']:>6}  {pct(stats['crkve_lokacija_potvrdjena'], n)}")
    print(f"  … od toga župnih crkava     {stats['zupne_crkve']:>7}")
    print("─" * 62)
    print(f"  Pravnih osoba (župe i sl.)  {stats['pravne_osobe_ukupno']:>7}")
    print(f"  … katoličkih župa           {stats['zupe_katolicke']:>7}"
          f"  (aktivnih i različitih: {stats['zupe_aktivne']})")
    print(f"  … s koordinatama            {stats['zupe_s_koordinatama']:>7}  {pct(stats['zupe_s_koordinatama'], stats['pravne_osobe_ukupno'])}")
    print(f"  … s telefonom / webom       {stats['zupe_s_telefonom']:>7} / {stats['zupe_s_webom']}")
    print(f"  … župa bez župne crkve      {stats['zupe_bez_zupne_crkve']:>7}"
          f"  (bez ijedne: {stats['zupe_bez_ijedne_crkve']})")
    print(f"  Biskupija i zajednica       {stats['biskupije_i_zajednice']:>7}")
    print(f"  Baština bez para            {stats['bastina_nespojena']:>7}")
    print(f"  Geo konflikata za pregled   {stats['geo_konflikti']:>7}")
    print("─" * 62)
    print("  Po tipu:", ", ".join(f"{k} {v}" for k, v in list(stats["po_tipu"].items())[:8]))
    print("═" * 62)
    log.info("zapisano: %s", OUT)


if __name__ == "__main__":
    run()
