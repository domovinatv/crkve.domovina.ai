"""Derivacija teritorija biskupija je izračun koji izgleda kao podatak — na
karti se ne vidi razlika između granice koja je preslikana iz izvora i one
koja je pogođena. Testovi fiksiraju pravila zbog kojih joj se smije vjerovati:
župa koja sjedi u naselju ima prednost pred najbližom, spajanje ne ostavlja
šavove, i mjera slaganja s OSM-om mjeri ono što tvrdi.
"""
from __future__ import annotations

import pytest

from src import dioceses as dio


def square(x: float, y: float, size: float = 1.0) -> list:
    """Jedan poligon (lista ringova) s donjim lijevim uglom u (x, y)."""
    return [[[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]]]


def sett(idx: int, x: float, y: float, size: float = 1.0, pop: int = 100):
    return dio.Settlement(
        idx=idx, name=f"n{idx}", lat=y + size / 2, lng=x + size / 2,
        population=pop, area_km2=1.0, polygons=[square(x, y, size)],
    )


def test_krizevacka_je_izuzeta_iz_particije():
    """Grkokatolička eparhija se preklapa s latinskima — u particiji bi im
    otela teritorij oko svake svoje župe."""
    assert "krizevacka-eparhija" in dio.OVERLAPPING_SLUGS


def test_zupa_u_naselju_pobjeđuje_bližu_izvana():
    """Župa koja SJEDI u naselju je dokaz; najbliža je tek procjena. Ovdje je
    tuđa župa geometrijski bliža težištu nego vlastita, pa bi naivni
    'najbliža nosi' dao krivu biskupiju."""
    s = [sett(0, 0, 0)]
    parishes = [
        dio.Parish(1, "unutra", "A", lat=0.9, lng=0.9),    # unutar naselja
        dio.Parish(2, "izvana", "B", lat=0.5, lng=1.01),   # bliže težištu, izvan
    ]
    a = dio.assign(s, parishes)
    assert a.by_settlement[0] == "A"
    assert (a.direct, a.nearest) == (1, 0)


def test_naselje_bez_zupe_ide_najblizoj():
    s = [sett(0, 0, 0), sett(1, 5, 5)]
    parishes = [dio.Parish(1, "p", "A", lat=0.5, lng=0.5)]
    a = dio.assign(s, parishes)
    assert a.by_settlement[0] == "A" and a.by_settlement[1] == "A"
    assert (a.direct, a.nearest) == (1, 1)


def test_naselje_s_dvije_biskupije_dobiva_vecinu():
    s = [sett(0, 0, 0)]
    parishes = [
        dio.Parish(1, "a1", "A", lat=0.2, lng=0.2),
        dio.Parish(2, "a2", "A", lat=0.3, lng=0.3),
        dio.Parish(3, "b1", "B", lat=0.8, lng=0.8),
    ]
    a = dio.assign(s, parishes)
    assert a.by_settlement[0] == "A"
    assert a.mixed == 1


def test_dissolve_spaja_susjedna_naselja_bez_sava():
    """Dva dodirna kvadrata iste biskupije daju JEDAN poligon površine 2,
    ne dva. Bez toga bi granica na karti imala unutarnje šavove."""
    s = [sett(0, 0, 0), sett(1, 1, 0)]
    a = dio.Assignment({0: "A", 1: "A"}, direct=2, nearest=0, mixed=0)
    out = dio.dissolve(s, a)
    assert set(out) == {"A"}
    assert out["A"].geom_type == "Polygon"
    assert out["A"].area == pytest.approx(2.0, rel=1e-6)


def test_dissolve_razdvaja_biskupije():
    s = [sett(0, 0, 0), sett(1, 1, 0)]
    a = dio.Assignment({0: "A", 1: "B"}, direct=2, nearest=0, mixed=0)
    out = dio.dissolve(s, a)
    assert set(out) == {"A", "B"}


def test_agreement_broji_samo_naselja_unutar_osm_granice():
    """Mjera se računa nad onim što OSM pokriva — naselje izvan njegove
    granice nije ni pogodak ni promašaj, inače bi nepotpuna OSM relacija
    izgledala kao naša greška."""
    s = [sett(0, 0, 0), sett(1, 1, 0), sett(2, 9, 9)]
    a = dio.Assignment({0: "A", 1: "B", 2: "A"}, direct=3, nearest=0, mixed=0)
    osm = dio._geom([square(0, 0, 2.0)])           # pokriva naselja 0 i 1
    assert dio.agreement(s, a, osm, "A") == (1, 2)


def test_iou_identicnih_je_jedan():
    g = dio._geom([square(0, 0)])
    assert dio.iou(g, g) == pytest.approx(1.0)
    assert dio.iou(g, dio._geom([square(5, 5)])) == 0.0


def test_osm_boundaries_slaze_wayeve_u_prsten():
    """Overpass vraća nesložene wayeve; granica nastaje tek njihovim
    spajanjem, pa `polygonize` mora zatvoriti prsten iz dva luka."""
    element = {
        "type": "relation",
        "tags": {"name": "Test biskupija"},
        "members": [
            {"type": "way", "role": "outer", "geometry": [
                {"lon": 0, "lat": 0}, {"lon": 1, "lat": 0}, {"lon": 1, "lat": 1}]},
            {"type": "way", "role": "outer", "geometry": [
                {"lon": 1, "lat": 1}, {"lon": 0, "lat": 1}, {"lon": 0, "lat": 0}]},
        ],
    }
    out = dio.osm_boundaries([element])
    assert out["Test biskupija"].area == pytest.approx(1.0)


def test_to_geojson_geometry_zaokruzuje_na_6_decimala():
    g = dio._geom([[[[0, 0], [1.123456789, 0], [1, 1], [0, 0]]]])
    assert "1.123457" in dio.to_geojson_geometry(g)
    assert "1.123456789" not in dio.to_geojson_geometry(g)
