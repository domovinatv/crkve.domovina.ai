"""Klijent za data.gov.hr (CKAN) — državne evidencije, bez API ključa.

Tri dataseta nose cijeli "pravni" sloj kataloga:

  KATOLICKE_PRAVNE_OSOBE  Evidencija pravnih osoba Katoličke Crkve u RH
                          (Ministarstvo pravosuđa i uprave). ~2100 zapisa,
                          od toga ~1560 župa. Polja: OIB, NAZIV, SJEDISTE,
                          BISKUPIJA_NADBISKUPIJA, EVIDENCIJSKI_BROJ, STATUS.

  VJERSKE_ZAJEDNICE       Evidencija vjerskih zajednica u RH — 54 zajednice
                          (SPC, islamska, evangelička, adventistička…).

  VJERSKE_ORG_OBLICI      Organizacijski oblici tih zajednica — 863 zapisa
                          (crkvene općine, parohije, džemati) s OIB-om i
                          sjedištem. To je nekatolički pandan župama.

  KULTURNA_DOBRA          Registar kulturnih dobara RH (Ministarstvo kulture
                          i medija) — 7950 zapisa, od toga 1758 "sakralna
                          graditeljska baština".

Resource UUID-i su hardkodirani jer CKAN `package_show` zna promijeniti
redoslijed resursa; `resolve()` ih po potrebi ponovno otkrije po datasetu i
formatu, pa link ne trune ako Ministarstvo re-uploada.

Odgovori se kešraju pod data/raw/datagovhr/.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "raw" / "datagovhr"
CKAN = "https://data.gov.hr/ckan/api/3/action"
DOWNLOAD = "https://data.gov.hr/ckan/dataset/{pkg}/resource/{res}/download/data.json"


def _user_agent() -> str:
    contact = os.environ.get("CONTACT_EMAIL", "stepanic.matija@gmail.com")
    return f"crkve-domovina-ai/0.1 (open church catalog; {contact})"


HEADERS = {"User-Agent": _user_agent(), "Accept": "application/json"}


class Dataset:
    """(dataset-name, package-uuid, resource-uuid) za jedan JSON resurs."""

    def __init__(self, key: str, name: str, pkg: str, res: str, label: str):
        self.key = key
        self.name = name      # CKAN `name` slug — koristi se za re-resolve
        self.pkg = pkg
        self.res = res
        self.label = label

    @property
    def url(self) -> str:
        return DOWNLOAD.format(pkg=self.pkg, res=self.res)


KATOLICKE_PRAVNE_OSOBE = Dataset(
    "katolicke-pravne-osobe",
    "evidencija-pravnih-osoba-katolicke-crkve-u-republici-hrvatskoj",
    "6d975f94-bcf2-484f-a3d6-25d953807efa",
    "de8fc36b-44e9-400d-9330-58f478c4fb4f",
    "Evidencija pravnih osoba Katoličke Crkve u RH",
)
VJERSKE_ZAJEDNICE = Dataset(
    "vjerske-zajednice",
    "evidencija-vjerskih-zajednica-u-republici-hrvatskoj",
    "4f927a36-4bf3-4cbd-88f8-209365dabf7b",
    "e96a3ab2-3d7f-49dd-a77f-d360c15c7b1a",
    "Evidencija vjerskih zajednica u RH",
)
VJERSKE_ORG_OBLICI = Dataset(
    "vjerske-org-oblici",
    "evidencija-vjerskih-zajednica-u-republici-hrvatskoj",
    "4f927a36-4bf3-4cbd-88f8-209365dabf7b",
    "45f14bdc-f375-4eda-8a15-5501e0ff3a70",
    "Organizacijski oblici vjerskih zajednica",
)
KULTURNA_DOBRA = Dataset(
    "kulturna-dobra",
    "kulturna-dobra",
    "c0410787-33b1-4299-b92c-9bbf38dd8bbf",
    "c9a9bce6-1b70-45ec-b2cf-d3f93bca7a02",
    "Registar kulturnih dobara RH",
)


def _cache_path(ds: Dataset) -> Path:
    h = hashlib.sha256(ds.url.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{ds.key}-{h}.json"


def resolve(ds: Dataset) -> list[str]:
    """Vrati sve JSON download URL-ove dataseta (fallback ako hardkodirani padne)."""
    try:
        r = httpx.get(f"{CKAN}/package_show", params={"id": ds.name},
                      headers=HEADERS, timeout=30, follow_redirects=True)
        r.raise_for_status()
        res = r.json()["result"]["resources"]
    except (httpx.HTTPError, KeyError, json.JSONDecodeError) as e:
        logger.warning("CKAN package_show(%s) pao: %s", ds.name, e)
        return []
    return [x["url"] for x in res if (x.get("format") or "").upper() == "JSON"]


def fetch(ds: Dataset, force: bool = False) -> list[dict[str, Any]]:
    """Dohvati dataset kao listu dictova. Keširano; `force` zaobilazi keš."""
    cache = _cache_path(ds)
    if cache.exists() and not force:
        return json.loads(cache.read_text())

    # Hardkodirani URL prvo; CKAN re-resolve tek ako padne (štedi jedan poziv
    # po datasetu u normalnom slučaju).
    last_err: Exception | None = None
    tried: set[str] = set()
    for url in [ds.url, *(resolve(ds) if _probe_fails(ds) else [])]:
        if url in tried:
            continue
        tried.add(url)
        try:
            r = httpx.get(url, headers=HEADERS, timeout=120, follow_redirects=True)
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            last_err = e
            logger.warning("data.gov.hr %s pao (%s), pokušavam sljedeći URL", ds.key, e)
            continue
        if not isinstance(data, list):
            # Neki resursi vraćaju {"records": [...]}; uzmi prvu listu u dictu.
            data = next((v for v in data.values() if isinstance(v, list)), [])
        if not data:
            continue
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data, ensure_ascii=False))
        logger.info("%s: %d zapisa (keš zapisan)", ds.label, len(data))
        return data
    raise RuntimeError(f"data.gov.hr nedostupan za {ds.key}: {last_err}")


def _probe_fails(ds: Dataset) -> bool:
    """HEAD na hardkodirani URL — ako ne prolazi, vrijedi platiti CKAN lookup."""
    try:
        r = httpx.head(ds.url, headers=HEADERS, timeout=20, follow_redirects=True)
        return r.status_code >= 400
    except httpx.HTTPError:
        return True


def split_sjediste(sjediste: str | None) -> tuple[str | None, str | None]:
    """'Zagreb, Kaptol 31' → ('Kaptol 31', 'Zagreb').

    Evidencije pišu sjedište kao "MJESTO, Ulica broj". Neki zapisi imaju samo
    mjesto, neki imaju zarez unutar naziva ulice — uzimamo prvi zarez kao
    granicu, ostatak je ulica.
    """
    if not sjediste:
        return None, None
    parts = [p.strip() for p in sjediste.split(",")]
    if len(parts) == 1:
        return None, parts[0] or None
    city = parts[0] or None
    street = ", ".join(parts[1:]).strip() or None
    return street, city
