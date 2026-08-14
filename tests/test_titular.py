"""Titular je ključ po kojem se spajaju izvori — ako parser padne, matching
tiho degradira u "sve ili ništa". Zato je pokriven primjerima iz sva tri
izvora (OSM nominativ, registar genitiv u verzalu, MinKulture opisni naziv).
"""
from __future__ import annotations

import pytest

from src.titular import head_key, key, parse


@pytest.mark.parametrize(
    "name,expected",
    [
        # OSM stil
        ("Crkva sv. Marka", "sv. Marko"),
        ("Crkva svetog Jurja", "sv. Juraj"),
        ("Kapela sv. Ane", "sv. Ana"),
        ("Crkva sv. Ivana Krstitelja", "sv. Ivan Krstitelj"),
        # Državna evidencija (verzal, genitiv, mjesto iza zareza)
        ("ŽUPA SV. MARKA EVANĐELISTA, ZAGREB", "sv. Marko Evanđelist"),
        ("ŽUPA SV. NIKOLE BISKUPA, VARAŽDIN", "sv. Nikola Biskup"),
        # Otajstva — ne razlažu se na "sv. X"
        ("ŽUPA UZNESENJA BLAŽENE DJEVICE MARIJE, ZAGREB", "Uznesenje BDM"),
        ("Crkva Presvetog Trojstva", "Presveto Trojstvo"),
        ("Crkva sv. Križa", "Sveti Križ"),
        # Kratice i pridjevski oblici iz državne evidencije / MinKulture —
        # 15 % župa ovisi o njima (vidi _BDM u src/titular.py).
        ("ŽUPA UZNESENJA B.D. MARIJE", "Uznesenje BDM"),
        ("ŽUPA UZNESENJA MARIJINA", "Uznesenje BDM"),
        ("Kompleks Katedrale Uznesenja Marijina", "Uznesenje BDM"),
        ("ŽUPA POHOĐENJA BDM", "Pohod BDM"),
        ("ŽUPA ROĐENJA B. D. MARIJE", "Rođenje BDM"),
        ("ŽUPA PRESV. TROJSTVA", "Presveto Trojstvo"),
        ("ŽUPA BEZGR. ZAČEĆA BDM", "Bezgrešno začeće BDM"),
        ("ŽUPA VELIKE GOSPE, SINJ", "Velika Gospa"),
        # Bez titulara
        ("Crkva", None),
        ("", None),
        (None, None),
    ],
)
def test_parse(name, expected):
    assert parse(name) == expected


def test_key_is_diacritic_insensitive():
    # Isti objekt iz dva izvora mora dati isti ključ.
    assert key("Crkva sv. Jurja") == key("ŽUPA SV. JURJA, LOVRAN")
    assert key("Crkva svetog Jurja") == key("Crkva sv. Jurja")


def test_key_distinguishes_different_saints():
    assert key("Crkva sv. Petra") != key("Crkva sv. Pavla")


@pytest.mark.parametrize(
    "a,b",
    [
        # Epitet varira po izvoru — glava mora biti ista da match preživi.
        ("Crkva sv. Ante", "Crkva sv. Ante Padovanskog"),
        ("ŽUPA SV. ANTUNA PADOVANSKOG, ZAGREB", "Crkva sv. Antuna"),
        ("Crkva sv. Ivana", "Crkva sv. Ivana Krstitelja"),
    ],
)
def test_head_key_ignores_epithet(a, b):
    assert head_key(a) == head_key(b)
    # …ali puni titular ih i dalje razlikuje (koristi se kao bonus na score).
    assert key(a) != key(b)


def test_head_key_still_separates_saints():
    assert head_key("Crkva sv. Petra") != head_key("Crkva sv. Pavla")


def test_place_after_comma_is_not_part_of_titular():
    # "OSIJEK" ne smije završiti u titularu — inače se ista župa u dva izvora
    # (jedan s mjestom, drugi bez) ne bi spojila.
    assert parse("ŽUPA SV. ANE, OSIJEK") == parse("Crkva sv. Ane")
