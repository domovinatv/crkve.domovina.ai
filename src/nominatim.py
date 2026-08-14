"""Nominatim (OpenStreetMap) geocoder s keširanjem i fallback ljestvicom.

Kopiran iz ../rodjendaonice.domovina.ai/src/nominatim.py (izvorno
klubovi.domovina.ai/scripts/10_geocode_nominatim.py). Radi na generičkim
(address, city, county) poljima.

Ovdje se koristi SAMO za sjedišta župa iz državne evidencije — građevine
dolaze iz OSM-a s već točnim koordinatama, pa geokodiranje nije na kritičnom
putu.

Poštuje NOMINATIM_ENDPOINT (lokalni Docker bez throttlea) inače javni SaaS
s 1.05 req/s. Odgovori se kešraju pod data/raw/nominatim/ po SHA upita.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "raw" / "nominatim"
USER_AGENT = (
    "crkve-domovina-ai/0.1 (open church catalog; "
    + os.environ.get("CONTACT_EMAIL", "stepanic.matija@gmail.com")
    + ")"
)
_BASE = os.environ.get("NOMINATIM_ENDPOINT", "https://nominatim.openstreetmap.org").rstrip("/")
ENDPOINT = f"{_BASE}/search"
_LOCAL = any(h in _BASE for h in ("localhost", "127.0.0.1", "nominatim:"))
_THROTTLE = 0.0 if _LOCAL else 1.05

# Croatia bbox za validaciju (odbaci prekogranične pogotke).
HR_LAT = (42.30, 46.60)
HR_LNG = (13.40, 19.50)

_ZIP_RE = re.compile(r"\b(\d{4,5})\b")


def in_hr(lat: float, lng: float) -> bool:
    return HR_LAT[0] <= lat <= HR_LAT[1] and HR_LNG[0] <= lng <= HR_LNG[1]


def _addr_tail(addr: str) -> str | None:
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    if parts and parts[-1].lower() == "hrvatska":
        parts = parts[:-1]
    if len(parts) >= 3:
        return ", ".join(parts[-2:])
    return None


def _zip_from(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r"(\d)\s+(\d)", r"\1\2", text)
    m = _ZIP_RE.search(cleaned)
    if m and len(m.group(1)) == 5:
        return m.group(1)
    return None


def build_query_candidates(rec: dict) -> list[str]:
    """Uređene kandidat-upite od najspecifičnijeg do najopćenitijeg."""
    out: list[str] = []
    county = (rec.get("county") or "").replace(" županija", "").strip()
    address = (rec.get("address") or "").strip()
    city = (rec.get("city") or "").strip()
    zip_code = _zip_from(address) or _zip_from(city)

    if address:
        out.append(f"{address}, Hrvatska")
        tail = _addr_tail(address)
        if tail:
            out.append(f"{tail}, Hrvatska")
    if zip_code:
        out.append(f"{zip_code}, Hrvatska")
    if city and county:
        out.append(f"{city}, {county}, Hrvatska")
    if city:
        out.append(f"{city}, Hrvatska")

    seen: set[str] = set()
    return [q for q in out if not (q in seen or seen.add(q))]


def _cache_path(query: str) -> Path:
    h = hashlib.sha256(query.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{h}.json"


def geocode_one(client: httpx.Client, query: str) -> tuple[float, float] | None:
    cache = _cache_path(query)
    if cache.exists():
        data = json.loads(cache.read_text())
    else:
        if _THROTTLE:
            time.sleep(_THROTTLE)
        try:
            r = client.get(
                ENDPOINT,
                params={"q": query, "format": "json", "countrycodes": "hr", "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
        except httpx.HTTPError as e:
            logger.warning("network error for %r: %s", query, e)
            return None
        if r.status_code != 200:
            logger.warning("nominatim %d for %r", r.status_code, query)
            return None
        data = r.json()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data, ensure_ascii=False))

    if not data:
        return None
    try:
        lat, lng = float(data[0]["lat"]), float(data[0]["lon"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return (lat, lng) if in_hr(lat, lng) else None


def geocode(client: httpx.Client, rec: dict) -> tuple[float, float] | None:
    """Probaj kandidate dok jedan ne pogodi. rec: {address, city, county}."""
    for q in build_query_candidates(rec):
        hit = geocode_one(client, q)
        if hit:
            return hit
    return None
