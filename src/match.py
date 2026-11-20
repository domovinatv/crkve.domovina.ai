"""Spajanje izvora na građevine: kulturna dobra → crkve, župe → župne crkve.

Problem: Registar kulturnih dobara i evidencija župa NEMAJU koordinate ni
OSM id. Imaju naziv + mjesto. OSM ima naziv + koordinate. Isti objekt izgleda
ovako u tri izvora:

  OSM              "Crkva sv. Ante"                          Dragljane
  MinKulture       "Crkva sv. Ante Padovanskog"              Dragljane / VRGORAC
  Evidencija       "ŽUPA SV. ANTUNA PADOVANSKOG, DRAGLJANE"  Dragljane

Strategija (svjesno konzervativna — lažni match je gori od nedostajućeg):

  1. BLOKIRANJE PO MJESTU, U DVIJE RAZINE. Prvo naselje (precizno), pa tek
     ako ondje nema kandidata — općina (široko). Redoslijed je bitan: općina
     Vrgorac ima 25 crkava u dvadesetak sela, i pretraga po općini nikad ne
     bi dala jasnog pobjednika, dok naselje Dragljane ima jednu ili dvije.
  2. TVRDI FILTAR PO SVECU, ali samo po GLAVI titulara (titular.head_key) —
     epitet ("Padovanskog", "Krstitelja") se razlikuje među izvorima i nije
     pouzdan za odbacivanje.
  3. rapidfuzz token_set_ratio na normaliziranom nazivu, uz prag.
  4. Ako više kandidata prijeđe prag, traži jasnog pobjednika (margina);
     inače ne matchaj — dvosmislenost ostaje nespojena i vidi se u statistici.

Za župe (scripts/11) prije svega toga ide 0. KONFESIJA (`compatible`,
odluka 4): kandidat koji pravna osoba ne smije dobiti uopće ne ulazi u
bazen, pa ne može ni pobijediti ni pokvariti marginu ispravnom kandidatu.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from rapidfuzz import fuzz

from .denomination import is_katolicka, is_nekatolicka
from .kinds import classify
from .normalize import norm_key, strip_diacritics
from .titular import head_key, key as titular_key

logger = logging.getLogger(__name__)

# Prag sličnosti naziva unutar istog mjesta. 82 je empirijski: ispod toga
# "Crkva sv. Petra" počinje matchati "Crkva sv. Pavla" u malim mjestima.
THRESHOLD = 82
# Pobjednik mora biti barem toliko bolji od drugoplasiranog.
MARGIN = 6

# Titulari koji su preširoki da bi nosili tvrdnju o jedinstvenosti. "Majka
# Božja" je u titular.py catch-all za SVE marijanske zazive, pa "Gospa od
# Utjehe" i "Gospa od Batka" dobiju isti ključ — a to su dvije različite crkve
# u istom mjestu. Za sličnost naziva je i takav titular koristan (bonus na
# score), ali _unique_by_titular_and_kind ga mora odbiti.
GENERIC_TITULARS = {"majka bozja"}


def place_key(*parts: str | None) -> set[str]:
    """Normalizirani ključevi mjesta za blokiranje. Prazni dijelovi se ignoriraju."""
    out: set[str] = set()
    for p in parts:
        if not p:
            continue
        k = strip_diacritics(str(p)).lower().strip()
        k = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in k)
        k = " ".join(k.split())
        if k:
            out.add(k)
            # "grad zagreb" i "zagreb" moraju blokirati zajedno
            if k.startswith("grad "):
                out.add(k[5:])
    return out


@dataclass
class Candidate:
    """Građevina iz baze, pripremljena za usporedbu."""

    id: int
    name: str
    places: set[str] = field(default_factory=set)
    nkey: str = ""
    tkey: str | None = None
    hkey: str | None = None
    kind: str | None = None
    religion: str | None = None
    denomination: str | None = None

    @classmethod
    def from_row(cls, row) -> "Candidate":
        name = row["name"] or ""
        cols = row.keys()
        return cls(
            id=row["id"],
            name=name,
            places=place_key(row["city"], row["settlement"], row["municipality"]),
            nkey=norm_key(name),
            tkey=titular_key(name),
            hkey=head_key(name),
            # `kind` iz baze ako postoji (OSM tagovi su pouzdaniji), inače iz naziva.
            kind=(row["kind"] if "kind" in cols and row["kind"] else classify({}, name)),
            religion=row["religion"] if "religion" in cols else None,
            denomination=row["denomination"] if "denomination" in cols else None,
        )


_KATOLICKA_EVIDENCIJA = "datagovhr:katolicke-pravne-osobe"


def _field(obj: Any, key: str) -> Any:
    """Isto čitanje za sqlite3.Row, dict i Candidate."""
    if hasattr(obj, "keys"):
        return obj[key] if key in obj.keys() else None
    return getattr(obj, key, None)


def compatible(church: Any, parish: Any) -> bool:
    """Smije li ova pravna osoba dobiti ovu građevinu? (odluka 4)

    Katolička pravna osoba (konfesija rimo-/grkokatolička ili zapis iz
    evidencije Katoličke Crkve) NE dobiva građevinu koja je sigurno
    nekatolička — po kindu (`pravoslavna-crkva`/`dzamija`/`sinagoga`, i bez
    `denomination`), po religiji ili po konfesiji. Kind sam nije dovoljan:
    protestantske crkve i Jehovini svjedoci su u OSM-u `kind=crkva`.
    Nekatolička pravna osoba NE dobiva građevinu katoličke konfesije.
    Nepoznata konfesija ne blokira.

    Definicija „nekatoličke građevine" je ista funkcija kojom audit mjeri
    `nekatolicke_na_katolickim` (`denomination.is_nekatolicka`).
    """
    p_den = _field(parish, "denomination")
    p_rel = _field(parish, "religion")
    parish_kat = is_katolicka(p_den) or _KATOLICKA_EVIDENCIJA in (_field(parish, "source") or "")
    church_nekat = is_nekatolicka(
        _field(church, "kind"), _field(church, "religion"), _field(church, "denomination"))
    if parish_kat:
        return not church_nekat
    if is_nekatolicka(None, p_rel, p_den):
        return church_nekat or not is_katolicka(_field(church, "denomination"))
    return True


def weak_claim(name: str, cand: Candidate) -> bool:
    """Je li pogodak samo podniz bez sveca? (scripts/11, redoslijed 1. prolaza)

    Pravna osoba imenuje sveca, a građevina nema titular: „FRANJEVAČKI
    SAMOSTAN SV. NIKOLE" i OSM „Franjevački samostan" daju token_set_ratio
    100 jer je cijeli naziv građevine podniz. To je slabiji dokaz od
    pogotka bez proturječja: ista građevina jednako savršeno odgovara i
    „FRANJEVAČKOM SAMOSTANU RIJEKA - TRSAT". Takav zahtjev se ne odbija
    (sam u mjestu je obično točan: Badija, Pridvorje), ali dolazi NA RED
    ZADNJI, pa građevinu prvo dobije pravna osoba kojoj naziv ne proturječi.
    """
    return bool(head_key(name)) and not cand.hkey


def build_index(rows: Iterable) -> dict[str, list[Candidate]]:
    """Mjesto → lista kandidata. Kandidat s više mjesta je u više blokova."""
    idx: dict[str, list[Candidate]] = {}
    for row in rows:
        c = Candidate.from_row(row)
        for p in c.places:
            idx.setdefault(p, []).append(c)
    return idx


def best_match(
    index: dict[str, list[Candidate]],
    name: str,
    *place_tiers: set[str],
    threshold: int = THRESHOLD,
    margin: int = MARGIN,
    accept: Callable[[Candidate], bool] | None = None,
) -> tuple[Candidate, int] | None:
    """Najbolji kandidat za naziv, gledajući razine mjesta redom.

    `accept` je tvrdi filtar koji se primjenjuje na bazen PRIJE ocjenjivanja
    (scripts/11: `lambda c: compatible(c, župa)`). Razina čiji su svi
    kandidati odbijeni ponaša se kao prazna — gleda se šira.

    `place_tiers` idu od najpreciznije (naselje) prema najširoj (općina).
    Prva razina koja uopće ima kandidata je i jedina koja se ocjenjuje — širi
    blok se ne miješa s užim jer bi udaljeni istoimeni objekt razvodnio
    marginu i ubio ispravan pogodak.
    """
    if not name:
        return None

    for places in place_tiers:
        if not places:
            continue
        pool: dict[int, Candidate] = {}
        for p in places:
            for c in index.get(p, []):
                if accept is None or accept(c):
                    pool[c.id] = c
        if not pool:
            continue
        hit = _score(pool, name, threshold, margin)
        if hit:
            return hit
        # Blok postoji ali nitko ne prolazi — probaj širu razinu.
    return None


def _score(
    pool: dict[int, Candidate], name: str, threshold: int, margin: int
) -> tuple[Candidate, int] | None:
    want_nkey = norm_key(name)
    want_tkey = titular_key(name)
    want_hkey = head_key(name)

    scored: list[tuple[int, Candidate]] = []
    for c in pool.values():
        # Tvrdi filtar: različit svetac = različit objekt, ma koliko nazivi
        # bili slični. Uspoređuje se glava titulara, ne puni (vidi titular.py).
        if want_hkey and c.hkey and want_hkey != c.hkey:
            continue
        score = fuzz.token_set_ratio(want_nkey, c.nkey)
        # Poklapanje punog titulara je jak signal — podigni score, ali ne preko
        # praga sam po sebi (isto mjesto + isti titular može biti više crkava).
        if want_tkey and c.tkey and want_tkey == c.tkey:
            score = min(100, score + 8)
        if score >= threshold:
            scored.append((score, c))

    if scored:
        scored.sort(key=lambda x: (-x[0], x[1].id))
        if len(scored) > 1 and scored[0][0] - scored[1][0] < margin:
            return None
        return scored[0][1], scored[0][0]

    return _unique_by_titular_and_kind(pool, want_tkey, name)


def _unique_by_titular_and_kind(
    pool: dict[int, Candidate], want_tkey: str | None, name: str
) -> tuple[Candidate, int] | None:
    """Zadnja šansa: jedinstvenost umjesto sličnosti naziva.

    Nazivi istog objekta znaju se potpuno razići — "Kompleks Katedrale
    Uznesenja Marijina" (Registar kulturnih dobara) i "katedrala Uznesenja
    Blažene Djevice Marije i svetih Stjepana i Ladislava" (OSM) daju
    token_set_ratio 54, daleko ispod praga, iako je riječ o istoj zgradi.

    Ako se u bloku poklapaju **titular I tip** i takav kandidat je **točno
    jedan**, to je jači dokaz od bilo kojeg tekstualnog praga: u jednom
    naselju nema dvije katedrale istog titulara. Bez oba uvjeta i bez
    jedinstvenosti — ne matchamo.
    """
    want_kind = classify({}, name)
    if not want_tkey or want_tkey in GENERIC_TITULARS or want_kind in (None, "ostalo"):
        return None
    hits = [c for c in pool.values() if c.tkey == want_tkey and c.kind == want_kind]
    if len(hits) != 1:
        return None
    return hits[0], 0  # score 0 = "spojeno po jedinstvenosti, ne po nazivu"
