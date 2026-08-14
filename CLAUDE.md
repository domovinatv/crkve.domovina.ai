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
- **Nominatim** — samo sjedišta župa koje nisu naslijedile koordinate crkve.

## Pipeline
`make all` = `init → ingest (01–05) → match (10–12) → export (30–32) →
sync-karta (33) → stats (40)`. Sve je idempotentno; sirovi odgovori se kešraju
u `data/raw/<izvor>/<sha>.json` pa drugi run ne dira mrežu (`make clean-cache`
za prisilni refresh).

Redoslijed 11 → 12 je bitan: `11_match_parishes` daje župi koordinate **njezine
crkve** (točno), a `12_geocode_parishes` tek ostatak gura na Nominatim (sporo,
1 req/s; ~30 min za ~1800 župa).

## Karta (gis.domovina.ai)
`scripts/33_sync_karta.py` prepiše `crkve.geojson`/`zupe.geojson` u
`../karta-hrvatske/apps/karta-web/public/data/`. Tamo je sloj:
`src/hooks/useCrkveLayer.ts` + toggle `showCrkve` u `src/lib/MapState.tsx` +
gumb „⛪ Crkve" u `src/components/ControlsPanel.tsx` + tipovi `CrkvaProperties`
u `src/lib/types.ts`. Deploy: `cd ../karta-hrvatske/apps/karta-web && npm run deploy`.

**GeoJSON-i su gitignored u karta-web** — regeneriraju se, ne commitaju.

## Gotchas (naučeno na teži način)
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
- **Nominatim je neupotrebljiv za masovno geokodiranje** (javni endpoint ~5 s
  po upitu × do 5 kandidata po župi = 10+ sati). Zamijenjen težištem naselja
  iz DGU granica: 1,5 s za sve, točnost razine mjesta. Nominatim ostaje iza
  `--nominatim` flaga.
- **Blokiranje po mjestu ide u dvije razine** (naselje, pa općina) i **ne
  miješa se**: općina Vrgorac ima 25 crkava u dvadesetak sela i nikad ne dade
  jasnog pobjednika, dok naselje Dragljane ima jednu.
- **Naselje se dodjeljuje prostorno** iz `../karta-hrvatske` naselja.geojson,
  ne iz OSM `addr:*` (prerijetki). Bez susjednog repoa (`KARTA_DATA_DIR`)
  pipeline radi, ali matching padne jer nema po čemu blokirati.
- **`_upsert` koristi `COALESCE(excluded.x, table.x)`** — kasniji izvor ne
  smije obrisati polje koje je raniji popunio (Wikidata nakon OSM-a).
- **Licenca podataka nije čisti CC-BY** — OSM je ODbL i nameće share-alike na
  izvedenu bazu. Vidi `LICENSE-DATA`.

## Otvoreno / sljedeći koraci
- **`heritage_unmatched`** — ostatak zaštićene baštine bez para (izvozi se u
  `data/exports/bastina-nespojeno.csv`). Dio su ruševine i objekti kojih u
  OSM-u nema; dio je posao za bolji matcher ili ručno mapiranje.
- **Župe bez crkve** — evidencija ima župu, OSM nema odgovarajuću građevinu.
- **Kontakti župa** (telefon/email/web) — nisu u državnoj evidenciji; išlo bi
  Firecrawlom po uzoru na `../klubovi.domovina.ai/scripts/04_backfill.py`.
- **Zaseban frontend crkve.domovina.ai** — po uzoru na
  `../klubovi.domovina.ai/frontend` (React PWA, Cloudflare Pages). Nije rađen.
