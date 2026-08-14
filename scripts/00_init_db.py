"""Kreiraj SQLite shemu (idempotentno).

  uv run python scripts/00_init_db.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import DB_PATH, init_db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("init-db")


def run() -> None:
    init_db()
    log.info("shema spremna: %s", DB_PATH)


if __name__ == "__main__":
    run()
