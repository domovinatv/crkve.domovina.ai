# CLAUDE.md — crkve.domovina.ai

Orijentacija za agente koji rade u ovom repozitoriju. Drži je aktualnom.

## Što je ovo
Single-source-of-truth **katalog svih crkava i sakralnih objekata u Hrvatskoj**
— građevine (koordinate, titular, zaštita, slika) i pravne osobe (župe,
samostani, crkvene općine, s OIB-om i biskupijom). Otvoreni podaci, potpuno
reproducibilno iz javnih izvora, **bez ijednog API ključa**.

Tech stack namjerno blizak sestrinskim projektima `../klubovi.domovina.ai` i
`../rodjendaonice.domovina.ai` (Python pipeline → SQLite → GeoJSON/CSV), a
karta je layer u `../karta-hrvatske/apps/karta-web` (gis.domovina.ai).

## Repo layout
```
src/         moduli: db, normalize, kinds, titular, match, geo_hr,
             overpass (OSM), datagovhr (CKAN), wikidata, nominatim
scripts/     numerirani pipeline 00→40 (vidi `make help`)
data/        crkve.db (SQLite, gitignored), raw/ keš, exports/ (GeoJSON+CSV)
tests/       pytest — titular, kinds, match (najrizičniji dijelovi)
Makefile     `make all` = cijeli pipeline od nule
```

## Model podataka — DVIJE tablice, ne jedna
| | `churches` | `parishes` |
|---|---|---|
| što je | **građevina** | **pravna osoba** |
| izvor | OSM, Wikidata, Registar kulturnih dobara | data.gov.hr evidencije |
| ključ | `slug` (+ `osm_type`/`osm_id`) | `slug` (+ `oib`/`registry_id`) |
| koordinate | 100% | tek nakon 11/12 |

Veza je N:1 (`churches.parish_id`, `is_parish_church`). Razdvojeno je jer
**to nisu isti skupovi**: ~1560 župa naspram ~6900 građevina — jedna župa ima
župnu crkvu + filijale + kapele, a mnoga crkva (samostanska, grobljanska,
poklonac) nema župu. `dioceses` drži (nad)biskupije i nekatoličke zajednice.

## Izvori (svi javni, bez ključa)
- **OSM Overpass** — `amenity=place_of_worship` + `building=church|chapel|…` +
  `amenity=monastery` + `historic=church|wayside_shrine`. Jedini izvor s
  koordinatama za sve; ~5200 zapisa su tlocrti (way/relation), ne točke.
  Overpass vraća **406 bez User-Agenta**.
- **data.gov.hr / Ministarstvo pravosuđa i uprave** — Evidencija pravnih osoba
  Katoličke Crkve (~2100, od toga 1563 ŽUPA) + Evidencija vjerskih zajednica
  (54 zajednice + 863 org. oblika). Jedini strojno čitljiv popis župa u RH;
  crkveni šematizmi su per-biskupija i u PDF-u.
- **data.gov.hr / Ministarstvo kulture i medija** — Registar kulturnih dobara,
  2038 sakralnih zapisa. **Nema koordinate** → spaja se heuristikom (scripts/10).
- **Wikidata SPARQL** (CC0) — slike s Commonsa, Wikipedija, arhitekt, godina.
- **Granice biskupija NE POSTOJE kao javan podatak** — OSM ih ima 3 od 15,
  Wikidata nijednu. Zato ih `scripts/20` derivira iz sjedišta župa preko
  granica naselja, a te 3 OSM relacije služe kao mjera (96,6–98,6 %).
- **Nominatim** — samo sjedišta župa koje nisu naslijedile koordinate crkve.
- **Google Places (New)** — JEDINI izvor s ključem, i **nije** u `make all`
  nego u `make places` (scripts/13). Nije geocoder za crkve (OSM je bolji,
  daje tlocrte) nego: (a) precizira 1652 župe koje leže na težištu naselja,
  (b) **nezavisno provjerava matcher** — usporedi Places točku župe s crkvom
  na koju smo je spojili; ≤300 m potvrda, >750 m u `geo_conflicts`. Oboje iz
  istog poziva; 2359 poziva ukupno, keširano.

## Pipeline
`make all` = `init → ingest (01–05) → match (10–12 + fix-locations) →
derive (20) → export (30–32) → sync-karta (33) → stats (40)`. Sve je idempotentno; sirovi
odgovori se kešraju u `data/raw/<izvor>/<sha>.json` pa drugi run ne dira
mrežu (`make clean-cache`
za prisilni refresh). Korak 20 mora doći poslije 12 (bez koordinata župa nema
se od čega derivirati) i prije 31.

