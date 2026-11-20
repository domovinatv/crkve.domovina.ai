"""Spoji župe (pravne osobe) na njihove župne crkve (građevine).

Ovo je veza koja katalog čini korisnim: 1563 župa iz državne evidencije dobiva
`churches.parish_id` + `is_parish_church=1` na svojoj matičnoj crkvi, pa se s
karte može skočiti na pravnu osobu (OIB, biskupija) i obratno.

Dva prolaza:

  1. ADRESA — župa ima sjedište ("Lovran, Trg sv. Jurja 1"). Ako u istom
     mjestu postoji crkva s istim titularom, to je gotovo sigurno župna crkva.
  2. TITULAR + MJESTO — župa "ŽUPA SV. JURJA, LOVRAN" i crkva "Crkva sv.
     Jurja" u Lovranu preko src/match.py (isti prag i margina kao za baštinu).

Nakon spajanja župne crkve, ostale crkve u ISTOM mjestu bez vlastite župe
dobivaju `parish_id` te župe (filijale/kapele), ali BEZ `is_parish_church`.
To je namjerno slabija tvrdnja — mjesto s jednom župom nema drugu nadležnost.

Ime mjesta pritom NIJE dovoljno: u Hrvatskoj postoje dva Lupoglava, tri
Soline, dvije Sesvete. Bez provjere udaljenosti crkve istarskog Lupoglava
završe na zagrebačkoj župi 180 km daleko. Zato: čim župa ima koordinate,
kandidat mora biti unutar `parish_geo.MAX_FILIJALA_KM`.

Konfesija (odluka 4, `match.compatible`) je tvrdi uvjet u oba prolaza.
U 1. prolazu ide PRIJE scoreanja: nekompatibilna građevina ne ulazi u
bazen, pa ne može ni pobijediti ni srušiti marginu ispravnom kandidatu.
U 2. prolazu samo ODBIJA: jedinstvenost se i dalje broji nad svim pravnim
osobama u mjestu. Izmjereno 2026-11-20: filtriranje prije brojanja dodalo
je 190 filijala, među njima sinagoge, džamije i Jehovine svjedoke na
srpskopravoslavne crkvene općine (pravilo štiti samo katoličku granicu), a
to je pitanje spajanja nekatoličkih zajednica, ne ovog pravila.

Redoslijed 1. prolaza: pogodak gdje pravna osoba imenuje sveca, a građevina
nema titular (`match.weak_claim`), dolazi na red zadnji. Bez toga je
„FRANJEVAČKI SAMOSTAN SV. NIKOLE" (Rijeka, Ivekovićeva 8) uzeo trsatski
„Franjevački samostan" prije „FRANJEVAČKOG SAMOSTANA RIJEKA - TRSAT": čim je
pravilo konfesije maknulo pravoslavnu sv. Nikolu iz bazena, podniz
„franjevački samostan" ostao je sam na scoreu 100 (2026-11-20, S2).

  uv run python scripts/11_match_parishes.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import connect  # noqa: E402
from src.match import (  # noqa: E402
    best_match, build_index, compatible, place_key, weak_claim)
from src.parish_geo import MAX_FILIJALA_KM, km  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("match-zupe")

# Vrste pravnih osoba koje uopće mogu imati "svoju" crkvu.
PARISH_KINDS = ("zupa", "svetiste", "samostan", "parohija", "crkvena-opcina", "dzemat")


def _too_far(seat: tuple | None, church: tuple | None) -> bool:
    """Je li crkva izvan dosega te župe? Bez koordinata — nema tvrdnje."""
    if not seat or not church or seat[0] is None or church[0] is None:
        return False
    return km(seat[0], seat[1], church[0], church[1]) > MAX_FILIJALA_KM


def run(dry_run: bool = False) -> None:
    stats = Counter()
    with connect() as conn:
        # Ponovni run mora krenuti od nule, inače stare (i krive) veze prežive
        # jer se `parish_id` samo upisuje, nikad ne briše.
        if not dry_run:
            # `is_parish_church` se vraća na 0, a ne na NULL: shema ima
            # DEFAULT 0, a CSV kolonu ispisuje doslovno — s NULL-om bi 5815
            # građevina u exportu zamijenilo tvrdnju „nije župna" prazninom.
            conn.execute("UPDATE churches SET parish_id = NULL, is_parish_church = 0")

        churches = conn.execute(
            "SELECT id, name, kind, religion, denomination, city, settlement, "
            "municipality, lat, lng FROM churches"
        ).fetchall()
        index = build_index(churches)
        pos = {c["id"]: (c["lat"], c["lng"]) for c in churches}

        placeholders = ", ".join("?" * len(PARISH_KINDS))
        parishes = conn.execute(
            f"SELECT * FROM parishes WHERE kind IN ({placeholders}) "
            "AND (registry_status IS NULL OR registry_status LIKE 'AKTIV%') "
            "AND duplicate_of IS NULL",
            PARISH_KINDS,
        ).fetchall()
        log.info("pravnih osoba za spajanje: %d | građevina: %d",
                 len(parishes), len(churches))

        taken: set[int] = set()
        matched_parish_place: list[tuple[int, set[str]]] = []
        # Sjedište župe se tijekom 1. prolaza može tek doznati (naslijedi ga od
        # svoje crkve), pa se drži u dictu — 2. prolaz treba svježu vrijednost.
        seat: dict[int, tuple] = {p["id"]: (p["lat"], p["lng"]) for p in parishes}

        # Evidencija daje samo mjesto sjedišta — jedna razina. Naziv za
        # usporedbu: "ŽUPA SV. JURJA, LOVRAN"; match.py skida tipski
        # prefiks i mjesto iza zareza sam.
        hits = {
            p["id"]: best_match(index, p["name"], place_key(p["city"]),
                                accept=lambda c, p=p: compatible(c, p))
            for p in parishes
        }
        # Građevinu koju traže dvije pravne osobe dobiva prva na redu. Slabi
        # zahtjevi (`match.weak_claim`: osoba imenuje sveca, građevina nema
        # titular) idu zadnji — sortiranje je stabilno, ostalo ostaje po id-u.
        order = sorted(parishes, key=lambda p: bool(
            hits[p["id"]] and weak_claim(p["name"], hits[p["id"]][0])))

        for p in order:
            places = place_key(p["city"])
            hit = hits[p["id"]]
            if not hit:
                stats["nespojeno"] += 1
                if places:
                    matched_parish_place.append((p["id"], places))
                continue
            cand, score = hit
            if cand.id in taken:
                stats["kandidat_vec_zauzet"] += 1
                continue
            if _too_far(seat.get(p["id"]), pos.get(cand.id)):
                stats["zupna_crkva_predaleko"] += 1
                continue
            taken.add(cand.id)
            stats["zupna_crkva_spojena"] += 1
            if seat.get(p["id"], (None, None))[0] is None:
                seat[p["id"]] = pos.get(cand.id, (None, None))

            if not dry_run:
                conn.execute(
                    "UPDATE churches SET parish_id = ?, is_parish_church = 1, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (p["id"], cand.id),
                )
                # Župa nasljeđuje koordinate svoje crkve — evidencija ih nema.
                conn.execute(
                    "UPDATE parishes SET lat = COALESCE(lat, ?), lng = COALESCE(lng, ?), "
                    "geocode_source = COALESCE(geocode_source, 'church') WHERE id = ?",
                    (
                        conn.execute("SELECT lat FROM churches WHERE id = ?",
                                     (cand.id,)).fetchone()["lat"],
                        conn.execute("SELECT lng FROM churches WHERE id = ?",
                                     (cand.id,)).fetchone()["lng"],
                        p["id"],
                    ),
                )
            matched_parish_place.append((p["id"], places))

        # 2. prolaz: filijale — crkve u mjestu gdje postoji točno JEDNA župa.
        by_place: dict[str, set[int]] = {}
        for pid, places in matched_parish_place:
            for pl in places:
                by_place.setdefault(pl, set()).add(pid)

        parish_by_id = {p["id"]: p for p in parishes}
        for c in churches:
            if c["id"] in taken:
                continue
            cand_parishes: set[int] = set()
            for pl in place_key(c["city"], c["settlement"], c["municipality"]):
                cand_parishes |= by_place.get(pl, set())
            if len(cand_parishes) != 1:
                stats["filijala_dvosmislena" if cand_parishes else "filijala_bez_zupe"] += 1
                continue
            pid = next(iter(cand_parishes))
            if not compatible(c, parish_by_id[pid]):
                stats["filijala_nekompatibilna"] += 1
                continue
            if _too_far(seat.get(pid), (c["lat"], c["lng"])):
                stats["filijala_predaleko"] += 1
                continue
            stats["filijala_spojena"] += 1
            if not dry_run:
                conn.execute(
                    "UPDATE churches SET parish_id = ? WHERE id = ? AND parish_id IS NULL",
                    (pid, c["id"]),
                )

        if not dry_run:
            conn.commit()
        linked = conn.execute(
            "SELECT COUNT(*) FROM churches WHERE parish_id IS NOT NULL"
        ).fetchone()[0]
        parish_churches = conn.execute(
            "SELECT COUNT(*) FROM churches WHERE is_parish_church = 1"
        ).fetchone()[0]
        geo_parishes = conn.execute(
            "SELECT COUNT(*) FROM parishes WHERE lat IS NOT NULL"
        ).fetchone()[0]

    log.info("gotovo%s: %s", " (dry-run)" if dry_run else "", dict(stats))
    log.info("crkava s župom: %d | župnih crkava: %d | župa s koordinatama: %d",
             linked, parish_churches, geo_parishes)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(**vars(ap.parse_args()))
