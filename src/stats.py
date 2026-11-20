"""Definicije skalarnih brojki iz `scripts/40_stats.py`, na jednom mjestu.

Izdvojeno da `src/audit.py` (kontekstne brojke uz metrike kvalitete) i
`scripts/40_stats.py` računaju „487 župa bez župne crkve" ISTIM SQL-om. Dvije
kopije istog upita razišle bi se pri prvoj izmjeni definicije — a to je
upravo brojka koju je jednom već trebalo ispraviti (vidi CLAUDE.md, „Župa bez
crkve su DVIJE različite brojke").
"""
from __future__ import annotations

import sqlite3

# Aktivna i različita pravna osoba: evidencija ima i ugašene (PRESTANAK) i
# isti subjekt upisan dvaput (`duplicate_of`, naša prosudba).
AKTIV = ("(p.registry_status IS NULL OR p.registry_status LIKE 'AKTIV%') "
         "AND p.duplicate_of IS NULL")

# Redoslijed je redoslijed ključeva u data/exports/stats.json — ne mijenjati
# bez razloga, 34_export_static i frontend čitaju te ključeve.
SQL: dict[str, str] = {
    "crkve_ukupno": "SELECT COUNT(*) FROM churches",
    "crkve_s_koordinatama": "SELECT COUNT(*) FROM churches WHERE lat IS NOT NULL",
    "crkve_sa_zupanijom": "SELECT COUNT(*) FROM churches WHERE county IS NOT NULL",
    "crkve_s_titularom": "SELECT COUNT(*) FROM churches WHERE titular IS NOT NULL",
    "crkve_sa_zastitom": "SELECT COUNT(*) FROM churches WHERE heritage_id IS NOT NULL",
    "crkve_sa_slikom": "SELECT COUNT(*) FROM churches WHERE commons_image IS NOT NULL",
    "crkve_s_wikipedijom": "SELECT COUNT(*) FROM churches WHERE wikipedia_url IS NOT NULL",
    "crkve_sa_zupom": "SELECT COUNT(*) FROM churches WHERE parish_id IS NOT NULL",
    "zupne_crkve": "SELECT COUNT(*) FROM churches WHERE is_parish_church = 1",
    "crkve_s_tlocrtom": "SELECT COUNT(*) FROM churches WHERE geom_kind IN ('way','relation')",
    "crkve_lokacija_potvrdjena": "SELECT COUNT(*) FROM churches WHERE geo_verified = 1",
    "geo_konflikti": "SELECT COUNT(*) FROM geo_conflicts",
    "pravne_osobe_ukupno": "SELECT COUNT(*) FROM parishes",
    "zupe_katolicke": "SELECT COUNT(*) FROM parishes WHERE kind = 'zupa'",
    # 1563 je koliko ZAPISA evidencija ima; jedan je ugašen
    # (PRESTANAK), jedan je isti subjekt upisan dvaput (Prgomet).
    "zupe_aktivne": "SELECT COUNT(*) FROM parishes p WHERE p.kind = 'zupa' AND " + AKTIV,
    "zupe_s_koordinatama": "SELECT COUNT(*) FROM parishes WHERE lat IS NOT NULL",
    "zupe_s_oib": "SELECT COUNT(*) FROM parishes WHERE oib IS NOT NULL",
    "zupe_s_telefonom": "SELECT COUNT(*) FROM parishes WHERE phone IS NOT NULL",
    "zupe_s_webom": "SELECT COUNT(*) FROM parishes WHERE website IS NOT NULL",
    # Dvije različite rupe, ne jedna: župa može imati spojene filijale
    # a ne i vlastitu župnu crkvu. Brojka 1563 − zupne_crkve je kriva
    # jer 77 župnih crkava pripada pravnim osobama koje nisu `zupa`
    # (samostani, svetišta).
    "zupe_bez_zupne_crkve": (
        "SELECT COUNT(*) FROM parishes p WHERE p.kind = 'zupa' AND " + AKTIV +
        " AND NOT EXISTS("
        " SELECT 1 FROM churches c WHERE c.parish_id = p.id AND c.is_parish_church = 1)"
    ),
    "zupe_bez_ijedne_crkve": (
        "SELECT COUNT(*) FROM parishes p WHERE p.kind = 'zupa' AND " + AKTIV +
        " AND NOT EXISTS("
        " SELECT 1 FROM churches c WHERE c.parish_id = p.id)"
    ),
    "biskupije_i_zajednice": "SELECT COUNT(*) FROM dioceses",
    "bastina_nespojena": "SELECT COUNT(*) FROM heritage_unmatched",
}


def scalar(conn: sqlite3.Connection, key: str) -> int:
    return conn.execute(SQL[key]).fetchone()[0]


def scalars(conn: sqlite3.Connection) -> dict[str, int]:
    return {k: scalar(conn, k) for k in SQL}
