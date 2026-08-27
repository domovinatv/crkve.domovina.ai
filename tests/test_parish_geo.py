"""Homonim naselja je tiha greška: geokoder vrati koordinatu, ništa ne pukne,
a sloj biskupija se prefarba (Barbat s Paga sjeo je na Rab i obojao ga
zadarskim). Testovi fiksiraju pravila zbog kojih se korekcija smije pustiti
blizu podataka: dvije razine naziva, prag za izvod županija, i to da se
ispravna koordinata NE dira.
"""
from __future__ import annotations

import pytest

from src import parish_geo as pg


def square(x: float, y: float, size: float = 1.0) -> list:
    return [[[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]]]


def s(name: str, jls: str, county: str, x: float, y: float,
      size: float = 1.0) -> pg.Settlement:
    return pg.Settlement(name, jls, county, y + size / 2, x + size / 2,
                         [square(x, y, size)])


@pytest.fixture
def fake_index(monkeypatch):
    """Zamijeni DGU indeks s pregledom od šačice naselja."""
    def install(items: list[pg.Settlement]):
        by_name: dict[str, list[pg.Settlement]] = {}
        for it in items:
            by_name.setdefault(pg._norm(it.name), []).append(it)
        monkeypatch.setattr(pg, "_index", lambda: (by_name, list(items)))
    return install


class Row(dict):
    """`sqlite3.Row` se ponaša kao mapiranje — dict je dovoljan dubler."""


def test_afiksni_kandidati_se_ne_mijesaju_s_tocnima(fake_index):
    fake_index([
        s("Vrh", "Krk", "Primorsko-goranska", 14, 45),
        s("Vrh", "Buzet", "Istarska", 13, 45),
        s("Kraljev Vrh", "Jakovlje", "Zagrebačka", 15, 45),
    ])
    exact, affix = pg.candidates("Vrh")
    assert {e.jls for e in exact} == {"Krk", "Buzet"}
    assert [a.jls for a in affix] == ["Jakovlje"]


def test_skraceni_naziv_iz_evidencije_nalazi_puni(fake_index):
    fake_index([
        s("Dicmo Kraj", "Dicmo", "Splitsko-dalmatinska", 16, 43),
        s("Kraj", "Pašman", "Zadarska", 15, 43),
    ])
    exact, affix = pg.candidates("Kraj")
    assert [e.jls for e in exact] == ["Pašman"]
    assert [a.jls for a in affix] == ["Dicmo"]


def test_podniz_se_ne_broji(fake_index):
    """„Vid" ne smije povući „Sveti Vid" — inače bi svako kratko ime kuhalo."""
    fake_index([s("Sveti Vid-Miholjice", "Malinska-Dubašnica",
                  "Primorsko-goranska", 14, 45)])
    exact, affix = pg.candidates("Vid")
    assert exact == [] and affix == []


def test_jedna_zupa_otvara_zupaniju(fake_index):
    """Riječka u Istarskoj ima točno jednu župu (Vodice, Lanišće) i to je istina.

    S pragom 2 je ta jedina župa ostajala nepokrivena, pa ju je korekcija
    htjela odseliti 58 km u istoimeno naselje u Primorsko-goranskoj.
    """
    fake_index([s("Vodice", "Lanišće", "Istarska", 13, 45)])
    rows = [Row(registry_id="702173", diocese="Riječka Nadbiskupija",
                city="Vodice", lat=45.5, lng=13.5)]
    assert pg.settled_counties(rows) == {"Riječka Nadbiskupija": {"Istarska"}}


def test_override_se_broji_na_odrediste_a_ne_na_trenutnu_tocku(monkeypatch, fake_index):
    """Inače izvod ovisi o tome je li korekcija već pokrenuta.

    Bujska Krasica se prvi run broji u Istarsku, a drugi (nakon što ju je
    override odselio u Bakar) više ne — pa se između runova mijenja skup
    dozvoljenih županija i s njim odluke o SVIM ostalim župama.
    """
    fake_index([s("Krasica", "Buje", "Istarska", 13, 45),
                s("Krasica", "Bakar", "Primorsko-goranska", 14, 45)])
    monkeypatch.setitem(pg.OVERRIDES, "702103",
                        ("Krasica", "Bakar", "x" * 40))
    rows = [Row(registry_id="702103", diocese="D", city="Krasica",
                lat=45.5, lng=13.5)]           # točka je još u bujskoj Krasici
    assert pg.settled_counties(rows) == {"D": {"Primorsko-goranska"}}


def test_tocka_u_ispravnoj_zupaniji_se_ne_dira(monkeypatch, fake_index):
    """Župni ured par km izvan naselja je normalan — nije razlog za pomicanje."""
    fake_index([s("Šibenik", "Šibenik", "Šibensko-kninska", 15, 43)])
    monkeypatch.setattr(pg.geo_hr, "locate",
                        lambda la, ln: pg.geo_hr.Place(None, None, "Šibensko-kninska"))
    row = Row(registry_id="1", diocese="D", city="Šibenik", lat=43.9, lng=15.9)
    assert pg.resolve(row, {"D": {"Šibensko-kninska"}}) is None


