"""Matching je najrizičniji dio pipelinea: lažni match tiho pripiše krivoj
crkvi tuđu zaštitu ili župu i to se ne vidi u brojkama. Testovi fiksiraju
tri pravila koja to sprječavaju: blokiranje po mjestu, tvrdi filtar titulara,
i odbijanje dvosmislenih pobjednika.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.match import best_match, build_index, place_key, weak_claim


def row(id_: int, name: str, city: str | None = None,
        settlement: str | None = None, municipality: str | None = None):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT ? AS id, ? AS name, ? AS city, ? AS settlement, ? AS municipality",
        (id_, name, city, settlement, municipality),
    ).fetchone()


@pytest.fixture
def index():
    return build_index([
        row(1, "Crkva sv. Jurja", city="Lovran"),
        row(2, "Crkva sv. Jurja", city="Petrinja"),
        row(3, "Crkva sv. Petra", city="Lovran"),
        row(4, "Crkva Uznesenja Blažene Djevice Marije", city="Zagreb"),
    ])


def test_matches_within_same_place(index):
    hit = best_match(index, "Župna crkva sv. Jurja", place_key("Lovran"))
    assert hit is not None
    assert hit[0].id == 1


def test_same_name_different_place_does_not_match(index):
    # Bez ovoga bi "Crkva sv. Jurja" iz Lovrana pokupila petrinjsku zaštitu.
    assert best_match(index, "Crkva sv. Jurja", place_key("Rijeka")) is None


def test_different_titular_same_place_rejected(index):
    # Petar vs Juraj u istom mjestu — tekstualno slično, stvarno različito.
    hit = best_match(index, "Crkva sv. Pavla", place_key("Lovran"))
    assert hit is None


def test_registry_uppercase_genitive_matches(index):
    hit = best_match(index, "ŽUPA UZNESENJA BLAŽENE DJEVICE MARIJE, ZAGREB",
                     place_key("Zagreb"))
    assert hit is not None and hit[0].id == 4


def test_ambiguous_candidates_return_none():
    # Dvije jednako dobre crkve u istom mjestu → radije ništa nego pogodak.
    idx = build_index([
        row(1, "Crkva sv. Ane", city="Osijek"),
        row(2, "Crkva sv. Ane", city="Osijek"),
    ])
    assert best_match(idx, "Crkva sv. Ane", place_key("Osijek")) is None


def test_narrow_tier_wins_over_wide_one():
    """Naselje mora presuditi prije nego općina razvodni kandidate.

    Općina Vrgorac ima crkvu sv. Ante u više sela; da se blokovi miješaju,
    margina nikad ne bi dala pobjednika i ispravan pogodak bi propao.
    """
    idx = build_index([
        row(1, "Crkva sv. Ante", settlement="Dragljane", municipality="Vrgorac"),
        row(2, "Crkva sv. Ante", settlement="Kljenak", municipality="Vrgorac"),
        row(3, "Crkva sv. Ante", settlement="Stilja", municipality="Vrgorac"),
    ])
    hit = best_match(idx, "Crkva sv. Ante Padovanskog",
                     place_key("Dragljane"), place_key("Vrgorac"))
    assert hit is not None and hit[0].id == 1


def test_wide_tier_used_when_narrow_is_empty():
    idx = build_index([row(1, "Crkva sv. Roka", settlement="Selce",
                           municipality="Crikvenica")])
    # Naselje iz izvora ne postoji u katalogu → padni na općinu.
    hit = best_match(idx, "Crkva sv. Roka", place_key("Nepostojeće"),
                     place_key("Crikvenica"))
    assert hit is not None and hit[0].id == 1


def test_epithet_does_not_block_match():
    # Bez head_key filtra ovo bi bio tvrdi reject i match rate bi pao ~11 pp.
    idx = build_index([row(1, "Crkva sv. Ante", settlement="Dragljane")])
    assert best_match(idx, "Crkva sv. Ante Padovanskog", place_key("Dragljane"))


def test_unique_titular_and_kind_matches_despite_different_names():
    """Nazivi se potpuno raziđu, ali titular + tip + jedinstvenost presuđuju.

    Registar kulturnih dobara zove zagrebačku katedralu "Kompleks Katedrale
    Uznesenja Marijina", OSM "katedrala Uznesenja Blažene Djevice Marije i
    svetih Stjepana i Ladislava" — token_set_ratio 54, duboko ispod praga.
    """
    idx = build_index([
        row(1, "katedrala Uznesenja Blažene Djevice Marije i svetih Stjepana i Ladislava",
            settlement="Zagreb"),
        row(2, "crkva sv. Marka", settlement="Zagreb"),
    ])
    hit = best_match(idx, "Kompleks Katedrale Uznesenja Marijina", place_key("Zagreb"))
    assert hit is not None and hit[0].id == 1


def test_generic_marian_titular_does_not_trigger_uniqueness():
    """"Gospa od Utjehe" i "Gospa od Batka" dijele titular "Majka Božja" —
    catch-all koji je koristan za prikaz, ali bi ovdje spojio dvije različite
    crkve u istom mjestu. Pet takvih lažnih spojeva je i nastalo prije
    GENERIC_TITULARS."""
    idx = build_index([row(1, "Crkva Gospe od Batka", settlement="Pučišća")])
    assert best_match(idx, "Crkva Blažene Gospe od Utjehe na groblju",
                      place_key("Pučišća")) is None


def test_uniqueness_needs_exactly_one_candidate():
    idx = build_index([
        row(1, "crkva Uznesenja Marijina", settlement="Sali"),
        row(2, "crkva Uznesenja Blažene Djevice Marije", settlement="Sali"),
    ])
    # Dvije crkve istog titulara i tipa u istom mjestu → nema jedinstvenosti.
    assert best_match(idx, "Kompleks crkve Uznesenja", place_key("Sali")) is None


def test_place_key_normalises_grad_prefix():
    assert "zagreb" in place_key("Grad Zagreb")
    assert place_key("ĐAKOVO") == place_key("Đakovo")


def test_empty_inputs_are_safe(index):
    assert best_match(index, "", place_key("Lovran")) is None
    assert best_match(index, "Crkva sv. Jurja", set()) is None


def test_weak_claim_trsat_ide_prije_sv_nikole():
    # Rijeka, 2026-11-20: OSM „Franjevački samostan" (Trsat, r3560310) nema
    # titular, pa je podniz obje pravne osobe i obje daju score 100. Kad je
    # pravilo konfesije maknulo pravoslavnu sv. Nikolu (koja je rušila
    # marginu), samostan s Ivekovićeve 8 uzeo je trsatsku zgradu jer mu je
    # id manji. Slab zahtjev mora doći na red zadnji.
    idx = build_index([row(1, "Franjevački samostan", city="Rijeka")])
    nikola = "FRANJEVAČKI SAMOSTAN SV. NIKOLE"
    trsat = "FRANJEVAČKI SAMOSTAN RIJEKA - TRSAT"
    hits = {n: best_match(idx, n, {"rijeka"}) for n in (nikola, trsat)}
    assert all(h is not None and h[0].id == 1 and h[1] == 100 for h in hits.values())
    assert weak_claim(nikola, hits[nikola][0])
    assert not weak_claim(trsat, hits[trsat][0])
    assert sorted([nikola, trsat], key=lambda n: weak_claim(n, hits[n][0])) == [trsat, nikola]


def test_weak_claim_ne_dira_poklapanje_titulara(index):
    cand, _ = best_match(index, "ŽUPA SV. JURJA", {"lovran"})
    assert not weak_claim("ŽUPA SV. JURJA", cand)
    # Ni pravna osoba bez sveca nije slab zahtjev.
    assert not weak_claim("FRANJEVAČKI SAMOSTAN RIJEKA - TRSAT", cand)


# --- marijanski zaziv (S4, odluka 405) --------------------------------------
# Blok općine Čabar iz baze (Z-834 „Majke Božje Svetogorske", naselje Gerovo).
_CABAR = [
    (11, "Crkva Majka Božja Snježna", "Gerovo"),
    (12, "crkva svetih Hermagora i Fortunata", "Gerovo"),
    (13, "Kapela Blažene Djevice Marije", "Čabar"),
    (14, "crkva Majke Božje od Sedam Žalosti", "Kozji Vrh"),
    (15, "Svetište Majke Božje Svetogorske", "Mali Lug"),
    (16, "Kapela Majka Božja Pomoćnica", "Plešce"),
]
_Z834 = ("Kompleks crkve Blažene Djevice Marije “Majke Božje Svetogorske” s pripadajućim "
         "građevinama, ruševnim građevinama, sajmištem, te pašnjakom i šumom")


def _cabar_index():
    return build_index([row(i, n, settlement=s, municipality="Čabar") for i, n, s in _CABAR])


def test_isti_zaziv_pobjeduje_golu_bdm():
    # Svetište i gola „Kapela BDM" oba daju token_set 100; isti zaziv odlučuje.
    hit = best_match(_cabar_index(), _Z834, place_key("Gerovo"), place_key("ČABAR"))
    assert hit and hit[0].id == 15 and hit[1] == 100


def test_gola_bdm_ostaje_spojiva_sa_zazivom():
    idx = build_index([row(1, "crkva Gospe od Planice", settlement="Komiža")])
    hit = best_match(idx, "Crkva BDM (Gospe od Planice)", place_key("Komiža"))
    assert hit and hit[0].id == 1                     # Z-5695


def test_razliciti_zazivi_ne_spajaju_se():
    # Z-4858 „Gospe od Lužina" (Ston) bila je na „Gospa od Ružarija".
    idx = build_index([row(1, "Gospa od Ružarija", settlement="Tomislavovac",
                           municipality="Ston")])
    assert best_match(idx, "Crkva Gospe od Lužina", place_key("Ston"), place_key("STON")) is None


def test_zaziv_ne_razbija_izjednacenje_s_nemarijanskim():
    # Rijeka: kapucinski samostan (zgrada bez titulara) i crkva Gospe Lurdske
    # oba daju 100 „KAPUCINSKOM SAMOSTANU GOSPE LURDSKE"; ostaje nespojeno kao
    # i prije, inače samostan otme župnu crkvu ŽUPI GOSPE LURDSKE.
    idx = build_index([row(1, "crkva Gospe Lurdske", city="Rijeka"),
                       row(2, "Kapucinski samostan", city="Rijeka")])
    assert best_match(idx, "KAPUCINSKI SAMOSTAN GOSPE LURDSKE RIJEKA", place_key("Rijeka")) is None
    assert best_match(idx, "ŽUPA GOSPE LURDSKE", place_key("Rijeka"))[0].id == 1
