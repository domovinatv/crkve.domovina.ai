# TODO — kvaliteta podataka crkve.domovina.ai

Radna lista. Čuva se u repou da napredak preživi između sesija. Označene stavke su gotove
i provjerene (`make test` zelen + `make audit` pokazuje ciljnu brojku). Odluke idu u
[docs/decisions.md](docs/decisions.md).

Plan po sesijama: [docs/plan.md](docs/plan.md). Handoff po sesiji: [docs/handoffs/](docs/handoffs/).

Legenda: `[x]` gotovo · `[ ]` otvoreno · `[~]` u radu · `(!)` traži korisnika · `→ Sn` planirana sesija

## F0 — temelj i mjerenje (ništa javno)

- [ ] `.venv` ponovno izgrađen (`rm -rf .venv && uv sync --group dev`), `uv run pytest` radi → S1
- [ ] CLAUDE.md: tablica karta-weba pokazuje na `src/hooks/use*Layer.ts` i `useLayerControls.ts`/`layers.ts` → S1
- [ ] `scripts/41_audit.py` + `make audit`: ispisuje svaku metriku iz audita 2026-11-20 i piše `data/exports/audit.json` → S1
- [ ] Izmjereno: rebuild iz keša (`make all-places`, bez mreže) daje isti sha `crkve.geojson` kao deployani; ako ne, uzrok zapisan → S1
- [ ] Polazne brojke audita zapisane u `docs/research/2026-11-2x-audit-polazno.md` → S1

## F1 — ispravci u pipelineu (lokalno, bez deploya)

- [ ] `src/denomination.py`: normalizacija konfesije (`catholic`→`roman_catholic`, `orthodox` uz pravoslavni kind → `serbian_orthodox` samo gdje je dokazivo, smeće → NULL); `audit.konfesija_nenormalizirana = 0` → S2
- [ ] Matcher (`src/match.py`, `scripts/11`): građevina se spaja samo na pravnu osobu kompatibilne konfesije; `audit.nekatolicke_na_katolickim = 0` → S2
- [ ] Rijeka, sv. Nikola (`svetog-nikole-rijeka-w437197445`) nije župna crkva katoličke župe; test koji to drži → S2
- [ ] `titular.py`: drugo ime u nizu „X i Y” u nominativ (`sv. Petar i Pavao`); `audit.titular_genitiv = 0`, testovi za 8 izmjerenih oblika → S3
- [ ] Đakovo, Svih Svetih: `kind = crkva` (ime pobjeđuje tag `building=mosque` kad ime kaže crkva) → S3
- [ ] Križevačka eparhija `kind = eparhija` → S3
- [ ] `dioceses.parish_count` = broj `kind='zupa'` (Gospić 85→86, Šibenik 74→75) → S3
- [ ] `Q132087369` na dvije nepovezane građevine: provjereno na Wikidati, krivi zapis odspojen → S3
- [ ] Engleski nazivi (21): odluka i provedba (hr naziv iz `name:hr`/Wikidate, inače ostaje) → S3
- [ ] Node+way duplikati iste zgrade spojeni u jedan zapis (tlocrt pobjeđuje, ID-jevi oba sačuvani); `audit.node_way_duplikati = 0` uz popis namjerno ostavljenih → S4
- [ ] Slug spojenog duplikata: stari URL ne smije dati 404 (redirect ili alias) → S4

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
- [ ] Pokreni dvaput, traži nulu: drugi `make all-places` ne mijenja nijedan export (sha) → S7
- [ ] Deploy svježeg snimka na obje adrese → S7
