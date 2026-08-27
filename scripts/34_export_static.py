"""Eksportiraj katalog u statički JSON za vlastiti frontend (crkve.domovina.ai).

Piše u `frontend/public/data/`, odakle ga Worker poslužuje kao asset — bez
baze, bez bindinga, bez ključa. Deploy je onda samo `build + wrangler deploy`.

Dvije jedinice stranice, jer su i u bazi dva različita skupa (vidi CLAUDE.md):

    crkva/<slug>.json      GRAĐEVINA (6966) — koordinate, titular, zaštita, slika
    zupa/<slug>.json       KATOLIČKA ŽUPA (aktivna, nedvostruka)
    ustanova/<slug>.json   ostale mjesne pravne osobe — samostan, crkvena
                           općina, svetište, parohija, džemat

`ustanova/` postoji da URL ne laže: samostan i crkvena općina nisu župe, a
zajedno drže 148 spojenih građevina. Administrativne pravne osobe (biskupija,
eparhija, provincija, caritas, ostalo — 611 zapisa) NEMAJU stranicu: nijedna
nema spojenu građevinu, pa bi stranica bila prazna.

Indeksi (jedan dohvat, pa karta i pretraga rade na klijentu):

    crkve-index.json       slim zapis po građevini (~1 MB, ~250 KB gzip)
    zupe-index.json        slim zapis po pravnoj osobi sa stranicom
    biskupije.json         (nad)biskupije i zajednice s brojkama
    biskupije.geojson      deriviarani teritoriji (poligoni) za kartu
    stats.json             kopija mjere iz `make stats`
    manifest.json          generated_at, brojke, schema_version

TRAŽI PRETHODNI `make stats` — stats.json je jedino mjesto gdje se brojke
poput „487 župa bez župne crkve" računaju (scripts/40). Ovdje se NE računaju
ponovo da se dvije brojke ne bi razišle; umjesto toga se provjerava svježina.

    uv run python scripts/34_export_static.py
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import connect  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("export-static")

OUT_DIR = ROOT / "frontend" / "public" / "data"
STATS_SRC = ROOT / "data" / "exports" / "stats.json"

SCHEMA_VERSION = 1

# Pravne osobe koje dobivaju stranicu, i pod kojim segmentom URL-a.
# Mjereno (2026-08-27): spojene građevine po vrsti — zupa 2780, samostan 109,
# crkvena-opcina 37, svetiste 2; sve ostale vrste 0.
ROUTE_BY_KIND = {
    "zupa": "zupa",
    "samostan": "ustanova",
    "crkvena-opcina": "ustanova",
    "svetiste": "ustanova",
    "parohija": "ustanova",
    "dzemat": "ustanova",
}

# Zastavice kod kojih je 0 isto što i „nema" — izbacuju se da payload ne raste.
# `church_count` NIJE ovdje: nula je nalaz („nema nijedne spojene građevine"),
# a ne odsutan podatak. Isto pravilo kao u scripts/31.
_DROP_IF_ZERO = {"is_parish_church", "geo_verified", "unesco"}


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

CHURCH_SQL = """
SELECT c.id, c.slug, c.name, c.name_official, c.kind, c.religion, c.denomination,
       c.titular, c.address, c.city, c.settlement, c.municipality, c.county,
       c.postal_code, c.lat, c.lng, c.geom_kind,
       c.parish_id, c.is_parish_church,
       c.osm_type, c.osm_id, c.wikidata_id, c.wikipedia_url, c.commons_image,
       c.heritage_id, c.heritage_status, c.heritage_class, c.heritage_desc,
       c.unesco, c.year_built, c.architect, c.style,
       c.phone, c.email, c.website,
       c.geo_verified, c.geo_verify_m, c.source,
       p.slug AS parish_slug, p.name AS parish_name, p.short_name AS parish_short_name,
       p.kind AS parish_kind, p.diocese AS diocese
