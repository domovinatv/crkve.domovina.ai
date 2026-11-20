"""Dedup OSM node + way (src/dedup.py, odluke 400–404).

Primjeri su stvarni parovi iz audita `node_way_duplikati` (S4), s OSM id-ovima,
koordinatama i tagovima iz keša `data/raw/osm`. Bez mreže; baza je in-memory
s pravom shemom.
"""
from __future__ import annotations

import random
import sqlite3

import pytest

from src import audit, dedup
from src.db import SCHEMA, _migrate
from src.dedup import Zapis


def z(osm_type, osm_id, lat, lng, name, named=True, role="worship", amenity=None,
      wikidata=None) -> Zapis:
    return Zapis(osm_type, osm_id, lat, lng, name, named, role, amenity, wikidata)


# --- Stvarni primjeri -----------------------------------------------------------

# Kanfanar: čvor s imenom (amenity) i bezimeni tlocrt building=church, 2 m.
PETRONILA_N = z("node", 10985250504, 45.122086, 13.8312917, "Crkva Sv. Petronila",
                amenity="place_of_worship")
PETRONILA_W = z("way", 1489968766, 45.1221002, 13.8313109, "Crkva", named=False)

# Šibenik: samostan (amenity=monastery) i crkva sv. Frane, 25 m.
FRANE_SAMOSTAN = z("node", 6710912634, 43.7337455, 15.891784, "Samostan sv. Frane",
                   role="monastery", amenity="monastery")
FRANE_CRKVA = z("way", 376493968, 43.733812, 15.8920858, "Crkva svetog Frane",
                amenity="place_of_worship")

# Šenkovec: poklonac „Sveta Jelena” (historic=wayside_shrine) uz crkvu, 22 m.
JELENA_POKLONAC = z("node", 4710271085, 46.4035531, 16.4192863, "Sveta Jelena",
                    role="shrine")
JELENA_CRKVA = z("way", 377888694, 46.4036107, 16.4195565,
                 "crkva svete Jelene Križarice", amenity="place_of_worship")

# Zagreb, Frankopanska: samostan sv. Vinka (čvor) i bezimeni building=monastery
# 23 m dalje — čisti tlocrt, jedini kandidat (odluka 401).
VINKO_SAMOSTAN = z("node", 6713054201, 45.8110804, 15.9694916, "Samostan svetog Vinka",
                   role="monastery", amenity="monastery")
VINKO_TLOCRT = z("way", 1242375443, 45.8112622, 15.9696215, "Sakralni objekt",
                 named=False, role="monastery")
VINKO_CRKVA = z("way", 435636894, 45.8112225, 15.9696263, "crkva svetog Vinka",
                amenity="place_of_worship", wikidata="Q26256693")

# Veli Lošinj: bezimeni tlocrt i DVA čvora s različitim titularom (0,4 m i 28 m).
LOSINJ_W = z("way", 1451602469, 44.523449, 14.5016691, "Crkva", named=False)
NAVJESTENJE_N = z("node", 9155894314, 44.5234514, 14.5016659,
                  "Crkvica Navjestenja B. D. Marije", amenity="place_of_worship")
KRIZ_N = z("node", 11264691774, 44.5235354, 14.502003, "Crkva Svetog Križa",
           amenity="place_of_worship")

# Mokošica: dva „Presvetog Spasitelja” na 38 m, oba s amenity — neodlučivo.
SPASITELJ_N = z("node", 12433613079, 42.6759325, 18.0927273, "Crkva Presvetog Spasitelja",
                amenity="place_of_worship")
SPASITELJ_W = z("way", 1228836695, 42.6756623, 18.092433, "crkva Presvetog Spasitelja",
                amenity="place_of_worship")


def _par(spojevi) -> set[tuple[str, str]]:
    return {(s.node.key, s.way.key) for s in spojevi}


def test_cvor_i_bezimeni_tlocrt_iste_crkve_spajaju_se():
    sp = dedup.plan([PETRONILA_N, PETRONILA_W])
    assert _par(sp) == {("n10985250504", "w1489968766")}
    assert sp[0].razlog == "bez_imena" and sp[0].distance_m < 3


def test_samostan_uz_crkvu_ostaju_dvije_zgrade():
    assert 20 < dedup.haversine_m(FRANE_SAMOSTAN.lat, FRANE_SAMOSTAN.lng,
                                  FRANE_CRKVA.lat, FRANE_CRKVA.lng) < 30
    assert dedup.zapreka(FRANE_SAMOSTAN, FRANE_CRKVA) == "uloga"
    # Uloga presuđuje i na 0 m — prag tu nije razlog.
    assert dedup.plan([FRANE_SAMOSTAN, FRANE_CRKVA], prag_m=1000, prag_tlocrt_m=1000) == []


