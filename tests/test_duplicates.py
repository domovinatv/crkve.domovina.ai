"""Evidencija zna isti pravni subjekt upisati dvaput (ŽUPA SV. STJEPANA,
Prgomet: dva evidencijska broja, ista adresa, tri mjeseca razmaka). Na karti
je to dvije točke jedna na drugoj, od kojih jedna nosi crveni prsten „nema
župnu crkvu" jer je matcher crkvu mogao dati samo jednoj.

Signatura mora ostati stroga: dvije zagrebačke „ŽUPA SV. MARKA EVANĐELISTE"
su dvije stvarne župe, a spajanje po nazivu i mjestu tiho gubi 6 zapisa.
"""
from __future__ import annotations

import pytest

from src.db import connect, init_db, mark_duplicates


def _add(conn, **kw):
    cols = ", ".join(kw)
    conn.execute(f"INSERT INTO parishes ({cols}) VALUES ({', '.join('?' * len(kw))})",
                 tuple(kw.values()))


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    init_db(path)
    with connect(path) as conn:
        yield conn


def _marked(conn):
    return {r["registry_id"] for r in
            conn.execute("SELECT registry_id FROM parishes WHERE duplicate_of IS NOT NULL")}


def test_isti_zapis_dvaput_ostavlja_najraniji(db):
    for rid, no, date in (("701385", "1.617", "2004-11-10"),
                          ("702150", "1.1296", "2005-02-14")):
        _add(db, slug=f"prgomet-{rid}", name="ŽUPA SV. STJEPANA", kind="zupa",
             city="Prgomet", address="Labin dalmatinski bb", registry_id=rid,
             registry_no=no, registered_at=date, registry_status="AKTIVAN")
    assert mark_duplicates(db) == 1
    assert _marked(db) == {702150}
    kept = db.execute("SELECT duplicate_of FROM parishes WHERE registry_id=702150").fetchone()
    assert kept["duplicate_of"] == 701385


def test_razlicita_adresa_nije_duplikat(db):
    """Povlja i Bol imaju istoimenu župu sv. Ivana Krstitelja u istoj biskupiji."""
    for rid, city, addr in (("1", "Bol", "Pjaca Joze Bodlovića 1"),
                            ("2", "Povlja", "Lokva 1")):
        _add(db, slug=f"ivan-{rid}", name="ŽUPA SV. IVANA KRSTITELJA", kind="zupa",
             city=city, address=addr, registry_id=rid, registry_status="AKTIVAN")
    assert mark_duplicates(db) == 0


def test_zapis_s_oib_om_nikad_nije_duplikat(db):
    """OIB je identitet pravne osobe — dva OIB-a su dvije osobe, ma koliko se
    nazivi poklapali."""
    for rid, oib in (("1", "11111111111"), ("2", "22222222222")):
        _add(db, slug=f"x-{rid}", name="ŽUPA SV. MARKA EVANĐELISTE", kind="zupa",
             city="Zagreb", address="Trg 1", registry_id=rid, oib=oib,
             registry_status="AKTIVAN")
    assert mark_duplicates(db) == 0


def test_ugasen_upis_se_ne_broji(db):
    """Prizna ima dva upisa, ali je jedan PRESTANAK — filtri ga ionako izbacuju,
    pa ga ne smijemo još i označiti kao duplikat aktivnoga."""
    _add(db, slug="prizna-a", name="ŽUPA SV. IVANA KRSTITELJA", kind="zupa",
         city="Prizna", address="Prizna bb", registry_id="702381",
         registry_status="PRESTANAK", registered_at="2005-03-18")
    _add(db, slug="prizna-b", name="ŽUPA SV. IVANA KRSTITELJA", kind="zupa",
         city="Prizna", address="Prizna bb", registry_id="702387",
         registry_status="AKTIVAN", registered_at="2005-03-21")
    assert mark_duplicates(db) == 0


def test_ponovni_run_ne_umnaza(db):
    for rid, date in (("1", "2004-01-01"), ("2", "2005-01-01"), ("3", "2006-01-01")):
        _add(db, slug=f"y-{rid}", name="ŽUPA X", kind="zupa", city="Y",
             address="Z 1", registry_id=rid, registered_at=date,
             registry_status="AKTIVAN")
    assert mark_duplicates(db) == 2
    assert mark_duplicates(db) == 2
    assert _marked(db) == {2, 3}
