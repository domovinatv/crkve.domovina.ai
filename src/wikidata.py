"""Wikidata SPARQL klijent — crkve u Hrvatskoj. Bez API ključa, sadržaj je CC0.

Wikidata je manja od OSM-a (~850 objekata s koordinatama naspram ~6800) ali
nosi ono što OSM nema: sliku na Commonsu, poveznicu na Wikipediju, arhitekta,
godinu gradnje, i vezu na Registar kulturnih dobara (property P1435/P4552).
Spaja se na OSM zapise preko `P402` (OSM relation id) ili prostorno.

Odgovori se kešraju pod data/raw/wikidata/.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "raw" / "wikidata"
ENDPOINT = "https://query.wikidata.org/sparql"

# Q1370598 = bogomolja (place of worship); pokriva crkve, kapele, džamije,
# sinagoge i samostanske crkve preko podklasa. Q224 = Hrvatska.
QUERY = """
SELECT ?item ?itemLabel ?coord ?image ?article ?inception ?architectLabel
       ?styleLabel ?heritage ?osmRel ?adminLabel ?typeLabel
WHERE {
  ?item wdt:P31/wdt:P279* wd:Q1370598 .
  ?item wdt:P17 wd:Q224 .
  ?item wdt:P625 ?coord .
  OPTIONAL { ?item wdt:P18 ?image . }
  OPTIONAL { ?item wdt:P571 ?inception . }
  OPTIONAL { ?item wdt:P84 ?architect . }
  OPTIONAL { ?item wdt:P149 ?style . }
  OPTIONAL { ?item wdt:P1435 ?heritage . }
  OPTIONAL { ?item wdt:P402 ?osmRel . }
  OPTIONAL { ?item wdt:P131 ?admin . }
  OPTIONAL { ?item wdt:P31 ?type . }
  OPTIONAL {
    ?article schema:about ?item ;
             schema:isPartOf <https://hr.wikipedia.org/> .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "hr,en". }
}
"""

_POINT_RE = re.compile(r"Point\(([-\d.]+)\s+([-\d.]+)\)")


def _user_agent() -> str:
    contact = os.environ.get("CONTACT_EMAIL", "stepanic.matija@gmail.com")
    return f"crkve-domovina-ai/0.1 (open church catalog; {contact})"


def query(sparql: str = QUERY, force: bool = False) -> list[dict[str, Any]]:
    """Pokreni SPARQL i vrati listu poravnatih dictova (vrijednosti, ne bindingsi)."""
    h = hashlib.sha256(sparql.encode()).hexdigest()[:16]
    cache = CACHE_DIR / f"{h}.json"
    if cache.exists() and not force:
        return json.loads(cache.read_text())

    r = httpx.get(
        ENDPOINT,
        params={"query": sparql},
        headers={"Accept": "application/sparql-results+json", "User-Agent": _user_agent()},
        timeout=180,
        follow_redirects=True,
    )
    r.raise_for_status()
    bindings = r.json()["results"]["bindings"]
    rows = [{k: v.get("value") for k, v in b.items()} for b in bindings]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows, ensure_ascii=False))
    logger.info("wikidata: %d redaka", len(rows))
    return rows


def parse_point(coord: str | None) -> tuple[float, float] | None:
    """'Point(15.97 45.81)' → (45.81, 15.97) — WKT je lng lat, mi vraćamo lat lng."""
    if not coord:
        return None
    m = _POINT_RE.search(coord)
    if not m:
        return None
    lng, lat = float(m.group(1)), float(m.group(2))
    return lat, lng


def qid(uri: str | None) -> str | None:
    """'http://www.wikidata.org/entity/Q123' → 'Q123'."""
    if not uri:
        return None
    return uri.rsplit("/", 1)[-1] or None


def commons_url(image: str | None) -> str | None:
    """Wikidata P18 vraća pun Special:FilePath URL, ali preko **http://**.

    Karta se servira s HTTPS-a, pa bi ga preglednik blokirao kao mixed content
    i slika se nikad ne bi prikazala. Zato prisilni upgrade sheme.
    """
    if not image:
        return None
    return image.replace("http://", "https://", 1) if image.startswith("http://") else image


def year_of(inception: str | None) -> str | None:
    """'1242-01-01T00:00:00Z' → '1242'. Negativne (pr. Kr.) godine propušta."""
    if not inception:
        return None
    m = re.match(r"^(-?\d{1,4})-", inception)
    return m.group(1) if m else None
