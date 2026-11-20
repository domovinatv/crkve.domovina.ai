"""Ispravci krivih OSM tagova, primijenjeni u ingestu (`scripts/01`).

Ispravak ide u pipeline, ne u bazu (odluka 2): baza se gradi od nule, pa bi
ručni UPDATE nestao na idućem rebuildu. Svaki unos nosi izvor i datum
provjere. Kad se tag ispravi u samom OSM-u, unos postaje no-op (vrijednost je
već ta) i smije se obrisati.

Vrijednost `None` briše tag.
"""
from __future__ import annotations

TAG_FIXES: dict[tuple[str, int], dict[str, str | None]] = {
    # Kapela sv. Terezije od Djeteta Isusa u Trnju (Sesvete) nosi `wikidata` i
    # `wikipedia` župne crkve Svih Svetih (way 459564717). Wikidata, provjereno
    # 2026-11-20: Q132087369 = „Župna crkva Svih Svetih u Zagrebu” (P31 crkvena
    # građevina, 45.8275, 16.11); kapela je Q132079947 „Pastoralni centar
    # bl. Alojzija Stepinca s kapelom sv. Terezije od Djeteta Isusa u Trnju”
    # (45.828056, 16.109722; 27 m od čvora), iz keša scripts/05. Posljedica
    # krivog taga: dvije građevine s istim Q (audit `wikidata_dijeljen`), a
    # Q132079947 je prostornim spajanjem pao na crkvu Svih Svetih i dao joj
    # sliku pastoralnog centra (odluka 308).
    ("node", 13304771994): {"wikidata": "Q132079947", "wikipedia": None},
}


def apply(osm_type: str, osm_id: int, tags: dict) -> dict:
    """Tagovi elementa s primijenjenim ispravcima (nova kopija, ulaz netaknut)."""
    fix = TAG_FIXES.get((osm_type, osm_id))
    if not fix:
        return tags
    out = dict(tags)
    for k, v in fix.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = v
    return out
