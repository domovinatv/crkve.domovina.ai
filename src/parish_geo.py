"""Razriješi sjedište župe kad je naziv naselja višeznačan.

**Zašto ovo postoji.** Državna evidencija piše sjedište kao „Mjesto, Ulica br"
— bez županije. U Hrvatskoj postoje dva Kostanjevca, tri Zagorja, dva Vrha,
dvije Vrane. `geo_hr.settlement_centroid()` zato višeznačno ime odbija i vraća
`None`; župa ostane bez koordinata **i bez `county`**. Onda `scripts/13`
(Places) ima čuvara „rezultat mora pasti u istu županiju", ali je `county`
`NULL` pa čuvar tiho ne radi ništa i Google slobodno bira krivi homonim.

Posljedica nije bila kozmetička: župa Bezgrešnog začeća BDM Barbat je na
**Pagu** (Zubovići), a sjela je na Barbat na **Rabu**, pa je derivacija u
`scripts/20` obojala dio Raba u Zadarsku nadbiskupiju iako je cijeli Rab
krčki. Sloj je bio kriv jer mu je ulaz bio kriv.

**Razrješenje.** Biskupija je podatak koji evidencija IMA, a geokoder ga ne
koristi. Iz župa koje su smještene same od sebe (točka leži u naselju koje
piše u evidenciji) izvede se biskupija → skup županija; tim se skupom onda
filtriraju kandidati za višeznačne. „Vrh" + Biskupija Krk daje jedan kandidat
(Krk), jer krčka biskupija nema nijednu župu u Istarskoj.

Evidencija uz to zna skratiti službeni naziv naselja („Kraj" za „Dicmo Kraj"),
pa se kandidati traže i po sufiksu.

Ono što se time ne da razriješiti — jer evidencija ne griješi u nazivu nego u
samom naselju — stoji u `OVERRIDES`, svaki s izvorom.
"""
from __future__ import annotations

import logging
import math
import unicodedata
from functools import lru_cache
from typing import NamedTuple

from src import geo_hr

logger = logging.getLogger(__name__)

# Iznad ove udaljenosti crkva ne može biti filijala te župe. Najveće stvarne
# hrvatske župe (Senj, Gračac) imaju crkve do ~15 km od sjedišta; 25 km je
# udoban strop koji ne dira nijednu stvarnu, a reže homonime (Lupoglav u
# Istri na zagrebačkoj župi je bio 180 km).
MAX_FILIJALA_KM = 25.0

