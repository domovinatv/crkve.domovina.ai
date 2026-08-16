"""Preslikaj GeoJSON export u ../karta-hrvatske (layer na gis.domovina.ai).

Pandan `npm run sync-data` u karta-web, samo u suprotnom smjeru: karta-web
povlači bazne slojeve iz svog data-pipelinea, a tematske slojeve (klubovi,
crkve) daju domenski repozitoriji.

Cilj: apps/karta-web/public/data/crkve.geojson (+ zupe.geojson).
Odredište se može pregaziti s KARTA_WEB_DATA_DIR. Ako repo nije kloniran,
skripta to javi i izađe s 0 — pipeline ne smije pasti zbog susjeda.

  uv run python scripts/33_sync_karta.py
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sync-karta")

SRC = ROOT / "data" / "exports"
DEFAULT_DST = ROOT.parent / "karta-hrvatske" / "apps" / "karta-web" / "public" / "data"
FILES = ["crkve.geojson", "zupe.geojson", "biskupije.geojson"]


def run() -> int:
    dst = Path(os.environ.get("KARTA_WEB_DATA_DIR", str(DEFAULT_DST)))
    if not dst.exists():
        log.warning("Odredište ne postoji: %s — preskačem sync "
                    "(kloniraj ../karta-hrvatske ili postavi KARTA_WEB_DATA_DIR).", dst)
        return 0

    copied = 0
    for name in FILES:
        src = SRC / name
        if not src.exists():
            log.warning("  nema %s — pokreni scripts/31_export_geojson.py", src)
            continue
        shutil.copyfile(src, dst / name)
        log.info("  %s → %s (%.1f MB)", name, dst / name, src.stat().st_size / 1e6)
        copied += 1

    log.info("preslikano datoteka: %d", copied)
    log.info("sljedeći korak: cd ../karta-hrvatske/apps/karta-web && npm run deploy")
    return 0


if __name__ == "__main__":
    sys.exit(run())
