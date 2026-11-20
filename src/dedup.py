"""Dedup OSM node + way/relation: ista zgrada ucrtana kao točka i kao tlocrt.

OSM često ima istu crkvu dvaput: čvor `amenity=place_of_worship` (s imenom)
i tlocrt `building=church|chapel` (često bez imena). Katalog bi bez ovoga imao
dvije stranice, dvije točke na karti i dva kandidata za svaki kasniji spoj
(Wikidata `_nearest` u `scripts/05` znao je sjesti na točku umjesto tlocrta).

Pravilo (odluka 400), par čvor N + way/relation W je ista zgrada ako:

  (a) ista **uloga** (`uloga()`): samostan (`amenity=monastery` ili
      `building=monastery`), poklonac (`historic=wayside_shrine`), ili
      bogoslužje (sve ostalo). Samostan uz crkvu i poklonac uz crkvu su dvije
      građevine, i kad nose ime istog sveca;
  (b) nazivi su spojivi (`nazivi_spojivi()`): isti `norm_key`, ista glava
      titulara, ili jedna strana nema OSM `name` (placeholder „Crkva”,
      „Kapela” iz `scripts/01`). Različite glave titulara nikad;
  (c) nisu dalje od `PRAG_M` (20 m), ili do `PRAG_TLOCRT_M` (40 m) kad je W
      čisti tlocrt (bez imena i bez `amenity`) a par je jedini kompatibilni
      i za N i za W (odluka 401);
  (d) nemaju različit `wikidata` tag (odluka 402).

Dodjela je jednoznačna i deterministička: svaki čvor ide najbližem
kompatibilnom wayu (izjednačenje po tipu i OSM id-u); kad isti way dobije više
čvorova, prima ih redom udaljenosti samo dok su međusobno spojivi. Redoslijed
ulaza ne utječe na ishod.

Preživljava way/relation (id, slug, koordinate, `geom_kind`, OSM identitet);
ostala polja su `COALESCE(way, čvor)`, a naziv/titular/kind dolaze s čvora kad
way nema OSM `name`. Identitet čvora ostaje u `church_merged` (odluka 403).

Pravilo se primjenjuje na kraju `scripts/01` (`apply`), PRIJE `05` i 10/11, pa
nijedan kasniji korak ne vidi duplikat. Audit (`src/audit.node_way_duplikati`)
koristi iste predikate nad bazom — zato uloga, „ima ime” i `amenity` žive u
kolonama `osm_role`, `osm_named`, `osm_amenity`.
"""
from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from . import kinds
from .normalize import norm_key
from .titular import head_key

PRAG_M = 20.0
PRAG_TLOCRT_M = 40.0

ULOGE = ("worship", "monastery", "shrine")

# Ručne iznimke, ključ (čvor, way) kao „n123”/„w456”/„r789”. Pravilo ih ne
# smije presuditi samo: NE_SPAJAJ su parovi koje bi krivo spojilo, SPOJI
# parovi koje krivo propušta. Svaki unos nosi razlog i izvor.
NE_SPAJAJ: dict[tuple[str, str], str] = {}
SPOJI: dict[tuple[str, str], str] = {
    # Čvor poklonca 0,3 m od središta tlocrta bezimene kapelice: točka je
    # unutar zgrade, pa je to ista kapelica tagirana kao `wayside_shrine`.
    ("n8676599438", "w1363262030"):
        "„kapelica Presveto Srce Isusovo” (wayside_shrine) u središtu tlocrta kapele, 0,3 m",
    # Bezimeni poklonac 0,6 m od središta „kapelice Uzvišenja Svetog Križa”.
    ("n13686533091", "w172136809"):
        "bezimeni poklonac u središtu tlocrta kapelice Uzvišenja Sv. Križa, 0,6 m",
    # Isti svetac, drukčije napisan (dijalekt, talijanski, tipfeler): glave
    # titulara se razlikuju pa ih pravilo (b) ne smije spojiti samo.
    ("n435090883", "w836489117"): "„Sv. Salvatore” = „Sv. Salvadur” (Cres), 1 m",
    ("n7728666449", "w737821027"): "„Sv. Petar” = „S. Pietro” (Stanić), 2 m",
    ("n847093760", "w366081978"): "„Sv. Križ” = „Sv. Kris” (Brseč), 3 m, ista župa",
    ("n7068953500", "w1138406286"): "„Sv. Pelegrin” = „Sv. Peegrin” (Kali), 7 m, ista župa",
    ("n1500273085", "w1188433578"):
        "„Grabrovica, Sv. Marija” = „Crkva Materinstvo Majke Božje”, 0 m",
}
# Ručni spoj u kojem je naziv čvora bolji od naziva waya (tipfeler, dijalekt
# ili talijanski na wayu); naziv waya tada ide u alias.
NAZIV_S_CVORA: set[str] = {"n7728666449", "n847093760", "n7068953500"}

