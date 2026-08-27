"""SQLite shema + upsert helperi za katalog crkava i sakralnih objekata.

Prilagođeno iz ../rodjendaonice.domovina.ai/src/db.py (koji je izveden iz
../klubovi.domovina.ai/src/db.py). Isti obrazac: slug je prirodni ključ,
upsert je idempotentan, `source` je JSON array pa se zna odakle je što došlo.

Dvije glavne tablice, namjerno razdvojene:

  churches   GRAĐEVINA — crkva, kapela, katedrala, samostanska crkva, džamija,
             sinagoga, poklonac. Ima koordinate. Izvor: OSM + Wikidata +
             Registar kulturnih dobara.

  parishes   PRAVNA OSOBA — župa, samostan, crkvena općina, parohija, džemat.
             Ima OIB i sjedište, ne mora imati koordinate. Izvor: državne
             evidencije (Ministarstvo pravosuđa i uprave preko data.gov.hr).

Odnos je N:1 — jedna župa ima župnu crkvu (`is_parish_church=1`) plus
filijalne crkve i kapele; crkva bez župe (samostanska, grobljanska, kapela
na privatnom posjedu) ima `parish_id IS NULL`. To je razlog zašto model NIJE
jedna tablica: 1563 župa iz registra i ~6800 građevina iz OSM-a nisu isti
skup i ne preslikavaju se 1:1.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "crkve.db"

SCHEMA = """
-- ---------------------------------------------------------------------------
-- GRAĐEVINE
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS churches (
  id              INTEGER PRIMARY KEY,
  slug            TEXT UNIQUE NOT NULL,
  name            TEXT NOT NULL,
  name_official   TEXT,      -- official_name / naziv iz registra ako se razlikuje
  kind            TEXT,      -- crkva | kapela | katedrala | bazilika | svetiste |
                             --   samostan | pravoslavna-crkva | dzamija |
                             --   sinagoga | poklonac | ostalo
  religion        TEXT,      -- christian | muslim | jewish | ...
  denomination    TEXT,      -- roman_catholic | serbian_orthodox | greek_catholic |
                             --   evangelical | baptist | ...
  titular         TEXT,      -- titular/zaštitnik: "sv. Marko", "Uznesenje BDM"

  -- Lokacija
  address         TEXT,
  city            TEXT,      -- addr:city / naselje
  settlement      TEXT,      -- mjesto smještaja (Registar kulturnih dobara)
  municipality    TEXT,      -- općina/grad (JLS)
  county          TEXT,      -- županija
  postal_code     TEXT,
  lat             REAL,
  lng             REAL,
  geom_kind       TEXT,      -- 'node' | 'way' | 'relation' (OSM primitiv)

  -- Veza na pravnu osobu
  parish_id       INTEGER REFERENCES parishes(id),
  is_parish_church INTEGER DEFAULT 0,   -- 1 = župna crkva te župe

  -- Vanjski identifikatori (svaki je i dedup ključ)
  osm_type        TEXT,      -- node | way | relation
  osm_id          INTEGER,
  wikidata_id     TEXT,      -- Q…
  wikipedia_url   TEXT,
  commons_image   TEXT,
  heritage_id     TEXT,      -- Oznaka_dobra iz Registra kulturnih dobara (Z-1234)
  heritage_status TEXT,      -- 'zaštićeno kulturno dobro' | 'preventivno zaštićeno' | ...
  heritage_class  TEXT,      -- Klasifikacija (sakralna graditeljska baština…)
  heritage_desc   TEXT,      -- Opis_dobra
  unesco          INTEGER DEFAULT 0,

  -- Povijest / gradnja
  year_built      TEXT,      -- start_date (OSM) ili Vrijeme_nastanka (MinKulture)
  architect       TEXT,
  style           TEXT,      -- building:architecture

  -- Kontakt
  phone           TEXT,
  email           TEXT,
  website         TEXT,

  -- Nezavisna provjera lokacije (Google Places, scripts/13)
  google_place_id TEXT,
  geo_verified    INTEGER DEFAULT 0,  -- 1 = Places potvrdio lokaciju/match
  geo_verify_m    REAL,               -- udaljenost OSM ↔ Places, u metrima

  -- Meta
  source          TEXT,      -- JSON array: ["osm","wikidata","kulturna-dobra"]
  notes           TEXT,
  created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS church_aliases (
  alias_id   INTEGER PRIMARY KEY,
  church_id  INTEGER NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
  alias      TEXT NOT NULL,
  source     TEXT,
  UNIQUE(church_id, alias, source)
);

-- ---------------------------------------------------------------------------
-- PRAVNE OSOBE (župe, samostani, crkvene općine, parohije, džemati)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parishes (
  id              INTEGER PRIMARY KEY,
  slug            TEXT UNIQUE NOT NULL,
  name            TEXT NOT NULL,       -- "ŽUPA SV. MARKA EVANĐELISTA, ZAGREB"
  short_name      TEXT,                -- bez prefiksa "ŽUPA", title-case
  kind            TEXT,                -- zupa | samostan | crkvena-opcina |
                                       --   parohija | dzemat | biskupija |
                                       --   provincija | caritas | ostalo
  religion        TEXT,
  denomination    TEXT,
  titular         TEXT,                -- parsan iz naziva župe

  oib             TEXT,
  diocese         TEXT,                -- (nad)biskupija / eparhija / zajednica
  community       TEXT,                -- naziv vjerske zajednice (nekatolici)

  address         TEXT,                -- sjedište, kako stoji u evidenciji
  city            TEXT,
  county          TEXT,
  lat             REAL,
  lng             REAL,
  geocode_source  TEXT,                -- 'nominatim' | 'church' | NULL

  registry_no     TEXT,                -- EVIDENCIJSKI_BROJ
  registry_id     INTEGER,             -- SBT_ID
  registry_status TEXT,                -- AKTIVAN / PRESTANAK
  registered_at   TEXT,                -- DATUM_UPISA
  leader_title    TEXT,                -- SLUZBA_OSOBE (Župnik, Biskup…)

  phone           TEXT,
  email           TEXT,
  website         TEXT,

  google_place_id TEXT,
  google_maps_uri TEXT,

  source          TEXT,
  notes           TEXT,
  -- NAŠA prosudba, ne podatak iz evidencije: `registry_id` zapisa koji je isti
  -- pravni subjekt upisan dvaput. Zato zasebna kolona, a ne izmišljen
  -- `registry_status` — evidencija za oba doista piše AKTIVAN.
  duplicate_of    INTEGER,
  created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- (Nad)biskupije / eparhije / vjerske zajednice — izvedeno iz evidencija.
CREATE TABLE IF NOT EXISTS dioceses (
  id            INTEGER PRIMARY KEY,
  slug          TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  kind          TEXT,     -- nadbiskupija | biskupija | eparhija | zajednica
  religion      TEXT,
  denomination  TEXT,
  oib           TEXT,
  seat          TEXT,
  parish_count  INTEGER DEFAULT 0,
  source        TEXT,
  created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Sirovi zapisi zaštićene sakralne baštine koji se NISU uspjeli spojiti na
-- građevinu. Čuvaju se da se ne izgube i da se vidi koliko match-a fali.
CREATE TABLE IF NOT EXISTS heritage_unmatched (
  id            INTEGER PRIMARY KEY,
  heritage_id   TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  settlement    TEXT,
  municipality  TEXT,
  county        TEXT,
  klasifikacija TEXT,
  status        TEXT,
  period        TEXT,
  description   TEXT,
  created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Neslaganja između naše lokacije i Google Placesa (scripts/13). Ovo je
-- izlaz nezavisne provjere: ili je OSM točka kriva, ili je župa spojena na
-- krivu crkvu, ili je Places vratio drugi objekt. Ne popravlja se automatski
-- — izvozi se u CSV da se vidi i po potrebi razriješi ručno.
CREATE TABLE IF NOT EXISTS geo_conflicts (
  id            INTEGER PRIMARY KEY,
  parish_id     INTEGER REFERENCES parishes(id) ON DELETE CASCADE,
  church_id     INTEGER REFERENCES churches(id) ON DELETE CASCADE,
  parish_name   TEXT,
  church_name   TEXT,
  place_name    TEXT,
  place_address TEXT,
  distance_m    REAL,
  our_lat       REAL,
  our_lng       REAL,
  place_lat     REAL,
  place_lng     REAL,
  created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Teritorij biskupije, DERIVIRAN iz sjedišta župa (scripts/20). Granice
-- hrvatskih biskupija ne postoje kao javna geometrija: OSM ima 3 od 15,
-- Wikidata nijednu. Zato je ovo izračun, a ne izvor — `osm_agreement` nosi
-- izmjereno slaganje s onime što u OSM-u postoji. Vidi src/dioceses.py.
CREATE TABLE IF NOT EXISTS diocese_areas (
  diocese_id       INTEGER PRIMARY KEY REFERENCES dioceses(id) ON DELETE CASCADE,
  name             TEXT NOT NULL,
  geometry         TEXT NOT NULL,   -- GeoJSON geometrija (MultiPolygon)
  area_km2         REAL,
  population       INTEGER,         -- stanovnika na području (DZS/DGU), NE vjernika
  settlement_count INTEGER,
  parish_count     INTEGER,
  church_count     INTEGER,
  method           TEXT,            -- kako je derivirano
  osm_agreement    REAL,            -- % naselja koja se slažu s OSM granicom (NULL ako je nema)
  created_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ch_name    ON churches(name);
CREATE INDEX IF NOT EXISTS idx_ch_city    ON churches(city);
CREATE INDEX IF NOT EXISTS idx_ch_county  ON churches(county);
CREATE INDEX IF NOT EXISTS idx_ch_kind    ON churches(kind);
CREATE INDEX IF NOT EXISTS idx_ch_parish  ON churches(parish_id);
CREATE INDEX IF NOT EXISTS idx_ch_osm     ON churches(osm_type, osm_id);
CREATE INDEX IF NOT EXISTS idx_ch_wd      ON churches(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_ch_herit   ON churches(heritage_id);
CREATE INDEX IF NOT EXISTS idx_pa_oib     ON parishes(oib);
CREATE INDEX IF NOT EXISTS idx_pa_city    ON parishes(city);
CREATE INDEX IF NOT EXISTS idx_pa_diocese ON parishes(diocese);
CREATE INDEX IF NOT EXISTS idx_pa_kind    ON parishes(kind);
CREATE INDEX IF NOT EXISTS idx_alias      ON church_aliases(alias);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Kolone dodane nakon prvog izdanja sheme. `CREATE TABLE IF NOT EXISTS` ne
# dira postojeću tablicu, pa bi bez ovoga postojeća baza ostala bez njih.
_ADDED_COLUMNS = [("parishes", "duplicate_of", "INTEGER")]


def _migrate(conn: sqlite3.Connection) -> None:
    for table, column, decl in _ADDED_COLUMNS:
        have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_db(db_path: Path = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()


# Signatura je namjerno stroga: ISTI tip, naziv, mjesto I adresa, i nijedan od
# zapisa nema OIB. Labavije se ne smije — dvije zagrebačke „ŽUPA SV. MARKA
# EVANĐELISTE" su dvije stvarne pravne osobe, a spajanje po nazivu i mjestu
# tiho gubi 6 zapisa (vidi CLAUDE.md). Zadržava se najranije upisan.
_DUPLICATE_SQL = """
SELECT kind, name, city, address, COUNT(*) n
FROM parishes
WHERE oib IS NULL
  AND (registry_status IS NULL OR registry_status LIKE 'AKTIV%')
GROUP BY kind, name, city, address
HAVING n > 1
"""


def mark_duplicates(conn: sqlite3.Connection) -> int:
    """Označi višestruke upise istog subjekta. Vraća broj označenih."""
    marked = 0
    conn.execute("UPDATE parishes SET duplicate_of = NULL WHERE duplicate_of IS NOT NULL")
    for g in conn.execute(_DUPLICATE_SQL).fetchall():
        rows = conn.execute(
            "SELECT id, registry_id FROM parishes WHERE oib IS NULL "
            "AND (registry_status IS NULL OR registry_status LIKE 'AKTIV%') "
            "AND kind IS ? AND name IS ? AND city IS ? AND address IS ? "
            "ORDER BY registered_at, registry_no, id",
            (g["kind"], g["name"], g["city"], g["address"]),
        ).fetchall()
        keep = rows[0]
        for dup in rows[1:]:
            conn.execute("UPDATE parishes SET duplicate_of = ? WHERE id = ?",
                         (keep["registry_id"], dup["id"]))
            marked += 1
    return marked


def _upsert(conn: sqlite3.Connection, table: str, key: str, key_val, fields: dict) -> int:
    """Generički INSERT … ON CONFLICT(key) DO UPDATE … RETURNING id.

    None vrijednosti se NE brišu preko postojećih — ingest skripte se vrte u
    nizu (OSM, pa Wikidata, pa kulturna dobra) i kasniji izvor ne smije
    obrisati ono što je raniji popunio. Zato `COALESCE(excluded.x, table.x)`.
    """
    cols = [key, *fields.keys()]
    vals = [key_val, *fields.values()]
    placeholders = ", ".join(["?"] * len(cols))
    updates = ", ".join(
        f"{c}=COALESCE(excluded.{c}, {table}.{c})" for c in cols if c != key
    )
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT({key}) DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP "
        "RETURNING id"
    )
    return conn.execute(sql, vals).fetchone()["id"]


def upsert_church(conn: sqlite3.Connection, slug: str, name: str, **fields) -> int:
    return _upsert(conn, "churches", "slug", slug, {"name": name, **fields})


def upsert_parish(conn: sqlite3.Connection, slug: str, name: str, **fields) -> int:
    return _upsert(conn, "parishes", "slug", slug, {"name": name, **fields})


def upsert_diocese(conn: sqlite3.Connection, slug: str, name: str, **fields) -> int:
    return _upsert(conn, "dioceses", "slug", slug, {"name": name, **fields})


def add_alias(conn: sqlite3.Connection, church_id: int, alias: str, source: str) -> None:
    if not alias:
        return
    conn.execute(
        "INSERT OR IGNORE INTO church_aliases (church_id, alias, source) VALUES (?, ?, ?)",
        (church_id, alias, source),
    )


def merge_source(existing: str | None, new: str) -> str:
    """Dodaj izvor u JSON array bez duplikata, stabilnim redoslijedom."""
    import json

    try:
        cur = json.loads(existing) if existing else []
    except (json.JSONDecodeError, TypeError):
        cur = []
    if new not in cur:
        cur.append(new)
    return json.dumps(cur, ensure_ascii=False)


def find_church_by_osm(conn: sqlite3.Connection, osm_type: str, osm_id: int):
    return conn.execute(
        "SELECT * FROM churches WHERE osm_type = ? AND osm_id = ?", (osm_type, osm_id)
    ).fetchone()
