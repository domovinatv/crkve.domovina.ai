"""Parsanje titulara (zaštitnika) iz naziva crkve ili župe.

Titular je pravi identitet sakralnog objekta — "Crkva sv. Marka",
"ŽUPA UZNESENJA BLAŽENE DJEVICE MARIJE, ZAGREB" i "Sv. Marko Evanđelist"
opisuju odnos prema istom svecu/otajstvu. Ovo je i ključ za spajanje
državne evidencije župa (samo naziv + sjedište) s OSM građevinama.

Vraća se normalizirani oblik u NOMINATIVU gdje je moguće ("sv. Marko"), jer
registri koriste genitiv ("ŽUPA SV. MARKA"), a OSM nominativ i genitiv
izmiješano.
"""
from __future__ import annotations

import re

from .normalize import strip_diacritics, strip_type_prefix

# "Blažena Djevica Marija" u svim oblicima u kojima se pojavljuje po izvorima.
# Državna evidencija skraćuje agresivno ("ŽUPA UZNESENJA B.D. MARIJE"), OSM
# piše puno, a Registar kulturnih dobara koristi pridjevski oblik ("Uznesenja
# Marijina"). Bez ove alternacije 229 od 1563 župa ostane bez titulara.
_BDM = r"(?:blažen\w*\s+djevic\w*\s+marij\w*|b\.?\s*d\.?\s*marij\w*|bdm|marijin\w*|gospin\w*)"
# Kratice "presv." / "bezgr." iz registra.
_PRESV = r"(?:presv\.?|presvet\w*)"
_BEZGR = r"(?:bezgr\.?|bezgrešn\w*|bezgresn\w*)"

# Otajstva/blagdani koji nisu "sv. X" — prepoznaju se kao cjelina.
# Redoslijed je prioritet: specifično prije generičkog ("Uznesenje BDM" mora
# pobijediti prije nego ga catch-all "Majka Božja" proguta).
_MYSTERIES = [
    (re.compile(rf"uznesenj\w*\s+{_BDM}|{_BDM}\s+uznesenj\w*", re.I), "Uznesenje BDM"),
    # "GOSPE", ne samo "GOSPOJA" — evidencija piše "ŽUPA VELIKE GOSPE, SINJ".
    (re.compile(r"velik\w*\s+gosp[aoe]\w*", re.I), "Velika Gospa"),
    (re.compile(rf"pohod\w*\s+{_BDM}|pohođenj\w*\s*{_BDM}?|pohodenj\w*\s*{_BDM}?", re.I),
     "Pohod BDM"),
    (re.compile(rf"rođenj\w*\s+{_BDM}|rodenj\w*\s+{_BDM}", re.I), "Rođenje BDM"),
    (re.compile(rf"{_BEZGR}\s+začeć\w*|{_BEZGR}\s+zaceć\w*", re.I), "Bezgrešno začeće BDM"),
    (re.compile(rf"{_BEZGR}\s+srca?\s+{_BDM}", re.I), "Bezgrešno Srce Marijino"),
    (re.compile(r"navještenj\w*|navjestenj\w*|blagovijest", re.I), "Navještenje Gospodnje"),
    (re.compile(rf"(gospe|gospa|{_BDM})\s+karmelsk\w*|karmelsk\w*\s+gospe", re.I),
     "Gospa Karmelska"),
    (re.compile(rf"{_PRESV}\s+trojstv\w*", re.I), "Presveto Trojstvo"),
    (re.compile(rf"{_PRESV}\s+srca?\s+isusov\w*|srca?\s+isusov\w*", re.I),
     "Presveto Srce Isusovo"),
    (re.compile(rf"preslavn\w*\s+imen\w*\s+{_BDM}|imen\w*\s+{_BDM}", re.I), "Ime Marijino"),
    (re.compile(rf"žalosn\w*\s+{_BDM}|{_BDM}\s+žalosn\w*", re.I), "Žalosna Gospa"),
    (re.compile(r"majk\w*\s+božj\w*|gospa\s+od|gospe\s+od|gospa\s+|gospe\s+"
                r"|marij\w*\s+pomoćnic\w*", re.I), "Majka Božja"),
    (re.compile(r"tijel\w*\s+i\s+krvi\s+kristov\w*|tijelov\w*", re.I), "Tijelovo"),
    # "sv." mora biti u uzorku uz "svetog/svetoga": izvori pišu i "Crkva sv.
    # Križa" i "ŽUPA UZVIŠENJA SVETOG KRIŽA" — bez toga bi prvi pao u granu
    # svetaca ("sv. Križ") a drugi u otajstva, i ista crkva ne bi imala isti
    # ključ ni šansu da se spoji.
    (re.compile(r"(uzvišenj\w*\s+)?(sv\.?|svet\w*)\s+križ\w*", re.I), "Sveti Križ"),
    (re.compile(r"duh\w*\s+svet\w*|(sv\.?|svet\w*)\s+duh\w*", re.I), "Duh Sveti"),
    (re.compile(r"krist\w*\s+kralj\w*", re.I), "Krist Kralj"),
    (re.compile(r"uskrsnuć\w*\s+isusov\w*|uskrsnuc\w*\s+isusov\w*", re.I), "Uskrsnuće Isusovo"),
    (re.compile(r"svih\s+svetih", re.I), "Svi Sveti"),
    (re.compile(r"pokoj?\w*\s+duš\w*|dušn\w*\s+dan", re.I), "Duše u čistilištu"),
]