# Parovi koji ostaju nespojeni NAMJERNO iako im se nazivi slažu i uloga je
# ista — redom 20–40 m, bez dokaza da su ista zgrada (OSM ingest ima samo
# središte tlocrta, ne poligon, pa „točka u tlocrtu” nije provjerljiva).
# Audit ih ispisuje u `namjerno_ostavljeni`, a ne u `value`.
# Mjerenja: docs/research/2026-11-20-s4-dedup.md.
OSTAVLJENI: dict[tuple[str, str], str] = {
    ("n12033838975", "w163600381"):
        "neodlučivo: bezimeni čvor 27 m od imenovane crkve sv. Ane (way ima amenity)",
    ("n1334853569", "w748844250"):
        "neodlučivo: „Sv. Petra” 32 m od „Crkva Sv. Petra” (way ima amenity)",
    ("n7984557860", "w856330473"):
        "neodlučivo: „Sv.Mihovil” 36 m od bezimenog waya s amenity",
    ("n12524980285", "w363439179"):
        "neodlučivo: bezimeni čvor 38 m od crkve sv. Ivana Krstitelja",
    ("n12433613079", "w1228836695"):
        "neodlučivo: dva „Presvetog Spasitelja” na 38 m, oba s amenity",
    ("n1790617199", "w232240918"):
        "vjerojatno dvije zgrade: kapela ↔ crkva Uznesenja na 39 m, različite župe",
    ("n4846513158", "w654467191"):
        "vjerojatno dvije zgrade: kapelica ↔ crkva sv. Lovre na 40 m",
}


def uloga(tags: dict) -> str:
    """Uloga građevine iz OSM tagova (pravilo (a))."""
    if tags.get("amenity") == "monastery" or tags.get("building") == "monastery":
        return "monastery"
    if tags.get("historic") == "wayside_shrine":
        return "shrine"
    return "worship"


def ima_ime(tags: dict) -> bool:
    """Ima li element vlastiti naziv; bez njega `scripts/01` upiše placeholder."""
    return bool(tags.get("name") or tags.get("official_name") or tags.get("alt_name"))


@dataclass(frozen=True)
class Zapis:
    osm_type: str
    osm_id: int
    lat: float
    lng: float
    name: str
    named: bool
    role: str
    amenity: str | None = None
    wikidata: str | None = None

    @property
    def key(self) -> str:
        return f"{self.osm_type[0]}{self.osm_id}"

    @property
    def cisti_tlocrt(self) -> bool:
        return self.osm_type != "node" and not self.named and not self.amenity


def _sort_key(z: Zapis) -> tuple[str, int]:
    return (z.osm_type, z.osm_id)


def nazivi_spojivi(a: Zapis, b: Zapis) -> str | None:
    """'bez_imena' | 'isti_naziv' | 'ista_glava', ili None (pravilo (b))."""
    if not a.named or not b.named:
        return "bez_imena"
    ha, hb = head_key(a.name), head_key(b.name)
    if ha and hb and ha != hb:
        return None
    na = norm_key(a.name)
    if na and na == norm_key(b.name):
        return "isti_naziv"
    if ha and ha == hb:
        return "ista_glava"
    return None


def wikidata_razlicit(a: Zapis, b: Zapis) -> bool:
    return bool(a.wikidata and b.wikidata and a.wikidata != b.wikidata)


def zapreka(node: Zapis, way: Zapis) -> str | None:
    """Zašto par NIJE ista zgrada bez obzira na udaljenost, ili None."""
    if node.role != way.role:
        return "uloga"
    if wikidata_razlicit(node, way):
        return "wikidata"
    if nazivi_spojivi(node, way) is None:
        return "nazivi"
    return None


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Ćelija ~55 × 55 m: par na ≤ 40 m je uvijek u istoj ili susjednoj ćeliji.
_CELL_LAT = 0.0005
_CELL_LNG = 0.0007


def parovi(zapisi: Iterable[Zapis], max_m: float) -> Iterator[tuple[float, Zapis, Zapis]]:
    """Svi parovi (udaljenost, čvor, way/relation) na ≤ max_m, sortirano."""
    zapisi = sorted(zapisi, key=_sort_key)
    grid: dict[tuple[int, int], list[Zapis]] = defaultdict(list)
    for z in zapisi:
        if z.osm_type != "node":
            grid[(math.floor(z.lat / _CELL_LAT), math.floor(z.lng / _CELL_LNG))].append(z)
    out = []
    for n in zapisi:
        if n.osm_type != "node":
            continue
        ci, cj = math.floor(n.lat / _CELL_LAT), math.floor(n.lng / _CELL_LNG)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for w in grid.get((ci + di, cj + dj), ()):
                    d = haversine_m(n.lat, n.lng, w.lat, w.lng)
                    if d <= max_m:
                        out.append((d, n, w))
    out.sort(key=lambda p: (p[1].osm_id, p[0], _sort_key(p[2])))
    yield from out


