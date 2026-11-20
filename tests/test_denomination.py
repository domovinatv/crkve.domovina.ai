"""Konfesija: normalizacija na dozvoljeni skup (odluka 101) i pravilo veze
građevina ↔ pravna osoba (odluka 4). Svaki slučaj je stvarna vrijednost iz
baze ili audita 2026-11-20 — ako normalizacija neku propusti, audit
`konfesija_nenormalizirana` ne pada na 0; ako pravilo neku propusti,
pravoslavna crkva opet postane župna crkva katoličke župe.
"""
from __future__ import annotations

import sqlite3

import pytest

from src import audit
from src.denomination import (
    DOZVOLJENE_DENOMINACIJE,
    DOZVOLJENE_RELIGIJE,
    community_denomination,
    is_katolicka,
    is_nekatolicka,
    normalize_denomination,
    normalize_religion,
)
from src.match import best_match, build_index, compatible

# ---------------------------------------------------------------------------
# Normalizacija — svaka vrijednost izvan skupa nađena u bazi (churches,
# parishes, dioceses), s brojem zapisa u komentaru.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,religion,expected", [
    ("catholic", "christian", "roman_catholic"),              # 1022 crkve
    ("adventist", "christian", "seventh_day_adventist"),      # 7 crkava, 106 župa, 1 biskupija
    ("roman_catholicadded", "christian", "roman_catholic"),   # 2 poklonca, Cres
    ("katolička", "christian", "roman_catholic"),             # Bubnjarci
    ("benedictine_sisters", "christian", "roman_catholic"),   # benediktinke, Split
    ("hungarian_reformed", "christian", "reformed"),          # Kopačevo, Kotlina
    ("united_reformed", "christian", "reformed"),             # Laslovo
    ("neo-pentecostal", "christian", "pentecostal"),          # Riječ života, Zagreb
    ("philadelphian", "christian", "pentecostal"),            # Brnjavac
    ("episcopal", "christian", "protestant"),                 # Dobrog Pastira, Osijek
    ("church_of_christ", "christian", "protestant"),          # Kristova crkva, Zaprešić
    ("serbian_orthodox;orthodox", "christian", "serbian_orthodox"),  # Daruvarski Brestovac
    ("old_paneuropean", "pagan", None),                       # Velika gomila, Igrane
    ("hare_krishna", "hindu", None),                          # ISKCON, Zagreb
    ("sv. florijan", "christian", None),                      # Ravna Gora: titular u krivom tagu
    ("sv. petar i pavel", "christian", None),                 # Nugla: isto
    ("jewish", "jewish", None),                               # 1 župa, 12 biskupija
    ("hindu", "hindu", None),                                 # 1 + 1
    ("buddhist", "buddhist", None),                           # 1 + 1
])
def test_normalize_denomination_stvarne_vrijednosti(raw, religion, expected):
    assert normalize_denomination(raw, religion) == expected


@pytest.mark.parametrize("value", sorted(DOZVOLJENE_DENOMINACIJE - {"sunni", "shia", "zen"}))
def test_dozvoljena_krscanska_ostaje(value):
    assert normalize_denomination(value, "christian") == value
    assert normalize_denomination(value.upper() + " ") == value


def test_orthodox_ostaje_genericki():
    # Ne nagađa srpsku: 69 crkava s `orthodox` ostaje `orthodox`.
    assert normalize_denomination("orthodox", "christian") == "orthodox"
    assert normalize_denomination("eastern_orthodox") == "orthodox"


def test_visestruka_nejasna_je_null():
    assert normalize_denomination("roman_catholic;serbian_orthodox") is None
    assert normalize_denomination("catholic;roman_catholic") == "roman_catholic"


def test_proturjecje_s_religijom_je_null():
    assert normalize_denomination("sunni", "muslim") == "sunni"
    assert normalize_denomination("zen", "buddhist") == "zen"
    assert normalize_denomination("sunni", "christian") is None
    assert normalize_denomination("roman_catholic", "muslim") is None
    assert normalize_denomination(None) is None
    assert normalize_denomination("  ") is None


