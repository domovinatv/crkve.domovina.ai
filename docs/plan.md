# Plan: kvaliteta podataka crkve.domovina.ai (studeni 2026.)

## Zašto

Audit 2026-11-20 (sesija S0) našao je u deployanim podacima sustavne greške koje ranije
revizije nisu hvatale, jer su provjeravale **lokacije**, a ne **značenje veza**:
nekatoličke građevine spojene na katoličke župe, titulare s drugim imenom u genitivu,
nenormaliziranu konfesiju, iste zgrade upisane dvaput (OSM točka + tlocrt) i koordinate
iz Google Placesa objavljene pod otvorenom licencom. Snimak izvora je od 2026-08-15.
Cilj lanca: ispraviti to u pipelineu (ne ručno u bazi), izmjeriti, objaviti na
crkve.domovina.ai i gis.domovina.ai, pa osvježiti izvore.

## Gdje se što mijenja

| Sloj | Datoteke | Tko čita |
|---|---|---|
| Normalizacija | `src/kinds.py`, `src/titular.py`, novi `src/denomination.py` | 01–05 ingest |
| Matcher | `src/match.py`, `scripts/11_match_parishes.py` | 11, 14 |
| Dedup | `scripts/01_ingest_osm.py` ili novi korak prije 10 | sve poslije |
| Koordinate | novi `src/dgu.py`, `scripts/12`, `scripts/13` | 14, 20, export |
| Export | `scripts/31`, `32`, `34`, `33_sync_karta.py` | frontend, karta-web |
| Mjerenje | novi `scripts/41_audit.py`, `make audit` | svaka sesija |

## Tvrdi uvjeti (svaka sesija)

- Ispravak živi u pipeline kodu i preživi `make all-places` iz keša. Ručni `UPDATE` u
  `data/crkve.db` nije ispravak.
- Rebuild iz keša ne dira mrežu. Mreža (svjež ingest, DGU, deploy) samo gdje paket kaže.
- `make test` zelen, `skipped 0`; svaka nova pravila imaju test na izmjerenim primjerima.
- Brojka u TODO-u, planu ili handoffu ima naredbu (`make audit` ili SQL) iz koje dolazi.
- Gotchas iz `CLAUDE.md` (titular po glavi, `GENERIC_TITULARS`, sidro ≠ vlastita crkva,
  `make all` briše Places…) vrijede. Prije izmjene matchera pročitaj
  `docs/2026-08-15-izgradnja-kataloga.md`.
- Deploy je vanjska radnja: samo iza vrata (S6, S7).

## Sesije

| # | Faza | Paket | Odluke | Gotovo kad |
|---|---|---|---|---|
| S1 | F0 | venv, CLAUDE.md, `make audit`, mjerenje reproducibilnosti | 100–199 | `make audit` ispisuje sve metrike; polazne brojke u `docs/research/`; rebuild iz keša = deployani sha (ili uzrok zapisan) |
| S2 | F1 | konfesija: normalizacija + pravilo u matcheru | 200–299 | `audit`: `konfesija_nenormalizirana = 0`, `nekatolicke_na_katolickim = 0`; spojenih župa ne pada za više od broja odspojenih nekatoličkih |
| S3 | F1 | titulari + sitnice (Đakovo, eparhija, parish_count, Wikidata, engleski nazivi) | 300–399 | `audit`: `titular_genitiv = 0`, `parish_count_razlika = 0`; testovi za svaki oblik |
| S4 | F1 | node+way duplikati | 400–499 | `audit.node_way_duplikati = 0` (osim popisa namjerno ostavljenih); stari slugovi ne daju 404 |
| S5 | F2 | DGU umjesto Placesa za objavljene koordinate | 500–599 | `audit.places_koordinate_u_exportu = 0`; DGU vs Places izmjereno; karta-web/frontend `typecheck` zelen |
| S6 | F3 | (!) deploy ispravljenog snimka | 600–699 | žive datoteke na obje adrese imaju sha lokalnog exporta; `deploy.sh` provjere zelene |
| S7 | F3 | (!) svjež ingest + dvaput-nula + deploy | 700–799 | diff snimaka zapisan; drugi run ne mijenja nijedan export; deploy |

**Procjena:** 7 sesija. **Vrata:** S6 (deploy) i S7 (mreža + deploy). **Paralelno:**
S3 i S4 ne dijele datoteke (titular/kinds vs. ingest OSM-a), ali obje mijenjaju
brojke koje mjere sve sljedeće sesije, pa se rade redom. **Najrizičnije:** S2 (pravilo
konfesije smije odspojiti samo krive veze; 2245 građevina nema konfesiju i ne smiju
pasti) i S5 (DGU pogađa ~87 % kućnih brojeva na drugom skupu; na adresama župa nije
izmjereno, a ostatak pada na težište naselja, što je gore od Placesa).

Trošak: nijedan paket ne koristi LLM petlje. Jedini mrežni trošak je DGU (besplatan,
bez kvote) u S5 i svjež ingest u S7. Google Places se u ovom lancu ne poziva.

## Gdje smo

S0 (2026-11-20, 5e8c36c): audit napravljen, plan napisan.
S1 (2026-11-20): `make audit` (11 metrika), `make rebuild` (od nule, offline, 2× identičan),
odluke 100–105. Polazne brojke: `docs/research/2026-11-20-audit-polazno.md`.
S2 (2026-11-20, 555c02a): `src/denomination.py`, `match.compatible`, slabi zahtjevi zadnji
(Trsat); konfesijske metrike na 0, odluke 200–206. Mjerenje: `docs/research/2026-11-20-s2-konfesija.md`.
S3 (2026-11-20, 4cc8ccf): titulari „X i Y” u nominativu, Tavelić u glavi, mjesto iz naziva
pravne osobe, BDM → Majka Božja, spor oko građevine dobiva pravna osoba iz istog naselja,
eparhija/manastiri, `osm_fixes`, hrvatski nazivi; `titular_genitiv` 302→0, `parish_count_razlika`
2→0, `wikidata_dijeljen` 4→3. Odluke 300–313, 314 povučena (Wikidata duplikati → S4). Mjerenje:
`docs/research/2026-11-20-s3-titulari.md`, `docs/research/2026-11-20-s3-rebuild.md`.
S4 (2026-11-20/21, a51eee0): dedup OSM node+way u `src/dedup.py` (kraj `01`, prije `05`),
uloga + spojiv naziv + ≤20 m, identitet točke u `church_merged`, stari slug → 301; marijanski
zaziv proturječi u `05`/`10` (Knežija, Z-834). `node_way_duplikati` 40→0 (73 spojena, 45
ostavljeno), crkava 6961→6890. Odluke 400–406. Mjerenje: `docs/research/2026-11-20-s4-dedup.md`,
`docs/research/2026-11-20-s4-titular.md`.
Sljedeća je S5.