def test_poklonac_uz_crkvu_ostaju_dvije_zgrade():
    assert dedup.zapreka(JELENA_POKLONAC, JELENA_CRKVA) == "uloga"
    assert dedup.plan([JELENA_POKLONAC, JELENA_CRKVA], prag_m=1000, prag_tlocrt_m=1000) == []


def test_samostan_ide_u_tlocrt_samostana_a_ne_u_crkvu():
    sp = dedup.plan([VINKO_SAMOSTAN, VINKO_TLOCRT, VINKO_CRKVA])
    assert _par(sp) == {("n6713054201", "w1242375443")}
    assert sp[0].razlog == "bez_imena+tlocrt" and 20 < sp[0].distance_m < 25


def test_prosireni_prag_samo_za_jedinog_kandidata():
    # Navještenje (0,4 m) se spaja; Sv. Križ (28 m) nije jedini kandidat za
    # isti bezimeni tlocrt, pa ostaje — dvije crkve različitih titulara.
    sp = dedup.plan([LOSINJ_W, NAVJESTENJE_N, KRIZ_N])
    assert _par(sp) == {("n9155894314", "w1451602469")}


def test_vise_cvorova_u_isti_way_samo_medusobno_spojivi():
    # Oba čvora na < 20 m od bezimenog tlocrta, ali različitih titulara:
    # drugi se odbija (inače bi tlocrt „progutao” dvije crkve).
    kriz_blizu = z("node", 11264691774, LOSINJ_W.lat + 0.0001, LOSINJ_W.lng,
                   "Crkva Svetog Križa")
    sp = dedup.plan([LOSINJ_W, NAVJESTENJE_N, kriz_blizu])
    assert _par(sp) == {("n9155894314", "w1451602469")}


def test_imenovani_par_iznad_praga_se_ne_spaja():
    assert 35 < dedup.haversine_m(SPASITELJ_N.lat, SPASITELJ_N.lng,
                                  SPASITELJ_W.lat, SPASITELJ_W.lng) < 40
    assert dedup.plan([SPASITELJ_N, SPASITELJ_W]) == []
    assert ("n12433613079", "w1228836695") in dedup.OSTAVLJENI


def test_razliciti_titular_na_30m_dvije_zgrade():
    n = z("node", 1, 45.8, 16.0, "Crkva sv. Roka")
    w = z("way", 2, 45.8 + 0.00027, 16.0, "Crkva sv. Marka")      # ~30 m
    assert dedup.zapreka(n, w) == "nazivi"
    assert dedup.plan([n, w], prag_m=1000, prag_tlocrt_m=1000) == []


def test_sveti_marko_tri_crkve():
    # Tri različite građevine istog titulara: čvor i dva waya, svaki > prag
    # od čvora. Nijedan par se ne spaja; way+way se nikad ne spaja.
    n = z("node", 1, 45.8, 16.0, "Sveti Marko")
    w1 = z("way", 2, 45.8 + 0.0005, 16.0, "Crkva sv. Marka")      # ~56 m
    w2 = z("way", 3, 45.8, 16.0 + 0.0004, "Kapela sv. Marka")     # ~31 m
    assert dedup.plan([n, w1, w2]) == []
    w3 = z("way", 4, 45.8 + 0.0005, 16.0 + 0.00001, "Crkva sv. Marka")
    assert dedup.plan([w1, w3, w2]) == []


def test_razlicit_wikidata_tag_ne_spaja():
    n = z("node", 1, 45.8, 16.0, "Crkva sv. Marka", wikidata="Q1")
    w = z("way", 2, 45.8, 16.0, "Crkva sv. Marka", wikidata="Q2")
    assert dedup.zapreka(n, w) == "wikidata"
    assert dedup.plan([n, w]) == []
    # Wikidata samo na jednoj strani nije zapreka.
    assert len(dedup.plan([n, z("way", 2, 45.8, 16.0, "Crkva sv. Marka")])) == 1


def test_cvor_ide_najblizem_wayu_deterministicki():
    # Sv. Karlo: dva bezimena tlocrta kapele na 3 i 6 m.
    n = z("node", 2649378629, 45.8, 16.0, "Sv. Karlo")
    w_dalji = z("way", 257450093, 45.8 + 0.00005, 16.0, "Kapela", named=False)
    w_blizi = z("way", 45505315, 45.8 + 0.00003, 16.0, "Kapela", named=False)
    assert _par(dedup.plan([n, w_dalji, w_blizi])) == {("n2649378629", "w45505315")}
    # Izjednačenje po OSM id-u: na istoj udaljenosti pobjeđuje manji id.
    a = z("way", 9, 45.8 + 0.00003, 16.0, "Kapela", named=False)
    b = z("way", 8, 45.8 + 0.00003, 16.0, "Kapela", named=False)   # ista točka
    assert _par(dedup.plan([n, a, b])) == {("n2649378629", "w8")}


