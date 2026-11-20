"""Spajanje Wikidata entiteta na OSM građevinu (scripts/05 `_nearest`), odluka 314."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "m05", Path(__file__).resolve().parent.parent / "scripts" / "05_ingest_wikidata.py")
m05 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m05)


def _grid(*rows):
    g = {}
    for r in rows:
        g.setdefault((int(r[1] * 100), int(r[2] * 100)), []).append(r)
    return g


def test_gradevina_s_drugim_q_nije_kandidat():
    # Q133733258 „BDM Bezgrešne na Knežiji" 20 m od w246443250 „BDM Pomoćnice"
    # koja već nosi Q125578862 — to su dvije crkve.
    g = _grid((1, 45.79, 15.95, "Majka Božja", "Q125578862"))
    assert m05._nearest(g, 45.7901, 15.9501, "majka bozja", "Q133733258") is None
    # Isti Q ili građevina bez Q-a: spaja se kao i prije
    g = _grid((2, 45.79, 15.95, "Majka Božja", None))
    assert m05._nearest(g, 45.7901, 15.9501, "majka bozja", "Q138496303") == 2