# Župe koje ne griješe u nazivu naselja nego je naziv u evidenciji naprosto
# krivi (ili nedovoljan), pa ih algoritam ne može razriješiti.
# registry_id → (naselje, JLS, izvor tvrdnje)
OVERRIDES: dict[str, tuple[str, str, str]] = {
    # Evidencija normalizirala „Barbat" u „Barbat Na Rabu"; župa je na Pagu.
    "701708": ("Zubovići", "Novalja",
               "Adresar Zadarske nadbiskupije: Barbat (Bezgrešno začeće BDM), "
               "53296 Zubovići, upravlja don Mladen Protić iz Kolana"),
    # Evidencija skratila „Dicmo Kraj" u „Kraj"; postoje i Kraj na Pašmanu i
    # Kraj u Mošćeničkoj Dragi, oba u drugim biskupijama.
    "700502": ("Dicmo Kraj", "Dicmo",
               "smn.hr/dicmo-donje: Župa sv. Jakova ap. – Dicmo Donje, "
               "Osoje 89, 21232 Dicmo"),
    # Evidencija normalizirala priobalnu Krasicu (Bakar) u istarski
    # dvojezični homonim „Krasica - Crassiza" (Buje).
    "702103": ("Krasica", "Bakar",
               "Riječka nadbiskupija; adresa u evidenciji je Krasica 126, "
               "a dvojezični naziv pripada bujskoj Krasici"),
    # Ovima biskupija sreže kandidate na dva, pa presuđuje adresa/izvor.
    "701094": ("Sveti Vid-Miholjice", "Malinska-Dubašnica",
               "na Krku su dva Sveta Vida; župna crkva sv. Mihovila je u "
               "Miholjicama (dekanat Omišalj), u Dobrinjskom je sv. Vid"),
    "702464": ("Zagorje", "Ogulin",
               "adresa u evidenciji je Gornje Zagorje 10 — zaselak "
               "ogulinskog, ne krnjačkog Zagorja"),
    "702384": ("Sveti Martin", "Sveta Nedelja",
               "Porečka i pulska biskupija: župa sv. Martina biskupa, "
               "Sv. Martin 23, 52231 Sveta Nedelja (labinski dekanat)"),
    # Ove tri je do praga 1 rješavao izvod županija. S pragom 1 svaka od njih
    # je JEDINA župa svoje biskupije u županiji u koju je krivo sjela, pa si
    # sama otvara tu županiju i time se štiti od korekcije. Zato eksplicitno.
    "702189": ("Novigrad - Cittanova", "Novigrad - Cittanova",
               "adresa u evidenciji je Park Novigradske biskupije 5, a "
               "sv. Pelagije je titular novigradske konkatedrale u Istri; "
               "zadarski Novigrad je župa sv. Katarine (Zadarska nadbiskupija)"),
    "701029": ("Vrana", "Cres",
               "Wikipedija, Župe Krčke biskupije: Vrana je u creskom "
               "dekanatu; Vrana kod Pakoštana je Zadarska nadbiskupija"),
    "702532": ("Sesvete", "Pleternica",
               "sam naziv u evidenciji glasi ŽUPA SVIH SVETIH, POŽEŠKE "
               "SESVETE — Požeška biskupija, a ne zagrebačke Sesvete"),
    # Ove je Places spustio unutar ISTE biskupije i ISTE županije, pa ih izvod
    # županija ne može vidjeti — greška je 9–15 km, ne 200. Svaka je
    # provjerena u adresaru nadležne biskupije.
    "701383": ("Selca kod Starog Grada", "Stari Grad",
               "Hvarska biskupija, adresar: Župa Male Gospe, Selca kod Starog "
               "Grada br. 20, 21460 Stari Grad — točka je bila na Braču"),
    "701272": ("Bol", "Bol",
               "Hvarska biskupija, adresar: Župa sv. Ivana Krstitelja, Pjaca "
               "Joze Bodlovića 1, 21420 Bol — ista adresa kao u evidenciji; "
               "istoimena župa u Povlji ima adresu Lokva 1"),
    "702192": ("Rakalj", "Marčana",
               "Porečka i pulska biskupija, popis župa: RAKALJ — župa "
               "Rođenja BDM (pošta Krnica); točka je bila u Labinu"),
    "702428": ("Majkusi", "Višnjan - Visignano",
               "Porečka i pulska biskupija: SVETI IVAN OD ŠTERNE — župa sv. "
               "Ivana Krstitelja, Majkusi 1, 52463 Višnjan"),
    "700625": ("Slime", "Omiš",
               "smn.hr/slime: župa i župna crkva sv. Ivana Krstitelja u "
               "Slimenu (područje grada Omiša), spominju se 1625."),
    "702420": ("Gornji Vaganac", "Plitvička Jezera",
               "Gospićko-senjska biskupija: Uzvišenje sv. Križa — Vaganac, "
               "uprava iz Drežnik Grada; u OSM-u je crkva Uzvišenja Svetog "
               "Križa u Gornjem Vagancu. Vaganac kod Gospića je 60 km dalje"),
}

