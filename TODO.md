# TODO — kvaliteta podataka crkve.domovina.ai

Radna lista. Čuva se u repou da napredak preživi između sesija. Označene stavke su gotove
i provjerene (`make test` zelen + `make audit` pokazuje ciljnu brojku). Odluke idu u
[docs/decisions.md](docs/decisions.md).

Plan po sesijama: [docs/plan.md](docs/plan.md). Handoff po sesiji: [docs/handoffs/](docs/handoffs/).

Legenda: `[x]` gotovo · `[ ]` otvoreno · `[~]` u radu · `(!)` traži korisnika · `→ Sn` planirana sesija

## F0 — temelj i mjerenje (ništa javno)

- [x] `.venv` ponovno izgrađen (`rm -rf .venv && uv sync --group dev`), `uv run pytest` radi → S1
- [x] CLAUDE.md: tablica karta-weba pokazuje na `src/hooks/use*Layer.ts` i `useLayerControls.ts`/`layers.ts` → S1
- [x] `scripts/41_audit.py` + `make audit`: ispisuje svaku metriku iz audita 2026-11-20 i piše `data/exports/audit.json` → S1
- [x] Izmjereno: rebuild iz keša (`make all-places`, bez mreže) daje isti sha `crkve.geojson` kao deployani; ako ne, uzrok zapisan → S1 (ne: 10 župa homonima; `make rebuild` 2× identičan; odluka 100)
- [x] Polazne brojke audita zapisane u `docs/research/2026-11-20-audit-polazno.md` → S1

## F1 — ispravci u pipelineu (lokalno, bez deploya)

- [x] `src/denomination.py`: normalizacija konfesije (`catholic`→`roman_catholic`, `orthodox` uz pravoslavni kind → `serbian_orthodox` samo gdje je dokazivo, smeće → NULL); `audit.konfesija_nenormalizirana = 0` → S2
- [x] Matcher (`src/match.py`, `scripts/11`): građevina se spaja samo na pravnu osobu kompatibilne konfesije; `audit.nekatolicke_na_katolickim = 0` → S2
- [x] Rijeka, sv. Nikola (`svetog-nikole-rijeka-w437197445`) nije župna crkva katoličke župe; test koji to drži → S2
- [x] `titular.py`: drugo ime u nizu „X i Y” u nominativ (`sv. Petar i Pavao`); `audit.titular_genitiv = 0`, testovi za 8 izmjerenih oblika → S3
- [x] Đakovo, Svih Svetih: `kind = crkva` (ime pobjeđuje tag `building=mosque` kad ime kaže crkva) → S2 (odluka 203)
- [x] Križevačka eparhija `kind = eparhija` → S3
- [x] `parish_count_razlika`: podatak je točan (aktivne+različite; odluka 104) — uskladi metriku i prikaz u `34`, ne broj → S3
- [x] `Q132087369` na dvije nepovezane građevine: provjereno na Wikidati, krivi zapis odspojen → S3
- [x] Engleski nazivi (32 po `make audit`: 20 Wikidata, 12 OSM): odluka i provedba (hr naziv iz `name:hr`/Wikidate, inače ostaje) → S3
- [x] Titular „B.” (ŽUPA SV. NIKOLE B., Rijeka) i obrnuti red „Isusova uskrsnuća” u `head_key`; Rijeka sv. Nikola nema nijednu građevinu → S3
- [x] `scripts/03`: 20 „MANASTIR” zapisa klasificirano kao `eparhija` → S3
- [ ] Pravoslavne pravne osobe: spajanje po naselju (172 jednoznačna para, uzorak 20: 17 točno, 0 krivo, 3 nejasno) + 14 građevina nepoznate konfesije koje prolaz 2 veže na SPC općine; zasebna stavka poslije S3 (odluka 206) → otvoreno
- [x] Regresije S3: Knežija Q133733258 stopljena u BDM Pomoćnice; Z-834 Mali Lug → S4 (odluke 405–406: marijanski zaziv proturječi, ne ulazi u ključ)
- [ ] Otvoreno iz S3 (pregledano u S4, presude u `docs/research/2026-11-20-s4-titular.md`, koda nema): Z-2014 Šibenik→Žaborić (vjerojatno krivo), Z-2282 Granešina (treba ručni override), Bjelovar Gospe Lurdske (3 kandidata 100), Mesdžid Split Q12627803 (Wikidata prostorni spoj ne gleda tip); plus „Gospe od Karmela”≠„Gospe Karmelske”, „Bezgrješnog” → poslije S5
- [ ] Frontend `/biskupije` „Ostale zajednice” zove `parish_count` „pravne osobe”; karta-web `useBiskupijeLayer.ts:201` eparhiju zove „Biskupija” → S5/S6
- [x] Node+way duplikati iste zgrade spojeni u jedan zapis (tlocrt pobjeđuje, ID-jevi oba sačuvani); `audit.node_way_duplikati = 0` uz popis namjerno ostavljenih → S4 (73 spojena, 45 ostavljeno; odluke 400–404)
- [x] Slug spojenog duplikata: stari URL ne smije dati 404 (redirect ili alias) → S4

- [x] Đakovo Svih Svetih (`kind=dzamija`) blokira `nekatolicke_zupne_crkve = 0` u S2 — S2 ispravlja kind ili čeka S3 → S2

## F2 — koordinate bez Googlea

- [ ] `src/dgu.py` (iz `../oou.domovina.ai/src/dgu.py`) + korak koji geokodira adrese župa; `geocode_source='dgu'` → S5
- [ ] Places ostaje samo interna provjera: `lat/lng` i `google_maps_uri` iz Placesa ne izlaze ni u jedan export; `audit.places_koordinate_u_exportu = 0`; isto za `phone` i `website` iz Placesa → S5
- [ ] Izmjereno: DGU vs Places na istim župama (medijan, p90 udaljenosti, udio pogodaka) → S5
- [ ] karta-web i frontend prilagođeni promjenama svojstava (tipovi, popup „izvor koordinata”) → S5

## F3 — objava

- [ ] (!) Korisnik odobrio deploy ispravljenog snimka → S6
- [ ] (!) Korisnik odlučio o Places koordinatama u git povijesti `data/exports/` (odluka 10) → S6
- [ ] Deploy crkve.domovina.ai + gis.domovina.ai, žive brojke = lokalni `audit.json` → S6
- [ ] (!) Korisnik odobrio svjež ingest (mreža: Overpass, data.gov.hr, Wikidata) → S7
- [ ] Svjež ingest, diff starog i novog snimka zapisan, `make audit` i dalje na ciljnim nulama → S7
- [ ] `10_match_heritage` ponovljiv na spojenoj bazi (sad ga štiti samo `clean-db`; odluka 105) → S7
- [ ] `frontend/public/data/manifest.json` `generated_at` jedini nedeterministički izlaz → S7
- [ ] Pokreni dvaput, traži nulu: drugi `make all-places` ne mijenja nijedan export (sha) → S7
- [ ] Deploy svježeg snimka na obje adrese → S7
