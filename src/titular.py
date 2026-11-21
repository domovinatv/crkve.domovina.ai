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
_BDM = (r"(?:blažen\w*\s+djevic\w*\s+marij\w*|bl\.?\s*djevic\w*\s+marij\w*"
        r"|b\.?\s*d\.?\s*marij\w*|bdm|marijin\w*|gospin\w*)")
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
    # Oba reda riječi: evidencija piše i „USKRSNUĆA ISUSOVA" i „ISUSOVA USKRSNUĆA",
    # OSM „crkva Isusova uskrsnuća" (S3, 2026-11-20).
    (re.compile(r"uskrsnu[ćc]\w*\s+isusov\w*|isusov\w*\s+uskrsnu[ćc]\w*", re.I),
     "Uskrsnuće Isusovo"),
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
    # S3 (2026-11-20): imena iz nizova „X i Y" koja su ostajala u genitivu
    # (audit `titular_genitiv`). Svako je izmjereno u bazi, nijedno nije
    # izvedeno pravilom.
    "ćirila": "Ćiril", "metoda": "Metod", "kirika": "Kirik", "kvirika": "Kvirik",
    "julite": "Julita", "feliksa": "Feliks", "fortunata": "Fortunat",
    "euzebija": "Euzebije", "poliona": "Polion", "mohora": "Mohor",
    "joakima": "Joakim", "prima": "Prim", "felicijana": "Felicijan",
    "izidora": "Izidor", "monike": "Monika", "agneze": "Agneza",
    "margarite": "Margarita", "srđa": "Srđ", "baha": "Bakho",
    "ladislava": "Ladislav", "kozme": "Kozma", "liberana": "Liberan",
    "teodora": "Teodor", "jude": "Juda", "mojsija": "Mojsije",
    "modesta": "Modest", "mihaila": "Mihailo", "gavrila": "Gavrilo",
    # „Mihajla" (registar, Vrhovine Z-6096) = OSM „Mihaila": isti nominativ, da
    # se glave slože (odluka 313).
    "mihajla": "Mihailo", "mihajlo": "Mihailo",
    # Nisu genitivi nego oblici koji se u nazivima zatječu: „Mihovile" je
    # vokativ (OSM „Sv.Mihovile i Sv.Mario"). „Pavle" (srpski nominativ) i
    # „Ante" su nominativi na -e — upisani kao takvi da ih audit ne broji.
    "mihovile": "Mihovil", "pavle": "Pavle", "ante": "Ante",
}

_STOP_AFTER = re.compile(
    r"\s*[,(]|\s+u\s+|\s+na\s+|\s+kod\s+|\s+pri\s+|\s+–\s+|\s+-\s+", re.IGNORECASE
)

# „Sv.Mario", „SV.SV. ĆIRILA" — oznaka sveca slijepljena s idućom riječi.
_GLUED_MARK = re.compile(r"\b(sv|bl)\.(?=\w)", re.IGNORECASE)
# Oznaka sveca UNUTAR niza („Roka i sv. Liberana", „Vida i svetog Jurja") —
# ne ide u titular, niz je „sv. Rok i Liberan".
# „Blažene" ovdje nije oznaka: „i Blažene Djevice Marije" je BDM (vidi parse).
_BDM_AT = re.compile(r"(blažen\w*|bl\.?)\s*djevic\w*\s+marij\w*", re.IGNORECASE)
_INNER_MARK = re.compile(r"^(sv\.?|svet\w*)$", re.IGNORECASE)
_BDM_START = re.compile(_BDM, re.IGNORECASE)
_QUOTES = "\"'„“”«»"
_STOP_WORDS = {"u", "na", "kod", "iz"}

# Zajednički naslov ISPRED niza („svetih Apostola Petra i Pavla", „Arhanđela
# Mihaila i Gavrila", „mučenika Srđa i Baha") odnosi se na sve članove niza i
# pada: glava titulara mora biti prvo IME, inače je „sv apostola" glava i
# pravoslavni hram ne dijeli ključ ni s jednim „sv. Petar i Pavao" (S3).
_SERIES_TITLE = {"apostola", "ap", "arhanđela", "arhandela", "arhangela",
                 "arkanđela", "arkandela", "mučenika", "mucenika"}
# Zajednički epitet IZA drugog imena niza („Petra i Pavla apostola", „AP.",
# „KUZME I DAMJANA MM."). U genitivu množine je isti kao u jednini, a izvori
# ga pišu nedosljedno (s njim, bez njega, iza zareza) — pada, da puni titular
# bude isti iz svih izvora: „sv. Petar i Pavao" (odluka 300).
_GROUP_EPITHET = {"apostola", "ap", "apostoli", "mučenika", "mucenika", "mm",
                  "mučenici", "mucenici"}