Redoslijed 11 → 12 je bitan: `11_match_parishes` daje župi koordinate **njezine
crkve** (točno), a `12_geocode_parishes` tek ostatak gura na Nominatim (sporo,
1 req/s; ~30 min za ~1800 župa).

`make fix-locations` (= `14_fix_parish_locations` pa **ponovo** 11) ide na
kraj, poslije Placesa: 13 je zadnji korak koji dira koordinate župa, pa bi
ranija korekcija bila pregažena. 11 se ponavlja jer premještena župa mijenja
skup svojih crkava; smije se ponavljati jer resetira `parish_id` na početku i
piše koordinate kroz `COALESCE` (ne gazi ono što je 14 upisao).

## Karta (gis.domovina.ai)
`scripts/33_sync_karta.py` prepiše `crkve.geojson`, `zupe.geojson` i
`biskupije.geojson` u `../karta-hrvatske/apps/karta-web/public/data/`. Svaki
sloj ondje ima hook + toggle u `src/lib/MapState.tsx` + gumb u
`src/components/ControlsPanel.tsx` + tipove u `src/lib/types.ts`:

| Gumb | Hook | Toggle | Tip |
|---|---|---|---|
| ⛪ Crkve | `useCrkveLayer.ts` | `showCrkve` | `CrkvaProperties` |
| 🏛 Župe | `useZupeLayer.ts` | `showZupe` | `ZupaProperties` |
| ✝️ Biskupije | `useBiskupijeLayer.ts` | `showBiskupije` | `BiskupijaProperties` |

Deploy: `cd ../karta-hrvatske/apps/karta-web && npm run deploy`.

**Župe:** crta pravne osobe (ne građevine), a **crveni prsten je župa bez
spojene župne crkve** — 487 od 1561. To je jedini prikaz te rupe u podacima: u
sloju Crkve takva župa naprosto ne postoji. Prsten ide u dva sloja (bijela
podloga pa crveni prsten) jer je ispod njega ispuna JLS-a proizvoljne boje —
jednobojni prsten se u nekoj županiji/temi uvijek stopi s podlogom.

**Biskupije:** jedini poligoni i jedini DERIVIRANI sloj, pa popup piše kako je
granica nastala i koliko se slaže s OSM-om. Dok je uključen, JLS ispuna pada
na prigušeni preset (mutacija živi u `useJlsLayer`, sloju koji tu ispunu
posjeduje) — dvije teritorijalne podjele s punom ispunom daju mulj.

**GeoJSON-i su gitignored u karta-web** — regeneriraju se, ne commitaju.

## Vlastiti frontend (`frontend/`)
TanStack Start + Nitro → Cloudflare **Worker** (`crkve-domovina`), shadcn/ui +
Tailwind v4. Nastao iz `../../stepanic/hr-site-starter`. Vlastite konvencije i
zamke: **`frontend/CLAUDE.md`**; kako je nastao i zašto ovaj stack:
**`docs/2026-08-28-frontend-tanstack.md`**.

Podatke mu piše `scripts/34_export_static.py` (`make export-web`, ide POSLIJE
`stats`) u `frontend/public/data/` — 9400 datoteka, gitignorane.
Deploy: `cd frontend && ./scripts/deploy.sh`.

Dvije jedinice stranice, kao i u bazi: `/crkva/$slug` je građevina,
`/zupa/$slug` i `/ustanova/$slug` su pravna osoba. `/ustanova/` postoji jer
samostan i crkvena općina nisu župe.

## Gotchas (naučeno na teži način)
- **Križevačka eparhija ne smije u particiju biskupija** — grkokatolička je,
  teritorij joj se preklapa sa svim latinskima, a 35 župa joj je razasuto po
  zemlji. `dioceses.OVERLAPPING_SLUGS` je izuzima; bez toga oko svake svoje
  župe otme komad susjedne biskupije.
- **`queryRenderedFeatures` vraća 0 za symbol slojeve i za krugove prozirne
  ispune** koji se uredno crtaju. Dvaput izgubljeno vrijeme na lažni negativ —
  rendering se provjerava okom (screenshot), ne tim pozivom.
- **`make all` nakon `make places` briše Places rezultate** — `all` ne
  uključuje korak 13, pa `geo_verified` i `geo_conflicts` ostanu prazni.
  Za ponovni export poslije Placesa: `make derive export sync-karta stats`.
