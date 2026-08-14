"""Naziv → slug/normalizirani ključ, s ispravnim rukovanjem hrvatskim đ/Đ.

Prilagođeno iz ../rodjendaonice.domovina.ai/src/normalize.py (izvorno
../klubovi.domovina.ai/src/normalize.py). Razlika je u tome što se ovdje NE
skidaju pravni oblici (d.o.o., obrt) nego crkveni prefiksi — "ŽUPA",
"CRKVA", "KAPELA" — jer oni nose tip, ne identitet, a identitet je titular
("sv. Marko") plus mjesto.
"""
from __future__ import annotations

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Đ/đ se ne dekomponiraju pod NFKD (samostalna slova), mapiramo eksplicitno.
_CROATIAN_MAP = str.maketrans({"đ": "d", "Đ": "D"})

# Tipski prefiksi koje skidamo prije slugifikacije — nose `kind`, ne identitet.
_TYPE_PREFIX_RE = re.compile(
    r"^\s*(rimokatolička\s+|grkokatolička\s+|pravoslavna\s+|srpska\s+pravoslavna\s+)?"
    r"(župa|zupa|crkva|crkve|kapela|katedrala|bazilika|svetište|svetiste|"
    r"samostan|opatija|hram|džamija|dzamija|sinagoga|poklonac|pil)\b\.?\s*",
    re.IGNORECASE,
)

# "sv." varijante → jedinstveni oblik prije usporedbe.
_SAINT_RE = re.compile(
    r"\b(sv\.?|svetog|svetoga|svete|sveti|sveta|svetom|svetih|st\.)\b\.?",
    re.IGNORECASE,
)


def strip_diacritics(s: str) -> str:
    s = s.translate(_CROATIAN_MAP)
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def strip_type_prefix(name: str) -> str:
    """"Crkva sv. Marka" → "sv. Marka"; "ŽUPA SV. ANE, OSIJEK" → "SV. ANE, OSIJEK"."""
    out = _TYPE_PREFIX_RE.sub("", name or "", count=1)
    return out.strip() or (name or "").strip()


def slugify(name: str, city: str | None = None, suffix: str | None = None) -> str:
    """Stabilan URL slug. `suffix` je za garantiranu jedinstvenost (npr. osm id).

    Titulari se ponavljaju stotinama puta ("Crkva sv. Ivana Krstitelja" postoji
    u ~90 mjesta), pa slug BEZ mjesta ne bi bio jedinstven — zato je `city`
    dio ključa, a pozivatelj dodaje `suffix` kad ni to nije dovoljno.
    """
    base = strip_diacritics(strip_type_prefix(name or "")).lower().strip()
    if city:
        city_norm = strip_diacritics(city).lower().strip()
        if city_norm and city_norm not in base:
            base = f"{base}-{city_norm}"
    if suffix:
        base = f"{base}-{strip_diacritics(str(suffix)).lower()}"
    base = _NON_ALNUM.sub("-", base).strip("-")
    return base or "crkva"


def norm_key(name: str, city: str | None = None) -> str:
    """Ključ za fuzzy usporedbu: bez dijakritike, bez tipskog prefiksa,
    "sv."/"svetog"/"svete" svedeno na "sv", samo alfanum + jedan razmak.

    Koristi se u src/match.py za spajanje Registra kulturnih dobara i župa na
    OSM građevine — tamo isti objekt dolazi kao "Crkva sv. Jurja",
    "Župna crkva Svetog Jurja" i "sv. Juraj".
    """
    base = strip_diacritics(strip_type_prefix(name or "")).lower()
    base = _SAINT_RE.sub(" sv ", base)
    base = re.sub(r"[^a-z0-9]+", " ", base).strip()
    if city:
        c = strip_diacritics(city).lower().strip()
        c = re.sub(r"[^a-z0-9]+", " ", c).strip()
        if c:
            base = f"{base} {c}"
    return re.sub(r"\s+", " ", base).strip()


def title_case_hr(s: str) -> str:
    """UPPERCASE registarski nazivi → čitljivo. Čuva "sv.", "BDM", rimske brojeve.

    Državne evidencije sve pišu velikim slovima ("ŽUPA BL. ALOJZIJA STEPINCA")
    pa je ovo potrebno za prikaz.
    """
    keep_upper = {"BDM", "OFM", "OP", "SJ", "OSB", "OCD", "SDB", "HR", "RH"}
    # Rimski broj traži ≥2 znaka: inače bi hrvatski veznik "i" ("Biskupija
    # porečka i pulska") prošao kao rimska jedinica i postao "I".
    roman = re.compile(r"^[IVXLCDM]{2,}\.?$")
    # Veznici i prijedlozi ostaju mali osim na početku.
    lower_words = {"i", "u", "na", "od", "za", "sa", "s", "iz", "te", "ili"}
    out: list[str] = []
    for w in (s or "").split():
        if out and w.lower() in lower_words:
            out.append(w.lower())
        elif w.upper() in keep_upper or roman.match(w.upper()):
            out.append(w.upper())
        elif w.upper() in {"SV.", "SV", "BL.", "BL"}:
            out.append(w.lower() if w.endswith(".") else w.lower() + ".")
        else:
            out.append(w.capitalize())
    return " ".join(out)
