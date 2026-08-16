# DOMOVINA Crkve — katalog svih crkava u Hrvatskoj

**Karta:** [gis.domovina.ai](https://gis.domovina.ai/) (slojevi „⛪ Crkve", „🏛 Župe" i „✝️ Biskupije")
&nbsp;·&nbsp; **Kod:** [MIT](LICENSE)
&nbsp;·&nbsp; **Podaci:** [ODbL + CC-BY](LICENSE-DATA)
&nbsp;·&nbsp; **Mreža:** dio [DOMOVINA](https://domovina.ai) ekosustava

---

## English summary

Open, machine-readable catalog of **every church and place of worship in
Croatia** — 6,966 buildings, all geocoded, plus 2,979 registered religious
legal entities (parishes, monasteries, congregations) with their national tax
IDs and dioceses.

Two entities, deliberately separate: **buildings** (`churches` — coordinates,
patron saint, heritage protection, photo) and **legal persons** (`parishes` —
OIB, seat, diocese), linked N:1 so a parish can own its parish church plus
filial churches and chapels, and a chapel can exist with no parish at all.

Compiled entirely from public sources with **no API keys**: OpenStreetMap
(Overpass), Croatia's open data portal (`data.gov.hr` — the Ministry of
Justice registers of Catholic legal persons and religious communities, and the
Ministry of Culture's Register of Cultural Heritage), and Wikidata. The whole
pipeline rebuilds from zero in seconds against cached sources: `make all`.

Part of the [DOMOVINA](https://github.com/domovinatv) umbrella — an open
Croatian podcast/data/AI ecosystem. Sister projects:
[klubovi.domovina.ai](https://klubovi.domovina.ai) (football clubs) and
[gis.domovina.ai](https://gis.domovina.ai) (the map this feeds).

---

## Hrvatski

Sustavan javni katalog **svih crkava, kapela, samostana, džamija i sinagoga u
Hrvatskoj** — s koordinatama, titularom, statusom zaštite, slikom i vezom na
župu — te **svih vjerskih pravnih osoba** iz državnih evidencija (OIB,
sjedište, biskupija).

Cilj: da postoji jedno mjesto s kojeg se može odgovoriti „koje su sve crkve u
Hrvatskoj i tko ih drži", bez ručnog prepisivanja iz PDF šematizama.

## Stanje kataloga

| Pokazatelj | Brojka | |
|---|---:|---:|
| **Građevina ukupno** | **6 966** | |
| … s koordinatama | 6 966 | 100 % |
| … s tlocrtom (poligon, ne točka) | 5 256 | 75,5 % |
| … sa županijom i naseljem | 6 957 | 99,9 % |
| … s parsanim titularom | 4 523 | 64,9 % |
| … sa statusom zaštite (MinKulture) | 1 115 | 16,0 % |
| … sa slikom (Wikimedia Commons) | 712 | 10,2 % |
| … s poveznicom na Wikipediju | 700 | 10,0 % |
| … povezano sa župom | 2 950 | 42,3 % |
| … od toga **župnih crkava** | 1 151 | |
| **Pravnih osoba** (župe, samostani, crkvene općine) | **2 979** | |
| … katoličkih **župa** | 1 563 | |
| … s OIB-om | 1 778 | |
| … s koordinatama | 2 928 | 98,3 % |
| Biskupija, eparhija i vjerskih zajednica | 70 | |
| … s telefonom (Places) | 1 064 | |
| … s webom (Places) | 875 | |
| Zaštićena baština bez para u OSM-u | 923 | |
| **Crkava s neovisno potvrđenom lokacijom** (Places) | **1 083** | 94 % župnih |
| Geo konflikata za ručni pregled | 40 | |

### Po tipu objekta

| Tip | Broj | Tip | Broj |
|---|---:|---|---:|
| crkva | 3 966 | katedrala | 22 |
| kapela | 1 434 | džamija | 20 |
| poklonac / pil | 900 | sinagoga | 16 |
| pravoslavna crkva | 288 | svetište | 11 |
| samostan | 185 | bazilika | 5 |
| ostalo | 119 | | |

### Župe po (nad)biskupiji

Zagrebačka 206 · Splitsko-makarska 188 · Đakovačko-osječka 153 · Porečka i
pulska 134 · Zadarska 116 · Varaždinska 105 · Požeška 93 · Riječka 90 ·
Gospićko-senjska 86 · Šibenska 75 · Sisačka 65 · Dubrovačka 61 ·
Bjelovarsko-križevačka 58 · Krčka 51 · Hvarska 46 · Križevačka eparhija 35

### Najčešći titulari

Majka Božja 285 · sv. Nikola 157 · sv. Rok 138 · Sveti Križ 138 ·
sv. Ivan Krstitelj 136 · Uznesenje BDM 98 · sv. Josip 91 · sv. Juraj 89 ·
Presveto Trojstvo 82 · sv. Petar 76 · sv. Ana 76 · Duh Sveti 76

## Izvori podataka

Svi su javni i besplatni. **Pipeline ne treba nijedan API ključ.**

### OpenStreetMap — Overpass API
Primarni izvor **građevina**. Upit je unija širih od `amenity=place_of_worship`
jer je hrvatski dio OSM-a nekonzistentno tagiran:

```
amenity=place_of_worship                          ~5 350
building=church|chapel|cathedral|mosque|…         objekti bez amenity taga
amenity=monastery                                 samostanski kompleksi
historic=church                                   nekadašnje crkve / ruševine
historic=wayside_shrine                           pilovi i poklonci
                                          ──────────────────
                                          ukupno   6 837 elemenata
```

Od toga je 5 256 zapisa `way`/`relation` — dakle stvarni tlocrt zgrade, ne
samo točka. Overpass vraća **406 bez `User-Agent` headera**.

### data.gov.hr — Evidencija pravnih osoba Katoličke Crkve
Ministarstvo pravosuđa i uprave. **2 117 zapisa**, od toga **1 563 ŽUPA**, 308
samostana, 14 (nad)biskupija — s OIB-om, sjedištem i pripadnom biskupijom.

Ovo je **jedini strojno čitljiv potpuni popis župa u RH**. Crkveni šematizmi
postoje, ali su per-biskupija, u PDF-u i nisu ujednačeni.

### data.gov.hr — Evidencija vjerskih zajednica
Isti registar, nekatolički dio: **54 vjerske zajednice** (SPC, Islamska
zajednica, evangelička, reformirana, adventisti, baptisti, Židovska zajednica…)
i **863 organizacijska oblika** (crkvene općine, parohije, džemati) s OIB-om.

### data.gov.hr — Registar kulturnih dobara RH
Ministarstvo kulture i medija. Od 7 950 zapisa, **2 038 je sakralne
graditeljske baštine** — oznaka zaštite (`Z-1234`), pravni status, vrijeme
nastanka i stručni opis konzervatorskog odjela. **Nema koordinate**, pa se
spaja heuristikom (vidi „Spajanje izvora").

### Wikidata (SPARQL, CC0)
844 objekta s koordinatama. Manji od OSM-a, ali nosi ono što OSM nema: sliku
na Commonsu, poveznicu na Wikipediju, arhitekta, godinu gradnje.

### Google Places API (New) — opcionalno, `make places`
Jedini korak koji treba ključ i jedini koji košta. **Nije** u `make all`.

Ovdje Places nije geocoder kao u sestrinskim projektima — građevine već imaju
100 % koordinata iz OSM-a, i to tlocrte. Radi dvije stvari koje drugi izvori
ne mogu, **iz istog poziva**:

1. **Preciziranje župa.** 1 652 župe ležale su na težištu naselja jer im nije
   nađena matična crkva — to je točnost sela, ne adrese. Places je **1 005**
   podigao na razinu zgrade i donio **1 064 telefona i 875 web adresa** kojih u
   državnoj evidenciji uopće nema. Pokrivenost koordinatama: 94,1 % → 98,3 %.
2. **Nezavisna provjera matchera.** Za 1 151 župu koja JEST spojena na crkvu
   usporedi se Places točka s tom crkvom. Places nije sudjelovao u matchanju,
   pa je to stvaran drugi izvor, ne kružna provjera:
   `≤ 300 m` → `geo_verified = 1`; `> 750 m` → zapis u `geo_conflicts` i
   `data/exports/geo-konflikti.csv` za ručni pregled (ništa se ne mijenja samo
   od sebe); između → ni potvrda ni konflikt.

   **Rezultat: 1 083 od 1 151 spoja potvrđeno (94 %), 40 za pregled.** Pregled
   pokazuje da ni tih 40 uglavnom nisu greške matchera nego druga zgrada iste
   župe — župni ured (Vrana, 837 m), pastoralni centar (Korčula, 1,7 km),
   samostan umjesto crkve. Zato se ne diraju automatski.

   **Sidro je težište naselja, namjerno NE crkva koju provjeravamo.** Crkva bi
   bila točnije sidro, ali bi provjeru učinila kružnom: rezultat koji
   proturječi našem matchu bio bi odbačen prije nego postane konflikt.
   Provjereno oboje — s crkvom kao sidrom 1 083 potvrde i 39 konflikata, s
   naseljem 1 083 i 40. Razlika je zanemariva, ali samo je druga brojka
   poštena.

Rezultat se ne primjenjuje slijepo: Text Search **uvijek** nešto vrati, pa se
traži sakralni tip objekta (ili vrlo sličan naziv) **i** poklapanje županije
nad DGU granicama — inače se odbacuje.

Opseg: **2 359 poziva** (jedan po aktivnoj pravnoj osobi), keširano po SHA
zahtjeva pa svaki sljedeći run ne troši kvotu — ponovni run s promijenjenom
logikom validacije stajao je 271 poziv umjesto 2 600.

**Sidro je najvažniji filtar.** Rezultat mora biti unutar 15 km od već poznate
pozicije župe (koordinate njezine crkve ili težište naselja). Bez toga je
**24 % preciziranih župa završilo >5 km od vlastitog naselja** — Text Search
rado vrati istoimenu crkvu s druge strane države („ŽUPA SV. MARIJE MAGDALENE,
BEBRINA" u Slavoniji → crkva u Brseču u Istri, 282 km). Filtar po županiji to
ne hvata sam jer 1 202 župe u evidenciji uopće nemaju upisanu županiju
(popunjava ih `scripts/12` prostorno, prije Placesa).

⚠️ Dvije zamke: default dnevna kvota `SearchTextRequestPerDayPerProject` je
**100** i diže se ručno u GCP konzoli; ključ s **IP restrikcijom** vraća 403
`API_KEY_IP_ADDRESS_BLOCKED` čim se promijeni javni IP. Skripta oba slučaja
imenuje u poruci umjesto generičkog „403".

### DGU granice iz `../karta-hrvatske`
Naselja (6 759 poligona) i JLS-ovi (556) služe za **prostornu dodjelu** naselja,
općine i županije svakoj građevini — i za offline geokodiranje sjedišta župa
preko težišta naselja. Isti sloj crta kartu na gis.domovina.ai, pa su granice
u katalogu i na karti po definiciji iste.

### Granice biskupija — izvor NE POSTOJI
Provjereno uživo: OpenStreetMap ima **3 od 15** biskupija kao
`boundary=religious_administration`, Wikidata **nijednu** (`P3896` prazan za
svih 10 hrvatskih dijeceza koje ima). Teritoriji se zato **deriviraju**
(`scripts/20`): naselje pripadne biskupiji župa koje u njemu sjede, ostala
najbližoj župi, pa se naselja iste biskupije spoje.

Te 3 OSM granice nisu upotrijebljene kao izvor nego kao **mjera**: slaganje je
96,6 % / 98,6 % / 97,9 % naselja (IoU 0,92–0,98), a zbroj svih 15 teritorija
56 530 km² naspram 56 594 km² kopna RH. Brojka slaganja stoji uz svaki
teritorij i piše u popupu na karti.

## Model podataka

```
  churches  (građevina)                 parishes  (pravna osoba)
  ─────────────────────                 ──────────────────────────
  6 966 zapisa                          2 979 zapisa
  koordinate: 100 %                     OIB: 1 778
  osm_type/osm_id, wikidata_id          registry_id (SBT_ID), registry_no
  titular, kind, denomination           diocese / community
  heritage_id, year_built, slika        address, city, leader_title
            │                                      ▲
            └── parish_id ─────────────────────────┘
                is_parish_church = 1  →  župna crkva
                is_parish_church = 0  →  filijalna crkva / kapela
                parish_id IS NULL     →  bez župe (samostanska, grobljanska,
                                          poklonac, nekatolička…)

  dioceses    70 — (nad)biskupije, eparhije, vjerske zajednice
  heritage_unmatched  923 — zaštićena baština bez para u OSM-u
```

Zašto dvije tablice a ne jedna: **to nisu isti skupovi.** 1 563 župa naspram
6 966 građevina. Jedna župa ima župnu crkvu plus filijale i kapele; mnoga
crkva nema župu. Model s jednom tablicom izgubio bi 1 778 OIB-ova i ne bi
mogao izraziti filijalu.

## Pipeline

```bash
make all         # cijeli lanac od nule, BEZ ijednog ključa
make places      # opcionalno: Google Places (treba GOOGLE_MAPS_API_KEY)
make all-places  # oboje
make help        # popis koraka
```

```
00_init_db                shema

01_ingest_osm             OSM Overpass  →  6 837 građevina, 99,9 % s naseljem
02_ingest_parishes_…      data.gov.hr   →  2 116 katoličkih pravnih osoba
03_ingest_religious_…     data.gov.hr   →  54 zajednice + 863 org. oblika
04_ingest_heritage        data.gov.hr   →  2 038 sakralnih kulturnih dobara
05_ingest_wikidata        SPARQL        →  844 objekta (442 spojeno po OSM
                                           `wikidata` tagu, 273 prostorno,
                                           129 novih)
        ▼
10_match_heritage         baština → građevina        1 115 spojeno (55 %)
11_match_parishes         župa → župna crkva         1 151 spojeno (74 % župa)
                          + filijale u istom mjestu  1 800
12_geocode_parishes       težište naselja (offline)  1 652
                          `--nominatim` = fini prolaz (opcionalno, sporo)
        ▼
13_places_parishes        Google Places (OPCIONALNO, treba ključ):
                          preciziranje župa + nezavisna provjera matchera
        ▼
20_derive_diocese_areas   teritoriji 15 biskupija iz sjedišta župa
                          + mjeri se o 3 granice koje OSM ima (96,6–98,6 %)
        ▼
30_build_fts              FTS5, dijakritički neosjetljivo
31_export_geojson         data/exports/{crkve,zupe,biskupije}.geojson
32_export_csv             + biskupije.csv, bastina-nespojeno.csv
33_sync_karta             →  ../karta-hrvatske/apps/karta-web/public/data/
40_stats                  izvještaj + stats.json
```

Sve je **idempotentno**, a sirovi odgovori se kešraju u
`data/raw/<izvor>/<sha>.json` — drugi run ne dira mrežu i traje ~5 sekundi.
`make clean-cache` prisiljava ponovni dohvat.

## Spajanje izvora (najrizičniji dio)

Registar kulturnih dobara i evidencija župa **nemaju koordinate ni OSM id** —
samo naziv i mjesto. Isti objekt izgleda ovako:

| izvor | naziv | mjesto |
|---|---|---|
| OSM | Crkva sv. Ante | Dragljane |
| MinKulture | Crkva sv. Ante Padovanskog | Dragljane / VRGORAC |
| Evidencija | ŽUPA SV. ANTUNA PADOVANSKOG | Dragljane |

Postupak (`src/match.py`), svjesno konzervativan — **lažni match je gori od
nedostajućeg**:

1. **Blokiranje po mjestu u dvije razine** — prvo naselje, pa tek ako ondje
   nema kandidata, općina. Razine se **ne miješaju**: općina Vrgorac ima 25
   crkava u dvadesetak sela i nikad ne bi dala jasnog pobjednika.
2. **Tvrdi filtar po svecu**, ali samo po *glavi* titulara — epitet varira po
   izvoru („sv. Ante" / „sv. Ante Padovanskog" / „SV. ANTUNA PADOVANSKOG").
3. **rapidfuzz** `token_set_ratio` na normaliziranom nazivu, prag 82.
4. Ako više kandidata prijeđe prag bez jasne razlike (margina 6) — **ne
   matchaj**. Dvosmislenost ostaje nespojena i vidi se u statistici.

Zbog toga 923 baštinska zapisa ostaju bez para; izvoze se u
`data/exports/bastina-nespojeno.csv` da se zna što fali.

## Instalacija i pokretanje

```bash
uv sync                  # Python 3.13, tri ovisnosti
make all                 # ~2 min prvi put (mrežni dohvat), ~5 s poslije
make test                # 97 testova
```

Nema `.env`-a ni ključeva. `.env.example` postoji samo za opcionalne stvari
(lokalni Nominatim, alternativni Overpass endpoint, kontakt u User-Agentu).

Za prostornu dodjelu naselja/županija treba **sestrinski repo
`../karta-hrvatske`** kloniran pokraj ovoga (ili `KARTA_DATA_DIR`). Bez njega
pipeline radi, ali bez naselja matching osjetno padne.

## Izlazi

```
data/crkve.db                     SQLite katalog + FTS5
data/exports/crkve.geojson        6 966 točaka (3,9 MB)
data/exports/zupe.geojson         2 928 točaka (2,5 MB)
data/exports/biskupije.geojson    15 teritorija, derivirano (0,7 MB)
data/exports/crkve.csv            pun izvoz, UTF-8 s BOM (Excel-friendly)
data/exports/zupe.csv
data/exports/biskupije.csv
data/exports/bastina-nespojeno.csv
data/exports/geo-konflikti.csv    prazno dok se ne pokrene `make places`
data/exports/stats.json
```

Pretraga po katalogu iz konzole:

```bash
uv run python -c "
from src.db import connect
for r in connect().execute(
    'SELECT name, city, county FROM churches_fts WHERE churches_fts MATCH ? LIMIT 5',
    ('katedrala split',)): print(dict(r))"
```

## Karta

Tri sloja na [gis.domovina.ai](https://gis.domovina.ai/):

**⛪ Crkve** — 6 966 građevina, boja po tipu, župne crkve veće,
katedrale/bazilike/svetišta vidljivi od zoom 7. Popup nosi titular, župu,
biskupiju, zaštitu, godinu, sliku i linkove (web, Wikipedija, OSM).

**🏛 Župe** — 2 928 vjerskih pravnih osoba. **Crveni prsten je župa bez spojene
župne crkve** (489 od 1 563) — te župe u sloju Crkve ne postoje jer za njih
građevine u katalogu nema, pa je ovo jedini prikaz te rupe na karti.

**✝️ Biskupije** — teritoriji 15 latinskih (nad)biskupija, derivirani (vidi
gore). Popup nosi površinu, stanovništvo, broj naselja, župa i crkava, i
**izmjereno slaganje s OSM granicom**. Križevačke eparhije nema jer se
preklapa sa svima.

```bash
make sync-karta                                 # GeoJSON → karta-web/public/data
cd ../karta-hrvatske/apps/karta-web && npm run deploy
```

Implementacija u `karta-hrvatske`: `useCrkveLayer.ts` / `useZupeLayer.ts` /
`useBiskupijeLayer.ts` u `src/hooks/`, toggleovi `showCrkve` / `showZupe` /
`showBiskupije` u `src/lib/MapState.tsx`, gumbi u
`src/components/ControlsPanel.tsx`, tipovi u `src/lib/types.ts`.
`sync-data.mjs` pokupi GeoJSON automatski iz ovog repoa (`SIBLING_LAYERS`).

## Licenca

Kod: **MIT**. Podaci: **ODbL 1.0** za sve što potječe iz OpenStreetMapa
(koordinate, geometrija, OSM tagovi) — OSM nameće share-alike na izvedenu bazu
— i **CC-BY 4.0** za originalni doprinos ovog repozitorija (shema, slugovi,
parsani titulari, klasifikacija, matchevi). Detalji i atribucija izvora:
[`LICENSE-DATA`](LICENSE-DATA).

Katalog opisuje javne građevine i javno registrirane pravne osobe. Netočan
zapis → otvorite issue.

## Pozadina odluka

Mjerenja, odbačene alternative i zamke iz izgradnje — zašto matcher radi baš
tako, zašto Nominatim nije upotrijebljen, kako je Places prvo štetio pa
popravljen: [`docs/2026-08-15-izgradnja-kataloga.md`](docs/2026-08-15-izgradnja-kataloga.md).

Sloj župa i ispravak brojke „župa bez crkve":
[`docs/2026-08-16-sloj-zupe.md`](docs/2026-08-16-sloj-zupe.md).
Zašto su granice biskupija izračunate i kako su izmjerene:
[`docs/2026-08-16-biskupije.md`](docs/2026-08-16-biskupije.md).

## Što još fali

- **923 zaštićena objekta** nemaju para u OSM-u — dio su ruševine, dio posao
  za bolji matcher.
- **489 župa** (od 1 563) nema spojenu župnu crkvu, a **422** nemaju spojenu
  nijednu građevinu. Na karti su to župe s crvenim prstenom u sloju „🏛 Župe".
- **Kontakti župa** (telefon, email, web) — nisu u državnoj evidenciji.
  Telefon i web dolaze uz `make places`; email bi išao Firecrawlom po uzoru na
  `../klubovi.domovina.ai/scripts/04_backfill.py`.
- **121 župa** precizirana Placesom i dalje je >5 km od svog naselja — to su
  višeznačna imena naselja (dvije Privlake, dvoje Selca) gdje sidro nije bilo
  određeno pa distance-filtar nije mogao raditi.
- **40 geo konflikata** čeka ručni pregled (`data/exports/geo-konflikti.csv`).
- **4 crkve dijele `wikidata_id` s vlastitim samostanskim kompleksom** — to je
  tako tagirano u OSM-u (crkva i samostan su dva objekta, jedan Wikidata
  entitet). Nije duplikat i ne smije se dedupati.
- **Zaseban frontend** `crkve.domovina.ai` — po uzoru na
  `../klubovi.domovina.ai/frontend` (React PWA na Cloudflare Pages). Zasad
  postoji samo sloj na zajedničkoj karti.
