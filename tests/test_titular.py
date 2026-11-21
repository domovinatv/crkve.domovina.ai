"""Titular je ključ po kojem se spajaju izvori — ako parser padne, matching
tiho degradira u "sve ili ništa". Zato je pokriven primjerima iz sva tri
izvora (OSM nominativ, registar genitiv u verzalu, MinKulture opisni naziv).
"""
from __future__ import annotations

import pytest

from src.titular import head_key, key, parse


@pytest.mark.parametrize(
    "name,expected",
    [
        # OSM stil
        ("Crkva sv. Marka", "sv. Marko"),
        ("Crkva svetog Jurja", "sv. Juraj"),
        ("Kapela sv. Ane", "sv. Ana"),
        ("Crkva sv. Ivana Krstitelja", "sv. Ivan Krstitelj"),
        # Državna evidencija (verzal, genitiv, mjesto iza zareza)
        ("ŽUPA SV. MARKA EVANĐELISTA, ZAGREB", "sv. Marko Evanđelist"),
        ("ŽUPA SV. NIKOLE BISKUPA, VARAŽDIN", "sv. Nikola Biskup"),
        # Otajstva — ne razlažu se na "sv. X"
        ("ŽUPA UZNESENJA BLAŽENE DJEVICE MARIJE, ZAGREB", "Uznesenje BDM"),
        ("Crkva Presvetog Trojstva", "Presveto Trojstvo"),
        ("Crkva sv. Križa", "Sveti Križ"),
        # Kratice i pridjevski oblici iz državne evidencije / MinKulture —
        # 15 % župa ovisi o njima (vidi _BDM u src/titular.py).
        ("ŽUPA UZNESENJA B.D. MARIJE", "Uznesenje BDM"),
        ("ŽUPA UZNESENJA MARIJINA", "Uznesenje BDM"),
        ("Kompleks Katedrale Uznesenja Marijina", "Uznesenje BDM"),
        ("ŽUPA POHOĐENJA BDM", "Pohod BDM"),
        ("ŽUPA ROĐENJA B. D. MARIJE", "Rođenje BDM"),
        ("ŽUPA PRESV. TROJSTVA", "Presveto Trojstvo"),
        ("ŽUPA BEZGR. ZAČEĆA BDM", "Bezgrešno začeće BDM"),
        ("ŽUPA VELIKE GOSPE, SINJ", "Velika Gospa"),
        # Bez titulara
        ("Crkva", None),
        ("", None),
        (None, None),
    ],
)
def test_parse(name, expected):
    assert parse(name) == expected


def test_key_is_diacritic_insensitive():
    # Isti objekt iz dva izvora mora dati isti ključ.
    assert key("Crkva sv. Jurja") == key("ŽUPA SV. JURJA, LOVRAN")
    assert key("Crkva svetog Jurja") == key("Crkva sv. Jurja")


def test_key_distinguishes_different_saints():
    assert key("Crkva sv. Petra") != key("Crkva sv. Pavla")


@pytest.mark.parametrize(
    "a,b",
    [
        # Epitet varira po izvoru — glava mora biti ista da match preživi.
        ("Crkva sv. Ante", "Crkva sv. Ante Padovanskog"),
        ("ŽUPA SV. ANTUNA PADOVANSKOG, ZAGREB", "Crkva sv. Antuna"),
        ("Crkva sv. Ivana", "Crkva sv. Ivana Krstitelja"),
    ],
)
def test_head_key_ignores_epithet(a, b):
    assert head_key(a) == head_key(b)
    # …ali puni titular ih i dalje razlikuje (koristi se kao bonus na score).
    assert key(a) != key(b)


def test_head_key_still_separates_saints():
    assert head_key("Crkva sv. Petra") != head_key("Crkva sv. Pavla")


def test_place_after_comma_is_not_part_of_titular():
    # "OSIJEK" ne smije završiti u titularu — inače se ista župa u dva izvora
    # (jedan s mjestom, drugi bez) ne bi spojila.
    assert parse("ŽUPA SV. ANE, OSIJEK") == parse("Crkva sv. Ane")


# --- S3 (2026-11-20): niz „X i Y" cijeli u nominativu ------------------------
# Oblici su stvarni nazivi iz baze (audit `titular_genitiv`, S1: 302 titulara).