# "sv." u svim padežima + eventualni "blaženi".
_SAINT_MARK = re.compile(
    r"\b(sv\.|sv\b|svet[iaoe]?[gm]?a?\b|svetih\b|bl\.|bl\b|blažen[iaoe]?[gm]?a?\b)\.?\s*",
    re.IGNORECASE,
)

# Genitiv → nominativ. Namjerno NEMA generičkih pravila (npr. "-a" → "") jer
# hrvatska svetačka imena imaju previše iznimaka (Marka→Marko, ali Petra→Petar,
# Nikole→Nikola) i generičko pravilo izmišlja nepostojeće oblike. Zato tablica
# poznatih imena; nepoznato ime ostaje kako jest, samo s velikim početnim slovom.
_KNOWN_NOM = {
    "marka": "Marko", "ivana": "Ivan", "petra": "Petar", "pavla": "Pavao",
    "jurja": "Juraj", "mihovila": "Mihovil", "mihaela": "Mihael",
    "nikole": "Nikola", "antuna": "Antun", "josipa": "Josip",
    "franje": "Franjo", "roka": "Rok", "vida": "Vid", "duje": "Duje",
    "dujma": "Dujam", "blaža": "Blaž", "martina": "Martin", "jakova": "Jakov",
    "filipa": "Filip", "kuzme": "Kuzma", "damjana": "Damjan",
    "stjepana": "Stjepan", "lovre": "Lovro", "lovrenca": "Lovrenac",
    "andrije": "Andrija", "barbare": "Barbara", "katarine": "Katarina",
    "ane": "Ana", "marije": "Marija", "magdalene": "Magdalena",
    "lucije": "Lucija", "agate": "Agata", "klare": "Klara", "cecilije": "Cecilija",
    "elizabete": "Elizabeta", "terezije": "Terezija", "helene": "Helena",
    "margarete": "Margareta", "doroteje": "Doroteja", "jelene": "Jelena",
    "leopolda": "Leopold", "florijana": "Florijan", "fabijana": "Fabijan",
    "sebastijana": "Sebastijan", "vinka": "Vinko", "dominika": "Dominik",
    "benedikta": "Benedikt", "bartola": "Bartol", "šimuna": "Šimun",
    "tome": "Toma", "matije": "Matija", "mateja": "Matej", "luke": "Luka",
    "grgura": "Grgur", "jeronima": "Jeronim", "ambrozija": "Ambrozije",
    "augustina": "Augustin", "alojzija": "Alojzije", "ignacija": "Ignacije",
    "križa": "Križ", "duha": "Duh", "obitelji": "Obitelj",
}

_STOP_AFTER = re.compile(
    r"\s*[,(]|\s+u\s+|\s+na\s+|\s+kod\s+|\s+pri\s+|\s+–\s+|\s+-\s+", re.IGNORECASE
)


