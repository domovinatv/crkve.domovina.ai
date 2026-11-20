# Audit polazno stanje i reproducibilnost (S1, 2026-11-20)

Polazni commit S1: `5e8c36c`. Mjereno na rebuildu iz keša `data/raw/` (snimak izvora 2026-08-15).

## Ukratko

- `make rebuild` (= `clean-db` + `PLACES_OFFLINE=1 make all-places`) je **reproducibilan**:
  dva runa od prazne baze daju bajt-identične `data/exports/*` i `audit.json` (0 mrežnih pokušaja).
- Rebuild **nije** bajt-identičan deployanom snimku (2026-08-27). Razlika je 10 župa, 1 crkva i
  3 geometrije biskupija, sve homonimi koje je korekcija 2026-08-17 premjestila (vidi dolje).
- Dva skrivena kvara reproducibilnosti, oba ispravljena u S1:
  1. `make all-places` iz keša je **išao na mrežu** (Places, 5 upita koji nikad nisu dohvaćeni).
  2. `make all` **nije bio od nule**: `init` ne briše bazu, a `10_match_heritage` na već spojenoj
     bazi kvari podatke.
- Svi kasniji paketi mjere razliku prema **ovom rebuildu**, ne prema deployanom snimku.

## Naredbe

```bash
# mreža blokirana mrtvim proxyjem: svaki pokušaj glasno padne (httpx poštuje *_PROXY)
export HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9 NO_PROXY=
make rebuild && shasum data/exports/*.geojson data/exports/*.csv data/exports/stats.json
make audit  && shasum data/exports/audit.json
make rebuild && …   # drugi run, usporedba sha
curl -s https://gis.domovina.ai/data/crkve.geojson | shasum   # deployano
```

## Sha

| datoteka | deployano (= HEAD `data/exports/`) | rebuild (2×, identično) |
|---|---|---|
| crkve.geojson | `abc12b793e93` | `74b0bd5340af` |
| zupe.geojson | `9f3cbeb5f7f0` | `ac8d9e66a820` |
| biskupije.geojson | `77b6b2e44f8c` | `4d6f4657f57b` |
| crkve.csv | `66e5f2b34cbd` | `9ffbb68df727` |
| zupe.csv | `d494e9a483ba` | `1ba8b05fbb0e` |
| biskupije.csv | `d4cd8dd2bf48` | `ea9ae71ed3ab` |
| bastina-nespojeno.csv | `15235360aed4` | `15235360aed4` |
| geo-konflikti.csv | `4be2b9c15b87` | `4be2b9c15b87` |
| stats.json | – | `09e640872d6d` |
| audit.json | – | `6ffe99eb3fa5` |

`frontend/public/data/`: 9399 datoteka identično u oba runa. Razlikuje se samo `manifest.json`,
jer nosi `generated_at` (sat).

## Kvar 1: Places iz keša išao na mrežu

Prvi `make all-places` pao je u `13_places_parishes` na `httpx.ConnectError`, jer upit nije bio u kešu.
Simulacija petlje upita nad bazom (bez mreže) našla je 5 promašaja:
`sv-marije-magdalene-kostanjevac-8348`, `sv-mihovila-ark-vrh-701089`, `sv-mihovila-ark-sveti-vid-701094`,
`uznesenja-b-d-marije-vrana-701029`, `…samostan-svetog-vinka-selca-5737`.

**Uzrok:** `13` proba varijante upita redom, dok `pick()` ne prihvati rezultat, a `pick` ovisi o sidru
(naselje, županija). Places run je bio 2026-08-15, a korekcija homonima (`14`, `parish_geo`)
2026-08-17. Za te župe se sidro poslije promijenilo, prvi keširani rezultat danas pada na sidru, pa
petlja traži varijantu koja nikad nije dohvaćena.

**Ispravak:** `PLACES_OFFLINE=1` (`src/places.py`). Promašaj keša vraća prazan rezultat, broji se i
logira, a ključ nije potreban. U rebuildu od nule promašaja je 4 (Sveti Vid, Vrana, po 2 varijante).
Sve 4 imaju `naselje-centroid` i prije i poslije.

## Kvar 2: `make all` nije bio od nule

`00_init_db` je idempotentan i ne briše bazu, a `_upsert` čuva stare vrijednosti (`COALESCE`). Drugi
run `make all-places` na postojećoj bazi daje drukčiji `crkve.geojson`:

| | od nule | drugi run na istoj bazi |
|---|---|---|
| `heritage_unmatched` | 923 | 2038 |
| građevina s `heritage_id` | 1115 | 1115 |
| građevina s `year_built` | 1499 | 659 |

`10_match_heritage` sve građevine koje već imaju `heritage_id` stavlja u `taken`. Zato svaki baštinski
zapis završi kao `kandidat_vec_zauzet` i ostane u `heritage_unmatched`, a `year_built` iz Registra
se izgubi. Deployani snimak ima brojke od nule (923/1115/1499), pa je u produkciji sve u redu. Kvar je
latentan za svaki ponovljeni run.