@pytest.mark.parametrize(
    "name,expected",
    [
        # 8 najčešćih oblika iz audita (S1)
        ("Crkvica Sv. Petra i Pavla", "sv. Petar i Pavao"),
        ("ŽUPA SV. PETRA I PAVLA, APOSTOLA", "sv. Petar i Pavao"),
        ("crkvica sv. Kuzme i Damjana", "sv. Kuzma i Damjan"),
        ("ŽUPA SV. KUZME I DAMJANA", "sv. Kuzma i Damjan"),
        ("Svetog Filipa i Jakova", "sv. Filip i Jakov"),
        ("Pravoslavna crkva Svetih Apostola Petra i Pavla", "sv. Petar i Pavao"),
        ("crkva svetih Fabijana i Sebastijana", "sv. Fabijan i Sebastijan"),
        ("crkva svetih Petra i Pavla apostola", "sv. Petar i Pavao"),
        ("konkatedrala svetog Ćirila i Metoda", "sv. Ćiril i Metod"),
        ("Crkva Sv. Ivana i Pavla", "sv. Ivan i Pavao"),
        # Ostali oblici istog tipa
        ("crkva svetih Kvirika i Julite", "sv. Kvirik i Julita"),
        ("Hram Sv. Arhanđela Mihaila i Gavrila", "sv. Mihailo i Gavrilo"),
        ("crkva svetih mučenika Srđa i Baha", "sv. Srđ i Bakho"),
        ("crkva svetih Šimuna i Jude Tadeja", "sv. Šimun i Juda Tadej"),
        ("Crkva Sv. Ap. Petra i Pavla", "sv. Petar i Pavao"),
        ("ŽUPA SV. PETRA I PAVLA AP.", "sv. Petar i Pavao"),
        ("ŽUPA SV. KUZME I DAMJANA MM.", "sv. Kuzma i Damjan"),
        ("crkva svetog Vida i svetog Jurja", "sv. Vid i Juraj"),
        ("ŽUPA SV. JURJA I SV. JAKOVA", "sv. Juraj i Jakov"),
        ('Crkva "sv. Fabijana i sv. Sebastijana"', "sv. Fabijan i Sebastijan"),
        ('BUGARSKA CRKVENA OPĆINA "SV.SV. ĆIRILA I METODA" - OSIJEK', "sv. Ćiril i Metod"),
        # „i" veže epitete jednog sveca, ne dva sveca
        ("ŽUPA SV. KATARINE DJEVICE I MUČENICE", "sv. Katarina Djevica i Mučenica"),
        ("crkva svetog Stjepana I. pape i mučenika", "sv. Stjepan I. Papa i Mučenik"),
        ("ŽUPA SV. JURJA MUČENIKA I SRCA MARIJINA", "sv. Juraj Mučenik i Srce Marijino"),
        ("ŽUPA SV. BENEDIKTA I ŽALOSNE GOSPE", "sv. Benedikt i Žalosna Gospa"),
        ("ŽUPA SV. ANTUNA PADOVANSKOG I B. D. MARIJE KRALJICE MUČENIKA",
         "sv. Antun Padovanski i BDM"),
        ("Kapela sv. Monike i sv. Leopolda Bogdana Mandića u Dankovcu",
         "sv. Monika i Leopold Bogdan Mandić"),
        # Bivši lažno pozitivni u auditu
        ("Crkva sv. Liberana i arheološko nalazište na Gomilama", "sv. Liberan"),
        ("Sv.Mihovile i Sv.Mario", "sv. Mihovil i Mario"),
        ("MAKEDONSKA PRAVOSLAVNA CRKVENA OPĆINA SV. CAR KONSTANTIN I CARICA ELENA",
         "sv. Car Konstantin i Carica Elena"),
    ],
)
def test_parse_niz_u_nominativu(name, expected):
    assert parse(name) == expected


@pytest.mark.parametrize(
    "name,place,expected",
    [
        ("ŽUPA SV. KUZME I DAMJANA POLAČA", "Polača", "sv. Kuzma i Damjan"),
        # „IŽ" nije prijedlog „iz" (prije se tu rezao naziv)
        ("ŽUPA SV. PETRA I PAVLA VELI IŽ", "Veli Iž", "sv. Petar i Pavao"),
        ("ŽUPA SV. IVANA I PAVLA PETRČANE", "Petrčane", "sv. Ivan i Pavao"),
        ("ŽUPA SV. NIKOLE B. BOŽAVA", "Božava", "sv. Nikola B"),
        # Glava se nikad ne skida, i kad je jednaka mjestu
        ("ŽUPA SV. ROKA", "Rok", "sv. Rok"),
    ],
)
def test_parse_skida_mjesto_bez_zareza(name, place, expected):
    assert parse(name, place=place) == expected


