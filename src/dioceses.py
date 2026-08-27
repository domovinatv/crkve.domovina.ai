"""Derivacija teritorija (nad)biskupija iz sjedišta župa.

**Zašto derivacija, a ne izvor.** Granice hrvatskih biskupija ne postoje kao
javno dostupna geometrija. Provjereno uživo (2026-08-16):

  * OSM ima **3 od 15** (`boundary=religious_administration`): Đakovačko-osječku,
    Požešku i Bjelovarsko-križevačku (+ Đakovačko-osječku metropoliju).
  * Wikidata **nijednu** — `P3896` (geoshape) je prazan za svih 10 hrvatskih
    dijeceza koje uopće ima, a `P402` (OSM relation) također.

Te 3 OSM relacije zato NISU izvor nego **mjera točnosti** — `agreement()` i
`iou()` uspoređuju našu derivaciju s njima. Ista logika kao kod Places
validacije: sidro provjere ne smije biti ono što provjeravamo.

**Metoda.** Svako naselje (DGU, 6759 poligona) pripadne biskupiji župa koje u
njemu sjede; naselje bez župe pripadne biskupiji najbliže župe. Naselja iste
biskupije se spoje u jedan poligon. Granica time ide po stvarnim granicama
naselja — agregirana, ali administrativna linija, a ne Voronoi šiljak.

**Što NIJE u particiji** (i zašto — sve troje bi tiho pokvarilo kartu):

  * **Križevačka eparhija** (grkokatolička) — teritorij joj se *preklapa* sa
    svim latinskim biskupijama, a njezinih 35 župa je razasuto po zemlji. U
    particiji bi otela teritorij susjedima oko svake svoje župe.
  * **Srpska pravoslavna crkva** — državna evidencija svih 403 crkvene općine
    vodi pod jednim imenom, bez podatka o eparhiji. Nema se iz čega derivirati.
  * **Vojni ordinarijat** — neteritorijalan po definiciji.

Modul (a ne skripta) jer se `scripts/20_…` ne može importati u testove — ime
modula ne smije počinjati brojkom. Ista pouka kao `src/places.py`.
"""
from __future__ import annotations

import json
import logging
import math
from typing import Any, Iterable, NamedTuple

from shapely.geometry import MultiPolygon, shape
from shapely.ops import polygonize, unary_union

logger = logging.getLogger(__name__)

# Grkokatolička eparhija — preklapa se s latinskim biskupijama, ne particionira.
OVERLAPPING_SLUGS = {"krizevacka-eparhija"}

# Tolerancija pojednostavljenja u stupnjevima. Na 45°N je 0,0008° ≈ 65 m —
# ispod razlučivosti na kojoj se granica biskupije uopće gleda, a datoteku
# smanji za red veličine.
SIMPLIFY_DEG = 0.0008

_CELL = 0.1


class Parish(NamedTuple):
    id: int
    name: str
    diocese: str
    lat: float
    lng: float


class Settlement(NamedTuple):
    """Naselje spremno za dodjelu: težište + poligoni + statistika."""
    idx: int
    name: str
    lat: float
    lng: float
    population: int
    area_km2: float
    polygons: list
    jls: str = ""
    county: str = ""


# ── geometrija bez shapelyja (dodjela) ────────────────────────────────────────

def _ring_centroid(ring: list) -> tuple[float, float]:
    """Težište poligona (shoelace). Vraća (lng, lat)."""
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
    """Apsolutna shoelace površina u kvadratnim stupnjevima (za „najveći ring")."""
    a = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2


def _point_in_ring(lng: float, lat: float, ring: list) -> bool:
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


def _point_in_polygon(lng: float, lat: float, poly: list) -> bool:
    if not poly or not _point_in_ring(lng, lat, poly[0]):
        return False
    return not any(_point_in_ring(lng, lat, hole) for hole in poly[1:])