# Prezime koje razlikuje DRUGOG sveca istog imena ide u glavu titulara:
# sv. Nikola Tavelić (franjevac, † 1391) nije sv. Nikola biskup. S istom
# glavom su se „ŽUPA SV. NIKOLE B." i obje rijecke crkve bodovale jednako
# (90/90) i župa je ostala bez crkve (S2 nalaz, S3 ispravak).
_HEAD_SURNAMES = {"tavelic"}


def _is_conj(word: str) -> bool:
    """„i"/„I" kao veznik. „I." (redni broj: „Stjepana I. pape") nije veznik."""
    return word in ("i", "I")


def _strip_place(words: list[str], place: str | None) -> list[str]:
    """Skini mjesto s kraja („ŽUPA SV. KUZME I DAMJANA POLAČA", sjedište
    Polača). Evidencija ga ponekad piše bez zareza; glava ostaje uvijek."""
    if not place:
        return words
    pw = _key_of(place).split()
    n = len(pw)
    if n and len(words) > n and [_key_of(w) for w in words[-n:]] == pw:
        # Kao i bez mjesta: naziv se na kraju čisti od točke („NIKOLE B.").
        return [*words[:-n - 1], words[-n - 1].rstrip(".,")]
    return words


def parse(name: str | None, place: str | None = None) -> str | None:
    """Izvuci titular iz naziva. Vraća npr. "sv. Marko" ili "Uznesenje BDM".

    `place` (sjedište pravne osobe) se skida s kraja naziva ako ga evidencija
    nije odvojila zarezom. Matcher ga ne daje — on uspoređuje glave, a mjesto
    nikad nije prva riječ.
    """
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

    core = _GLUED_MARK.sub(r"\1. ", core)
    m = _SAINT_MARK.search(core)
    if not m:
        return None
    # „Blažene Djevice Marije" nije svetac „Djevica": `_SAINT_MARK` bi uzeo
    # „Blažene" kao „sv." i titular bi bio „sv. Djevice Marije" (S3 rebuild:
    # Z-2282 Granešina spojen na Kraljicu mira). BDM bez otajstva je generički
    # marijanski titular (`match.GENERIC_TITULARS`): naziv ne kaže koji zaziv.
    # Samo kad je BAŠ ta oznaka prva — „sv. Antuna i Blažene Djevice Marije"
    # ostaje sv. Antun (odluka 312).
    if _BDM_AT.match(core, m.start()):
        return "Majka Božja"
    rest = core[m.end():].strip(" .,-")
    # Ponovljena oznaka: „SV. SV. ĆIRILA I METODA" (bugarska crkvena općina).
    while (m2 := _SAINT_MARK.match(rest)) and m2.end() and rest[m2.end():].strip(" .,-"):
        rest = rest[m2.end():].strip(" .,-")
    if not rest:
        return None

    words: list[str] = []
    for w in rest.split():
        w = w.strip(_QUOTES)
        if not w:
            continue
        # Stajemo na veznik koji uvodi mjesto. Bez skidanja dijakritike:
        # otok „IŽ" nije prijedlog „iz" („ŽUPA SV. PETRA I PAVLA VELI IŽ").
        if w.lower() in _STOP_WORDS:
            break
        words.append(w)
    words = _strip_place(words, place)
    # „i sv. Y" → „i Y": oznaka unutar niza ne broji se u duljinu niza.
    words = [w for i, w in enumerate(words)
             if not (i and _is_conj(words[i - 1]) and _INNER_MARK.match(w))]

    # Titular je ime + eventualni epitet ("Ivana Krstitelja"): do 4 riječi.
    # Niz („Petra i Pavla", „Jurja mučenika i Srca Marijina") smije biti dulji:
    # do 4 riječi iza prvog veznika.
    conj = next((i for i, w in enumerate(words[:4]) if _is_conj(w)), None)
    words = words[:4] if conj is None else words[:conj + 4]
    if conj is not None and conj >= 2 and _low(words[0]) in _SERIES_TITLE:
        words = words[1:]
    if not words:
        return None

    head = _to_nominative(words[0])
    tail: list[str] = []
    series = conj is not None
    seen_conj = after_conj = False
    names = 1
    for i, w in enumerate(words[1:], start=1):
        lw = _low(w)
        if _is_conj(w):
            tail.append("i")
            seen_conj = after_conj = True
            continue
        if after_conj:
            after_conj = False
            # „ANTUNA PADOVANSKOG I B. D. MARIJE": drugi član niza je BDM.
            # Bez ovoga „B." postane „Biskup", a „Blažene" se izgubi.
            if _BDM_START.match(" ".join(words[i:])):
                tail.append("BDM")
                break
            if lw in _EPITHETS or lw in _SERIES_EPITHETS:  # „djevice i mučenice"
                tail.append(_epithet(w, head, series=True))
            elif _known(w) or w[:1].isupper():  # drugo ime niza
                tail.append(_to_nominative(w))
                names += 1
            else:
                # „sv. Liberana i arheološko nalazište": iza veznika nije
                # ime — niz je gotov, veznik ne pripada titularu.
                tail.pop()
                break
            continue
        if seen_conj and names >= 2 and lw in _GROUP_EPITHET:
            continue
        # Registri pišu sve verzalom ("SV. MARKA EVANĐELISTA") — epitet spusti
        # u normalan oblik i, gdje je poznat, u nominativ, da titular bude
        # čitljiv ("sv. Ivan Krstitelj", ne "sv. Ivan Krstitelja").
        tail.append(_epithet(w, head, series=series))
    while tail and tail[-1] == "i":
        tail.pop()

    label = f"sv. {head}" + (f" {' '.join(tail)}" if tail else "")
    return re.sub(r"\s+", " ", label).strip()


