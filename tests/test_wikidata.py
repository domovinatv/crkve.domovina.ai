"""Wikidata helperi — mali, ali svaki je izvor tihe greške na karti."""
from __future__ import annotations

from src.wikidata import commons_url, parse_point, qid, year_of


def test_parse_point_swaps_wkt_order():
    # WKT je Point(lng lat), a mi svugdje radimo s (lat, lng).
    assert parse_point("Point(15.9794 45.8144)") == (45.8144, 15.9794)


def test_parse_point_handles_missing():
    assert parse_point(None) is None
    assert parse_point("nešto drugo") is None


def test_qid_extracts_entity_id():
    assert qid("http://www.wikidata.org/entity/Q312220") == "Q312220"
    assert qid(None) is None


def test_commons_url_upgrades_to_https():
    # Wikidata vraća http://; na HTTPS karti bi to bio blokiran mixed content.
    assert commons_url("http://commons.wikimedia.org/x.jpg").startswith("https://")
    assert commons_url("https://commons.wikimedia.org/x.jpg").startswith("https://")
    assert commons_url(None) is None


def test_commons_url_only_replaces_scheme():
    # Ne smije pokvariti URL koji sadrži "http://" u query stringu.
    out = commons_url("http://x.org/a?u=http://y.org")
    assert out == "https://x.org/a?u=http://y.org"


def test_year_of():
    assert year_of("1242-01-01T00:00:00Z") == "1242"
    assert year_of(None) is None
    assert year_of("neispravno") is None