- **„Župa bez crkve" su DVIJE različite brojke**, i nijedna nije `1563 −
  zupne_crkve`: 77 župnih crkava pripada pravnim osobama koje nisu `zupa`
  (samostani, svetišta), pa ta razlika daje krivih 412. Točno je **487 župa
  bez spojene župne crkve** i **421 bez ijedne spojene građevine**
  (`zupe_bez_zupne_crkve`, `zupe_bez_ijedne_crkve` u `scripts/40`).
- **`church_count` se u exportu ZADRŽAVA i kad je 0**, za razliku od zastavica
  u `_DROP_IF_ZERO`: nula je nalaz („nema nijedne spojene građevine"), a ne
  „nema podatka". Izostavljanjem bi rupa u podacima postala nevidljiva.
- **723 katoličke pravne osobe nemaju OIB**, a naziv+mjesto nije jedinstven
  (dvije zagrebačke „ŽUPA SV. MARKA EVANĐELISTE"). Slug sufiks je OIB, a ako
  ga nema — `SBT_ID`. Bez toga se 6 zapisa tiho gubi.
- **Titular se uspoređuje po GLAVI, ne po punom nazivu** (`titular.head_key`):
  isti objekt je „sv. Ante" (OSM), „sv. Ante Padovanskog" (MinKulture) i
  „SV. ANTUNA PADOVANSKOG" (evidencija). Tvrdi filtar na puni titular obara
  match rate s ~53% na ~42%.
- **Državna evidencija skraćuje marijanske titulare** („UZNESENJA B.D.
  MARIJE", „POHOĐENJA BDM", „PRESV. TROJSTVA"), a MinKulture koristi
  pridjevski oblik („Uznesenja Marijina"). Konstanta `_BDM` u `titular.py`
  pokriva sve oblike — bez nje 229 od 1563 župa ostane bez titulara.
- **`GENERIC_TITULARS` u `match.py`**: „Majka Božja" je catch-all za SVE
  marijanske zazive, pa „Gospa od Utjehe" i „Gospa od Batka" dobiju isti
  ključ. Za bonus na score to je u redu, ali pravilo jedinstvenosti mora ga
  odbiti — inače nastane 5 lažnih spojeva (izmjereno).
- **Pravilo jedinstvenosti** (`_unique_by_titular_and_kind`) hvata slučajeve
  gdje se nazivi potpuno raziđu: „Kompleks Katedrale Uznesenja Marijina" vs
  „katedrala Uznesenja BDM i svetih Stjepana i Ladislava" daju score 54, ali
  u Zagrebu je samo jedna katedrala tog titulara. Donosi 37 spojeva.
- **Wikidata P18 vraća `http://`** — na HTTPS karti to je blokiran mixed
  content i slika se nikad ne prikaže. `wikidata.commons_url` radi upgrade.
- **MapLibre `case` traži boolean.** `["case", ["get", "is_parish_church"], …]`
  s brojem 0/1 baca „Expected boolean but found number" i **obori cijeli sloj
  bez greške vidljive na karti**. Uvijek `["==", ["get", …], 1]`.
- **FTS5 bez `content=`**: mjesto se indeksira kao `COALESCE(city, settlement,
  municipality)`, a external-content tablica pretpostavlja da su indeksirane
  vrijednosti identične izvornima — razišlo bi indeks i sadržaj.
- **Places Text Search UVIJEK nešto vrati** — bez filtra u katalog uđu kafići
  i trgovine iz istog mjesta. `places.pick()` traži sakralni `types` (ili vrlo
  sličan naziv) **i** poklapanje županije nad DGU granicama. Bbox oko HR je
  pregrub: obuhvaća i Ljubljanu i Sarajevo.
- **Sidro (`anchor`) je najvažniji filtar u `places.pick()`** — rezultat mora
  biti unutar 15 km od poznate pozicije župe. Bez njega je 24 % preciziranih
  župa završilo >5 km od vlastitog naselja („BEBRINA" u Slavoniji → Brseč u
  Istri, 282 km). Filtar po županiji to NE hvata jer 1202 župe nemaju upisanu
  županiju — zato `scripts/12` sad prostorno popunjava `parishes.county` PRIJE
  Placesa. Redoslijed 12 → 13 je zbog toga obavezan.
- **Konflikti nisu greške matchera.** Od 40 preostalih, većina je druga zgrada
  iste župe (župni ured, pastoralni centar, samostan). Zato `geo_conflicts`
  ništa ne mijenja automatski — to je red za pregled, ne popravak.
