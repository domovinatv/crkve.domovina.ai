"""Izgradi FTS5 indeks nad građevinama i župama (pretraga u appu/CLI-ju).

Isti obrazac kao klubovi.domovina.ai/scripts/08_build_fts.py: tablice se ruše i
grade ispočetka (jeftinije od inkrementalnog održavanja za ovaj volumen i
uklanja rizik da indeks odluta od podataka).

Indeksira se naziv + titular + mjesto + županija, s `unicode61 remove_diacritics 2`
pa "sv jurja lovran" nađe "Crkva sv. Jurja" u Lovranu.

NAMJERNO **bez `content=`** (external-content FTS5): mjesto se indeksira kao
`COALESCE(city, settlement, municipality)` jer `city` (OSM `addr:city`) postoji
samo za dio crkava, a naselje za sve. Kod external-content tablice SQLite
pretpostavlja da su indeksirane vrijednosti identične onima u izvornoj tablici
— izvedena vrijednost bi razišla indeks i sadržaj, `integrity-check` bi pao, a
`rebuild` tiho izgubio pogotke. Vlastita kopija od ~7000 redaka je jeftinija
od te klase bugova.

  uv run python scripts/30_build_fts.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import connect  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fts")

DDL = """
DROP TABLE IF EXISTS churches_fts;
CREATE VIRTUAL TABLE churches_fts USING fts5(
  name, titular, city, county, kind,
  tokenize="unicode61 remove_diacritics 2"
);
INSERT INTO churches_fts (rowid, name, titular, city, county, kind)
  SELECT id, name, COALESCE(titular,''), COALESCE(city, settlement, municipality, ''),
         COALESCE(county,''), COALESCE(kind,'')
  FROM churches;

DROP TABLE IF EXISTS parishes_fts;
CREATE VIRTUAL TABLE parishes_fts USING fts5(
  name, short_name, titular, city, diocese,
  tokenize="unicode61 remove_diacritics 2"
);
INSERT INTO parishes_fts (rowid, name, short_name, titular, city, diocese)
  SELECT id, name, COALESCE(short_name,''), COALESCE(titular,''),
         COALESCE(city,''), COALESCE(diocese,'')
  FROM parishes;
"""


def run() -> None:
    with connect() as conn:
        conn.executescript(DDL)
        conn.commit()
        c = conn.execute("SELECT COUNT(*) FROM churches_fts").fetchone()[0]
        p = conn.execute("SELECT COUNT(*) FROM parishes_fts").fetchone()[0]
        demo = conn.execute(
            "SELECT name, city FROM churches_fts WHERE churches_fts MATCH ? LIMIT 3",
            ("sv jurja",),
        ).fetchall()
    log.info("FTS: %d građevina, %d pravnih osoba", c, p)
    log.info("proba 'sv jurja': %s", [(r["name"], r["city"]) for r in demo])


if __name__ == "__main__":
    run()
