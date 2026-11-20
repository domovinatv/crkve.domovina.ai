"""Metrike kvalitete podataka — mjerni instrument lanca S1–S7 (vidi docs/plan.md).

`scripts/40_stats.py` mjeri POKRIVENOST (koliko čega ima). Ovo mjeri GREŠKE:
svaka metrika broji zapise koji su sigurno ili vrlo vjerojatno krivi, i uz broj
nosi sortiran popis primjera, da se ispravak može provjeriti zapis po zapis, a
ne samo po tome što se brojka smanjila.

Svaka metrika je funkcija `(conn) -> dict` s ključem `value` (cijeli broj,
cilj je 0 ili dokumentirani ostatak) i po potrebi `examples` i razdiobama.
`METRICS` je registar: redoslijed u njemu je redoslijed u ispisu i u
`audit.json`. Izlaz je deterministički (bez vremena, sve sortirano), pa isti
ulaz daje isti sha — po tome se vidi je li rebuild nešto promijenio.

Kontekstne brojke (ukupno crkava, aktivne župe, župe bez crkve…) NE računaju
se ovdje nego `src/stats.py`, isti SQL kao `scripts/40_stats.py`.
"""
from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

from . import dedup, stats
from .denomination import (  # noqa: F401 — re-eksport, vidi „Konfesija" niže
    DOZVOLJENE_DENOMINACIJE,
    DOZVOLJENE_RELIGIJE,
    KATOLICKE,
    NEKATOLICKE_DENOMINACIJE,
    NEKATOLICKI_KINDOVI,
    NEKRSCANSKE_RELIGIJE,
    is_nekatolicka,
)
from .normalize import je_engleski, norm_key
from .titular import _EPITHETS, _KNOWN_NOM, _SERIES_EPITHETS, head_key

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Konfesija
# ---------------------------------------------------------------------------

# Konstante i pravilo žive u src/denomination.py — matcher (src/match.py)
# i ingest koriste iste, inače se mjera i pravilo raziđu. Ovdje se samo
# re-eksportiraju jer ih testovi i stariji kod traže kao `audit.X`.


# ---------------------------------------------------------------------------
# Pomoćno
# ---------------------------------------------------------------------------

def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _counter(items) -> dict[str, int]:
    """Razdioba sortirana po broju silazno, pa po ključu — deterministički."""
    c = Counter(items)
    return {k: v for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))}


# ---------------------------------------------------------------------------
# 1. Nekatoličke građevine spojene na katoličke pravne osobe
# ---------------------------------------------------------------------------

_SPOJENE_SQL = """
SELECT c.slug, c.kind, c.religion, c.denomination, c.is_parish_church,
       p.slug AS parish_slug
FROM churches c JOIN parishes p ON p.id = c.parish_id
WHERE p.denomination IN ({})
ORDER BY c.slug
""".format(", ".join(f"'{d}'" for d in sorted(KATOLICKE)))