def test_niz_ne_mijenja_glavu_prvog_imena():
    # Matcher uspoređuje glave: drugi član niza ne smije ući u nju.
    assert head_key("ŽUPA SV. PETRA I PAVLA") == head_key("Crkva sv. Petra") == "sv petar"
    assert head_key("crkvica sv. Kuzme i Damjana") == "sv kuzma"
    # Naslov ispred niza nije ime: glava je Petar, kao u katoličkom nazivu.
    assert head_key("Pravoslavna crkva Svetih Apostola Petra i Pavla") == "sv petar"


def test_isusova_uskrsnuca_u_oba_reda_rijeci():
    assert parse("ŽUPA ISUSOVA USKRSNUĆA") == "Uskrsnuće Isusovo"
    assert head_key("crkva Isusova uskrsnuća") == head_key("ŽUPA USKRSNUĆA ISUSOVA")


def test_nikola_biskup_i_tavelic_su_razliciti_sveci():
    # S2: „ŽUPA SV. NIKOLE B." (Rijeka) bodovala je 90 i sv. Nikolu biskupa i
    # sv. Nikolu Tavelića — margina 0, župa bez crkve.
    zupa = head_key("ŽUPA SV. NIKOLE B.")
    assert zupa == head_key("crkva svetog Nikole biskupa") == "sv nikola"
    assert head_key("crkva svetog Nikole Tavelića") == "sv nikola tavelic"
    assert head_key("ŽUPA SV. NIKOLE TAVELIĆA") == "sv nikola tavelic"
    assert head_key("ŽUPA SV. NIKOLE TEVELIĆA") == "sv nikola tavelic"   # tipfeler evidencije
    assert head_key("Crkva sv. Nikole Tavelić") == "sv nikola tavelic"


def test_leopold_b_je_bogdan():
    assert parse("ŽUPA SV. LEOPOLDA B. MANDIĆA") == "sv. Leopold Bogdan Mandić"
    assert key("ŽUPA SV. LEOPOLDA B. MANDIĆA") == key("crkva svetog Leopolda Bogdana Mandića")


def test_epitet_izvan_niza_ostaje_kako_je():
    # Bez niza ime ostaje u genitivu, pa se ni epitet ne diže (inače miješano).
    assert parse("crkva sv. Silvestra pape") == "sv. Silvestra pape"


# --- S3 ispravci nakon rebuilda (odluke 312–313) -----------------------------

@pytest.mark.parametrize("name", [
    "crkva Blažene Djevice Marije - Kraljice mira",        # w403099918
    "Crkva Blažene Djevice Marije i župni dvor",           # registar Z-2282
    "Kapelica Blažene Djevice Marije",
])
def test_bdm_bez_otajstva_nije_svetac_djevica(name):
    assert parse(name) == "Majka Božja"
    assert head_key(name) == "majka bozja"


def test_bdm_s_otajstvom_ostaje_otajstvo():
    assert parse("crkva rođenja Blažene Djevice Marije") == "Rođenje BDM"
    assert parse("Crkva Uznesenja bl. Djevice Marije") == "Uznesenje BDM"
    # BDM kao drugi član niza ne preuzima titular
    assert head_key("crkva svetog Antuna Padovanskog i Blažene Djevice Marije") == "sv antun"


def test_granesina_i_kraljica_mira_nisu_isti_titular():
    # Z-2282: registar „Blažene Djevice Marije" ne smije se jedinstvenošću
    # spojiti na Kraljicu mira — generički titular ne nosi jedinstvenost.
    from src.match import GENERIC_TITULARS
    assert key("Crkva Blažene Djevice Marije i župni dvor") in GENERIC_TITULARS
    assert head_key("crkva rođenja Blažene Djevice Marije") != "majka bozja"


def test_mihajla_i_mihaila_imaju_istu_glavu():
    # Z-6096 Vrhovine: registar „Mihajla", OSM „Mihaila"
    reg = "Crkva sv. Arhangela Mihajla i Gavrila"
    osm = "crkva svetih arhangela Mihaila i Gavrila"
    assert parse(reg) == parse(osm) == "sv. Mihailo i Gavrilo"
    assert head_key(reg) == head_key(osm) == "sv mihailo"


