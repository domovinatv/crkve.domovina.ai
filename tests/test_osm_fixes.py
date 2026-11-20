"""Ispravci OSM tagova (src/osm_fixes.py) — ulaz iz keša Overpassa, bez mreže."""
from __future__ import annotations

from src import osm_fixes

# Tagovi čvora 13304771994 kako ih vraća Overpass (keš 2026-08-15).
TEREZIJA = {
    "amenity": "place_of_worship", "denomination": "roman_catholic",
    "name": "kapela svete Terezije od Djeteta Isusa u Trnju", "religion": "christian",
    "wikidata": "Q132087369", "wikipedia": "hr:Župna crkva Svih Svetih u Zagrebu",
}


def test_kapela_u_trnju_ne_nosi_wikidata_crkve_svih_svetih():
    t = osm_fixes.apply("node", 13304771994, TEREZIJA)
    assert t["wikidata"] == "Q132079947"
    assert "wikipedia" not in t
    assert t["name"] == TEREZIJA["name"]
    assert TEREZIJA["wikidata"] == "Q132087369"     # ulaz netaknut


def test_ostali_elementi_prolaze_bez_promjene():
    t = {"wikidata": "Q132087369"}
    assert osm_fixes.apply("way", 459564717, t) is t
