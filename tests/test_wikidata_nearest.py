"""scripts/05 `_nearest`: prostorno spajanje Wikidate uz provjeru zaziva (odluka 405)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from src import titular

_spec = importlib.util.spec_from_file_location(
    "ingest_wikidata", Path(__file__).parent.parent / "scripts" / "05_ingest_wikidata.py")
w05 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w05)


def _grid(*rows):
    g: dict = {}
    for cid, lat, lng, name in rows:
        g.setdefault((int(lat * 100), int(lng * 100)), []).append(
            (cid, lat, lng, titular.parse(name), titular.zaziv(name)))
    return g


def _near(grid, lat, lng, name):
    return w05._nearest(grid, lat, lng, titular.key(name), titular.zaziv(name))


def test_kneziji_bezgresna_nije_pomocnica():
    # Q133733258 (kapela 2006.) i w246443250 (župna crkva 1929.), ~20 m.
    g = _grid((1, 45.7930458, 15.9524526, "crkva Blažene Djevice Marije Pomoćnice"))
    assert _near(g, 45.793055555, 15.952222222,
                 "Kapela Blažene Djevice Marije Bezgrešne na Knežiji") is None
    # Isti entitet Pomoćnice (Q125578862) i dalje sjeda na svoju crkvu.
    assert _near(g, 45.7930757, 15.9522095,
                 "Župna crkva Blažene Djevice Marije Pomoćnice u Knežiji") == 1


def test_gola_bdm_sjeda_na_zaziv():
    # Marija Bistrica: entitet bez zaziva smije na baziliku Majke Božje Bistričke.
    g = _grid((1, 46.0, 16.1, "bazilika Majke Božje Bistričke"))
    assert _near(g, 46.0002, 16.1002, "Crkva Majke Božje (Marija Bistrica)") == 1
