"""Konfesija i religija: dozvoljeni skup (odluka 101), normalizacija, pravilo.

Jedno mjesto za tri potrošača koji se ne smiju razići:

  - ingest (`scripts/01`, `02`, `03`, `05`) piše samo vrijednosti iz
    dozvoljenog skupa — `normalize_denomination`, `normalize_religion`;
  - matcher (`src/match.py: compatible`) ne spaja nekatoličku građevinu na
    katoličku pravnu osobu i obrnuto — `is_nekatolicka`, `is_katolicka`;
  - audit (`src/audit.py`) mjeri isto to — iste konstante, ista funkcija.

Ako audit i matcher imaju svaki svoju definiciju „nekatoličke građevine",
metrika `nekatolicke_na_katolickim` ne pada na 0 ni kad pravilo radi.
"""
from __future__ import annotations

import re

# Pravna osoba je „katolička" ako joj je konfesija jedna od ovih. Evidencija
# Katoličke Crkve upisuje sve (i Križevačku eparhiju) kao `roman_catholic`;
# `greek_catholic` je tu da pravilo vrijedi i kad se eparhija razdvoji.
KATOLICKE = frozenset({"roman_catholic", "greek_catholic"})

# Dozvoljene vrijednosti `denomination` — OSM wiki konvencija (Key:denomination),
# suženo na ono što u Hrvatskoj postoji. Isti skup vrijedi za `churches`,
# `parishes` i `dioceses`, jer matcher uspoređuje konfesiju građevine s
# konfesijom pravne osobe pa obje strane moraju govoriti istim rječnikom.
#   - `catholic` NIJE dozvoljen: OSM ga smatra dvosmislenim, ovdje je uvijek
#     rimokatolička (1022 zapisa, sve u katoličkim krajevima; nijedan na
#     Križevačkoj eparhiji, vidi `_SINONIMI`).
#   - `orthodox` JEST dozvoljen: OSM-ova generička vrijednost kad konkretna
#     crkva nije poznata. U `serbian_orthodox` se smije dići samo dokazivo.
#   - adventisti su `seventh_day_adventist` (OSM wiki), ne `adventist`:
#     Kršćanska adventistička crkva u RH je crkva adventista sedmog dana.
#   - Religija nije konfesija: `jewish`, `hindu`, `buddhist` kao `denomination`
#     su naš propust iz ingesta zajednica, ne vrijednost.
DOZVOLJENE_DENOMINACIJE = frozenset({
    # katoličke
    "roman_catholic", "greek_catholic", "old_catholic",
    # pravoslavne
    "orthodox", "serbian_orthodox", "macedonian_orthodox", "bulgarian_orthodox",
    "russian_orthodox", "greek_orthodox", "romanian_orthodox",
    # protestantske i ostale kršćanske
    "protestant", "lutheran", "reformed", "evangelical", "baptist", "pentecostal",
    "seventh_day_adventist", "methodist", "anglican", "waldensian",
    "jehovahs_witness", "mormon", "new_apostolic",
    # islam
    "sunni", "shia",
    # budizam
    "zen",
})

DOZVOLJENE_RELIGIJE = frozenset({
    "christian", "muslim", "jewish", "buddhist", "hindu", "pagan",
})

# Konfesije koje NISU katoličke — eksplicitno nabrojano, ne „sve osim
# katoličkih": nepoznata vrijednost (`krščanstvo1`, `sv. florijan`, NULL)
# nije dokaz da građevina nije katolička. Uz dozvoljene su i poznati
# nenormalizirani sinonimi (`adventist`, `hungarian_reformed`…): baza
# izgrađena prije normalizacije ih još ima, a nedvosmisleno su nekatolički.
NEKATOLICKE_DENOMINACIJE = frozenset({
    "old_catholic",
    "orthodox", "serbian_orthodox", "macedonian_orthodox", "bulgarian_orthodox",
    "russian_orthodox", "greek_orthodox", "romanian_orthodox", "eastern_orthodox",
    "protestant", "lutheran", "reformed", "hungarian_reformed", "united_reformed",
    "calvinist", "evangelical", "baptist", "pentecostal", "neo-pentecostal",
    "philadelphian", "seventh_day_adventist", "adventist", "methodist", "anglican",
    "episcopal", "waldensian", "church_of_christ", "jehovahs_witness", "mormon",
    "new_apostolic",
    "sunni", "shia", "zen", "hare_krishna",
})
NEKRSCANSKE_RELIGIJE = frozenset({"muslim", "jewish", "buddhist", "hindu", "pagan"})
NEKATOLICKI_KINDOVI = frozenset({"pravoslavna-crkva", "dzamija", "sinagoga"})