**Ispravak:** `make clean-db`, koji `all` i `all-places` sad pozivaju prvi. Sam `10` i dalje nije
ponovljiv na spojenoj bazi. To je otvoreno za S7 (dvaput-nula), dok `make rebuild` uvijek kreće od nule.

## Rebuild od nule vs deployani snimak

SQL usporedba svih tablica (bez `*_at`), `crkve-A.db` naspram baze koja je bila na disku 2026-08-27:

- `churches`: 1 red, `crkva-kostanjevac-w1504181702` sad ima `parish_id`.
- `parishes`: 10 redova, sve homonimi ili Places:
  - Kostanjevac i Vrh: koordinata **obrisana** (`parish_geo.Drop`), dosad `naselje-centroid`.
  - Prgomet: duplikat, bez koordinate.
  - Barbat, Sveti Martin, Požeške Sesvete: `places`.
  - Sveti Vid, Vrana, Kraj, Zagorje: samo `google_place_id`/`phone`/`website`.
- `diocese_areas`: 3 geometrije (posljedica gornjih sjedišta).

Deployani snimak je, dakle, nastao inkrementalno: Places prije korekcije homonima. Rebuild od nule je
poštenija polazna točka. `places_koordinate_u_exportu` je zato 991 (deployano 989).

## `make audit` na rebuildu (polazne brojke lanca)

```
METRIKA                       VRIJ.  OPIS
───────────────────────────────────────────────────────────────────────────────────────
nekatolicke_na_katolickim        72  nekatolička građevina (kind/religija/konfesija) spojena na katoličku pravnu osobu
nekatolicke_zupne_crkve           2  … od toga označena kao župna crkva
titular_genitiv                 302  titular „sv. X i Y” (djelomično) u genitivu — crkve + pravne osobe [crkve 196, pravne osobe 106]
konfesija_nenormalizirana      1175  denomination/religion izvan dozvoljenog skupa — crkve + pravne osobe + biskupije [churches 1051, parishes 109, dioceses 15]
node_way_duplikati               40  OSM node + way/relation ≤40 m, isti naziv ili glava titulara [isti naziv 33, ista glava 29]
places_koordinate_u_exportu     991  župe s koordinatama iz Google Placesa (idu u javne exporte) [google_maps_uri 2139]
parish_count_razlika              2  katolička biskupija: parish_count ≠ broj zapisa kind='zupa'
wikidata_dijeljen                 4  isti wikidata_id na više građevina [neočekivani: Q132087369]
engleski_nazivi                  32  naziv građevine na engleskom (Church/Chapel/Saint/St. …) [wikidata 20, osm 12]
bez_zupanije                      9  građevina bez županije
crkve_dalje_20km_od_zupe          9  spojena građevina > 20 km od koordinata svoje pravne osobe
───────────────────────────────────────────────────────────────────────────────────────
KONTEKST (definicije iz src/stats.py = scripts/40_stats.py)
crkve_ukupno                   6966
crkve_sa_zupom                 2929
zupne_crkve                    1151
zupe_aktivne                   1561
zupe_bez_zupne_crkve            487
zupe_bez_ijedne_crkve           421
```

Odstupanja od brojki iz audita S0 (definicije su sad u `src/audit.py`):

- **`nekatolicke_na_katolickim` 72:** po kindu/konfesiji:
  - 38 pravoslavna-crkva/serbian_orthodox, 14 pravoslavna-crkva/orthodox;
  - 5 kapela/samostana s pravoslavnom konfesijom;
  - 5 džamija;
  - 10 protestantskih/JW.
  S0 je pisao 71 = 52+5+9, a ta razdioba daje 66.
- **`titular_genitiv` 302:** 196 crkava + 106 pravnih osoba. Osam imenovanih oblika daje 133 u crkvama,
  a generičko pravilo nađe još 63 (Ćirila i Metoda, Kvirika i Julite…). Poznati lažno pozitivni:
  „sv. Car Konstantin I Carica”, „sv. Liberana i arheološko nalazište”, „sv. Mihovile i Sv.Mario”.
- **`konfesija_nenormalizirana` 1175:** crkve 1051 (`catholic` 1022), pravne osobe 109 (`adventist`,
  piše ga naš `scripts/03`), biskupije 15. `orthodox` je dozvoljen (odluka 101), pa se ne broji.
- **`node_way_duplikati` 40:** 33 s istim nazivom, 29 s istom glavom titulara; jedan par smije imati oboje.
  Isti sirovi naziv daje 22 (S0: ~23). Isti titular preko svih tipova parova daje 78 (S0: ~77), od
  toga way+way 28, way+wikidata 15, relation+way 4, a to nije node+way.
- **`parish_count_razlika` 2**, ali **0 prema aktivnim i različitim župama**: `parish_count` namjerno
  ne broji Priznu (ugašena) ni duplikat Prgomet. Ispravak „85→86” iz TODO-a bio bi pogrešan smjer
  (odluka 104).
- **`engleski_nazivi` 32:** 20 iz Wikidate (engleski label), 12 iz OSM-a.
