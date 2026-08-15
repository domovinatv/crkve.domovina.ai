"""Google Places API (New) — precizne koordinate + kontakt + nezavisna provjera.

Prilagođeno iz ../rodjendaonice.domovina.ai/src/places.py (izvorno
klubovi.domovina.ai/scripts/27_google_geocode.py).

Uloga je ovdje UŽA nego u sestrinskim projektima. Ondje je Places bio glavni
izvor otkrivanja; ovdje građevine već dolaze iz OSM-a sa 100 % koordinata (i
to tlocrtima), pa Places služi za dvije stvari koje OSM i državne evidencije
ne mogu:

  1. **Preciziranje župa.** 1652 župe imaju samo težište naselja jer im nije
     nađena matična crkva — to je točnost sela, ne adrese. Places nad
     "ŽUPA SV. X, Mjesto" vraća točku na razini zgrade, plus telefon i web
     koje državna evidencija uopće nema.

  2. **Nezavisna provjera matchera.** Spajanje župa na crkve (scripts/11) je
     heuristika nad nazivima. Ako Places za istu župu vrati točku unutar
     nekoliko stotina metara od crkve na koju smo je spojili, to je potvrda iz
     izvora koji nije sudjelovao u matchanju. Ako je kilometrima daleko —
     match je vjerojatno kriv i ide u `geo_conflicts`.

Oba se dobivaju iz ISTOG poziva, pa je trošak jedan upit po župi.

Trošak: Text Search (New). ~2400 poziva za sve aktivne župe; keširano po SHA
zahtjeva pod data/raw/places/, pa svaki sljedeći run ne troši kvotu.

⚠️ Dvije zamke naučene u sestrinskim repoima:
  - default dnevna kvota `SearchTextRequestPerDayPerProject` je **100** —
    diže se ručno u GCP konzoli (APIs & Services → Quotas);
  - ključ s **IP restrikcijom** vraća 403 `API_KEY_IP_ADDRESS_BLOCKED` čim se
    promijeni javni IP. Poruka niže to izričito imenuje da se ne gubi vrijeme.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from rapidfuzz import fuzz

from .normalize import norm_key, strip_type_prefix, title_case_hr

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

CACHE_DIR = ROOT / "data" / "raw" / "places"
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join(
    f"places.{f}" for f in (
        "id", "displayName", "formattedAddress", "location",
        "types", "primaryType", "primaryTypeDisplayName",
        "nationalPhoneNumber", "internationalPhoneNumber", "websiteUri",
        "googleMapsUri", "businessStatus", "addressComponents",
    )
)

HR_LAT = (42.30, 46.60)
HR_LNG = (13.40, 19.50)

# Places `types` koji potvrđuju da je rezultat sakralni objekt, a ne kafić s
# imenom "Sv. Ana". Bez ove provjere Text Search zna vratiti bilo što iz mjesta.
SACRAL_TYPES = {
    "church", "place_of_worship", "mosque", "synagogue", "hindu_temple",
    "cemetery",  # groblja često nose crkvu; prihvaćamo uz provjeru naziva
}

_NON_HR = (
    "slovenija", "slovenia", "bosna i hercegovina", "bosnia", "bih",
    "srbija", "serbia", "crna gora", "montenegro", "italija", "italy",
    "mađarska", "hungary", "austrija", "austria",
)


def in_hr(lat: float, lng: float) -> bool:
    return HR_LAT[0] <= lat <= HR_LAT[1] and HR_LNG[0] <= lng <= HR_LNG[1]


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _cache_path(payload: dict) -> Path:
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return CACHE_DIR / f"{h}.json"


class PlacesError(RuntimeError):
    """Greška koja znači 'ne pokušavaj dalje' (ključ, kvota, dozvole)."""


class PlacesClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise PlacesError(
                "GOOGLE_MAPS_API_KEY nije postavljen. Kopiraj .env.example u .env "
                "i upiši ključ (Places API New mora biti uključen na projektu)."
            )
        self._client = httpx.Client(timeout=30.0)
        self.calls = 0
        self.cache_hits = 0

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()

    def search_text(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Text Search ograničen na HR bbox; vraća parsirane rezultate. Keširano."""
        body = {
            "textQuery": query,
            "regionCode": "HR",
            "languageCode": "hr",
            "maxResultCount": max_results,
            "locationRestriction": {
                "rectangle": {
                    "low": {"latitude": HR_LAT[0], "longitude": HR_LNG[0]},
                    "high": {"latitude": HR_LAT[1], "longitude": HR_LNG[1]},
                }
            },
        }
        cache = _cache_path(body)
        if cache.exists():
            self.cache_hits += 1
            data = json.loads(cache.read_text())
        else:
            r = self._client.post(
                PLACES_URL,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": FIELD_MASK,
                },
            )
            self.calls += 1
            if r.status_code == 403:
                raise PlacesError(_explain_403(r.text))
            if r.status_code == 429:
                raise PlacesError(
                    "Places 429 — probijena kvota. Default "
                    "`SearchTextRequestPerDayPerProject` je 100/dan; digni je u GCP "
                    "konzoli (APIs & Services → Quotas) ili nastavi sutra "
                    "(keširani odgovori se ne ponavljaju)."
                )
            if r.status_code != 200:
                logger.warning("places %d za %r: %s", r.status_code, query, r.text[:200])
                return []
            data = r.json()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        return [p for p in (self._parse(x) for x in (data.get("places") or [])) if p]

    @staticmethod
    def _parse(p: dict) -> dict[str, Any] | None:
        loc = p.get("location") or {}
        lat, lng = loc.get("latitude"), loc.get("longitude")
        if lat is None or lng is None or not in_hr(float(lat), float(lng)):
            return None
        addr = p.get("formattedAddress") or ""
        if any(c in addr.lower() for c in _NON_HR):
            return None
        city = postal = county = None
        for comp in p.get("addressComponents") or []:
            types = comp.get("types") or []
            if "locality" in types or "postal_town" in types:
                city = comp.get("longText")
            elif "administrative_area_level_1" in types:
                county = comp.get("longText")
            elif "postal_code" in types:
                postal = comp.get("longText")
        types = p.get("types") or []
        return {
            "place_id": p.get("id"),
            "name": (p.get("displayName") or {}).get("text"),
            "address": addr,
            "city": city,
            "county": county,
            "postal_code": postal,
            "lat": float(lat),
            "lng": float(lng),
            "phone": p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber"),
            "website": p.get("websiteUri"),
            "types": types,
            "is_sacral": bool(set(types) & SACRAL_TYPES),
            "primary_type": (p.get("primaryTypeDisplayName") or {}).get("text")
            or p.get("primaryType"),
            "google_maps_uri": p.get("googleMapsUri"),
            "business_status": p.get("businessStatus"),
        }


