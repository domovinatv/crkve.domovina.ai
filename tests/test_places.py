"""Places sloj — validacija rezultata i dijagnostika grešaka.

Places je jedini izvor koji košta i jedini koji može tiho podmetnuti krivi
objekt: Text Search UVIJEK nešto vrati, pa bez filtra u katalog uđu kafići i
trgovine iz istog mjesta. Sve se testira bez ijednog mrežnog poziva.
"""
from __future__ import annotations

import pytest

from src.places import _explain_403, haversine_m, in_hr, pick, queries_for


def test_in_hr_bbox_accepts_croatia():
    assert in_hr(45.8144, 15.9794)          # Zagreb
    assert in_hr(42.65, 18.09)              # Dubrovnik
    assert in_hr(46.48, 16.36)              # Čakovec


def test_in_hr_bbox_rejects_far_away():
    assert not in_hr(48.21, 16.37)          # Beč
    assert not in_hr(41.90, 12.50)          # Rim
    assert not in_hr(44.43, 26.10)          # Bukurešt


def test_in_hr_bbox_is_coarse_by_design():
    """Pravokutnik oko HR neizbježno obuhvaća Ljubljanu i Sarajevo.

    Zato bbox NIJE jedina obrana: `pick()` dodatno traži da se točka poklopi
    sa županijom iz DGU granica (point-in-polygon), što je pravi filtar —
    vidi test_pick_rejects_wrong_county.
    """
    assert in_hr(46.05, 14.51)              # Ljubljana — unutar pravokutnika
    assert in_hr(43.86, 18.41)              # Sarajevo — isto


def test_haversine_known_distance():
    # Zagrebačka katedrala → crkva sv. Marka: ~500 m zračne linije.
    assert 350 < haversine_m(45.8144, 15.9794, 45.8167, 15.9739) < 700


def test_haversine_zero():
    assert haversine_m(45.0, 16.0, 45.0, 16.0) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize(
    "body,needle",
    [
        ('{"error":{"message":"The provided API key has an IP address restriction"}}',
         "IP restrikciju"),
        ('{"error":{"message":"requests from referer are blocked"}}', "referrer"),
        ('{"error":{"message":"Places API (New) has not been used in project"}}',
         "nije uključen"),
        ('{"error":{"message":"something else"}}', "nema dozvole"),
    ],
)
def test_explain_403_names_the_actual_fix(body, needle):
    # 403 ima tri uzroka i tri različita rješenja — poruka mora reći KOJI je.
    assert needle in _explain_403(body)


# --- queries_for ------------------------------------------------------------

def test_queries_go_from_specific_to_general():
    qs = queries_for("ŽUPA SV. JURJA", "Lovran", "Trg sv. Jurja 1")
    assert len(qs) == 3
    assert qs[0] == "Župa sv. Jurja, Trg sv. Jurja 1, Lovran"
    assert qs[1] == "Župa sv. Jurja, Lovran"
    # Bez riječi "Župa" — Google češće zna crkvu nego župni ured.
    assert qs[2] == "Crkva sv. Jurja, Lovran"


def test_queries_without_address():
    qs = queries_for("ŽUPA SV. ANE", "Osijek", None)
    assert all("None" not in q for q in qs)
    assert qs[0] == "Župa sv. Ane, Osijek"


def test_no_queries_without_city():
    # Bez mjesta upit ne bi bio ograničen ni na što korisno.
    assert queries_for("ŽUPA SV. ANE", None, None) == []


# --- pick -------------------------------------------------------------------

ZG = (45.8144, 15.9794)


def _res(name, latlng=ZG, sacral=True):
    return {"name": name, "lat": latlng[0], "lng": latlng[1], "is_sacral": sacral}


def test_pick_accepts_sacral_result():
    hit = pick([_res("Crkva sv. Marka")], "ŽUPA SV. MARKA, ZAGREB", "Grad Zagreb")
    assert hit is not None and hit["name"] == "Crkva sv. Marka"


def test_pick_rejects_non_sacral_unrelated_name():
    # Klasičan promašaj Text Searcha: lokal koji nosi ime sveca.
    assert pick([_res("Konoba Sveti Marko", sacral=False)],
                "ŽUPA SV. MARKA, ZAGREB", "Grad Zagreb") is None


def test_pick_accepts_non_sacral_when_name_matches_strongly():
    # Google zna ne otagirati crkvu kao place_of_worship — tada presuđuje naziv.
    hit = pick([_res("Župa sv. Marka Evanđelista", sacral=False)],
               "ŽUPA SV. MARKA EVANĐELISTA", "Grad Zagreb")
    assert hit is not None


def test_pick_rejects_wrong_county():
    # Istoimeno mjesto u drugoj županiji — Places zna odlutati.
    split = (43.5081, 16.4402)
    assert pick([_res("Crkva sv. Marka", latlng=split)],
                "ŽUPA SV. MARKA", "Grad Zagreb") is None


def test_pick_takes_first_acceptable_not_first_result():
    hits = [_res("Pizzeria Sv. Marko", sacral=False), _res("Crkva sv. Marka")]
    assert pick(hits, "ŽUPA SV. MARKA", "Grad Zagreb")["name"] == "Crkva sv. Marka"


def test_pick_without_county_skips_location_check():
    # Ako župa nema županiju, prostorni filtar se ne smije primijeniti.
    assert pick([_res("Crkva sv. Marka")], "ŽUPA SV. MARKA", None) is not None
