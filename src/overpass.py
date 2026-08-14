"""Tanak klijent nad OSM Overpass API-jem. Bez API ključa.

Kopiran iz ../rodjendaonice.domovina.ai/src/overpass.py — isti obrazac
(keš po SHA upita, dva endpointa, retry). Ovdje je OSM PRIMARNI izvor
geometrije: `amenity=place_of_worship` + srodni tagovi daju ~6800 sakralnih
objekata u HR, od kojih su ~5200 tlocrti (way/relation), ne točke.

Odgovori se kešraju pod data/raw/osm/ po SHA upita — pipeline je zato
idempotentan i drugi run ne dira mrežu.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "raw" / "osm"
_ENV_EP = os.environ.get("OVERPASS_ENDPOINT")
ENDPOINTS = [_ENV_EP] if _ENV_EP else [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _user_agent() -> str:
    contact = os.environ.get("CONTACT_EMAIL", "stepanic.matija@gmail.com")
    return f"crkve-domovina-ai/0.1 (open church catalog; {contact})"


# overpass-api.de vraća 406 bez User-Agenta.
HEADERS = {
    "User-Agent": _user_agent(),
    "Accept": "application/json",
}


def _cache_path(query: str) -> Path:
    h = hashlib.sha256(query.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{h}.json"


def query(overpass_ql: str) -> list[dict[str, Any]]:
    """Pokreni Overpass QL i vrati listu elemenata (s `center` za ways/relations).

    Dodaj `[out:json]` i `out center;` u QL prije poziva. Vraća `elements`.
    """
    cache = _cache_path(overpass_ql)
    if cache.exists():
        return json.loads(cache.read_text()).get("elements", [])

    last_err: Exception | None = None
    for ep in ENDPOINTS:
        for attempt in range(3):
            try:
                r = httpx.post(ep, data={"data": overpass_ql}, headers=HEADERS, timeout=180)
            except httpx.HTTPError as e:
                last_err = e
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 200:
                data = r.json()
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(data, ensure_ascii=False))
                return data.get("elements", [])
            if r.status_code in (429, 504):
                logger.warning("overpass %d (%s), retry", r.status_code, ep)
                time.sleep(5 * (attempt + 1))
                continue
            last_err = RuntimeError(f"overpass {r.status_code}: {r.text[:200]}")
            break
    raise RuntimeError(f"overpass nedostupan: {last_err}")


def latlng(el: dict) -> tuple[float, float] | None:
    if "lat" in el and "lon" in el:
        return float(el["lat"]), float(el["lon"])
    c = el.get("center")
    if c and "lat" in c and "lon" in c:
        return float(c["lat"]), float(c["lon"])
    return None