# Koliko sigurno smještenih župa treba da bi se županija pripisala biskupiji.
#
# Bio je 2, da krivo smještena župa ne bi sama sebi opravdala županiju
# (novigradska je Porečkoj i pulskoj upisivala Zadarsku). Prag 2 je međutim
# RUŠIO ispravne podatke: Riječka nadbiskupija u Istarskoj županiji ima točno
# jednu župu — sv. Martina u Vodicama (Lanišće, Ćićarija). Čim je override
# odselio bujsku Krasicu iz Istre, potpora Istarskoj pala je na 1, pa je
# sljedeći run htio Vodice premjestiti 58 km u istoimeno naselje u
# Primorsko-goranskoj. Korekcija bi si tako sama proizvela grešku, i to
# kaskadno — svaki run drugačiji rezultat.
#
# Zato prag 1, a slučaj koji je prag 2 hvatao (Novigrad) rješava OVERRIDE.
# Kompromis je svjestan i asimetričan: propuštena greška ostaje kakva jest,
# a ispravan podatak se ne kvari. Cijena je da usamljena krivo smještena župa
# može sama sebi napisati dozvolu — takva se hvata OVERRIDE-om, s izvorom.
MIN_ZUPA_PO_ZUPANIJI = 1

# Koliko daleko od SVAKOG naselja koje evidencija imenuje točka smije biti a da
# je još uvijek smatramo dokazom. Nije prag pogreške nego prag besmisla:
# izmjereno nad svih 1562 župe, iznad 30 km ostaje točno jedan slučaj koji nije
# već pokriven OVERRIDES-om (Prgomelje → Dubrovnik, 314 km). Niže se ne smije:
# na 20 km upada Žirje (upisano na „Šibenik", a otok je 22 km od grada) i još
# nekoliko župa kojima sjedište legitimno nije u imenovanom naselju.
MAX_SJEDISTE_KM = 30.0

# Biskupije koje ne particioniraju teritorij — ne ulaze u izvod županija.
_SKIP_DIOCESE = {"Križevačka Eparhija"}


class Settlement(NamedTuple):
    name: str
    jls: str
    county: str
    lat: float
    lng: float
    polygons: list


def _norm(s: str | None) -> str:
    s = (s or "").translate(str.maketrans({"đ": "d", "Đ": "D"}))
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in s.lower())
    return " ".join(s.split())


def km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Ekvirektangularna udaljenost — dovoljno za „je li ovo isto mjesto"."""
    dy = lat1 - lat2
    dx = (lng1 - lng2) * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dy, dx) * 111.32


def _ring_centroid(ring: list) -> tuple[float, float]:
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if a == 0:
        return ring[0][0], ring[0][1]
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def _ring_area(ring: list) -> float:
    a = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2


def _in_ring(lng: float, lat: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            if lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def _point_in_poly(poly: list, lat: float, lng: float) -> bool:
    return bool(poly) and _in_ring(lng, lat, poly[0]) and not any(
        _in_ring(lng, lat, h) for h in poly[1:]
    )


def contains(s: Settlement, lat: float, lng: float) -> bool:
    return any(_point_in_poly(poly, lat, lng) for poly in s.polygons)


def _scanline_point(poly: list, lat: float) -> tuple[float, float] | None:
    """Sredina najšireg unutarnjeg raspona na vodoravnici — zajamčeno unutra.

    Parnost presjeka sa SVIM prstenovima (vanjskim i rupama) daje ispravan
    raspored unutra/vani, pa se rupa ne može odabrati kao unutrašnjost.
    """
    xs: list[float] = []
    for ring in poly:
        n = len(ring)
        for i in range(n):
            x0, y0 = ring[i][0], ring[i][1]
            x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
            if (y0 > lat) != (y1 > lat):
                xs.append((x1 - x0) * (lat - y0) / (y1 - y0) + x0)
    if len(xs) < 2:
        return None
    xs.sort()
    span = max(zip(xs[0::2], xs[1::2]), key=lambda ab: ab[1] - ab[0])
    return (span[0] + span[1]) / 2, lat


def representative_point(polys: list) -> tuple[float, float] | None:
    """(lat, lng) točka koja ZAISTA leži unutar naselja.

    Težište najvećeg prstena je dobra točka za konveksna naselja, ali svako
    12. hrvatsko naselje je toliko razvedeno da mu težište padne van. Prijašnji
    fallback — prvi vrh poligona — leži NA granici, a `_in_ring` rubnu točku
    odbija: 84 od 6759 naselja imalo je „vlastitu" točku koja u njemu nije.

    Nije kozmetika: override za Sveti Vid-Miholjice zato je vraćao „premjesti"
    na svakom runu, pa je korekcija na svakom runu iznova gazila koordinatu
    razine zgrade težištem naselja. Pipeline nije bio idempotentan.
    """
    best = max((p for p in polys if p and p[0]), key=lambda p: _ring_area(p[0]),
               default=None)
    if not best:
        return None
    lng, lat = _ring_centroid(best[0])
    if _point_in_poly(best, lat, lng):
        return lat, lng
    ys = [pt[1] for pt in best[0]]
    for frac in (0.5, 0.35, 0.65, 0.2, 0.8):    # više pokušaja: „U" naselje
        y = min(ys) + (max(ys) - min(ys)) * frac
        hit = _scanline_point(best, y)
        if hit and _point_in_poly(best, hit[1], hit[0]):
            return hit[1], hit[0]
    return None


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, list[Settlement]], list[Settlement]]:
    """(normalizirano ime → naselja, sva naselja). Ime NIJE jedinstveno."""
    by_name: dict[str, list[Settlement]] = {}
    allo: list[Settlement] = []
    for _bbox, polys, props in geo_hr.naselja_features():
        pt = representative_point(polys)
        if not pt:
            continue
        s = Settlement(props.get("name") or "", props.get("jls_name") or "",
                       props.get("zupanija") or "", pt[0], pt[1], polys)
        allo.append(s)
        by_name.setdefault(_norm(s.name), []).append(s)
    return by_name, allo