@dataclass(frozen=True)
class Spoj:
    node: Zapis
    way: Zapis
    distance_m: float
    razlog: str     # nazivi ('isti_naziv' | 'ista_glava' | 'bez_imena') [+ '+tlocrt'] | 'rucno'


def plan(zapisi: Iterable[Zapis], prag_m: float = PRAG_M,
         prag_tlocrt_m: float = PRAG_TLOCRT_M,
         ne_spajaj: dict | None = None, spoji: dict | None = None) -> list[Spoj]:
    """Koji čvor se spaja u koji way/relation. Čista funkcija, bez baze."""
    ne_spajaj = NE_SPAJAJ if ne_spajaj is None else ne_spajaj
    spoji = SPOJI if spoji is None else spoji
    zapisi = list(zapisi)

    komp: list[tuple[float, Zapis, Zapis]] = []
    rucno: list[tuple[float, Zapis, Zapis]] = []
    for d, n, w in parovi(zapisi, max(prag_m, prag_tlocrt_m)):
        k = (n.key, w.key)
        if k in spoji:
            rucno.append((d, n, w))
        elif k not in ne_spajaj and zapreka(n, w) is None:
            komp.append((d, n, w))
    # Ručno spajanje vrijedi i iznad praga.
    if spoji:
        po_kljucu = {z.key: z for z in zapisi}
        vec = {(n.key, w.key) for _, n, w in rucno}
        for (nk, wk) in sorted(spoji):
            if (nk, wk) not in vec and nk in po_kljucu and wk in po_kljucu:
                n, w = po_kljucu[nk], po_kljucu[wk]
                rucno.append((haversine_m(n.lat, n.lng, w.lat, w.lng), n, w))

    # Koliko kompatibilnih kandidata ima svaka strana unutar šireg praga.
    po_cvoru, po_wayu = defaultdict(int), defaultdict(int)
    for _, n, w in komp:
        po_cvoru[n.key] += 1
        po_wayu[w.key] += 1

    def dopusten(d: float, n: Zapis, w: Zapis) -> str | None:
        if d <= prag_m:
            return ""
        if (d <= prag_tlocrt_m and w.cisti_tlocrt
                and po_cvoru[n.key] == 1 and po_wayu[w.key] == 1):
            return "+tlocrt"
        return None

    # Čvor → najbliži dopušteni way.
    izbor: dict[str, tuple[float, Zapis, Zapis, str]] = {}
    for d, n, w in rucno:
        izbor[n.key] = (d, n, w, "rucno")
    for d, n, w in sorted(komp, key=lambda p: (p[0], _sort_key(p[1]), _sort_key(p[2]))):
        if n.key in izbor:
            continue
        dod = dopusten(d, n, w)
        if dod is None:
            continue
        izbor[n.key] = (d, n, w, nazivi_spojivi(n, w) + dod)

    # Way prima čvorove redom udaljenosti dok su međusobno spojivi.
    po_w: dict[str, list] = defaultdict(list)
    for v in izbor.values():
        po_w[v[2].key].append(v)
    spojevi: list[Spoj] = []
    for wk in sorted(po_w):
        prihvaceni: list[Zapis] = []
        for d, n, w, razlog in sorted(po_w[wk], key=lambda v: (v[0], _sort_key(v[1]))):
            if razlog != "rucno" and any(
                    nazivi_spojivi(n, p) is None or wikidata_razlicit(n, p)
                    for p in prihvaceni):
                continue
            prihvaceni.append(n)
            spojevi.append(Spoj(n, w, d, razlog))
    spojevi.sort(key=lambda s: (_sort_key(s.way), _sort_key(s.node)))
    return spojevi


# ---------------------------------------------------------------------------
# Baza
# ---------------------------------------------------------------------------

_ZAPISI_SQL = """
SELECT osm_type, osm_id, lat, lng, name, osm_named, osm_role, osm_amenity, wikidata_id
FROM churches
WHERE osm_type IS NOT NULL AND lat IS NOT NULL AND lng IS NOT NULL
"""


