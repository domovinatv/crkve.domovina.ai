"""Audit kvalitete podataka: metrike grešaka iz src/audit.py.

Ispisuje tablicu metrika i piše audit.json — bez vremena i sa sortiranim
popisima, pa isti ulaz daje isti sha. Bazu otvara SAMO ZA ČITANJE, da se
smije pustiti i na kopiju ili na bazu koju pipeline upravo gradi.

  uv run python scripts/41_audit.py
  uv run python scripts/41_audit.py --db /tmp/crkve-kopija.db --out /tmp/audit.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import audit  # noqa: E402
from src.db import DB_PATH  # noqa: E402

OUT = ROOT / "data" / "exports" / "audit.json"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=Path, default=DB_PATH, help="SQLite baza (default data/crkve.db)")
    ap.add_argument("--out", type=Path, default=OUT, help="izlazni JSON (default data/exports/audit.json)")
    args = ap.parse_args(argv)

    if not args.db.exists():
        sys.exit(f"nema baze: {args.db}")
    conn = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        result = audit.run(conn)
    finally:
        conn.close()

    print(audit.format_table(result))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"\nzapisano: {args.out}")


if __name__ == "__main__":
    main()