def _nekatolicke_spojene(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return [r for r in conn.execute(_SPOJENE_SQL)
            if is_nekatolicka(r["kind"], r["religion"], r["denomination"])]


def _oznaka(r) -> str:
    return f"{r['kind'] or '?'} / {r['denomination'] or r['religion'] or '?'}"


def nekatolicke_na_katolickim(conn: sqlite3.Connection) -> dict:
    rows = _nekatolicke_spojene(conn)
    return {
        "value": len(rows),
        "po_kindu_i_konfesiji": _counter(_oznaka(r) for r in rows),
        "examples": sorted(f"{r['slug']} → {r['parish_slug']}" for r in rows),
    }


def nekatolicke_zupne_crkve(conn: sqlite3.Connection) -> dict:
    rows = [r for r in _nekatolicke_spojene(conn) if r["is_parish_church"] == 1]
    return {
        "value": len(rows),
        "po_kindu_i_konfesiji": _counter(_oznaka(r) for r in rows),
        "examples": sorted(f"{r['slug']} → {r['parish_slug']}" for r in rows),
    }


# ---------------------------------------------------------------------------
# 2. Titular „X i Y" ostavljen (djelomično) u genitivu
# ---------------------------------------------------------------------------

# Leksikon padeža iz samog parsera (src/titular.py): ključevi su genitivi,
# vrijednosti nominativi. Oblik koji je isti u oba padeža (Duje) nije dokaz.
_LEKS = {**_KNOWN_NOM, **_EPITHETS, **_SERIES_EPITHETS}
_GEN_LEKS = {k for k, v in _LEKS.items() if k != v.lower()}
_NOM_LEKS = {v.lower() for v in _LEKS.values()}
_OZNAKA_SVETCA = re.compile(r"^(sv|svet\w*|bl|blažen\w*)$")
_VEZNIK = "i"


def _rijec(w: str) -> str:
    return w.lower().strip(".,;:\"'()")


def padez(word: str) -> str | None:
    """'nom' | 'gen' | None (ne zna se) za jednu riječ titulara.

    Redom: leksikon parsera; pa morfologija hrvatskih svetačkih imena —
      - završetak na suglasnik ili -o je NOMINATIV (Petar, Pavao, Metod,
        Lovro): genitiv imena nikad ne završava tako;
      - završetak na -e (osim -je: Duje, Ambrozije, groblje) je GENITIV
        (Kuzme, Ane, Julite, mučenice): nominativ na -e je rijedak i u -je;
      - završetak na -a je DVOSMISLEN (Pavla je genitiv, Kuzma i Ana
        nominativ) — odlučuje par u kojem riječ stoji, vidi `genitiv_u_nizu`.
    """
    w = _rijec(word)
    if not w.isalpha() or _OZNAKA_SVETCA.match(w) or w == _VEZNIK:
        return None
    if w in _GEN_LEKS:
        return "gen"
    if w in _NOM_LEKS:
        return "nom"
    if w[-1] not in "aeiou" or w.endswith("o"):
        return "nom"
    if w.endswith("e") and not w.endswith("je"):
        return "gen"
    return None


def genitiv_u_nizu(titular: str | None) -> str | None:
    """Vrati 'mijesano' | 'sve_genitiv' za titular „sv. X i Y" koji nije
    (cijeli) u nominativu, inače None.

    Titular je po definiciji (src/titular.py) u NOMINATIVU, ali `parse` u
    nominativ diže samo PRVU riječ — ostatak niza ostaje kako je stajao u
    nazivu („Crkva sv. Petra i Pavla" → „sv. Petar i Pavla"), a ime koje
    parser ne poznaje ostaje cijelo u genitivu („sv. Ćirila i Metoda").
    Pravilo je zato generičko, nad cijelim nizom, a ne popis oblika:

      1. riječ je genitiv po `padez` (leksikon parsera ili nastavak -e) →
         titular je kriv;
      2. desni član para oko „i" na -a koji nije poznat nominativ je genitiv,
         osim ako je lijevi član poznat nominativ na -a (Kuzma, Nikola, Ana):
         uz takav lijevi član desni može biti i ženski nominativ („Joakim i
         Ana" je ispravan, „Vid i Modesta", „Ćirila i Metoda" nisu).

    Gleda samo titulare s veznikom „i" — pojedinačno ime u genitivu („sv.
    Mohora") je druga, rjeđa greška parsera i ne broji se ovdje.
    'mijesano' = u nizu ima i nominativa (tipično „sv. Petar i Pavla"),
    'sve_genitiv' = nominativa nema („sv. Apostola Petra i Pavla").
    """
    if not titular or not titular.startswith("sv. "):
        return None
    words = titular[4:].split()
    low = [_rijec(w) for w in words]
    if _VEZNIK not in low:
        return None
    cases = [padez(w) for w in words]

    for i, w in enumerate(low):
        if w != _VEZNIK or i == 0:
            continue
        j = i + 1
        while j < len(low) and _OZNAKA_SVETCA.match(low[j] or "-"):
            j += 1          # „X i sv. Y", „X i svetog Y"
        if j >= len(low):
            continue
        left, right = low[i - 1], low[j]
        if (right.isalpha() and right.endswith("a") and right not in _NOM_LEKS
                and not (left.endswith("a") and left in _NOM_LEKS)):
            cases[j] = "gen"

    if "gen" not in cases:
        return None
    return "mijesano" if "nom" in cases else "sve_genitiv"


def _titular_genitiv_tablica(conn: sqlite3.Connection, table: str) -> dict:
    hits = []
    for r in conn.execute(f"SELECT slug, titular FROM {table} "
                          "WHERE titular IS NOT NULL ORDER BY slug"):
        vrsta = genitiv_u_nizu(r["titular"])
        if vrsta:
            hits.append((r["slug"], r["titular"], vrsta))
    return {
        "value": len(hits),
        "mijesano": sum(1 for h in hits if h[2] == "mijesano"),
        "sve_genitiv": sum(1 for h in hits if h[2] == "sve_genitiv"),
        "oblici_top20": dict(list(_counter(h[1] for h in hits).items())[:20]),
        "examples": sorted(h[0] for h in hits),
    }


def titular_genitiv(conn: sqlite3.Connection) -> dict:
    crkve = _titular_genitiv_tablica(conn, "churches")
    zupe = _titular_genitiv_tablica(conn, "parishes")
    return {"value": crkve["value"] + zupe["value"], "churches": crkve, "parishes": zupe}


# ---------------------------------------------------------------------------
# 3. Konfesija / religija izvan dozvoljenog skupa
# ---------------------------------------------------------------------------

def _nedozvoljene(conn: sqlite3.Connection, table: str) -> dict:
    denom = Counter()
    rel = Counter()
    for r in conn.execute(f"SELECT denomination, religion FROM {table}"):
        if r["denomination"] is not None and r["denomination"] not in DOZVOLJENE_DENOMINACIJE:
            denom[r["denomination"]] += 1
        if r["religion"] is not None and r["religion"] not in DOZVOLJENE_RELIGIJE:
            rel[r["religion"]] += 1
    return {
        "value": sum(denom.values()) + sum(rel.values()),
        "denomination": _counter(denom.elements()),
        "religion": _counter(rel.elements()),
    }


def konfesija_nenormalizirana(conn: sqlite3.Connection) -> dict:
    per = {t: _nedozvoljene(conn, t) for t in ("churches", "parishes", "dioceses")}
    return {"value": sum(p["value"] for p in per.values()), **per}


# ---------------------------------------------------------------------------
# 4. Ista zgrada dvaput: OSM node + way/relation
# ---------------------------------------------------------------------------

NODE_WAY_M = 40.0
# Ćelija mreže ≈ 55 m u obje osi na 45° s. š.: par unutar 40 m je uvijek u
# istoj ili susjednoj ćeliji, pa je usporedba lokalna umjesto O(n²).
_CELL_LAT = 0.0005
_CELL_LNG = 0.0007


def _cell(lat: float, lng: float) -> tuple[int, int]:
    return math.floor(lat / _CELL_LAT), math.floor(lng / _CELL_LNG)


def _tip(r) -> str:
    """OSM primitiv, ili 'wikidata' za zapis koji postoji samo na Wikidati."""
    return r["osm_type"] or "wikidata"


def parovi_blizu(conn: sqlite3.Connection, max_m: float = NODE_WAY_M):
    """Svi parovi građevina na ≤ max_m, preko mreže (svaki par jednom)."""
    rows = conn.execute(
        "SELECT slug, name, osm_type, lat, lng FROM churches "
        "WHERE lat IS NOT NULL AND lng IS NOT NULL ORDER BY slug"
    ).fetchall()
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        grid[_cell(r["lat"], r["lng"])].append(i)
    for i, a in enumerate(rows):
        ci, cj = _cell(a["lat"], a["lng"])
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for j in grid.get((ci + di, cj + dj), ()):
                    if j <= i:
                        continue
                    b = rows[j]
                    d = haversine_m(a["lat"], a["lng"], b["lat"], b["lng"])
                    if d <= max_m:
                        yield a, b, d


def _ista_zgrada(a, b) -> tuple[bool, bool] | None:
    """(isti_naziv, ista_glava) ako par smije biti ista zgrada, inače None.
    Različite glave titulara = dvije zgrade (crkva i kapela uz nju)."""
    ha, hb = head_key(a["name"]), head_key(b["name"])
    if ha and hb and ha != hb:
        return None
    na = norm_key(a["name"])
    isti_naziv = bool(na) and na == norm_key(b["name"])
    ista_glava = bool(ha) and ha == hb
    return (isti_naziv, ista_glava) if (isti_naziv or ista_glava) else None


def node_way_duplikati(conn: sqlite3.Connection) -> dict:
    """Glavna brojka: OSM node + way/relation ≤ 40 m kojima se nazivi slažu
    (isti naziv, ista glava titulara, ili jedna strana bez OSM imena), a
    `src/dedup.py` ih NIJE spojio. Predikati su dedupovi (`nazivi_spojivi`,
    `zapreka`), pa mjera i pravilo ne mogu otići svaki na svoju stranu.

    U `value` ide samo par koji pravilo smatra istom zgradom a nije spojen.
    Par različite uloge ili različitog `wikidata` taga, i par iz
    `dedup.OSTAVLJENI`, je namjerno ostavljen i ide u `namjerno_ostavljeni`
    s razlogom. Ostali tipovi parova (way+way, way+wikidata…) ne ulaze u
    `value` — way+way je često crkva i zvonik/kapela istog titulara — ali se
    ispisuju u `ostali_tipovi_ista_glava`."""

    ostali = Counter()
    for a, b, _ in parovi_blizu(conn):
        tipovi = {_tip(a), _tip(b)}
        if "node" in tipovi and tipovi & {"way", "relation"} and len(tipovi) == 2:
            continue
        hit = _ista_zgrada(a, b)
        if hit and hit[1]:
            ostali["+".join(sorted([_tip(a), _tip(b)]))] += 1

    slug = {(r["osm_type"], r["osm_id"]): r["slug"] for r in conn.execute(
        "SELECT slug, osm_type, osm_id FROM churches WHERE osm_type IS NOT NULL")}
    pairs, ostavljeni = [], []
    for d, n, w in dedup.parovi(dedup.zapisi_iz_baze(conn), NODE_WAY_M):
        nazivi = dedup.nazivi_spojivi(n, w)
        if nazivi is None:
            continue
        opis = (f"{slug[(n.osm_type, n.osm_id)]} ~ {slug[(w.osm_type, w.osm_id)]} "
                f"({round(d)} m)")
        zapreka = dedup.zapreka(n, w)
        if (n.key, w.key) in dedup.OSTAVLJENI:
            ostavljeni.append(f"{opis}: {dedup.OSTAVLJENI[(n.key, w.key)]}")
        elif zapreka == "uloga":
            ostavljeni.append(f"{opis}: dvije zgrade, uloga {n.role} ≠ {w.role}")
        elif zapreka == "wikidata":
            ostavljeni.append(f"{opis}: različit wikidata {n.wikidata} ≠ {w.wikidata}")
        else:
            pairs.append({"opis": opis, "nazivi": nazivi})
    pairs.sort(key=lambda p: p["opis"])
    spojeno = conn.execute("SELECT COUNT(*) FROM church_merged").fetchone()[0]
    return {
        "value": len(pairs),
        "isti_naziv": sum(p["nazivi"] == "isti_naziv" for p in pairs),
        "ista_glava_titulara": sum(p["nazivi"] == "ista_glava" for p in pairs),
        "bez_imena": sum(p["nazivi"] == "bez_imena" for p in pairs),
        "spojeno": spojeno,
        "namjerno_ostavljeni": sorted(ostavljeni),
        "ostali_tipovi_ista_glava": _counter(ostali.elements()),
        "examples": [p["opis"] for p in pairs],
    }


# ---------------------------------------------------------------------------
# 5. Google Places koordinate u javnim exportima
# ---------------------------------------------------------------------------

EXPORT_SKRIPTE = ("31_export_geojson.py", "32_export_csv.py", "34_export_static.py")
_RE_KOORD_ZUPE = re.compile(r"\bp\.lat\b")
_RE_MAPS_URI = re.compile(r"\bgoogle_maps_uri\b")


def export_izvozi(text: str) -> dict:
    """Statička provjera izvora export skripte: izvozi li koordinate župa
    (`p.lat` iz `parishes p`) i Google Maps URI."""
    return {"koordinate_zupa": bool(_RE_KOORD_ZUPE.search(text)),
            "google_maps_uri": bool(_RE_MAPS_URI.search(text))}


def places_koordinate_u_exportu(conn: sqlite3.Connection,
                                scripts_dir: Path = ROOT / "scripts") -> dict:
    q = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    skripte = {}
    for name in EXPORT_SKRIPTE:
        path = scripts_dir / name
        skripte[name] = export_izvozi(path.read_text()) if path.exists() else None
    return {
        "value": q("SELECT COUNT(*) FROM parishes "
                   "WHERE geocode_source = 'places' AND lat IS NOT NULL"),
        "google_maps_uri": q("SELECT COUNT(*) FROM parishes WHERE google_maps_uri IS NOT NULL"),
        "google_place_id_zupe": q("SELECT COUNT(*) FROM parishes "
                                  "WHERE google_place_id IS NOT NULL"),
        "izvoze": skripte,
    }


# ---------------------------------------------------------------------------
# 6. dioceses.parish_count ≠ broj aktivnih i različitih župa u tablici parishes
# ---------------------------------------------------------------------------

def parish_count_razlika(conn: sqlite3.Connection) -> dict:
    """Uspoređuje s brojem AKTIVNIH i različitih župa (`src.stats.AKTIV`, ista
    definicija kao `zupe_aktivne`) — upravo to `parish_count` iz scripts/02
    broji (odluka 104). Broj ZAPISA `kind='zupa'` (uključuje ugašenu Priznu i
    duplikat Prgomet) ide uz svaku razliku i u `razlika_prema_zapisima`, kao
    kontekst; metrika ga ne cilja (odluka 307)."""
    rows = conn.execute(
        "SELECT d.slug, d.parish_count, "
        " (SELECT COUNT(*) FROM parishes p WHERE p.diocese = d.name AND p.kind = 'zupa') n, "
        " (SELECT COUNT(*) FROM parishes p WHERE p.diocese = d.name AND p.kind = 'zupa' AND "
        + stats.AKTIV + ") aktivne "
        "FROM dioceses d WHERE d.denomination IN ({}) ORDER BY d.slug".format(
            ", ".join(f"'{x}'" for x in sorted(KATOLICKE)))
    ).fetchall()
    diff = [r for r in rows if (r["parish_count"] or 0) != r["aktivne"]]
    return {
        "value": len(diff),
        "razlika_prema_zapisima": sum(1 for r in rows if (r["parish_count"] or 0) != r["n"]),
        "examples": [f"{r['slug']}: parish_count {r['parish_count']}, aktivnih {r['aktivne']}, "
                     f"zapisa {r['n']}" for r in diff],
    }


# ---------------------------------------------------------------------------
# 7. Isti Wikidata entitet na više građevina
# ---------------------------------------------------------------------------

def wikidata_dijeljen(conn: sqlite3.Connection) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for r in conn.execute("SELECT wikidata_id, slug, kind FROM churches "
                          "WHERE wikidata_id IS NOT NULL ORDER BY wikidata_id, slug"):
        groups[r["wikidata_id"]].append(r)
    shared = {q: rs for q, rs in groups.items() if len(rs) > 1}
    # Očekivano (CLAUDE.md): OSM tagira crkvu i samostanski kompleks kao dva
    # objekta s jednim Wikidata entitetom.
    neocekivani = sorted(q for q, rs in shared.items()
                         if not any(r["kind"] == "samostan" for r in rs))
    return {
        "value": len(shared),
        "neocekivani": neocekivani,
        "examples": [f"{q}: " + ", ".join(f"{r['slug']} [{r['kind']}]" for r in rs)
                     for q, rs in sorted(shared.items())],
    }


# ---------------------------------------------------------------------------
# 8. Sitnice: engleski nazivi, građevine bez županije, filijale daleko od župe
# ---------------------------------------------------------------------------

# Definicija engleskog naziva je u src/normalize.py (`je_engleski`): ista
# funkcija bira hrvatski naziv u ingestu (scripts/01, 05), pa mjera i pravilo
# nisu dvije definicije.


def engleski_nazivi(conn: sqlite3.Connection) -> dict:
    hits = [r for r in conn.execute("SELECT slug, name, osm_type FROM churches ORDER BY slug")
            if je_engleski(r["name"])]
    return {
        "value": len(hits),
        "po_izvoru": _counter("osm" if r["osm_type"] else "wikidata" for r in hits),
        "examples": [f"{r['slug']}: {r['name']}" for r in hits],
    }


def bez_zupanije(conn: sqlite3.Connection) -> dict:
    slugs = [r[0] for r in conn.execute(
        "SELECT slug FROM churches WHERE county IS NULL ORDER BY slug")]
    return {"value": len(slugs), "examples": slugs}


DALEKO_KM = 20.0


def crkve_dalje_20km_od_zupe(conn: sqlite3.Connection) -> dict:
    hits = []
    for r in conn.execute(
        "SELECT c.slug, c.lat, c.lng, p.slug AS ps, p.lat AS plat, p.lng AS plng "
        "FROM churches c JOIN parishes p ON p.id = c.parish_id "
        "WHERE c.lat IS NOT NULL AND p.lat IS NOT NULL ORDER BY c.slug"
    ):
        km = haversine_m(r["lat"], r["lng"], r["plat"], r["plng"]) / 1000
        if km > DALEKO_KM:
            hits.append(f"{r['slug']} → {r['ps']} ({km:.1f} km)")
    return {"value": len(hits), "examples": hits}


# ---------------------------------------------------------------------------
# Registar
# ---------------------------------------------------------------------------

Metric = tuple[str, Callable[[sqlite3.Connection], dict], str]

METRICS: list[Metric] = [
    ("nekatolicke_na_katolickim", nekatolicke_na_katolickim,
     "nekatolička građevina (kind/religija/konfesija) spojena na katoličku pravnu osobu"),
    ("nekatolicke_zupne_crkve", nekatolicke_zupne_crkve,
     "… od toga označena kao župna crkva"),
    ("titular_genitiv", titular_genitiv,
     "titular „sv. X i Y” (djelomično) u genitivu — crkve + pravne osobe"),
    ("konfesija_nenormalizirana", konfesija_nenormalizirana,
     "denomination/religion izvan dozvoljenog skupa — crkve + pravne osobe + biskupije"),
    ("node_way_duplikati", node_way_duplikati,
     f"OSM node + way/relation ≤{NODE_WAY_M:.0f} m, spojivi nazivi, a dedup ih nije spojio"),
    ("places_koordinate_u_exportu", places_koordinate_u_exportu,
     "župe s koordinatama iz Google Placesa (idu u javne exporte)"),
    ("parish_count_razlika", parish_count_razlika,
     "katolička biskupija: parish_count ≠ broj aktivnih i različitih župa"),
    ("wikidata_dijeljen", wikidata_dijeljen,
     "isti wikidata_id na više građevina"),
    ("engleski_nazivi", engleski_nazivi,
     "naziv građevine na engleskom (Church/Chapel/Saint/St. …)"),
    ("bez_zupanije", bez_zupanije,
     "građevina bez županije"),
    ("crkve_dalje_20km_od_zupe", crkve_dalje_20km_od_zupe,
     f"spojena građevina > {DALEKO_KM:.0f} km od koordinata svoje pravne osobe"),
]

KONTEKST = ["crkve_ukupno", "crkve_sa_zupom", "zupne_crkve", "zupe_aktivne",
            "zupe_bez_zupne_crkve", "zupe_bez_ijedne_crkve"]


def run(conn: sqlite3.Connection) -> dict:
    """Sve metrike + kontekst, u redoslijedu registra."""
    out = {"metrike": {}, "kontekst": {}}
    for name, fn, opis in METRICS:
        out["metrike"][name] = {"opis": opis, **fn(conn)}
    for k in KONTEKST:
        out["kontekst"][k] = stats.scalar(conn, k)
    return out


def _sazetak(name: str, m: dict) -> str:
    """Kratka podbrojka za tablicu na stdout."""
    if name == "titular_genitiv":
        return f"crkve {m['churches']['value']}, pravne osobe {m['parishes']['value']}"
    if name == "konfesija_nenormalizirana":
        return ", ".join(f"{t} {m[t]['value']}" for t in ("churches", "parishes", "dioceses"))
    if name == "node_way_duplikati":
        return (f"spojeno {m['spojeno']}, namjerno ostavljeno "
                f"{len(m['namjerno_ostavljeni'])}")
    if name == "places_koordinate_u_exportu":
        return f"google_maps_uri {m['google_maps_uri']}"
    if name == "wikidata_dijeljen":
        return "neočekivani: " + (", ".join(m["neocekivani"]) or "—")
    if name == "engleski_nazivi":
        return ", ".join(f"{k} {v}" for k, v in m["po_izvoru"].items())
    return ""


def format_table(result: dict) -> str:
    lines = []
    w = max(len(n) for n in [*result["metrike"], *result["kontekst"]])
    lines.append(f"{'METRIKA':<{w}}  {'VRIJ.':>6}  OPIS")
    lines.append("─" * (w + 60))
    for name, m in result["metrike"].items():
        extra = _sazetak(name, m)
        lines.append(f"{name:<{w}}  {m['value']:>6}  {m['opis']}"
                     + (f" [{extra}]" if extra else ""))
    lines.append("─" * (w + 60))
    lines.append("KONTEKST (definicije iz src/stats.py = scripts/40_stats.py)")
    for k, v in result["kontekst"].items():
        lines.append(f"{k:<{w}}  {v:>6}")
    return "\n".join(lines)