def candidates(city: str | None) -> tuple[list[Settlement], list[Settlement]]:
    """(točni, afiksni) kandidati za sjedište.

    Evidencija zna skratiti službeni naziv s obje strane — „Kraj" za „Dicmo
    Kraj", „Novigrad" za „Novigrad - Cittanova", „Sveti Vid" za „Sveti
    Vid-Miholjice" — pa se uz točan pogodak uzimaju i naselja kojima je
    traženo ime cijela prva ili zadnja riječ(i). Podniz se NE traži: „Vid" ne
    smije povući „Sveti Vid".

    Afiksni pogodci se drže ODVOJENO i gledaju tek ako točan naziv ne dade
    odgovor: „Vrh" ima dva točna pogotka, ali tridesetak afiksnih (Kraljev
    Vrh, Trški Vrh…) koji bi ga učinili nerazrješivim.
    """
    key = _norm(city)
    if not key:
        return [], []
    by_name, allo = _index()
    exact = list(by_name.get(key) or [])
    seen = {id(s) for s in exact}
    affix = [s for s in allo
             if id(s) not in seen
             and (_norm(s.name).startswith(key + " ") or _norm(s.name).endswith(" " + key))]
    return exact, affix


def _override_county(row) -> str | None:
    """Županija koju ručno provjeren override propisuje toj župi."""
    entry = OVERRIDES.get(str(row["registry_id"] or ""))
    if not entry:
        return None
    name, jls, _ = entry
    for s in _index()[0].get(_norm(name), []):
        if s.jls == jls:
            return s.county
    return None


def settled_counties(rows) -> dict[str, set[str]]:
    """Biskupija → županije u kojima SIGURNO ima župu.

    „Sigurno" = točka leži unutar naselja čije ime piše u evidenciji. Kod
    višeznačnog imena upravo točka bira koji je homonim, pa dvojba ne smeta —
    smeta samo neslaganje, a takve župe ovaj filtar ispadaju same.

    Župa pod OVERRIDE-om se broji na SVOJE ISPRAVLJENO odredište, bez obzira
    gdje joj je točka trenutno. Inače izvod ovisi o tome je li korekcija već
    pokrenuta: prvi run bujsku Krasicu broji u Istarsku, drugi (nakon što ju
    je override odselio u Bakar) više ne — pa se skup dozvoljenih županija
    mijenja između runova i korekcija kaskadno mijenja odluke.

    Županija se pripisuje od `MIN_ZUPA_PO_ZUPANIJI` župa naviše.
    """
    tally: dict[str, dict[str, int]] = {}
    for r in rows:
        d = r["diocese"]
        if not d or d in _SKIP_DIOCESE:
            continue
        county = _override_county(r)
        if county is None:
            if r["lat"] is None:
                continue
            exact, affix = candidates(r["city"])
            county = next((s.county for s in exact + affix
                           if contains(s, r["lat"], r["lng"])), None)
        if county is None:
            continue
        tally.setdefault(d, {})
        tally[d][county] = tally[d].get(county, 0) + 1
    return {d: {c for c, n in cs.items() if n >= MIN_ZUPA_PO_ZUPANIJI}
            for d, cs in tally.items()}


