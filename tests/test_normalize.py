"""Slug i title-case rade nad državnim registrima koji sve pišu verzalom —
greške ovdje su vidljive na karti u svakom popupu."""
from __future__ import annotations

import pytest

from src.normalize import norm_key, slugify, strip_type_prefix, title_case_hr


def test_slug_strips_type_prefix_and_adds_place():
    assert slugify("Crkva sv. Marka", "Zagreb") == "sv-marka-zagreb"
    assert slugify("ŽUPA SV. ANE", "Osijek") == "sv-ane-osijek"


def test_slug_handles_croatian_d():
    # đ/Đ se ne dekomponiraju pod NFKD — bez eksplicitnog mapiranja ispadnu.
    assert "d" in slugify("Crkva sv. Đurđa", "Đakovo")
    assert slugify("Crkva sv. Đurđa", "Đakovo") == "sv-durda-dakovo"


def test_slug_suffix_makes_it_unique():
    a = slugify("Crkva sv. Marka", "Zagreb", suffix="w123")
    b = slugify("Crkva sv. Marka", "Zagreb", suffix="w456")
    assert a != b and a.endswith("w123")


def test_slug_never_empty():
    assert slugify("") == "crkva"
    assert slugify("...") == "crkva"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Crkva sv. Marka", "sv. Marka"),
        ("ŽUPA SV. ANE, OSIJEK", "SV. ANE, OSIJEK"),
        ("Franjevački samostan", "Franjevački samostan"),  # nije prefiks na početku
        ("Kapela", "Kapela"),                              # sam tip ostaje
    ],
)
def test_strip_type_prefix(name, expected):
    assert strip_type_prefix(name) == expected


def test_norm_key_unifies_saint_forms():
    assert norm_key("Crkva svetog Jurja") == norm_key("Crkva sv. Jurja")
    assert norm_key("Crkva sv. Ane") == norm_key("Kapela svete Ane")


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Veznik "i" ne smije proći kao rimska jedinica.
        ("BISKUPIJA POREČKA I PULSKA", "Biskupija Porečka i Pulska"),
        ("ZAGREBAČKA NADBISKUPIJA", "Zagrebačka Nadbiskupija"),
        ("ŽUPA BL. ALOJZIJA STEPINCA", "Župa bl. Alojzija Stepinca"),
        # Kratice ostaju verzalne.
        ("ŽUPA UZNESENJA BDM", "Župa Uznesenja BDM"),
        # Prava rimska brojka preživi.
        ("PAPA IVAN XXIII", "Papa Ivan XXIII"),
    ],
)
def test_title_case_hr(raw, expected):
    assert title_case_hr(raw) == expected