- **Sidro NE SMIJE biti crkva koju provjeravamo** (`_anchor` vraća težište
  naselja). S crkvom kao sidrom provjera postaje kružna: rezultat koji joj
  proturječi odbaci se prije nego postane konflikt. Izmjereno oboje —
  1083/39 s crkvom, 1083/40 s naseljem; razlika je zanemariva, ali samo je
  druga brojka poštena tvrdnja o „nezavisnoj provjeri".
- **`13_places_parishes` mora biti ponovljiv** — briše raniji konflikt i
  resetira `geo_verified` za župu prije novog ishoda. Bez toga drugi run bez
  rebuilda duplicira konflikte i ostavlja zaglavljene potvrde.
- **4 crkve dijele `wikidata_id` sa svojim samostanom** — OSM tako tagira
  (crkva i samostanski kompleks = dva objekta, jedan Wikidata entitet).
  Očekivano, nije duplikat.
- **Places 403 ima tri različita uzroka** (IP restrikcija ključa / referrer
  restrikcija / API nije uključen) i tri različita rješenja —
  `places._explain_403` ih razlikuje da se ne gubi vrijeme na pogrešnom.
  Stanje 2026-08-15: ključ `../rodjendaonice.domovina.ai` (projekt
  **738176355812**, ključ „Maps Platform API Key", uid `d126c763-bd0a-4a21-…`)
  je odblokiran dodavanjem IP-a u allowlist — u njoj su sad `89.201.137.96`
  (stari, NE brisati) i `89.164.104.204`. `--allowed-ips` zamjenjuje cijelu
  listu, pa kod idućeg IP-a navedi SVE. Ključ `../klubovi.domovina.ai` i dalje
  vraća PERMISSION_DENIED (Places API (New) nije uključen na tom projektu).
- **Validacija Placesa živi u `src/places.py`, ne u skripti** — modul čije ime
  počinje brojkom (`13_…`) ne može se importati u testove.
- **Nominatim je neupotrebljiv za masovno geokodiranje** (javni endpoint ~5 s
  po upitu × do 5 kandidata po župi = 10+ sati). Zamijenjen težištem naselja
  iz DGU granica: 1,5 s za sve, točnost razine mjesta. Nominatim ostaje iza
  `--nominatim` flaga.
- **Ime mjesta nije identitet mjesta.** Dva Kostanjevca, tri Zagorja, dvije
  Vrane, dva Sveta Vida. `12`/`13` su župe znale spustiti na krivi homonim
  (Barbat s Paga sjeo na Rab i obojao pola otoka zadarskim), a `11` je crkve
  vezao na župu 180 km daleko. Otud `src/parish_geo.py` + `scripts/14` i prag
  `MAX_FILIJALA_KM = 25`.
- **Prag „koliko župa otvara županiju biskupiji" je 1, ne 2** — i to je
  izmjereno, ne lijenost. S 2 je Riječka nadbiskupija gubila Istarsku (ondje
  ima točno jednu župu, Vodice/Lanišće) pa ju je korekcija htjela odseliti
  58 km. S 1 se usamljena kriva župa može sama zaštititi — te idu u
  `parish_geo.OVERRIDES`, svaka s izvorom.
- **Izvod županija računa se nad ISPRAVLJENIM odredištima** (`_override_county`).
  Inače prvi run broji bujsku Krasicu u Istarsku, drugi ne — pa se dozvoljene
  županije mijenjaju između runova i korekcija kaskadno mijenja odluke.
- **Koordinata koja nije ni blizu imenovanog naselja BRIŠE SE**, i kad se ne
  zna prava (`parish_geo.Drop`, prag `MAX_SJEDISTE_KM = 30`). Prazna
  koordinata je poštena; točka 314 km od svakog Prgomelja na karti izgleda
  jednako uvjerljivo kao sve ostale. Prag je izmjeren: ispod 30 km upada
  Žirje (upisano na „Šibenik", a otok je 22 km od grada). Ovo je i jedini
  filtar koji uopće gleda **Križevačku eparhiju** — nju izvod županija
  preskače (`_SKIP_DIOCESE`), pa joj inače nitko ne provjerava sjedišta.
- **`duplicate_of` je NAŠA prosudba, ne podatak iz evidencije** — zato
  zasebna kolona, a ne izmišljen `registry_status`: država za oba upisa
  doista piše AKTIVAN. Signatura je stroga (isti kind+naziv+mjesto+adresa,
  nijedan bez OIB-a) jer labavija tiho gubi 6 stvarnih zapisa. Pogađa točno
  1 župu (ŽUPA SV. STJEPANA, Prgomet).
- **„1563 katoličke župe" je broj ZAPISA, ne župa** — jedan je ugašen
  (PRESTANAK, Prizna), jedan je duplikat (Prgomet). Aktivnih i različitih je
  **1561** (`zupe_aktivne` u `scripts/40`).
- **Točka naselja mora biti provjereno UNUTAR naselja.** Težište razvedenog
  („U") naselja pada van, a fallback na prvi vrh poligona leži NA granici gdje
  point-in-polygon vraća False: 84 od 6759 naselja tvrdilo je da ne sadrži
  samo sebe. Zbog toga je override za Sveti Vid-Miholjice na svakom runu
  iznova gazio koordinatu razine zgrade. `parish_geo.representative_point()`.
- **Blokiranje po mjestu ide u dvije razine** (naselje, pa općina) i **ne
  miješa se**: općina Vrgorac ima 25 crkava u dvadesetak sela i nikad ne dade
  jasnog pobjednika, dok naselje Dragljane ima jednu.
- **Naselje se dodjeljuje prostorno** iz `../karta-hrvatske` naselja.geojson,
  ne iz OSM `addr:*` (prerijetki). Bez susjednog repoa (`KARTA_DATA_DIR`)
  pipeline radi, ali matching padne jer nema po čemu blokirati.
- **`_upsert` koristi `COALESCE(excluded.x, table.x)`** — kasniji izvor ne
  smije obrisati polje koje je raniji popunio (Wikidata nakon OSM-a).
- **Na Workeru `fetch` na vlastiti origin NE dohvaća assete** nego se vrati u
  sam Worker. SSR loader koji tako čita `/data/*` dobije 404, pa svaka
  stranica s loaderom postane 404 — a one bez loadera rade, što skriva uzrok.
  Ispravno je `env.ASSETS.fetch()` (`frontend/src/lib/data.ts`). Lokalni
  `bun run dev` to NE hvata; `wrangler dev --local` hvata.
- **Licenca podataka nije čisti CC-BY** — OSM je ODbL i nameće share-alike na
  izvedenu bazu. Vidi `LICENSE-DATA`.

## Zašto je nešto tako — pozadina odluka
Mjerenja koja su odredila pragove, alternative koje su probane pa odbačene
(Nominatim, model s jednom tablicom, crkva kao sidro) i zamke koje su koštale
vremena: **`docs/2026-08-15-izgradnja-kataloga.md`**. Sloj „🏛 Župe" i
ispravak brojke „župa bez crkve": **`docs/2026-08-16-sloj-zupe.md`**.
Zašto su granice biskupija izračunate i kako su izmjerene:
**`docs/2026-08-16-biskupije.md`**. Zašto 923 nespojena baštinska zapisa nisu
rupa u OSM-u nego odluka matchera, i koju dijagnozu napraviti prije izmjene:
**`docs/2026-08-17-bastina-nespojeno.md`**. Kako je homonim naselja obojao Rab
u zadarsko i zašto je korekcija dvaput bila neidempotentna:
**`docs/2026-08-17-revizija-lokacija-zupa.md`**. Kako je nastao vlastiti
frontend, zašto TanStack Start umjesto SPA + Pages iz starijeg plana, i zamka
s assetima na Workeru: **`docs/2026-08-28-frontend-tanstack.md`**. Ako mijenjaš
matcher, Places validaciju ili derivaciju granica, pročitaj to prije nego
"popraviš" nešto što je namjerno.

## Otvoreno / sljedeći koraci
- **`heritage_unmatched`** — ostatak zaštićene baštine bez para (izvozi se u
  `data/exports/bastina-nespojeno.csv`). Izmjereno: **za 922 od 923 blok
  kandidata NIJE bio prazan** (821 ima građevina u vlastitom naselju, 101 u
  općini, samo 1 nigdje), pa je „nema toga u OSM-u" pogrešno objašnjenje —
  matcher je gledao pa odbio. Prije mijenjanja pragova napravi dijagnozu faze
  u kojoj `best_match` odustaje: **`docs/2026-08-17-bastina-nespojeno.md`**.
- **Župe bez crkve** — evidencija ima župu, OSM nema odgovarajuću građevinu.
  487 bez župne crkve, 421 bez ijedne; na karti su crveni prsten u sloju Župe.
- **Kontakti župa** (telefon/email/web) — nisu u državnoj evidenciji; išlo bi
  Firecrawlom po uzoru na `../klubovi.domovina.ai/scripts/04_backfill.py`.
- **Domena `crkve.domovina.ai`** — frontend je živ na
  `https://crkve-domovina.d-o-m.workers.dev`, ali domena još nije zakačena
  (Workers → crkve-domovina → Domains & Routes).