FROM churches c
LEFT JOIN parishes p ON p.id = c.parish_id
ORDER BY c.id
"""

# Aktivne i nedvostruke pravne osobe. `registry_status` dolazi u dva roda
# (AKTIVAN za katoličke, AKTIVNA za ostale evidencije) — otud LIKE.
PARISH_SQL = """
SELECT p.id, p.slug, p.name, p.short_name, p.kind, p.religion, p.denomination,
       p.titular, p.oib, p.diocese, p.community,
       p.address, p.city, p.county, p.lat, p.lng, p.geocode_source,
       p.registry_no, p.registry_id, p.registry_status, p.registered_at,
       p.leader_title, p.phone, p.email, p.website, p.google_maps_uri, p.source
FROM parishes p
WHERE p.duplicate_of IS NULL
  AND (p.registry_status IS NULL OR p.registry_status LIKE 'AKTIV%')
ORDER BY p.name
"""

# Građevine grupirane po pravnoj osobi — jedan upit umjesto 2368 podupita.
PARISH_CHURCHES_SQL = """
SELECT c.parish_id, c.slug, c.name, c.kind, c.city, c.lat, c.lng,
       c.is_parish_church, c.heritage_id, c.commons_image
FROM churches c
WHERE c.parish_id IS NOT NULL
ORDER BY c.is_parish_church DESC, c.name
"""

DIOCESE_SQL = """
SELECT d.id, d.slug, d.name, d.kind, d.religion, d.denomination, d.oib, d.seat,
       d.parish_count,
       a.geometry, a.area_km2, a.population, a.settlement_count,
       a.parish_count AS area_parish_count, a.church_count AS area_church_count,
       a.method, a.osm_agreement
FROM dioceses d
LEFT JOIN diocese_areas a ON a.diocese_id = d.id
ORDER BY d.name
"""


# ---------------------------------------------------------------------------
# Helperi
# ---------------------------------------------------------------------------

def _clean(row, drop=()) -> dict:
    """Row → dict bez praznih polja i bez nula koje znače „nema"."""
    out = {}
    for k in row.keys():
        if k in drop:
            continue
        v = row[k]
        if v is None or v == "":
            continue
        if k in _DROP_IF_ZERO and not v:
            continue
        if k == "source" and isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                pass
        out[k] = v
    return out


def _write(path: Path, payload) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(body, encoding="utf-8")
    return len(body.encode("utf-8"))


def _purge_stale(dirname: str, keep: set[str]) -> int:
    """Obriši per-slug datoteke kojih više nema u bazi.

    Bez ovoga preimenovan ili obrisan slug ostavlja živu stranicu iza sebe:
    datoteka je i dalje u assetima, Worker je i dalje poslužuje, a nitko je ne
    linka — pa se ne primijeti. Export mora biti odraz baze, ne njezina unija
    kroz vrijeme.
    """
    d = OUT_DIR / dirname
    if not d.exists():
        return 0
    removed = 0
    for f in d.glob("*.json"):
        if f.stem not in keep:
            f.unlink()
            removed += 1
    return removed


def _wrap(items: list) -> dict:
    """Indeks nosi svoju brojku — potrošač ne mora brojati polje da bi je znao."""
    return {"count": len(items), "items": items}