def test_biskupija_razrjesava_homonim(monkeypatch, fake_index):
    fake_index([
        s("Vrana", "Cres", "Primorsko-goranska", 14, 44),
        s("Vrana", "Pakoštane", "Zadarska", 15, 43),
    ])
    monkeypatch.setattr(pg.geo_hr, "locate",
                        lambda la, ln: pg.geo_hr.Place(None, None, "Zadarska"))
    row = Row(registry_id="1", diocese="Biskupija Krk", city="Vrana",
              lat=43.5, lng=15.5)
    fix = pg.resolve(row, {"Biskupija Krk": {"Primorsko-goranska"}})
    assert fix and fix.target.jls == "Cres"


def test_dvosmislen_ostatak_se_ne_pomice(monkeypatch, fake_index):
    """Dva kandidata u dozvoljenoj županiji — bolje ništa nego nagađanje."""
    fake_index([
        s("Zagorje", "Ogulin", "Karlovačka", 15, 45),
        s("Zagorje", "Krnjak", "Karlovačka", 15.5, 45.5),
    ])
    monkeypatch.setattr(pg.geo_hr, "locate",
                        lambda la, ln: pg.geo_hr.Place(None, None, "Krapinsko-zagorska"))
    row = Row(registry_id="nema-override", diocese="D", city="Zagorje",
              lat=46.1, lng=15.9)
    assert pg.resolve(row, {"D": {"Karlovačka"}}) is None


def test_svaki_override_ima_izvor():
    for rid, (name, jls, source) in pg.OVERRIDES.items():
        assert rid.isdigit(), rid
        assert name and jls
        assert len(source) > 30, f"{rid}: override bez obrazloženja"


def test_reprezentativna_tocka_je_uvijek_unutra():
    """„U"-oblik: težište pada u zaljev, a prijašnji fallback na prvi vrh
    poligona ležao je NA granici, gdje `_in_ring` vraća False. Zbog toga je
    84 od 6759 naselja imalo točku koja u njemu nije, pa je override za
    Sveti Vid-Miholjice na svakom runu iznova javljao „premjesti"."""
    u = [[[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3], [0, 0]]]
    lat, lng = pg.representative_point([u])
    assert pg._point_in_poly(u, lat, lng)


def test_reprezentativna_tocka_ne_pada_u_rupu():
    prsten = [
        [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
        [[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]],
    ]
    lat, lng = pg.representative_point([prsten])
    assert pg._point_in_poly(prsten, lat, lng)


def test_daleko_od_svih_kandidata_brise_koordinatu(fake_index):
    """Grkokatolička župa u Prgomelju sjela je u Dubrovnik, 314 km od oba
    Prgomelja. Odredište se ne zna (dva su), ali točka sigurno nije dokaz —
    a Križevačku eparhiju izvod županija ne pokriva, pa je ovo jedini filtar
    koji je uopće pogleda."""
    fake_index([
        s("Prgomelje", "Pakrac", "Požeško-slavonska", 17, 45),
        s("Prgomelje", "Bjelovar", "Bjelovarsko-bilogorska", 16, 45),
    ])
    row = Row(registry_id="701807", diocese="Križevačka Eparhija",
              city="Prgomelje", lat=42.65, lng=18.09)
    out = pg.resolve(row, {})
    assert isinstance(out, pg.Drop)
    assert "314" in out.reason or "km" in out.reason


def test_daleko_od_jedinog_kandidata_premjesta(fake_index):
    fake_index([s("Prgomelje", "Bjelovar", "Bjelovarsko-bilogorska", 16, 45)])
    row = Row(registry_id="nema-override", diocese="D", city="Prgomelje",
              lat=42.65, lng=18.09)
    out = pg.resolve(row, {})
    assert isinstance(out, pg.Fix) and out.target.jls == "Bjelovar"


def test_sjediste_izvan_imenovanog_naselja_ali_blizu_se_ne_dira(monkeypatch, fake_index):
    """Žirje je u evidenciji upisano na „Šibenik" i leži 22 km od grada.
    Prag mora ostati iznad toga — inače korekcija otok vuče na kopno."""
    fake_index([s("Šibenik", "Šibenik", "Šibensko-kninska", 15.85, 43.7, size=0.1)])
    monkeypatch.setattr(pg.geo_hr, "locate",
                        lambda la, ln: pg.geo_hr.Place(None, None, "Šibensko-kninska"))
    row = Row(registry_id="701996", diocese="Šibenska Biskupija", city="Šibenik",
              lat=43.66, lng=15.66)
    assert pg.km(43.66, 15.66, 43.75, 15.90) < pg.MAX_SJEDISTE_KM
    assert pg.resolve(row, {"Šibenska Biskupija": {"Šibensko-kninska"}}) is None