# --- validacija rezultata ---------------------------------------------------
# Živi ovdje, a ne u scripts/13, iz dva razloga: pripada uz klijent (bez ovoga
# je `search_text` opasan jer Text Search UVIJEK nešto vrati), i modul koji
# počinje brojkom se ne može importati u testove.

NAME_MIN = 70  # minimalna sličnost naziva kad tip rezultata nije sakralni


def queries_for(name: str, city: str | None, address: str | None) -> list[str]:
    """Kandidat-upiti za jednu župu, od najspecifičnijeg prema najopćenitijem."""
    readable = title_case_hr(name)
    core = strip_type_prefix(readable).strip()
    city = (city or "").strip()
    address = (address or "").strip()

    out: list[str] = []
    if address and city:
        out.append(f"{readable}, {address}, {city}")
    if city:
        out.append(f"{readable}, {city}")
        # Bez riječi "Župa": Google češće zna crkvu nego župni ured.
        if core and core != readable:
            out.append(f"Crkva {core}, {city}")
    seen: set[str] = set()
    return [q for q in out if not (q in seen or seen.add(q))]


def pick(results: list[dict], parish_name: str, county: str | None) -> dict | None:
    """Prvi rezultat koji je uvjerljivo TAJ objekt, ili None.

    Text Search uvijek vrati nešto — bez ova dva filtra u katalog uđu kafići i
    trgovine iz istog mjesta:
      1. sakralni `types`, ili vrlo sličan naziv ako tipa nema;
      2. ista županija (Places zna odlutati u susjedno istoimeno mjesto).
    """
    from . import geo_hr  # lokalni import: geo_hr učitava 21 MB granica

    want = norm_key(parish_name)
    for r in results:
        if not r.get("is_sacral"):
            if fuzz.token_set_ratio(want, norm_key(r.get("name") or "")) < NAME_MIN:
                continue
        place = geo_hr.locate(r["lat"], r["lng"])
        if county and place.county and place.county != county:
            continue
        return r
    return None


def _explain_403(body: str) -> str:
    """403 iz Placesa ima tri različita uzroka i tri različita rješenja."""
    low = (body or "").lower()
    if "ip address restriction" in low or "api_key_ip_address_blocked" in low:
        return (
            "Places 403 — ključ ima IP restrikciju koja ne pokriva tvoj trenutni "
            "javni IP. U GCP konzoli (APIs & Services → Credentials → ključ → "
            "Application restrictions) dodaj IP ili privremeno makni restrikciju."
        )
    if "referer" in low:
        return (
            "Places 403 — ključ je ograničen na HTTP referrer (za web), a ovo je "
            "server-side poziv. Treba ključ bez referrer restrikcije."
        )
    if "has not been used" in low or "disabled" in low or "not enabled" in low:
        return (
            "Places 403 — Places API (New) nije uključen na projektu tog ključa. "
            "Uključi 'Places API (New)' u GCP konzoli."
        )
    return f"Places 403 — nema dozvole. Odgovor: {body[:300]}"