def _load_stats() -> dict:
    """Mjera iz scripts/40. Odbija se ako je zastarjela — brojke na webu bi
    inače tiho tvrdile stanje neke ranije verzije baze."""
    if not STATS_SRC.exists():
        raise SystemExit(
            f"{STATS_SRC} ne postoji — pokreni `make stats` prije ovog koraka."
        )
    return json.loads(STATS_SRC.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_churches(conn, parish_route: dict[int, tuple[str, str]]) -> tuple[list[dict], int]:
    """Per-slug detalji + slim indeks. Vraća (indeks, broj zapisanih datoteka)."""
    rows = conn.execute(CHURCH_SQL).fetchall()

    # Sestrinske građevine iste župe — jedan prolaz, pa lookup.
    by_parish: dict[int, list[dict]] = {}
    for r in conn.execute(PARISH_CHURCHES_SQL):
        by_parish.setdefault(r["parish_id"], []).append({
            "slug": r["slug"], "name": r["name"], "kind": r["kind"],
            **({"is_parish_church": 1} if r["is_parish_church"] else {}),
        })

    index: list[dict] = []
    written = 0
    for r in rows:
        d = _clean(r, drop=("parish_id", "parish_slug", "parish_name",
                            "parish_short_name", "parish_kind", "diocese"))
        pid = r["parish_id"]
        if pid and r["parish_slug"]:
            route, _ = parish_route.get(pid, ("", ""))
            d["parish"] = {
                "slug": r["parish_slug"],
                "name": r["parish_name"],
                **({"short_name": r["parish_short_name"]} if r["parish_short_name"] else {}),
                "kind": r["parish_kind"],
                **({"diocese": r["diocese"]} if r["diocese"] else {}),
                # prazan route = pravna osoba nema stranicu (administrativna,
                # ugašena ili duplikat) — frontend tada ne linka, samo ispiše
                **({"route": route} if route else {}),
            }
            siblings = [s for s in by_parish.get(pid, []) if s["slug"] != r["slug"]]
            if siblings:
                d["siblings"] = siblings

        _write(OUT_DIR / "crkva" / f"{r['slug']}.json", d)
        written += 1

        item = {
            "slug": r["slug"], "name": r["name"], "kind": r["kind"],
            "lat": round(r["lat"], 6), "lng": round(r["lng"], 6),
        }
        for key in ("titular", "city", "county", "denomination"):
            if r[key]:
                item[key] = r[key]
        if r["heritage_id"]:
            item["heritage"] = 1
        if r["commons_image"]:
            item["image"] = 1
        if r["parish_slug"]:
            item["parish_slug"] = r["parish_slug"]
        if r["is_parish_church"]:
            item["is_parish_church"] = 1
        index.append(item)

    stale = _purge_stale("crkva", {r["slug"] for r in rows})
    if stale:
        log.info("crkva/: obrisano %d zaostalih datoteka", stale)

    return index, written


def export_parishes(conn) -> tuple[list[dict], dict[int, tuple[str, str]], int]:
    """Per-slug detalji za pravne osobe sa stranicom + slim indeks."""
    rows = conn.execute(PARISH_SQL).fetchall()

    by_parish: dict[int, list[dict]] = {}
    for r in conn.execute(PARISH_CHURCHES_SQL):
        entry = {"slug": r["slug"], "name": r["name"], "kind": r["kind"]}
        for key in ("city", "heritage_id"):
            if r[key]:
                entry[key] = r[key]
        if r["lat"] is not None:
            entry["lat"], entry["lng"] = round(r["lat"], 6), round(r["lng"], 6)
        if r["is_parish_church"]:
            entry["is_parish_church"] = 1
        if r["commons_image"]:
            entry["image"] = 1
        by_parish.setdefault(r["parish_id"], []).append(entry)

    routes: dict[int, tuple[str, str]] = {}
    index: list[dict] = []
    written = 0
    for r in rows:
        route = ROUTE_BY_KIND.get(r["kind"] or "")
        if not route:
            continue
        routes[r["id"]] = (route, r["slug"])

        churches = by_parish.get(r["id"], [])
        d = _clean(r, drop=("id",))
        d["route"] = route
        d["churches"] = churches
        # Nula se ZADRŽAVA: „nema nijedne spojene građevine" je nalaz, i jedini
        # način da se rupa u podacima vidi na stranici (421 župa, mjereno).
        d["church_count"] = len(churches)
        d["has_parish_church"] = 1 if any(c.get("is_parish_church") for c in churches) else 0

        _write(OUT_DIR / route / f"{r['slug']}.json", d)
        written += 1

        item = {
            "slug": r["slug"], "name": r["name"], "kind": r["kind"], "route": route,
            "church_count": d["church_count"], "has_parish_church": d["has_parish_church"],
        }
        for key in ("short_name", "titular", "city", "county", "diocese", "community"):
            if r[key]:
                item[key] = r[key]
        if r["lat"] is not None:
            item["lat"], item["lng"] = round(r["lat"], 6), round(r["lng"], 6)
        index.append(item)

    # Pravne osobe BEZ stranice i dalje trebaju biti u routes mapi kao prazne,
    # da export crkava zna da za njih nema linka (a ne da ga izmisli).
    for r in rows:
        routes.setdefault(r["id"], ("", r["slug"]))

    for seg in set(ROUTE_BY_KIND.values()):
        stale = _purge_stale(seg, {i["slug"] for i in index if i["route"] == seg})
        if stale:
            log.info("%s/: obrisano %d zaostalih datoteka", seg, stale)

    return index, routes, written


def export_dioceses(conn, parish_index: list[dict]) -> tuple[list[dict], dict, int]:
    rows = conn.execute(DIOCESE_SQL).fetchall()

    by_diocese: dict[str, list[dict]] = {}
    for item in parish_index:
        d = item.get("diocese")
        if d:
            by_diocese.setdefault(d, []).append(item)

    index: list[dict] = []
    features: list[dict] = []
    written = 0
    for r in rows:
        parishes = by_diocese.get(r["name"], [])
        detail = _clean(r, drop=("id", "geometry"))
        detail["parishes"] = parishes
        detail["listed_parish_count"] = len(parishes)
        _write(OUT_DIR / "biskupija" / f"{r['slug']}.json", detail)
        written += 1

        item = {k: v for k, v in detail.items() if k != "parishes"}
        item["has_area"] = 1 if r["geometry"] else 0
        index.append(item)

        if r["geometry"]:
            props = {k: v for k, v in detail.items() if k != "parishes"}
            features.append({
                "type": "Feature",
                "id": r["id"],
                "geometry": json.loads(r["geometry"]),
                "properties": props,
            })

    stale = _purge_stale("biskupija", {r["slug"] for r in rows})
    if stale:
        log.info("biskupija/: obrisano %d zaostalih datoteka", stale)

    return index, {"type": "FeatureCollection", "features": features}, written


def run() -> None:
    stats = _load_stats()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        live_churches = conn.execute("SELECT COUNT(*) FROM churches").fetchone()[0]
        if stats.get("crkve_ukupno") != live_churches:
            raise SystemExit(
                f"stats.json je zastario ({stats.get('crkve_ukupno')} crkava) naspram "
                f"baze ({live_churches}) — pokreni `make stats` pa ponovo ovo."
            )

        parish_index, routes, n_parishes = export_parishes(conn)
        church_index, n_churches = export_churches(conn, routes)
        diocese_index, diocese_fc, n_dioceses = export_dioceses(conn, parish_index)

    sizes = {
        "crkve-index.json": _write(OUT_DIR / "crkve-index.json", _wrap(church_index)),
        "zupe-index.json": _write(OUT_DIR / "zupe-index.json", _wrap(parish_index)),
        "biskupije.json": _write(OUT_DIR / "biskupije.json", _wrap(diocese_index)),
        "biskupije.geojson": _write(OUT_DIR / "biskupije.geojson", diocese_fc),
        "stats.json": _write(OUT_DIR / "stats.json", stats),
    }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": {
            "crkve": len(church_index),
            "pravne_osobe_sa_stranicom": len(parish_index),
            "zupe": sum(1 for p in parish_index if p["route"] == "zupa"),
            "ustanove": sum(1 for p in parish_index if p["route"] == "ustanova"),
            "biskupije": len(diocese_index),
            "biskupije_s_teritorijem": len(diocese_fc["features"]),
        },
    }
    sizes["manifest.json"] = _write(OUT_DIR / "manifest.json", manifest)

    total_files = n_churches + n_parishes + n_dioceses + len(sizes)
    log.info("crkva/: %d datoteka", n_churches)
    log.info("zupa/ + ustanova/: %d datoteka (%d župa, %d ustanova)",
             n_parishes, manifest["counts"]["zupe"], manifest["counts"]["ustanove"])
    log.info("biskupija/: %d datoteka (%d s teritorijem)",
             n_dioceses, manifest["counts"]["biskupije_s_teritorijem"])
    for name, size in sizes.items():
        log.info("%-20s %6.1f KB", name, size / 1024)
    log.info("ukupno %d datoteka u %s", total_files, OUT_DIR.relative_to(ROOT))


if __name__ == "__main__":
    run()
