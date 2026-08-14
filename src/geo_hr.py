"""Točka → naselje + JLS (općina/grad) + županija, point-in-polygon nad DGU granicama.

Ne dohvaća ništa s mreže i nema shapely — koristi kanonske GeoJSON granice
koje već postoje u sestrinskom repozitoriju `../karta-hrvatske`
(`apps/karta-web/public/data/`). To je isti podatkovni sloj koji crta karta na
gis.domovina.ai, pa su naselja i županije u katalogu i na karti po definiciji
identične.

Primarni sloj je **naselja** (6759 poligona; svaki nosi `name`, `jls_name`,
`zupanija`), a `jls` je fallback za točke izvan naselja (šume, otočići, more
uz obalu). Naselje je bitno jer je to granularnost na kojoj rade svi ostali
izvori: državna evidencija piše sjedište župe kao "Prizna, Prizna bb", a
Registar kulturnih dobara ima "Mjesto_smjestaja". Bez naselja se matching
oslanja na općinu i propada u ruralnim krajevima gdje jedna općina ima
dvadesetak sela s vlastitim crkvama.

Zašto ovako a ne preko OSM `addr:*` tagova: samo dio crkava ima adresu, a
`addr:city` je nekonzistentan. Koordinate ima 100% OSM zapisa, pa prostorna
dodjela pokriva sve.

Put se može pregaziti s KARTA_DATA_DIR; ako granice nisu dostupne, funkcije
vraćaju prazan rezultat i pipeline nastavlja bez lokacijskih atributa.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KARTA_DATA = ROOT.parent / "karta-hrvatske" / "apps" / "karta-web" / "public" / "data"

# Veličina ćelije grid indeksa u stupnjevima (~11 km). Dovoljno sitno da
# prosječna ćelija ima nekoliko poligona, dovoljno krupno da indeks stane u
# memoriju bez fragmentacije.
_CELL = 0.1


class Place(NamedTuple):
    settlement: str | None
    municipality: str | None
    county: str | None


EMPTY = Place(None, None, None)


def _data_dir() -> Path:
    return Path(os.environ.get("KARTA_DATA_DIR", str(DEFAULT_KARTA_DATA)))


def _polygons(geom: dict) -> list:
    t = geom.get("type")
    if t == "Polygon":
        return [geom.get("coordinates") or []]
    if t == "MultiPolygon":
        return list(geom.get("coordinates") or [])
    return []


def _load(filename: str) -> tuple[list, dict[tuple[int, int], list[int]]]:
    """Vrati (features, grid) gdje je feature (bbox, polygons, props)."""
    path = _data_dir() / filename
    if not path.exists():
        logger.warning(
            "Granice nisu nađene (%s). Naselja/županije ostaju prazne. "
            "Kloniraj ../karta-hrvatske ili postavi KARTA_DATA_DIR.", path
        )
        return [], {}

    fc = json.loads(path.read_text())
    feats: list = []
    grid: dict[tuple[int, int], list[int]] = {}
    for f in fc.get("features", []):
        polys = _polygons(f.get("geometry") or {})
        if not polys:
            continue
        xs = [c[0] for p in polys for ring in p for c in ring]
        ys = [c[1] for p in polys for ring in p for c in ring]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        idx = len(feats)
        feats.append((bbox, polys, f.get("properties") or {}))
        for gx in range(int(bbox[0] / _CELL), int(bbox[2] / _CELL) + 1):
            for gy in range(int(bbox[1] / _CELL), int(bbox[3] / _CELL) + 1):
                grid.setdefault((gx, gy), []).append(idx)
    logger.info("%s: %d poligona, %d ćelija indeksa", filename, len(feats), len(grid))
    return feats, grid


@lru_cache(maxsize=1)
def _naselja():
    return _load("naselja.geojson")


@lru_cache(maxsize=1)
def _jls():
    return _load("jls.geojson")


def _point_in_ring(lng: float, lat: float, ring: list) -> bool:
    """Ray casting. Ring je [[lng, lat], …]."""
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
    """Prvi ring je vanjski, ostali su rupe."""
    if not poly or not _point_in_ring(lng, lat, poly[0]):
        return False
    return not any(_point_in_ring(lng, lat, hole) for hole in poly[1:])


def _hit(layer, lat: float, lng: float) -> dict | None:
    feats, grid = layer
    for idx in grid.get((int(lng / _CELL), int(lat / _CELL)), []):
        bbox, polys, props = feats[idx]
        if not (bbox[0] <= lng <= bbox[2] and bbox[1] <= lat <= bbox[3]):
            continue
        if any(_point_in_polygon(lng, lat, p) for p in polys):
            return props
    return None


def locate(lat: float | None, lng: float | None) -> Place:
    """(naselje, općina/grad, županija) za točku."""
    if lat is None or lng is None:
        return EMPTY

    props = _hit(_naselja(), lat, lng)
    if props:
        return Place(props.get("name"), props.get("jls_name"), props.get("zupanija"))

    # Izvan naselja (šuma, otočić, priobalje) — barem JLS i županija.
    props = _hit(_jls(), lat, lng)
    if props:
        return Place(None, props.get("name"), props.get("zupanija"))
    return EMPTY


def _area_centroid(ring: list) -> tuple[float, float]:
    """Težišnica poligona (shoelace). Vraća (lng, lat)."""
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


@lru_cache(maxsize=1)
def _settlement_points() -> dict[str, list[tuple[float, float, str, str]]]:
    """Normalizirano ime naselja → [(lat, lng, puno ime, županija)].

    Ime nije jedinstveno (u HR postoji više „Brezovica"), pa je vrijednost
    lista — pozivatelj odlučuje što s višeznačnošću.
    """
    feats, _ = _naselja()
    out: dict[str, list[tuple[float, float, str, str]]] = {}
    for _bbox, polys, props in feats:
        # Najveći poligon (otok + kopneni dio nekog naselja) nosi težište.
        biggest = max(polys, key=lambda p: len(p[0]) if p else 0)
        lng, lat = _area_centroid(biggest[0])
        # Težište konkavnog oblika zna ispasti izvan njega — tada uzmi vrh na
        # rubu, koji je i dalje "u naselju" za potrebe prikaza sjedišta župe.
        if not _point_in_polygon(lng, lat, biggest):
            lng, lat = biggest[0][0][0], biggest[0][0][1]
        name = props.get("name") or ""
        key = _norm_place(name)
        if key:
            out.setdefault(key, []).append((lat, lng, name, props.get("zupanija")))
    return out


def _norm_place(s: str) -> str:
    import unicodedata

    s = s.translate(str.maketrans({"đ": "d", "Đ": "D"}))
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in s.lower())
    return " ".join(s.split())


def settlement_centroid(
    name: str | None, county: str | None = None
) -> tuple[float, float] | None:
    """Težište naselja po imenu, ili None ako nema ili je višeznačno.

    Ovo je offline zamjena za Nominatim kod sjedišta župa: točnost je razina
    naselja (ne kućnog broja), ali je instant, bez rate limita i bez ovisnosti
    o vanjskom servisu. Za većinu župa sjedište ionako nije precizno zapisano.
    Ako ime nosi više naselja, `county` razrješava; bez njega — ništa.
    """
    if not name:
        return None
    hits = _settlement_points().get(_norm_place(name))
    if not hits:
        return None
    if len(hits) > 1 and county:
        want = _norm_place(county)
        hits = [h for h in hits if _norm_place(h[3] or "") == want] or hits
    if len(hits) != 1:
        return None
    return hits[0][0], hits[0][1]


COUNTIES: list[str] = [
    "Zagrebačka", "Krapinsko-zagorska", "Sisačko-moslavačka", "Karlovačka",
    "Varaždinska", "Koprivničko-križevačka", "Bjelovarsko-bilogorska",
    "Primorsko-goranska", "Ličko-senjska", "Virovitičko-podravska",
    "Požeško-slavonska", "Brodsko-posavska", "Zadarska", "Osječko-baranjska",
    "Šibensko-kninska", "Vukovarsko-srijemska", "Splitsko-dalmatinska",
    "Istarska", "Dubrovačko-neretvanska", "Međimurska", "Grad Zagreb",
]