_ORTHODOX = frozenset(d for d in DOZVOLJENE_DENOMINACIJE if d.endswith("orthodox"))
_NEKRSCANSKE_DENOMINACIJE = frozenset({"sunni", "shia", "zen"})

# Izvorna vrijednost → dozvoljena. Svaka je viđena u stvarnim podacima
# (OSM, evidencija vjerskih zajednica); ključ je već `strip().lower()`.
_SINONIMI: dict[str, str] = {
    # Izmjereno 2026-11-20: od 1022 `catholic` nijedan nije na pravnoj osobi
    # Križevačke eparhije, a jedini u grkokatoličkom kraju (Kostanjevac,
    # Žumberak) spojen je na rimokatoličku župu sv. Marije Magdalene.
    "catholic": "roman_catholic",
    "katolička": "roman_catholic",
    "katolicka": "roman_catholic",
    "rimokatolička": "roman_catholic",
    "roman_catholicadded": "roman_catholic",  # zalijepljen komentar mappera (Cres)
    "benedictine_sisters": "roman_catholic",  # benediktinke, Split — red, ne konfesija
    "eastern_orthodox": "orthodox",
    "adventist": "seventh_day_adventist",
    "hungarian_reformed": "reformed",
    "united_reformed": "reformed",
    "calvinist": "reformed",
    "neo-pentecostal": "pentecostal",
    "philadelphian": "pentecostal",   # Filadelfijska crkva = pentekostni pokret
    # Episkopalna/Kristova crkva: nekatolička je sigurno, uža konfesija nije
    # (episkopalnih ima i anglikanskih i metodističkih) — generička vrijednost
    # čuva ono što se zna i ne izmišlja ostatak.
    "episcopal": "protestant",
    "church_of_christ": "protestant",
}

_RELIGIJE_SINONIMI: dict[str, str] = {
    "krščanstvo": "christian",
    "kršćanstvo": "christian",
    "christianity": "christian",
    "islam": "muslim",
    "judaism": "jewish",
}


def _parts(value: str | None) -> list[str]:
    """OSM višestruka vrijednost `serbian_orthodox;orthodox` → dijelovi."""
    if not value:
        return []
    return [p.strip().lower() for p in str(value).split(";") if p.strip()]


def _one_denomination(v: str) -> str | None:
    v = _SINONIMI.get(v, v)
    return v if v in DOZVOLJENE_DENOMINACIJE else None


def normalize_denomination(value: str | None, religion: str | None = None) -> str | None:
    """Izvorna `denomination` → vrijednost iz `DOZVOLJENE_DENOMINACIJE` ili None.

    - sinonimi i jednoznačno smeće se popravljaju (`_SINONIMI`);
    - religija upisana kao konfesija (`jewish`, `hindu`…) → None;
    - nepoznata vrijednost (`sv. florijan`, `old_paneuropean`) → None —
      prazno je pošteno, izmišljena konfesija nije;
    - višestruka vrijednost: ako se svi dijelovi svedu na isto, to; ako je
      jedan generički `orthodox` a drugi konkretna pravoslavna crkva, ona
      konkretna (uža tvrdnja koja ne proturječi široj); inače None;
    - `religion` (već normaliziran ili ne) služi kao provjera proturječja:
      kršćanska konfesija uz nekršćansku religiju i obrnuto → None.
    """
    vals = {_one_denomination(p) for p in _parts(value)} - {None}
    if not vals:
        return None
    if len(vals) > 1:
        specific = vals - {"orthodox"}
        if "orthodox" in vals and len(specific) == 1 and next(iter(specific)) in _ORTHODOX:
            vals = specific
        else:
            return None
    denom = next(iter(vals))

    rel = normalize_religion(religion)
    if rel is not None:
        krscanska = denom not in _NEKRSCANSKE_DENOMINACIJE
        if krscanska != (rel == "christian"):
            return None
    return denom


def normalize_religion(value: str | None) -> str | None:
    """Izvorna `religion` → vrijednost iz `DOZVOLJENE_RELIGIJE` ili None.

    `krščanstvo1`/`krščanstvo2` (OSM, Lasinja, Razdrto Tuheljsko) su
    jednoznačno kršćanstvo s pripisanom znamenkom. `bogomilism` nije u
    dozvoljenom skupu i ne svodi se ni na što → None.
    """
    v = (value or "").strip().lower()
    if not v:
        return None
    v = _RELIGIJE_SINONIMI.get(v.rstrip("0123456789"), v)
    return v if v in DOZVOLJENE_RELIGIJE else None