@pytest.mark.parametrize("raw,expected", [
    ("krščanstvo1", "christian"),   # 3 poklonca, Lasinja
    ("krščanstvo2", "christian"),   # Razdrto Tuheljsko
    ("bogomilism", None),           # 2 „bogumilska" centra
    ("Christian", "christian"),
    ("pagan", "pagan"),
    (None, None),
])
def test_normalize_religion(raw, expected):
    assert normalize_religion(raw) == expected


def test_audit_koristi_iste_konstante():
    # Jedna definicija za mjeru i pravilo — re-eksport, ne kopija.
    assert audit.DOZVOLJENE_DENOMINACIJE is DOZVOLJENE_DENOMINACIJE
    assert audit.DOZVOLJENE_RELIGIJE is DOZVOLJENE_RELIGIJE
    assert audit.is_nekatolicka is is_nekatolicka


def test_is_katolicka():
    assert is_katolicka("roman_catholic")
    assert is_katolicka("greek_catholic")
    assert is_katolicka("catholic")             # baza prije normalizacije
    assert not is_katolicka("old_catholic")     # starokatolici nisu u zajedništvu s Rimom
    assert not is_katolicka(None)


# ---------------------------------------------------------------------------
# Evidencija vjerskih zajednica (scripts/03)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("KRŠĆANSKA ADVENTISTIČKA CRKVA U REPUBLICI HRVATSKOJ", ("christian", "seventh_day_adventist")),
    # REFORM bi pogodio prije ADVENTIST — bila je „reformed"
    ("REFORMNI POKRET ADVENTISTA SEDMOG DANA", ("christian", "seventh_day_adventist")),
    ("EVANGELIČKA METODISTIČKA CRKVA U HRVATSKOJ", ("christian", "methodist")),
    ("EVANGELIČKA CRKVA VALDESE", ("christian", "waldensian")),
    # bila „protestant" (pravilo CRKV), a to su starokatolici
    ("KATOLIČKA STARA CRKVA", ("christian", "old_catholic")),
    ("HRVATSKA STAROKATOLIČKA CRKVA", ("christian", "old_catholic")),
    ("NOVOAPOSTOLSKA CRKVA U REPUBLICI HRVATSKOJ", ("christian", "new_apostolic")),
    ("HRVATSKA ZAJEDNICA CRKVE ISUSA KRISTA SVETACA POSLJEDNJIH DANA", ("christian", "mormon")),
    ("SCIJENTOLOŠKA CRKVA U HRVATSKOJ", (None, None)),
    ("ŽIDOVSKA OPĆINA ZAGREB", ("jewish", None)),
    ("BUDISTIČKA ZAJEDNICA DHARMALOKA", ("buddhist", None)),
    ("HINDUISTIČKA VJERSKA ZAJEDNICA HRVATSKE", ("hindu", None)),
    ("SRPSKA PRAVOSLAVNA CRKVA U HRVATSKOJ", ("christian", "serbian_orthodox")),
    ("ISLAMSKA ZAJEDNICA U HRVATSKOJ", ("muslim", "sunni")),
    ("BAHÁ´Í ZAJEDNICA HRVATSKE", None),
])
def test_community_denomination(name, expected):
    assert community_denomination(name) == expected


def test_community_samo_dozvoljene_vrijednosti():
    from src.denomination import _DENOM_RULES
    for pat, (rel, den) in _DENOM_RULES:
        assert rel is None or rel in DOZVOLJENE_RELIGIJE, pat.pattern
        assert den is None or den in DOZVOLJENE_DENOMINACIJE, pat.pattern


# ---------------------------------------------------------------------------
# Pravilo veze (odluka 4)
# ---------------------------------------------------------------------------

KATOLICKA_ZUPA = {"denomination": "roman_catholic", "religion": "christian",
                  "source": '["datagovhr:katolicke-pravne-osobe"]'}
SPC_OPCINA = {"denomination": "serbian_orthodox", "religion": "christian",
              "source": '["datagovhr:vjerske-zajednice"]'}
RIJEKA_SV_NIKOLA = {"id": 1, "name": "crkva svetog Nikole", "kind": "pravoslavna-crkva",
                    "religion": "christian", "denomination": "serbian_orthodox",
                    "city": None, "settlement": "Rijeka", "municipality": "Rijeka"}


