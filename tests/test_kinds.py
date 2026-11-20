"""Klasifikacija tipa određuje što se vidi na karti i pod kojim filterom —
pogrešan `kind` je vidljiv bug, ne kozmetika."""
from __future__ import annotations

import pytest

from src.kinds import classify, denomination_hr, org_kind, religion_of


@pytest.mark.parametrize(
    "tags,name,expected",
    [
        ({"amenity": "place_of_worship", "building": "cathedral"}, None, "katedrala"),
        # Naziv nadjačava pregenerički building=church…
        ({"amenity": "place_of_worship", "building": "church"}, "Katedrala sv. Duje", "katedrala"),
        # …ali specifičan building tag nadjačava naziv.
        ({"building": "chapel"}, "Crkva sv. Roka", "kapela"),
        ({"amenity": "place_of_worship", "religion": "christian",
          "denomination": "serbian_orthodox"}, "Crkva sv. Nikole", "pravoslavna-crkva"),
        ({"amenity": "place_of_worship", "religion": "muslim"}, None, "dzamija"),
        ({"amenity": "place_of_worship", "religion": "jewish"}, None, "sinagoga"),
        ({"historic": "wayside_shrine"}, None, "poklonac"),
        ({"amenity": "monastery"}, None, "samostan"),
        ({}, "Svetište Majke Božje Bistričke", "svetiste"),
        ({}, "Bazilika Srca Isusova", "bazilika"),
        ({}, "Franjevački samostan", "samostan"),
        ({}, None, "ostalo"),
        # building=mosque/synagogue je zgrada, ne namjena: bivša džamija u
        # Đakovu je katolička crkva Svih Svetih (OSM w522826735)…
        ({"amenity": "place_of_worship", "building": "mosque", "religion": "christian",
          "denomination": "roman_catholic"}, "crkva Svih Svetih", "crkva"),
        # …a pentekostna crkva u Osijeku stoji u bivšoj sinagogi (w555206682).
        ({"amenity": "place_of_worship", "building": "synagogue", "religion": "christian",
          "denomination": "pentecostal"}, "Evanđeoska pentakostalna crkva Radosne vijesti",
         "crkva"),
        # Prave džamije i sinagoge ne mijenjaju kind.
        ({"amenity": "place_of_worship", "building": "mosque", "religion": "muslim"},
         "Džamija Gunja", "dzamija"),
        ({"building": "mosque"}, None, "dzamija"),                       # Vidovići
        ({"amenity": "place_of_worship", "building": "synagogue", "religion": "jewish"},
         "Mala sinagoga", "sinagoga"),
        ({"building": "synagogue"}, "Varaždinska sinagoga", "sinagoga"),
        # Višestruka konfesija normalizirana → prepoznato pravoslavlje.
        ({"amenity": "place_of_worship", "religion": "christian",
          "denomination": "serbian_orthodox;orthodox"},
         "Srpska pravoslavna crkva svetih Petra i Pavla", "pravoslavna-crkva"),
    ],
)
def test_classify(tags, name, expected):
    assert classify(tags, name) == expected


def test_religion_falls_back_to_kind():
    assert religion_of({}, "kapela") == "christian"
    assert religion_of({}, "dzamija") == "muslim"
    assert religion_of({"religion": "christian"}, "ostalo") == "christian"
    assert religion_of({}, "ostalo") is None


def test_religion_normalizirana():
    assert religion_of({"religion": "krščanstvo1"}, "poklonac") == "christian"
    # Nepoznata religija iz izvora nije dokaz kršćanstva — ne pada na kind.
    assert religion_of({"religion": "bogomilism"}, "ostalo") is None


def test_denomination_hr():
    assert denomination_hr("roman_catholic") == "rimokatolička"
    assert denomination_hr("serbian_orthodox") == "srpska pravoslavna"
    # Nepoznato se propušta čitljivo, ne baca.
    assert denomination_hr("some_new_thing") == "some new thing"
    assert denomination_hr(None) is None


# --- vrsta pravne osobe iz evidencije vjerskih zajednica (scripts/03) --------

@pytest.mark.parametrize("name,kind", [
    # S2 nalaz: 20 manastira je bilo `eparhija` jer naziv počinje eparhijom.
    ("SRPSKA PRAVOSLAVNA CRKVA U HRVATSKOJ, EPARHIJA SLAVONSKA, PRAVOSLAVNI MANASTIR PAKRA",
     "samostan"),
    ("SRPSKA PRAVOSLAVNA CRKVA U HRVATSKOJ, EPARHIJA GORNJOKARLOVAČKA, "
     "MANASTIR PREOBRAŽENJA GOSPODNJEG U KOMOGOVINI", "samostan"),
    # Eparhija sama i njezin upravni odbor ostaju eparhija.
    ("SRPSKA PRAVOSLAVNA CRKVA U HRVATSKOJ, EPARHIJA SLAVONSKA", "eparhija"),
    ("SRPSKA PRAVOSLAVNA CRKVA U HRVATSKOJ, EPARHIJA DALMATINSKA, EPARHIJSKI UPRAVNI ODBOR",
     "eparhija"),
    # Crkvena općina u eparhiji ostaje crkvena općina.
    ("SRPSKA PRAVOSLAVNA CRKVA U HRVATSKOJ, EPARHIJA OSJEČKOPOLJSKA I BARANJSKA, "
     "CRKVENA OPĆINA BELI MANASTIR", "crkvena-opcina"),
    # Beli Manastir je grad, ne samostan.
    ("MJESNA CRKVA BELI MANASTIR", "ostalo"),
    ("EVANĐEOSKA PENTEKOSTNA CRKVA, BELI MANASTIR", "ostalo"),
])
def test_org_kind_manastir_nije_eparhija(name, kind):
    assert org_kind(name) == kind