def test_redoslijed_ulaza_ne_mijenja_ishod():
    ulaz = [PETRONILA_N, PETRONILA_W, FRANE_SAMOSTAN, FRANE_CRKVA, JELENA_POKLONAC,
            JELENA_CRKVA, VINKO_SAMOSTAN, VINKO_TLOCRT, VINKO_CRKVA, LOSINJ_W,
            NAVJESTENJE_N, KRIZ_N, SPASITELJ_N, SPASITELJ_W]
    prvi = dedup.plan(ulaz)
    rng = random.Random(4)
    for _ in range(20):
        mijesano = ulaz[:]
        rng.shuffle(mijesano)
        assert dedup.plan(mijesano) == prvi
    assert _par(prvi) == {("n10985250504", "w1489968766"), ("n6713054201", "w1242375443"),
                          ("n9155894314", "w1451602469")}


def test_rucne_iznimke():
    # Posavski Bregi: „kapelica” tagirana kao wayside_shrine u središtu
    # tlocrta bezimene kapele (0,3 m) — pravilo je propušta zbog uloge.
    n = z("node", 8676599438, 45.6821863, 16.3514305, "kapelica Presveto Srce Isusovo",
          role="shrine")
    w = z("way", 1363262030, 45.6821834, 16.3514301, "Kapela", named=False)
    assert dedup.plan([n, w], spoji={}) == []
    sp = dedup.plan([n, w])
    assert _par(sp) == {("n8676599438", "w1363262030")} and sp[0].razlog == "rucno"
    # NE_SPAJAJ obara par koji bi pravilo spojilo.
    assert dedup.plan([PETRONILA_N, PETRONILA_W],
                      ne_spajaj={("n10985250504", "w1489968766"): "test"}) == []


def test_uloga_i_ime_iz_tagova():
    assert dedup.uloga({"amenity": "monastery"}) == "monastery"
    assert dedup.uloga({"building": "monastery", "amenity": "place_of_worship"}) == "monastery"
    assert dedup.uloga({"historic": "wayside_shrine"}) == "shrine"
    assert dedup.uloga({"building": "church"}) == "worship"
    assert not dedup.ima_ime({"building": "church"})
    assert dedup.ima_ime({"alt_name": "Sv. Ivan"})


# --- Baza: apply ----------------------------------------------------------------

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    yield conn
    conn.close()


def _ins(conn, zap: Zapis, slug: str, **kw) -> int:
    row = dict(slug=slug, name=zap.name, osm_type=zap.osm_type, osm_id=zap.osm_id,
               geom_kind=zap.osm_type, lat=zap.lat, lng=zap.lng, osm_role=zap.role,
               osm_named=int(zap.named), osm_amenity=zap.amenity,
               wikidata_id=zap.wikidata, source='["osm"]', **kw)
    cur = conn.execute(f"INSERT INTO churches ({', '.join(row)}) "
                       f"VALUES ({', '.join('?' * len(row))})", tuple(row.values()))
    return cur.lastrowid


def test_apply_prezivljava_way_s_nazivom_cvora(db):
    nid = _ins(db, PETRONILA_N, "sv-petronila-kanfanar-n10985250504", kind="crkva",
               titular="sv. Petronila", denomination="roman_catholic", city="Kanfanar")
    wid = _ins(db, PETRONILA_W, "crkva-kanfanar-w1489968766", kind="crkva",
               county="Istarska županija")
    db.execute("INSERT INTO church_aliases (church_id, alias, source) "
               "VALUES (?, 'Sv. Petronila', 'osm:alt_name')", (nid,))
    sp = dedup.apply(db)
    assert len(sp) == 1
    rows = db.execute("SELECT * FROM churches").fetchall()
    assert len(rows) == 1
    c = rows[0]
    # Identitet i geometrija waya …
    assert (c["id"], c["slug"], c["osm_type"], c["osm_id"], c["geom_kind"]) == \
        (wid, "crkva-kanfanar-w1489968766", "way", 1489968766, "way")
    assert (c["lat"], c["lng"]) == (PETRONILA_W.lat, PETRONILA_W.lng)
    # … naziv i titular čvora (way nema OSM name), ostalo COALESCE.
    assert (c["name"], c["titular"], c["osm_named"]) == ("Crkva Sv. Petronila", "sv. Petronila", 1)
    assert (c["denomination"], c["city"], c["county"]) == \
        ("roman_catholic", "Kanfanar", "Istarska županija")
    m = db.execute("SELECT * FROM church_merged").fetchone()
    assert (m["church_id"], m["osm_type"], m["osm_id"], m["slug"], m["razlog"]) == \
        (wid, "node", 10985250504, "sv-petronila-kanfanar-n10985250504", "bez_imena")
    aliases = {(r["alias"], r["source"]) for r in db.execute("SELECT * FROM church_aliases")}
    assert aliases == {("Sv. Petronila", "osm:alt_name")}