# --- marijanski zaziv (S4, odluka 405) --------------------------------------
from src.titular import zaziv, zaziv_sukob  # noqa: E402


@pytest.mark.parametrize("name,expected", [
    ("crkva Blažene Djevice Marije Pomoćnice", {"pomocnic"}),          # Knežija w246443250
    ("Kapela Blažene Djevice Marije Bezgrešne na Knežiji", {"bezgres"}),  # Q133733258
    ("Svetište Majke Božje Svetogorske", {"svetogor"}),               # Mali Lug
    ("Kompleks crkve Blažene Djevice Marije “Majke Božje Svetogorske” s pripadajućim "
     "građevinama, ruševnim građevinama, sajmištem, te pašnjakom i šumom", {"svetogor"}),  # Z-834
    ("Crkva Gospe od Snijega", {"snjez"}),
    ("Crkva Majka Božja Snježna", {"snjez"}),
    ("Crkva Majke Božje Sniježne (sv. Helene)", {"snjez"}),
    ("Crkva Majke Božje od sv. Krunice (sv. Rozalije)", {"ruzarij"}),  # Z-321
    ("ŽUPA GOSPE OD RUŽARIJA BORAJA", {"ruzarij", "boraj"}),
    ("crkva Majke Božje Sljemenske Kraljice Hrvata", {"sljemen", "kraljic", "hrvat"}),
    ("Samostan Gospe od Delorita", {"loret"}),
])
def test_zaziv(name, expected):
    assert zaziv(name) == frozenset(expected)


@pytest.mark.parametrize("name", [
    "Kapela Blažene Djevice Marije",                  # gola BDM (Čabar, Z-2599)
    "Crkva Blažene Djevice Marije i župni dvor",      # Z-2282 Granešina: „i" nije zaziv
    "Crkva BDM (Gospe od Planice)",                   # Z-5695 Komiža: zaziv je u zagradi
    "ŽUPA BLAŽENE DJEVICE MARIJE",
    "Crkva sv. Marka",                                 # nije generički marijanski
    "Crkva Uznesenja Blažene Djevice Marije",          # otajstvo, ne „Majka Božja"
])
def test_bez_zaziva(name):
    assert zaziv(name) is None


def test_zaziv_ne_mijenja_kljuc():
    # Puni ključ i glava ostaju generički: zaziv samo proturječi, ne razlikuje.
    assert key("Svetište Majke Božje Svetogorske") == "majka bozja"
    assert head_key("crkva Blažene Djevice Marije Pomoćnice") == "majka bozja"


@pytest.mark.parametrize("a,b,sukob", [
    ("Kapela Blažene Djevice Marije Bezgrešne na Knežiji",
     "crkva Blažene Djevice Marije Pomoćnice", True),                  # Knežija
    ("Svetište Majke Božje Svetogorske", "Crkva Gospe Lurdske", True),
    ("Crkva Gospe od Lužina", "Gospa od Ružarija", True),                # Z-4858 Ston
    # Gola BDM je spojiva sa svakim zazivom (pravilo (b) odbačeno, −22 spoja).
    ("Kapela Blažene Djevice Marije", "Svetište Majke Božje Svetogorske", False),
    ("Crkva BDM (Gospe od Planice)", "crkva Gospe od Planice", False),   # Z-5695 Komiža
    ("Crkva Majke Božje (Marija Bistrica)", "bazilika Majke Božje Bistričke", False),
    # Ista pobožnost, drugi zapis.
    ("Crkva Majke Božje Sljemenske", "ŽUPA MAJKE BOŽJE SLJEMENSKE KRALJICE HRVATA", False),
    ("Gospa od Sniga", "Crkva Gospe Snježne", False),
    ("Crkva Gospe od Milosrđa", "crkva Gospe od Milosti", False),       # RST-1286 Suđurađ
    ("Crkva Gospe od Sedam žalosti", "Kapela Gospe Žalosne", False),
    ("ŽUPA GOSPE OD RUŽARIJA BORAJA", "Gospa od Ružarija", False),       # mjesto u nazivu
])
def test_zaziv_sukob(a, b, sukob):
    assert zaziv_sukob(a, b) is sukob
    assert zaziv_sukob(b, a) is sukob
