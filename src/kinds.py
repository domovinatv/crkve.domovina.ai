"""Klasifikacija sakralnih objekata u kanonske `kind` / `religion` / `denomination`.

OSM je tagiran nekonzistentno: ista katedrala može biti
`amenity=place_of_worship + building=cathedral`, samo `building=church`, ili
`amenity=place_of_worship + church:type=cathedral`. Naziv je često jedini
pouzdan signal ("Katedrala sv. Duje"). Zato klasifikacija gleda, redom:

  1. eksplicitne OSM tagove (`building`, `church:type`, `denomination`)
  2. naziv objekta (hrvatski ključni pojmovi)
  3. religiju kao zadnji fallback (muslim → džamija, jewish → sinagoga)

Kanonski `kind` je ono po čemu se filtrira na karti, pa mora biti mali,
zatvoren skup.
"""
from __future__ import annotations

import re

# Kanonski tipovi. Redoslijed = prioritet kod klasifikacije po nazivu
# (katedrala pobjeđuje crkvu jer je i katedrala "crkva").
KINDS = [
    "katedrala",
    "bazilika",
    "svetiste",
    "samostan",
    "dzamija",
    "sinagoga",
    "pravoslavna-crkva",
    "kapela",
    "poklonac",
    "crkva",
    "ostalo",
]

# Tipovi koji NISU crkva u užem smislu — karta ih po defaultu skriva.
MINOR_KINDS = {"poklonac"}

_NAME_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("katedrala", re.compile(r"\bkatedral|\bstolna\s+crkva|\bprvostolnic", re.I)),
    ("bazilika", re.compile(r"\bbazilik", re.I)),
    ("svetiste", re.compile(r"\bsvetišt|\bsvetist|\bmarijansk\w*\s+svet", re.I)),
    ("samostan", re.compile(r"\bsamostan|\bopatij|\bmanastir|\bfranjevačk\w*\s+samost", re.I)),
    ("dzamija", re.compile(r"\bdžamij|\bdzamij|\bmesdžid|\bislamsk\w*\s+centar", re.I)),
    ("sinagoga", re.compile(r"\bsinagog", re.I)),
    ("poklonac", re.compile(r"\bpoklonac|\bpil\b|\braspelo|\bkalvarij|\bkip\s+sv", re.I)),
    ("kapela", re.compile(r"\bkapel|\bkapelic", re.I)),
    ("crkva", re.compile(r"\bcrkv|\bhram\b", re.I)),
]

_BUILDING_MAP = {
    "cathedral": "katedrala",
    "basilica": "bazilika",
    "chapel": "kapela",
    "mosque": "dzamija",
    "synagogue": "sinagoga",
    "monastery": "samostan",
    "church": "crkva",
    "temple": "crkva",
    "shrine": "poklonac",
    "wayside_shrine": "poklonac",
}

_CHURCH_TYPE_MAP = {
    "cathedral": "katedrala",
    "basilica": "bazilika",
    "chapel": "kapela",
    "shrine": "svetiste",
    "monastery": "samostan",
}

# OSM `denomination` → čitljiv hrvatski naziv + je li pravoslavna.
DENOMINATION_HR = {
    "roman_catholic": "rimokatolička",
    "catholic": "katolička",
    "greek_catholic": "grkokatolička",
    "serbian_orthodox": "srpska pravoslavna",
    "orthodox": "pravoslavna",
    "eastern_orthodox": "pravoslavna",
    "macedonian_orthodox": "makedonska pravoslavna",
    "protestant": "protestantska",
    "evangelical": "evangelička",
    "lutheran": "luteranska",
    "reformed": "reformirana",
    "calvinist": "kalvinistička",
    "baptist": "baptistička",
    "pentecostal": "pentekostna",
    "adventist": "adventistička",
    "jehovahs_witness": "Jehovini svjedoci",
    "sunni": "sunitska",
    "jewish": "židovska",
    "old_catholic": "starokatolička",
}

_ORTHODOX = {"serbian_orthodox", "orthodox", "eastern_orthodox", "macedonian_orthodox",
             "russian_orthodox", "bulgarian_orthodox", "romanian_orthodox"}


def classify(tags: dict | None = None, name: str | None = None) -> str:
    """Vrati kanonski `kind`. `tags` su OSM tagovi (mogu biti prazni)."""
    tags = tags or {}

    ct = (tags.get("church:type") or "").lower()
    if ct in _CHURCH_TYPE_MAP:
        return _CHURCH_TYPE_MAP[ct]

    b = (tags.get("building") or "").lower()
    if b in _BUILDING_MAP:
        # `building=church` je pregenerički da nadjača naziv "Katedrala …";
        # naziv provjeravamo prvi za crkvu/hram, tag za sve ostalo.
        if b not in ("church", "temple"):
            return _BUILDING_MAP[b]

    if tags.get("historic") == "wayside_shrine" or tags.get("amenity") == "monastery":
        return "poklonac" if tags.get("historic") == "wayside_shrine" else "samostan"

    if name:
        for kind, pat in _NAME_PATTERNS:
            if pat.search(name):
                if kind == "crkva":
                    denom = (tags.get("denomination") or "").lower()
                    if denom in _ORTHODOX:
                        return "pravoslavna-crkva"
                return kind

    denom = (tags.get("denomination") or "").lower()
    if denom in _ORTHODOX:
        return "pravoslavna-crkva"

    if b in _BUILDING_MAP:
        return _BUILDING_MAP[b]

    rel = (tags.get("religion") or "").lower()
    if rel == "muslim":
        return "dzamija"
    if rel == "jewish":
        return "sinagoga"
    if rel == "christian":
        return "crkva"

    return "ostalo"


def religion_of(tags: dict | None = None, kind: str | None = None) -> str | None:
    tags = tags or {}
    rel = (tags.get("religion") or "").strip().lower()
    if rel:
        return rel
    if kind == "dzamija":
        return "muslim"
    if kind == "sinagoga":
        return "jewish"
    if kind in {"crkva", "kapela", "katedrala", "bazilika", "svetiste",
                "samostan", "pravoslavna-crkva", "poklonac"}:
        return "christian"
    return None


def denomination_hr(denom: str | None) -> str | None:
    if not denom:
        return None
    return DENOMINATION_HR.get(denom.strip().lower(), denom.strip().lower().replace("_", " "))