def _dist2(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Kvadrat udaljenosti, ekvirektangularno (dovoljno za „koja je bliža")."""
    dy = lat1 - lat2
    dx = (lng1 - lng2) * math.cos(math.radians((lat1 + lat2) / 2))
    return dy * dy + dx * dx


# ── dodjela naselja biskupiji ─────────────────────────────────────────────────

def settlements(feats: Iterable) -> list[Settlement]:
    """`geo_hr.naselja_features()` → lista naselja s težištem i statistikom."""
    out: list[Settlement] = []
    for idx, (_bbox, polys, props) in enumerate(feats):
        biggest = max((p[0] for p in polys if p), key=_ring_area, default=None)
        if not biggest:
            continue
        lng, lat = _ring_centroid(biggest)
        out.append(Settlement(
            idx=idx,
            name=props.get("name") or "",
            lat=lat,
            lng=lng,
            population=int(props.get("stanovnistvo") or 0),
            area_km2=float(props.get("area_km2") or 0.0),
            polygons=polys,
            jls=props.get("jls_name") or "",
            county=props.get("zupanija") or "",
        ))
    return out


def _grid(items: list[Settlement]) -> dict[tuple[int, int], list[int]]:
    g: dict[tuple[int, int], list[int]] = {}
    for i, s in enumerate(items):
        xs = [c[0] for p in s.polygons for ring in p for c in ring]
        ys = [c[1] for p in s.polygons for ring in p for c in ring]
        for gx in range(int(min(xs) / _CELL), int(max(xs) / _CELL) + 1):
            for gy in range(int(min(ys) / _CELL), int(max(ys) / _CELL) + 1):
                g.setdefault((gx, gy), []).append(i)
    return g


class Assignment(NamedTuple):
    by_settlement: dict[int, str]     # index u `settlements` → naziv biskupije
    direct: int                       # naselja u kojima župa doista sjedi
    nearest: int                      # naselja dodijeljena najbližoj župi
    mixed: int                        # naselja s župama dviju biskupija


def assign(sett: list[Settlement], parishes: list[Parish]) -> Assignment:
    """Dodijeli svako naselje jednoj biskupiji.

    Dvije razine, namjerno tim redom: župa koja *sjedi* u naselju je dokaz,
    a najbliža župa je tek procjena. Naselje u kojem sjede župe dviju
    biskupija dobiva onu s više župa (izmjereno: takvih je šačica, sve su
    velika naselja na granici).

    „Najbliža" se pritom traži u koncentričnim krugovima — prvo unutar iste
    općine/grada, pa iste županije, pa tek onda bilo gdje. Zračna udaljenost
    ne zna za more: Metajna na Pagu nema župu, a najbliža joj je preko
    Velebitskog kanala u Gospićko-senjskoj, iako je cijeli otok podijeljen
    između Krčke i Zadarske. Upravna granica je jeftin, ali dobar surogat za
    „ista strana vode".
    """
    grid = _grid(sett)
    counts: dict[int, dict[str, int]] = {}
    seat_of: dict[int, int] = {}          # indeks župe → indeks naselja u kojem sjedi

    for pi, p in enumerate(parishes):
        for i in grid.get((int(p.lng / _CELL), int(p.lat / _CELL)), []):
            if any(_point_in_polygon(p.lng, p.lat, poly) for poly in sett[i].polygons):
                counts.setdefault(i, {})
                counts[i][p.diocese] = counts[i].get(p.diocese, 0) + 1
                seat_of[pi] = i
                break

    by: dict[int, str] = {}
    mixed = 0
    for i, c in counts.items():
        if len(c) > 1:
            mixed += 1
        by[i] = max(c.items(), key=lambda kv: (kv[1], kv[0]))[0]

    direct = len(by)
    in_jls: dict[str, list[int]] = {}
    in_county: dict[str, list[int]] = {}
    for pi in range(len(parishes)):
        si = seat_of.get(pi)
        if si is None:
            continue
        in_jls.setdefault(sett[si].jls, []).append(pi)
        in_county.setdefault(sett[si].county, []).append(pi)

    everyone = list(range(len(parishes)))
    for i, s in enumerate(sett):
        if i in by:
            continue
        pool = in_jls.get(s.jls) or in_county.get(s.county) or everyone
        best = min(pool, key=lambda pi: _dist2(s.lat, s.lng,
                                               parishes[pi].lat, parishes[pi].lng))
        by[i] = parishes[best].diocese

    return Assignment(by, direct, len(by) - direct, mixed)


# ── spajanje u teritorij ──────────────────────────────────────────────────────

def _geom(polys: list):
    g = MultiPolygon([(p[0], p[1:]) for p in polys if p])
    return g if g.is_valid else g.buffer(0)


def dissolve(sett: list[Settlement], assignment: Assignment) -> dict[str, Any]:
    """Naziv biskupije → shapely geometrija njezina teritorija."""
    groups: dict[str, list] = {}
    for i, diocese in assignment.by_settlement.items():
        groups.setdefault(diocese, []).append(_geom(sett[i].polygons))

    out: dict[str, Any] = {}
    for diocese, geoms in groups.items():
        merged = unary_union(geoms)
        out[diocese] = merged.simplify(SIMPLIFY_DEG, preserve_topology=True)
    return out


def area_km2(geom) -> float:
    """Površina iz kvadratnih stupnjeva u km², ekvirektangularno oko težišta."""
    lat = geom.centroid.y
    return geom.area * (111.32 ** 2) * math.cos(math.radians(lat))


# ── validacija nad OSM granicama ──────────────────────────────────────────────

def osm_boundaries(elements: list[dict]) -> dict[str, Any]:
    """Overpass `out geom` relacije → naziv → shapely poligon.

    Članovi relacije su nesloženi wayevi; `polygonize` ih spaja u prstenove.
    Uzimaju se samo `outer` (i članovi bez uloge, koje OSM tolerira).
    """
    out: dict[str, Any] = {}
    for el in elements:
        if el.get("type") != "relation":
            continue
        name = (el.get("tags") or {}).get("name")
        lines = [
            [(pt["lon"], pt["lat"]) for pt in m.get("geometry") or []]
            for m in el.get("members") or []
            if m.get("type") == "way" and m.get("role") in ("outer", "", None)
        ]
        polys = list(polygonize([ln for ln in lines if len(ln) > 1]))
        if not polys or not name:
            continue
        out[name] = unary_union(polys)
    return out


def agreement(
    sett: list[Settlement],
    assignment: Assignment,
    osm_geom,
    diocese: str,
) -> tuple[int, int]:
    """(pogođenih, ukupno) naselja čije težište leži unutar OSM granice.

    Mjera koja ne ovisi o shapelyjevoj aritmetici površina: pita „bi li ovo
    naselje po nama pripalo istoj biskupiji kao po OSM-u".
    """
    minx, miny, maxx, maxy = osm_geom.bounds
    hit = total = 0
    for i, s in enumerate(sett):
        if not (minx <= s.lng <= maxx and miny <= s.lat <= maxy):
            continue
        if not osm_geom.contains(shape({"type": "Point", "coordinates": [s.lng, s.lat]})):
            continue
        total += 1
        if assignment.by_settlement.get(i) == diocese:
            hit += 1
    return hit, total


def iou(a, b) -> float:
    """Intersection over union. Omjer je invarijantan na skaliranje osi,
    pa ga stupnjevi ne kvare."""
    u = a.union(b).area
    return (a.intersection(b).area / u) if u else 0.0


def to_geojson_geometry(geom) -> str:
    """Shapely → kompaktan GeoJSON string (6 decimala ≈ 10 cm)."""
    def rnd(obj):
        if isinstance(obj, (list, tuple)):
            if obj and isinstance(obj[0], (int, float)):
                return [round(float(obj[0]), 6), round(float(obj[1]), 6)]
            return [rnd(o) for o in obj]
        return obj

    g = geom.__geo_interface__
    return json.dumps({"type": g["type"], "coordinates": rnd(g["coordinates"])},
                      separators=(",", ":"))