def _low(word: str) -> str:
    return word.lower().strip(".,;:")


def _known(word: str) -> bool:
    key = strip_diacritics(_low(word))
    return any(strip_diacritics(k) == key for k in _KNOWN_NOM)


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
    # S3 (2026-11-20). „TEVELIĆA" je tipfeler evidencije (Repušnica).
    # „B." (= biskupa) se NAMJERNO ne širi u „Biskup" (odluka 302): puni
    # titular nosi bonus +8 u matcheru, pa je u Čakovcu crkva iz drugog
    # naselja iste općine srušila marginu točnoj (izmjereno: +3 spoja, −1).
    "tavelića": "Tavelić", "tevelića": "Tavelić", "tadeja": "Tadej",
    "bogdana": "Bogdan", "mandića": "Mandić",
    # Već nominativ; upisan da ga audit ne proglasi genitivom („-a").
    "carica": "Carica",
}

# Epiteti koji se u nominativ dižu SAMO u nizu „X i Y". Izvan niza ime ispred
# njih ostaje u genitivu („sv. Silvestra pape", „Djevice Marije Kraljice") i
# nominativ samo epiteta dao bi mješavinu („sv. Silvestra Papa").
_SERIES_EPITHETS = {
    "mučenice": "Mučenica", "mucenice": "Mučenica", "mučenika": "Mučenik",
    "pape": "Papa", "kraljice": "Kraljica",
    # Otajstvo kao drugi član niza („sv. Jurja i Srca Marijina").
    "srca": "Srce", "marijina": "Marijino", "marijinog": "Marijino",
    "žalosne": "Žalosna", "gospe": "Gospa",
}