def _rows(*dicts):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    out = []
    for d in dicts:
        cols = ", ".join(f"? AS {k}" for k in d)
        out.append(conn.execute(f"SELECT {cols}", tuple(d.values())).fetchone())
    return out


def test_rijeka_sv_nikola_ne_ide_na_katolicku_zupu():
    assert not compatible(RIJEKA_SV_NIKOLA, KATOLICKA_ZUPA)
    idx = build_index(_rows(RIJEKA_SV_NIKOLA))
    # Bez pravila je to savršen pogodak (score 100) — zato je tvrdi uvjet.
    assert best_match(idx, "ŽUPA SV. NIKOLE B.", {"rijeka"}) is not None
    assert best_match(idx, "ŽUPA SV. NIKOLE B.", {"rijeka"},
                      accept=lambda c: compatible(c, KATOLICKA_ZUPA)) is None


def test_filtar_prije_scoreanja_cuva_marginu():
    # Pravoslavna istog titulara bi srušila marginu katoličkoj — filtar je
    # PRIJE scoreanja, pa katolička pobjeđuje.
    katolicka = {**RIJEKA_SV_NIKOLA, "id": 2, "name": "crkva svetog Nikole biskupa",
                 "kind": "crkva", "denomination": "roman_catholic"}
    idx = build_index(_rows(RIJEKA_SV_NIKOLA, katolicka))
    hit = best_match(idx, "ŽUPA SV. NIKOLE BISKUPA", {"rijeka"},
                     accept=lambda c: compatible(c, KATOLICKA_ZUPA))
    assert hit is not None and hit[0].id == 2


def test_pravoslavna_bez_denominacije_ne_ide_na_katolicku():
    crkva = {"kind": "pravoslavna-crkva", "religion": "christian", "denomination": None}
    assert not compatible(crkva, KATOLICKA_ZUPA)


@pytest.mark.parametrize("kind", ["dzamija", "sinagoga"])
def test_dzamija_sinagoga_bez_denominacije_ne_ide_na_katolicku(kind):
    assert not compatible({"kind": kind, "religion": None, "denomination": None}, KATOLICKA_ZUPA)


def test_katolicka_bez_denominacije_i_dalje_ide():
    assert compatible({"kind": "kapela", "religion": "christian", "denomination": None},
                      KATOLICKA_ZUPA)
    assert compatible({"kind": "crkva", "religion": None, "denomination": None},
                      KATOLICKA_ZUPA)
    assert compatible({"kind": "crkva", "religion": "christian", "denomination": "catholic"},
                      KATOLICKA_ZUPA)


@pytest.mark.parametrize("denom", ["baptist", "jehovahs_witness", "pentecostal",
                                   "seventh_day_adventist", "adventist", "protestant"])
def test_protestantska_kind_crkva_ne_ide_na_katolicku(denom):
    # Npr. Baptistička crkva Sion (Sirač) → ŽUPA POHODA BDM, SIRAČ u auditu.
    assert not compatible({"kind": "crkva", "religion": "christian", "denomination": denom},
                          KATOLICKA_ZUPA)


def test_obrnuto_katolicka_ne_ide_na_nekatolicku():
    # Svih Svetih, Erdut (roman_catholic) bila je filijala SPC crkvene općine.
    rkt = {"kind": "crkva", "religion": "christian", "denomination": "roman_catholic"}
    assert not compatible(rkt, SPC_OPCINA)
    # Sv. Ćirila i Metoda, Rijeka bila je župna crkva starokatoličke općine.
    assert not compatible(rkt, {"denomination": "old_catholic", "religion": "christian"})
    # Nepoznata konfesija ne blokira ni u tom smjeru.
    assert compatible({"kind": "kapela", "religion": "christian", "denomination": None},
                      SPC_OPCINA)
    assert compatible(RIJEKA_SV_NIKOLA, SPC_OPCINA)


def test_katolicka_po_evidenciji_i_bez_konfesije():
    zupa = {"denomination": None, "religion": None,
            "source": '["datagovhr:katolicke-pravne-osobe"]'}
    assert not compatible(RIJEKA_SV_NIKOLA, zupa)


def test_nepoznata_pravna_osoba_ne_blokira():
    assert compatible(RIJEKA_SV_NIKOLA, {"denomination": None, "religion": None})
