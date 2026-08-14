"""Klasifikacija tipa određuje što se vidi na karti i pod kojim filterom —
pogrešan `kind` je vidljiv bug, ne kozmetika."""
from __future__ import annotations

import pytest

from src.kinds import classify, denomination_hr, religion_of


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
    ],
)
def test_classify(tags, name, expected):
    assert classify(tags, name) == expected


def test_religion_falls_back_to_kind():
    assert religion_of({}, "kapela") == "christian"
    assert religion_of({}, "dzamija") == "muslim"
    assert religion_of({"religion": "christian"}, "ostalo") == "christian"
    assert religion_of({}, "ostalo") is None


def test_denomination_hr():
    assert denomination_hr("roman_catholic") == "rimokatolička"
    assert denomination_hr("serbian_orthodox") == "srpska pravoslavna"
    # Nepoznato se propušta čitljivo, ne baca.
    assert denomination_hr("some_new_thing") == "some new thing"
    assert denomination_hr(None) is None