def _epithet(word: str, head: str = "", series: bool = False) -> str:
    raw = word.lower().strip(".,")
    if raw == "b" and _key_of(head) == "leopold":
        return "Bogdan"                       # „SV. LEOPOLDA B. MANDIĆA"
    if series and raw in _SERIES_EPITHETS:
        return _SERIES_EPITHETS[raw]
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

    Iznimka je prezime koje razlikuje drugog sveca istog imena
    (`_HEAD_SURNAMES`: „sv. Nikola Tavelić" → "sv nikola tavelic").
    """
    t = parse(name)
    if not t:
        return None
    if not t.startswith("sv. "):
        return _key_of(t)
    words = t[4:].split()
    head = words[0]
    if len(words) > 1 and _key_of(words[1]) in _HEAD_SURNAMES:
        head = f"{head} {words[1]}"
    return _key_of(f"sv. {head}")


def _key_of(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", strip_diacritics(t).lower()).strip()


# --- Marijanski zaziv (S4, odluka 405) --------------------------------------
# Generički titular „Majka Božja" (odluka 312, `match.GENERIC_TITULARS`) guta
# zaziv: „BDM Pomoćnice" (Knežija, 1929) i „BDM Bezgrešne" (Knežija, 2006) imaju
# isti puni ključ, pa ih `scripts/05` spoji u jednu građevinu, a `scripts/10`
# ne razlikuje „Majke Božje Svetogorske" od gole „Kapele BDM" (Z-834).
# Zaziv NE ulazi u `key()`/`head_key()` ni u prikaz: on samo kaže kad su dva
# marijanska naziva SIGURNO različita (oba imaju zaziv i zazivi se razlikuju).
# Gola „BDM"/„Majka Božja" bez zaziva ostaje spojiva sa svakim zazivom —
# pravilo (b) „generički titular nije slaganje" je odbačeno (−22 spoja).
_ZAZIV_MARK = re.compile(rf"(?:majk\w*\s+božj\w*|gosp[aeio]\w*|{_BDM}|marij\w*)(?=\s|$)",
                         re.IGNORECASE)
# „Gospe od Zdravlja", „Gospe kraj mora", „Gospa pod lipom": zaziv je iduća riječ.
_ZAZIV_PREP = {"od", "kod", "pod", "kraj", "van"}
# Riječ bez prijedloga je zaziv samo ako je pridjev („Lurdske", „Snježna",
# „Bistričke") ili marijanski naslov („Pomoćnice", „Kraljice"). Bez toga bi
# mjesto iza naziva (evidencija, „… GOSPE OD RUŽARIJA BORAJA") ili „i župni
# dvor" (Z-2282) postali zaziv.
_ZAZIV_WORD = re.compile(r"\w{3,}(?:sk|ck|n)[ae]$|\w{3,}ic[ae]$|\w{3,}at[ae]$")
# Zaziv je gotov na vezniku ili prijedlogu („Fatimske i svete Magdalene",
# „Svetogorske s pripadajućim građevinama"); „svete/presvete/svih" ne nose
# razliku („od Presvete Krunice" = „od Krunice").
_ZAZIV_STOP = {"i", "ili", "s", "sa", "/", "-", "–", "u", "na", "kod", "iz"}
_ZAZIV_FILL = {"svete", "presvete", "sv.", "svih", "čudotvorne"}
# Ista pobožnost, različit zapis — izmjereno u nazivima iz svih izvora.
_ZAZIV_SYN = {
    "snjeg": "snjez", "snig": "snjez",                      # „od Snijega/Sniga" = Snježna
    "rozarij": "ruzarij", "ruzar": "ruzarij", "krunic": "ruzarij", "ruzaric": "ruzarij",
    "karme": "karmel", "karmin": "karmel",
    "lauretan": "loret", "delorit": "loret",              # „Delorita" = de Loreto (Kuna)
    "sedam": "zalos", "zalost": "zalos",                    # „od Sedam Žalosti" = Žalosna
    # „od Milosti" i „od Milosrđa" se miješaju: RST-1286 „Gospe od Milosrđa"
    # (Suđurađ) je OSM „crkva Gospe od Milosti", jedina marijanska u naselju.
    "milosrd": "milost",
}


def _zaziv_stem(word: str) -> str:
    s = strip_diacritics(word).lower().strip(".,;:")
    s = s.replace("ije", "je")                     # sniježna = snježna
    s = re.sub(r"[aeiou]+$", "", s)
    s = re.sub(r"(sk|ck|n)$", "", s)               # lurdsk → lurd, loretsk → loret
    return _ZAZIV_SYN.get(s, s)


def zaziv(name: str | None) -> frozenset[str] | None:
    """Ključ marijanskog zaziva za naziv s generičkim titularom „Majka Božja".

    Skup osnova riječi zaziva (do 3, do prvog veznika): „crkva BDM Pomoćnice"
    → {"pomocnic"}, „Majke Božje Sljemenske Kraljice Hrvata" → {"sljemen",
    "kraljic", "hrvat"}, „Gospa od Snijega" i „Majka Božja Snježna" → {"snjez"}.
    Gola „Kapela Blažene Djevice Marije" i svaki drugi titular → None.
    """
    if not name or parse(name) != "Majka Božja":
        return None
    core = strip_type_prefix(name.strip())
    core = core.translate({ord(q): " " for q in _QUOTES})
    core = _STOP_AFTER.split(core, maxsplit=1)[0].strip()
    marks = list(_ZAZIV_MARK.finditer(core))
    if not marks:
        return None
    words = core[marks[-1].end():].split()
    if not words:
        return None
    if words[0].lower() in _ZAZIV_PREP:
        words = words[1:]
    elif not _ZAZIV_WORD.search(strip_diacritics(words[0]).lower().strip(".,;:")):
        return None
    out: set[str] = set()
    for w in words:
        if w.lower() in _ZAZIV_STOP or len(out) == 3:
            break
        if w.lower() in _ZAZIV_FILL:
            continue
        out.add(_zaziv_stem(w))
    return frozenset(out) or None


def zaziv_sukob(a: str | None, b: str | None) -> bool:
    """Proturječe li zazivi dvaju naziva? Samo kad OBA imaju zaziv i nemaju
    nijednu zajedničku riječ („Kraljice Hrvata" i „Sljemenske Kraljice Hrvata"
    nisu sukob; „Pomoćnice" i „Bezgrešne" jesu)."""
    return zazivi_u_sukobu(zaziv(a), zaziv(b))


def zazivi_u_sukobu(za: frozenset[str] | None, zb: frozenset[str] | None) -> bool:
    return bool(za and zb and not (za & zb))