def parse(name: str | None) -> str | None:
    """Izvuci titular iz naziva. Vraća npr. "sv. Marko" ili "Uznesenje BDM"."""
    if not name:
        return None
    core = strip_type_prefix(name.strip())
    # Odsijeci mjesto iza zareza: "SV. ANE, OSIJEK" → "SV. ANE"
    core = _STOP_AFTER.split(core, maxsplit=1)[0].strip()
    if not core:
        return None

    for pat, label in _MYSTERIES:
        if pat.search(core):
            return label

    m = _SAINT_MARK.search(core)
    if not m:
        return None
    rest = core[m.end():].strip(" .,-")
    if not rest:
        return None

    words = rest.split()
    # Titular je ime + eventualni epitet ("Ivana Krstitelja", "Petra i Pavla").
    # Uzimamo do 4 riječi, ali stajemo na veznik koji uvodi mjesto.
    keep: list[str] = []
    for w in words[:4]:
        if strip_diacritics(w).lower() in {"u", "na", "kod", "iz"}:
            break
        keep.append(w)
    if not keep:
        return None

    head = _to_nominative(keep[0])
    # Registri pišu sve verzalom ("SV. MARKA EVANĐELISTA") — epitet spusti u
    # normalan oblik i, gdje je poznat, u nominativ, da titular bude čitljiv
    # ("sv. Ivan Krstitelj", ne "sv. Ivan Krstitelja").
    tail = " ".join(_epithet(w) for w in keep[1:]).strip()
    label = f"sv. {head}" + (f" {tail}" if tail else "")
    return re.sub(r"\s+", " ", label).strip()


# Epiteti uz svetačko ime, u genitivu → nominativ. Ne utječu na matching
# (head_key ih ignorira), samo na čitljivost prikaza.
_EPITHETS = {
    "krstitelja": "Krstitelj", "evanđelista": "Evanđelist",
    "evanđeliste": "Evanđelist", "evandelista": "Evanđelist",
    "apostola": "Apostol", "biskupa": "Biskup", "mučenika": "Mučenik",
    "mucenika": "Mučenik", "prvomučenika": "Prvomučenik",
    "opata": "Opat", "kralja": "Kralj", "arkanđela": "Arkanđel",
    "arkandela": "Arkanđel", "djevice": "Djevica", "udovice": "Udovica",
    "pustinjaka": "Pustinjak", "ispovjedatelja": "Ispovjedatelj",
    "padovanskog": "Padovanski", "asiškog": "Asiški", "asiskog": "Asiški",
    "sijenske": "Sijenska", "aleksandrijske": "Aleksandrijska",
    "labudske": "Labudska", "bosanske": "Bosanska",
}


def _epithet(word: str) -> str:
    raw = word.lower().strip(".,")
    if raw in _EPITHETS:
        return _EPITHETS[raw]
    return word.capitalize() if word.isupper() else word


def _to_nominative(word: str) -> str:
    key = strip_diacritics(word).lower().strip(".,")
    raw_key = word.lower().strip(".,")
    if raw_key in _KNOWN_NOM:
        return _KNOWN_NOM[raw_key]
    for k, v in _KNOWN_NOM.items():
        if strip_diacritics(k) == key:
            return v
    return word.capitalize()


def key(name: str | None) -> str | None:
    """Usporedivi ključ punog titulara (bez dijakritike, mala slova)."""
    t = parse(name)
    if not t:
        return None
    return _key_of(t)


def head_key(name: str | None) -> str | None:
    """Ključ SAMO svečeva imena, bez epiteta — "sv. Ante Padovanskog" → "sv ante".

    Epitet je najnestabilniji dio titulara: isti objekt je u OSM-u "Crkva sv.
    Ante", u Registru kulturnih dobara "Crkva sv. Ante Padovanskog", a u
    evidenciji "ŽUPA SV. ANTUNA PADOVANSKOG". Tvrdi filtar u src/match.py zato
    uspoređuje glave (koje se moraju poklapati), a puni titular služi samo kao
    bonus na score. Otajstva ("Uznesenje BDM") nemaju glavu/epitet pa se vraćaju
    cijela.
    """
    t = parse(name)
    if not t:
        return None
    if not t.startswith("sv. "):
        return _key_of(t)
    head = t[4:].split(" ", 1)[0]
    return _key_of(f"sv. {head}")


def _key_of(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", strip_diacritics(t).lower()).strip()
