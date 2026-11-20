"""Metrike kvalitete (src/audit.py) su mjerilo cijelog lanca S1–S7: sesija je
gotova kad metrika padne na 0. Ako metrika broji krivo, „gotovo" je laž —
zato svaka ima bar jedan zapis koji MORA brojati i jedan koji NE SMIJE.

Baza je in-memory s pravom shemom iz src/db.py, bez mreže.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from src import audit
from src.db import SCHEMA, _migrate

# ~11 m po 0.0001° geografske širine
LAT, LNG = 45.8, 16.0


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    yield conn
    conn.close()


def _ins(conn, table: str, **kw) -> int:
    cols = ", ".join(kw)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({', '.join('?' * len(kw))})",
                       tuple(kw.values()))
    return cur.lastrowid


def church(conn, slug, name="Crkva sv. Marka", **kw) -> int:
    kw.setdefault("lat", LAT)
    kw.setdefault("lng", LNG)
    kw.setdefault("county", "Grad Zagreb")
    return _ins(conn, "churches", slug=slug, name=name, **kw)


def parish(conn, slug, name="ŽUPA SV. MARKA", **kw) -> int:
    kw.setdefault("kind", "zupa")
    kw.setdefault("denomination", "roman_catholic")
    return _ins(conn, "parishes", slug=slug, name=name, **kw)


def _examples(m: dict) -> str:
    return " ".join(m.get("examples", []))


# --- 1. nekatoličke na katoličkim ------------------------------------------

def test_pravoslavna_na_katolickoj_zupi_se_broji(db):
    p = parish(db, "zupa-kat")
    church(db, "hram-sv-nikole", kind="pravoslavna-crkva",
           denomination="serbian_orthodox", parish_id=p, is_parish_church=1)
    m = audit.nekatolicke_na_katolickim(db)
    assert m["value"] == 1
    assert "hram-sv-nikole → zupa-kat" in m["examples"]
    assert m["po_kindu_i_konfesiji"] == {"pravoslavna-crkva / serbian_orthodox": 1}
    assert audit.nekatolicke_zupne_crkve(db)["value"] == 1


def test_katolicka_i_nepoznata_konfesija_se_ne_broje(db):
    p = parish(db, "zupa-kat")
    church(db, "kat", denomination="catholic", parish_id=p, is_parish_church=1)
    # smeće u konfesiji nije dokaz da građevina nije katolička
    church(db, "smece", denomination="sv. florijan", religion="krščanstvo1", parish_id=p)
    # pravoslavna na PRAVOSLAVNOJ crkvenoj općini je ispravna
    po = parish(db, "sco", kind="crkvena-opcina", denomination="serbian_orthodox")
    church(db, "hram", kind="pravoslavna-crkva", denomination="serbian_orthodox", parish_id=po)
    assert audit.nekatolicke_na_katolickim(db)["value"] == 0
    assert audit.nekatolicke_zupne_crkve(db)["value"] == 0


def test_nekatolicka_filijala_nije_zupna_crkva(db):
    p = parish(db, "zupa-kat")
    church(db, "dzamija", kind="dzamija", religion="muslim", parish_id=p)
    assert audit.nekatolicke_na_katolickim(db)["value"] == 1
    assert audit.nekatolicke_zupne_crkve(db)["value"] == 0


def test_visestruka_osm_vrijednost_se_rastavlja():
    assert audit.is_nekatolicka("crkva", "christian", "serbian_orthodox;orthodox")
    assert not audit.is_nekatolicka("crkva", None, None)


# --- 2. titular u genitivu ---------------------------------------------------

@pytest.mark.parametrize("titular,vrsta", [
    ("sv. Petar i Pavla", "mijesano"),
    ("sv. Kuzma i Damjana", "mijesano"),
    ("sv. Filip i Jakova", "mijesano"),
    ("sv. Ivan i Pavla", "mijesano"),
    ("sv. Fabijan i Sebastijana", "mijesano"),
    ("sv. Petar i Pavla Apostol", "mijesano"),
    ("sv. Vid i Modesta", "mijesano"),
    ("sv. Katarina Djevica i mučenice", "mijesano"),
    ("sv. Ćirila i Metoda", "sve_genitiv"),
    ("sv. Apostola Petra i Pavla", "sve_genitiv"),
    ("sv. Kvirika i Julite", "sve_genitiv"),
    ("sv. Petar I Pavla", "mijesano"),          # verzal iz evidencije
])
def test_genitiv_u_nizu_hvata(titular, vrsta):
    assert audit.genitiv_u_nizu(titular) == vrsta


@pytest.mark.parametrize("titular", [
    "sv. Petar i Pavao",
    "sv. Kuzma i Damjan",
    "sv. Ćiril i Metod",
    "sv. Joakim i Ana",          # ženski nominativ na -a
    "sv. Ilija i Luka",
    "sv. Matej Apostol i Evanđelist",
    "sv. Marko",                 # bez veznika: izvan dosega metrike
    "Uznesenje BDM",
    None,
    # S3: nominativi koje je pravilo „-e"/„-a" krivo brojalo
    "sv. Car Konstantin i Carica Elena",
    "sv. Ante i Rok",
    "sv. Ivan i Pavle",
    "sv. Mihovil i Mario",
    "sv. Hermagora i Fortunat",
    "sv. Juraj Mučenik i Srce Marijino",
    "sv. Benedikt i Žalosna Gospa",
])
def test_genitiv_u_nizu_propusta(titular):
    assert audit.genitiv_u_nizu(titular) is None


def test_titular_genitiv_broji_obje_tablice_odvojeno(db):
    church(db, "a", titular="sv. Petar i Pavla")
    church(db, "b", titular="sv. Petar i Pavao")
    parish(db, "z", titular="sv. Ćirila I Metoda")
    m = audit.titular_genitiv(db)
    assert (m["value"], m["churches"]["value"], m["parishes"]["value"]) == (2, 1, 1)
    assert m["churches"]["examples"] == ["a"]
    assert m["churches"]["oblici_top20"] == {"sv. Petar i Pavla": 1}
    assert m["parishes"]["sve_genitiv"] == 1


# --- 3. konfesija izvan dozvoljenog skupa -----------------------------------

def test_nedozvoljene_konfesije_se_broje_po_tablici(db):
    church(db, "a", denomination="catholic")
    church(db, "b", denomination="roman_catholicadded")
    church(db, "c", religion="bogomilism")
    parish(db, "z", denomination="adventist")
    m = audit.konfesija_nenormalizirana(db)
    assert m["value"] == 4
    assert m["churches"]["denomination"] == {"catholic": 1, "roman_catholicadded": 1}
    assert m["churches"]["religion"] == {"bogomilism": 1}
    assert m["parishes"]["denomination"] == {"adventist": 1}


def test_dozvoljene_i_prazne_konfesije_se_ne_broje(db):
    church(db, "a", denomination="roman_catholic", religion="christian")
    church(db, "b", denomination="orthodox", religion="christian")
    church(db, "c")
    parish(db, "z", denomination="serbian_orthodox", religion="christian")
    assert audit.konfesija_nenormalizirana(db)["value"] == 0


# --- 4. node + way ista zgrada -------------------------------------------------

def test_node_i_way_iste_crkve_na_10m(db):
    church(db, "sv-marka-n1", "Sv. Marko", osm_type="node", osm_id=1)
    church(db, "crkva-sv-marka-w2", "Crkva sv. Marka", osm_type="way", osm_id=2,
           lat=LAT + 0.0001)
    m = audit.node_way_duplikati(db)
    assert m["value"] == 1
    assert m["ista_glava_titulara"] == 1 and m["isti_naziv"] == 0
    assert m["examples"] == ["sv-marka-n1 ~ crkva-sv-marka-w2 (11 m)"]


def test_node_way_isti_naziv_bez_titulara(db):
    church(db, "crkva-n1", "Crkva", osm_type="node", osm_id=1)
    church(db, "crkva-w2", "Crkva", osm_type="way", osm_id=2)
    m = audit.node_way_duplikati(db)
    assert (m["value"], m["isti_naziv"], m["ista_glava_titulara"]) == (1, 1, 0)


def test_node_way_razliciti_titulari_ili_daleko_se_ne_broje(db):
    church(db, "marko-n1", "Crkva sv. Marka", osm_type="node", osm_id=1)
    church(db, "rok-w2", "Kapela sv. Roka", osm_type="way", osm_id=2)   # isto mjesto, drugi titular
    church(db, "marko-w3", "Crkva sv. Marka", osm_type="way", osm_id=3,
           lat=LAT + 0.001)                                              # ~111 m
    church(db, "marko-w4", "Crkva sv. Marka", osm_type="way", osm_id=4)
    # way+way istog titulara drugdje: ne ulazi u value, samo u ostale tipove
    church(db, "ivan-w5", "Crkva sv. Ivana", osm_type="way", osm_id=5, lat=LAT + 1)
    church(db, "ivan-w6", "Zvonik sv. Ivana", osm_type="way", osm_id=6, lat=LAT + 1)
    m = audit.node_way_duplikati(db)
    assert m["value"] == 1                 # samo marko-n1 ~ marko-w4
    assert m["examples"] == ["marko-n1 ~ marko-w4 (0 m)"]
    assert m["ostali_tipovi_ista_glava"] == {"way+way": 1}


def test_haversine():
    assert audit.haversine_m(45.0, 16.0, 45.0, 16.0) == 0
    assert audit.haversine_m(45.0, 16.0, 45.001, 16.0) == pytest.approx(111.2, abs=0.5)


# --- 5. Places koordinate u exportu -----------------------------------------

def test_places_koordinate_broje_samo_places_izvor(db, tmp_path):
    parish(db, "a", lat=LAT, lng=LNG, geocode_source="places", google_maps_uri="https://maps")
    parish(db, "b", lat=LAT, lng=LNG, geocode_source="church")
    parish(db, "c", geocode_source="places")          # bez koordinate: ništa se ne izvozi
    (tmp_path / "31_export_geojson.py").write_text("SELECT p.lat, p.lng, p.google_maps_uri")
    (tmp_path / "32_export_csv.py").write_text("SELECT c.lat FROM churches c")
    m = audit.places_koordinate_u_exportu(db, scripts_dir=tmp_path)
    assert m["value"] == 1
    assert m["google_maps_uri"] == 1
    assert m["izvoze"]["31_export_geojson.py"] == {"koordinate_zupa": True, "google_maps_uri": True}
    assert m["izvoze"]["32_export_csv.py"] == {"koordinate_zupa": False, "google_maps_uri": False}
    assert m["izvoze"]["34_export_static.py"] is None


def test_prave_export_skripte_se_mogu_procitati(db):
    m = audit.places_koordinate_u_exportu(db)
    assert m["value"] == 0
    assert set(m["izvoze"]) == set(audit.EXPORT_SKRIPTE)
    assert all(v is not None for v in m["izvoze"].values())


# --- 6. parish_count ---------------------------------------------------------

def test_parish_count_razlika(db):
    for slug, name, n in (("gospic", "Gospićko-senjska Biskupija", 1),
                          ("krk", "Biskupija Krk", 2)):
        _ins(db, "dioceses", slug=slug, name=name, kind="biskupija",
             denomination="roman_catholic", parish_count=n)
    parish(db, "g1", diocese="Gospićko-senjska Biskupija")
    parish(db, "g2", diocese="Gospićko-senjska Biskupija", registry_status="PRESTANAK")
    parish(db, "k1", diocese="Biskupija Krk")
    parish(db, "k2", diocese="Biskupija Krk")
    parish(db, "k3", diocese="Biskupija Krk", duplicate_of=1)   # isti subjekt dvaput
    # zajednica: parish_count broji org. oblike, ne župe — ne uspoređuje se
    _ins(db, "dioceses", slug="spc", name="SPC", kind="zajednica",
         denomination="serbian_orthodox", parish_count=400)
    m = audit.parish_count_razlika(db)
    # Ugašena (Gospić) i duplikat (Krk) nisu razlika: parish_count broji aktivne.
    assert m["value"] == 0 and m["examples"] == []
    assert m["razlika_prema_zapisima"] == 2
    db.execute("UPDATE dioceses SET parish_count = 5 WHERE slug = 'krk'")
    m = audit.parish_count_razlika(db)
    assert m["value"] == 1
    assert m["examples"] == ["krk: parish_count 5, aktivnih 2, zapisa 3"]


# --- 7. dijeljen wikidata_id -------------------------------------------------

def test_wikidata_dijeljen(db):
    church(db, "crkva-a", wikidata_id="Q1", kind="crkva")
    church(db, "samostan-a", wikidata_id="Q1", kind="samostan")
    church(db, "kapela-b", wikidata_id="Q2", kind="kapela")
    church(db, "crkva-b", wikidata_id="Q2", kind="crkva")
    church(db, "sama", wikidata_id="Q3", kind="crkva")
    m = audit.wikidata_dijeljen(db)
    assert m["value"] == 2
    assert m["neocekivani"] == ["Q2"]
    assert not any("Q3" in e for e in m["examples"])


# --- 8. sitnice ----------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("Church of St. George", True),
    ("St. Anne's Church", True),
    ("Chapel of Cemetery", True),
    ("Kingdom Hall", True),
    ("Saint Franjo", True),
    ("Crkva sv. Jurja", False),
    ("Macukoni - XVII St.", False),      # st. = stoljeće
    ("Kapela Gospe od Zdravlja", False),
    (None, False),
])
def test_je_engleski(name, expected):
    assert audit.je_engleski(name) is expected


def test_engleski_nazivi_po_izvoru(db):
    church(db, "a-q1", "Church of St. George")
    church(db, "b-w1", "St. Martin", osm_type="way", osm_id=1)
    church(db, "c-w2", "Crkva sv. Martina", osm_type="way", osm_id=2)
    m = audit.engleski_nazivi(db)
    assert m["value"] == 2
    assert m["po_izvoru"] == {"osm": 1, "wikidata": 1}


def test_bez_zupanije(db):
    church(db, "sa", county="Istarska")
    church(db, "bez", county=None)
    assert audit.bez_zupanije(db) == {"value": 1, "examples": ["bez"]}


def test_crkve_dalje_20km_od_zupe(db):
    p = parish(db, "zupa", lat=LAT, lng=LNG)
    church(db, "blizu", parish_id=p, lat=LAT + 0.1)       # ~11 km
    church(db, "daleko", parish_id=p, lat=LAT + 0.25)     # ~28 km
    church(db, "bez-zupe", lat=LAT + 1)
    m = audit.crkve_dalje_20km_od_zupe(db)
    assert m["value"] == 1
    assert m["examples"] == ["daleko → zupa (27.8 km)"]


# --- registar, kontekst, determinizam ----------------------------------------

def test_run_ima_sve_metrike_i_kontekst_iz_stats(db):
    p = parish(db, "zupa")
    church(db, "c", parish_id=p, is_parish_church=1)
    parish(db, "bez-crkve")
    out = audit.run(db)
    assert list(out["metrike"]) == [m[0] for m in audit.METRICS]
    assert all(isinstance(m["value"], int) for m in out["metrike"].values())
    assert out["kontekst"] == {"crkve_ukupno": 1, "crkve_sa_zupom": 1, "zupne_crkve": 1,
                               "zupe_aktivne": 2, "zupe_bez_zupne_crkve": 1,
                               "zupe_bez_ijedne_crkve": 1}
    # isti ulaz → isti bajtovi (sha audit.json mora biti reproducibilan)
    assert json.dumps(out, ensure_ascii=False) == json.dumps(audit.run(db), ensure_ascii=False)
    assert "crkve_ukupno" in audit.format_table(out)