def is_nekatolicka(kind: str | None, religion: str | None, denom: str | None) -> bool:
    """Je li građevina (ili pravna osoba) SIGURNO nekatolička.

    Po tipu (`pravoslavna-crkva`/`dzamija`/`sinagoga`), po nekršćanskoj
    religiji ILI po nekatoličkoj konfesiji. Nepoznato nije dokaz.
    """
    if kind in NEKATOLICKI_KINDOVI:
        return True
    if (religion or "").strip().lower() in NEKRSCANSKE_RELIGIJE:
        return True
    return any(p in NEKATOLICKE_DENOMINACIJE for p in _parts(denom))


def is_katolicka(denom: str | None) -> bool:
    """Je li konfesija katolička (rimo- ili grkokatolička).

    Gleda i sirovi `catholic`, da pravilo radi i na bazi izgrađenoj prije
    normalizacije. Starokatolici NISU katolici u ovom smislu (nisu u
    zajedništvu s Rimom) i stoje u `NEKATOLICKE_DENOMINACIJE`.
    """
    return any(_SINONIMI.get(p, p) in KATOLICKE for p in _parts(denom))


# ---------------------------------------------------------------------------
# Evidencija vjerskih zajednica (scripts/03): naziv zajednice → konfesija
# ---------------------------------------------------------------------------

# Naziv zajednice → (religion, denomination). Ono što se ne prepozna dobiva
# religion=NULL umjesto pogrešne pretpostavke. Prvo pravilo koje pogodi
# pobjeđuje, pa uže ide prije šireg: „Reformni pokret ADVENTISTA" nije
# reformirana crkva, „Evangelička METODISTIČKA" nije evangelička, a
# „Katolička Stara Crkva" (starokatolici) i Scijentološka crkva nisu
# protestanti iako im naziv sadrži „CRKV". Vrijednosti su iz dozvoljenog
# skupa (odluka 101); religija nikad nije i konfesija (`jewish` → NULL).
_DENOM_RULES: list[tuple[re.Pattern, tuple[str | None, str | None]]] = [
    (re.compile(r"SRPSKA\s+PRAVOSLAVNA", re.I), ("christian", "serbian_orthodox")),
    (re.compile(r"MAKEDONSKA\s+PRAVOSLAVNA", re.I), ("christian", "macedonian_orthodox")),
    (re.compile(r"BUGARSKA\s+PRAVOSLAVNA", re.I), ("christian", "bulgarian_orthodox")),
    (re.compile(r"PRAVOSLAVN", re.I), ("christian", "orthodox")),
    (re.compile(r"ISLAMSK|MUSLIMANSK", re.I), ("muslim", "sunni")),
    (re.compile(r"ŽIDOVSK|JEVREJSK|IZRAELITSK", re.I), ("jewish", None)),
    (re.compile(r"ADVENTIST", re.I), ("christian", "seventh_day_adventist")),
    (re.compile(r"METODIST", re.I), ("christian", "methodist")),
    (re.compile(r"VALDE", re.I), ("christian", "waldensian")),
    (re.compile(r"EVANGELIČK|LUTERANSK", re.I), ("christian", "evangelical")),
    (re.compile(r"REFORM|KALVIN", re.I), ("christian", "reformed")),
    (re.compile(r"BAPTIST", re.I), ("christian", "baptist")),
    (re.compile(r"PENTEKOST|DUHOVN\w*\s+CRKV", re.I), ("christian", "pentecostal")),
    (re.compile(r"JEHOVIN", re.I), ("christian", "jehovahs_witness")),
    (re.compile(r"GRKOKATOLIČK|KRIŽEVAČK", re.I), ("christian", "greek_catholic")),
    (re.compile(r"STAROKATOLIČK|KATOLIČK\w*\s+STAR", re.I), ("christian", "old_catholic")),
    (re.compile(r"NOVOAPOSTOLSK", re.I), ("christian", "new_apostolic")),
    (re.compile(r"SVETACA\s+POSLJEDNJIH\s+DANA", re.I), ("christian", "mormon")),
    (re.compile(r"SCIJENTOLO", re.I), (None, None)),
    (re.compile(r"KRIST|CRKV|EVANĐEO|EVANDEO", re.I), ("christian", "protestant")),
    (re.compile(r"BUDIST", re.I), ("buddhist", None)),
    (re.compile(r"HINDU|VAIŠNAV|VAISNAV|KRIŠN", re.I), ("hindu", None)),
]


def community_denomination(name: str) -> tuple[str | None, str | None] | None:
    """(religion, denomination) ili None kad nijedno pravilo ne pogodi.

    None ≠ (None, None): Scijentološka crkva je PREPOZNATA kao „ni jedno ni
    drugo" i ne smije pasti na pravilo iz naziva organizacijskog oblika.
    """
    for pat, (rel, den) in _DENOM_RULES:
        if pat.search(name or ""):
            return normalize_religion(rel), normalize_denomination(den, rel)
    return None