class Fix(NamedTuple):
    target: Settlement
    reason: str


class Drop(NamedTuple):
    """Točka je besmislena, a odredište nije jednoznačno → bolje nikakva.

    Prazna koordinata je poštena („ne znamo gdje je"); točka 314 km od svakog
    naselja koje evidencija imenuje je tvrdnja koja nije istinita, a na karti
    izgleda jednako uvjerljivo kao i sve ostale.
    """
    reason: str


def _too_far_from_named(row) -> tuple[float, list[Settlement]] | None:
    """(udaljenost, kandidati) ako je točka dalje od SVIH imenovanih naselja."""
    exact, affix = candidates(row["city"])
    cands = exact + affix
    if not cands or row["lat"] is None:
        return None
    if any(contains(s, row["lat"], row["lng"]) for s in cands):
        return None
    d = min(km(row["lat"], row["lng"], s.lat, s.lng) for s in cands)
    return (d, exact or affix) if d > MAX_SJEDISTE_KM else None


def resolve(row, counties: dict[str, set[str]]) -> Fix | Drop | None:
    """Što učiniti sa sjedištem župe: premjestiti, obrisati, ili ništa."""
    rid = str(row["registry_id"] or "")
    if rid in OVERRIDES:
        name, jls, src = OVERRIDES[rid]
        for s in _index()[0].get(_norm(name), []):
            if s.jls == jls:
                if row["lat"] is not None and contains(s, row["lat"], row["lng"]):
                    return None
                return Fix(s, f"override — {src}")
        logger.warning("override za %s pokazuje na nepoznato naselje %s/%s",
                       rid, name, jls)
        return None

    if row["lat"] is None:
        return None

    # Prije izvoda županija: točka koja nije ni blizu nijednog naselja koje
    # evidencija imenuje. Ne treba joj biskupija, pa hvata i Križevačku
    # eparhiju — biskupiju koja se preklapa sa svima i zato uopće nije u
    # izvodu (`_SKIP_DIOCESE`), a bez toga joj nitko ne provjerava sjedišta.
    far = _too_far_from_named(row)
    if far:
        d, cands = far
        where = ", ".join(f"{s.name}/{s.jls}" for s in cands)
        if len(cands) == 1:
            return Fix(cands[0], f"točka je bila {d:.0f} km od jedinog "
                                 f"naselja tog imena ({where})")
        return Drop(f"točka je bila {d:.0f} km od svakog naselja tog imena "
                    f"({where}) — koje je pravo, evidencija ne kaže")

    allowed = counties.get(row["diocese"] or "", set())
    if not allowed:
        return None

    # Jedini okidač: točka je u županiji u kojoj ta biskupija NEMA župa. Ne
    # dira se sve ostalo — župni ured koji stoji par kilometara izvan naselja
    # iz evidencije je normalna stvar (Žirje je upisano na „Šibenik"), a
    # zamijeniti mu Placesovu koordinatu težištem naselja bilo bi pogoršanje.
    here = geo_hr.locate(row["lat"], row["lng"]).county
    if here is None or here in allowed:
        return None

    exact, affix = candidates(row["city"])
    narrowed = [s for s in exact if s.county in allowed]
    if len(narrowed) != 1:
        narrowed = [s for s in exact + affix if s.county in allowed]
    if len(narrowed) != 1:
        return None
    return Fix(narrowed[0],
               f"točka je bila u županiji {here}, a {row['diocese']} ondje "
               f"nema nijednu župu (ima u {', '.join(sorted(allowed))})")