def zapisi_iz_baze(conn: sqlite3.Connection) -> list[Zapis]:
    """OSM zapisi iz baze. `osm_named` NULL (zapis koji nije upisao `01`) znači
    „ima ime”: placeholder je samo ono za što to `01` izričito kaže."""
    return [
        Zapis(r["osm_type"], r["osm_id"], r["lat"], r["lng"], r["name"],
              r["osm_named"] != 0, r["osm_role"] or "worship",
              r["osm_amenity"], r["wikidata_id"])
        for r in conn.execute(_ZAPISI_SQL).fetchall()
    ]


# Polja koja se NE uzimaju s čvora: identitet i geometrija waya, i ono što se
# računa posebno (naziv, izvor, dedup kolone).
_ZADRZI = {"id", "slug", "lat", "lng", "geom_kind", "osm_type", "osm_id",
           "created_at", "updated_at", "source", "name", "titular", "kind",
           "osm_named", "osm_role", "osm_amenity"}


def _row(conn: sqlite3.Connection, z: Zapis) -> sqlite3.Row:
    return conn.execute("SELECT * FROM churches WHERE osm_type = ? AND osm_id = ?",
                        (z.osm_type, z.osm_id)).fetchone()


def _merge_source(a: str | None, b: str | None) -> str | None:
    out: list[str] = []
    for s in (a, b):
        try:
            for x in json.loads(s) if s else []:
                if x not in out:
                    out.append(x)
        except (json.JSONDecodeError, TypeError):
            pass
    return json.dumps(out, ensure_ascii=False) if out else (a or b)


def _kind(n: sqlite3.Row, w: sqlite3.Row) -> str | None:
    """Kind preživjelog zapisa (odluka 400). Tlocrtov `building=chapel|church`
    je bolji dokaz od čvorova `amenity` bez `building`, pa kind ostaje wayev,
    osim (1) kad ga je izveo NAZIV čvora („Kapela sv. Ivana Nepomuka” na
    bezimenom `building=church`) i uloge su iste, ili (2) wayev je `ostalo`
    (bezimeni `amenity` bez religije), a čvor zna više."""
    if not w["kind"] or w["kind"] == "ostalo":
        return n["kind"] or w["kind"]
    if (not w["osm_named"] and n["osm_named"] and n["osm_role"] == w["osm_role"]
            and kinds.classify({}, n["name"]) != "ostalo"):
        return n["kind"]
    return w["kind"]


def apply(conn: sqlite3.Connection) -> list[Spoj]:
    """Spoji duplikate u bazi: čvor u way, identitet čvora u `church_merged`."""
    spojevi = plan(zapisi_iz_baze(conn))
    for s in spojevi:
        n, w = _row(conn, s.node), _row(conn, s.way)
        upd = {k: (w[k] if w[k] is not None else n[k])
               for k in w.keys() if k not in _ZADRZI}
        if (not w["osm_named"] and n["osm_named"]) or s.node.key in NAZIV_S_CVORA:
            upd.update(name=n["name"], titular=n["titular"], osm_named=1)
        upd["kind"] = _kind(n, w)
        upd["source"] = _merge_source(w["source"], n["source"])
        cols = ", ".join(f"{k} = ?" for k in upd)
        conn.execute(f"UPDATE churches SET {cols} WHERE id = ?", [*upd.values(), w["id"]])
        ime = upd.get("name", w["name"])

        conn.execute(
            "INSERT OR IGNORE INTO church_aliases (church_id, alias, source) "
            "SELECT ?, alias, source FROM church_aliases WHERE church_id = ?",
            (w["id"], n["id"]))
        for r in (n, w):
            if r["osm_named"] and r["name"] != ime:
                conn.execute(
                    "INSERT OR IGNORE INTO church_aliases (church_id, alias, source) "
                    "VALUES (?, ?, 'osm-dedup')", (w["id"], r["name"]))
        conn.execute(
            "INSERT INTO church_merged (church_id, osm_type, osm_id, slug, name, razlog, distance_m) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(osm_type, osm_id) DO UPDATE SET church_id = excluded.church_id, "
            "slug = excluded.slug, name = excluded.name, razlog = excluded.razlog, "
            "distance_m = excluded.distance_m",
            (w["id"], n["osm_type"], n["osm_id"], n["slug"], n["name"], s.razlog,
             round(s.distance_m, 1)))
        conn.execute("DELETE FROM churches WHERE id = ?", (n["id"],))
    # Čvor koji je opet samostalan (pravilo ga više ne spaja) nije alias.
    conn.execute(
        "DELETE FROM church_merged WHERE EXISTS (SELECT 1 FROM churches c "
        "WHERE c.osm_type = church_merged.osm_type AND c.osm_id = church_merged.osm_id)")
    return spojevi