def test_apply_imenovani_way_cuva_naziv_a_naziv_cvora_ide_u_alias(db):
    n = z("node", 9560145265, 45.0, 15.0, "kapela sv. Ivana", amenity="place_of_worship")
    w = z("way", 43948277, 45.0, 15.0, "Sv. Ivan", amenity="place_of_worship")
    _ins(db, n, "kapela-sv-ivana-n9560145265", kind="kapela")
    wid = _ins(db, w, "sv-ivan-w43948277", kind="crkva")
    dedup.apply(db)
    c = db.execute("SELECT name, kind FROM churches").fetchone()
    assert tuple(c) == ("Sv. Ivan", "crkva")
    assert db.execute("SELECT church_id, alias, source FROM church_aliases").fetchall()[0][:] == \
        (wid, "kapela sv. Ivana", "osm-dedup")


def test_apply_ponovljen_ne_mijenja_nista(db):
    _ins(db, PETRONILA_N, "n-slug")
    _ins(db, PETRONILA_W, "w-slug")
    dedup.apply(db)
    prije = [tuple(r) for r in db.execute("SELECT * FROM churches")]
    assert dedup.apply(db) == []
    assert [tuple(r) for r in db.execute("SELECT * FROM churches")] == prije
    assert db.execute("SELECT COUNT(*) FROM church_merged").fetchone()[0] == 1


def test_audit_nakon_dedupa(db):
    for zap, slug in [(PETRONILA_N, "petronila-n"), (PETRONILA_W, "petronila-w"),
                      (FRANE_SAMOSTAN, "frane-n"), (FRANE_CRKVA, "frane-w"),
                      (SPASITELJ_N, "spasitelj-n"), (SPASITELJ_W, "spasitelj-w")]:
        _ins(db, zap, slug)
    prije = audit.node_way_duplikati(db)
    assert prije["value"] == 1 and prije["examples"] == ["petronila-n ~ petronila-w (2 m)"]
    dedup.apply(db)
    m = audit.node_way_duplikati(db)
    assert m["value"] == 0 and m["spojeno"] == 1
    assert m["namjerno_ostavljeni"] == [
        "frane-n ~ frane-w (25 m): dvije zgrade, uloga monastery ≠ worship",
        "spasitelj-n ~ spasitelj-w (38 m): " + dedup.OSTAVLJENI[("n12433613079", "w1228836695")],
    ]


@pytest.mark.parametrize("cvor, kind_cvora, kind_waya, ocekivano", [
    # Okrug Gornji: čvor amenity bez building, tlocrt building=chapel.
    ("Sv. Karlo", "crkva", "kapela", "kapela"),
    # Tounj: tip piše u nazivu čvora, tlocrt je generički building=church.
    ("Kapela Sv Ivana Nepomuka", "kapela", "crkva", "kapela"),
    # Hum: bezimeni amenity bez religije je `ostalo`; čvor zna više.
    ("Sv. Todor", "crkva", "ostalo", "crkva"),
])
def test_apply_kind_prezivljenog(db, cvor, kind_cvora, kind_waya, ocekivano):
    _ins(db, z("node", 1, 45.0, 15.0, cvor), "n1", kind=kind_cvora)
    _ins(db, z("way", 2, 45.0, 15.0, "Kapela", named=False), "w2", kind=kind_waya)
    dedup.apply(db)
    assert db.execute("SELECT name, kind FROM churches").fetchone()[:] == (cvor, ocekivano)


def test_apply_rucni_spoj_s_nazivom_cvora(db):
    # Brseč: „Sv. Križ” (čvor) i „Sv. Kris” (tlocrt) — različite glave, ručni
    # spoj; prikazuje se standardni naziv čvora, dijalektalni ide u alias.
    n = z("node", 847093760, 45.0, 15.0, "Sv. Križ", amenity="place_of_worship")
    w = z("way", 366081978, 45.0, 15.00003, "Sv. Kris")
    assert dedup.zapreka(n, w) == "nazivi"
    _ins(db, n, "sv-kriz-brsec-n847093760", titular="sv. Križ")
    wid = _ins(db, w, "sv-kris-brsec-w366081978", titular="sv. Kris")
    (s,) = dedup.apply(db)
    assert s.razlog == "rucno"
    c = db.execute("SELECT slug, name, titular FROM churches").fetchone()
    assert tuple(c) == ("sv-kris-brsec-w366081978", "Sv. Križ", "sv. Križ")
    assert db.execute("SELECT church_id, alias, source FROM church_aliases").fetchone()[:] == \
        (wid, "Sv. Kris", "osm-dedup")
