# Handoffi za sesije S1–S7 (kvaliteta podataka)

Plan je u [`docs/plan.md`](../plan.md), odluke u [`docs/decisions.md`](../decisions.md).
Svaka sesija ima svoj handoff `SN.md`. Korisnik nakon `/clear` kaže „nastavi kvalitetu
podataka” (ili „nastavi zadnji handoff”) ili zalijepi prompt iz clipboarda.

## Lanac

1. Sesija N počinje iz `docs/handoffs/SN.md`.
2. Sesija N radi svoj paket po pravilima ispod.
3. Na kraju sesija N:
   - označi `SN` u tablici „Stanje lanca” (commit, testovi, ključne `audit` brojke) i
     stavke u `TODO.md`;
   - **ako je naučila nešto što mijenja neki od sljedećih paketa, uredi `S(N+1).md`**, a po
     potrebi i kasnije handoffe i plan. Nedovršeni dio paketa N ide na **vrh** `S(N+1).md`;
   - u `S(N+1).md` upiše polazni commit i brojke (`make test`, `make audit`);
   - pozove `/wrap-up`. Handoff prompt za clipboard i `~/.claude/handoffs/crkve.domovina.ai/`
     je **sadržaj `docs/handoffs/S(N+1).md`**.
4. Ako sesija ostane bez konteksta usred paketa, nastavak je opet `SN` s popisom onoga što
   je ostalo na vrhu datoteke. Broj se ne povećava.
5. **Vrata:** S6 i S7 počinju pitanjem korisniku upisanim na vrh njihova handoffa. Dok
   korisnik ne odluči, lanac stoji; osvježe se samo „Gdje smo” u planu i ova tablica.

Handoff se mijenja samo prema naprijed: gotovi `SN` se ne prepisuju, služe kao povijest.

## Stanje lanca

| Sesija | Paket | Stanje | Commit | Testovi | Napomena |
| --- | --- | --- | --- | --- | --- |
| S0 | Audit + plan | gotovo | 5e8c36c | 126 | audit 2026-11-20; odluke 1–9 |
| S1 | venv, CLAUDE.md, `make audit`, reproducibilnost | gotovo | (S1 HEAD) | 177 | `make rebuild` 2× identičan; nekat. 72, genitiv 302, konf. 1175, dupl. 40, places 991; odluke 100–105 |
| S2 | Konfesija: normalizacija + pravilo matchera | otvoreno | | | |
| S3 | Titulari + sitnice | otvoreno | | | |
| S4 | Node+way duplikati | otvoreno | | | |
| S5 | DGU umjesto Placesa | otvoreno | | | |
| S6 | (!) Deploy ispravljenog snimka | vrata | | | |
| S7 | (!) Svjež ingest + dvaput-nula + deploy | vrata | | | |

## Zajednička pravila (vrijede u svakoj sesiji)

- **Polazak:** `uv run pytest -q` (ili `make test`) i potvrda u jednoj rečenici da je
  zeleno. Ako nije, prvo to popravi. Od S2 i `make audit` mora proći bez greške.
  Repo je **javan** na GitHubu (`domovinatv/crkve.domovina.ai`), wrap-up pusha `main`.
- **Opseg:** `src/`, `scripts/`, `tests/`, `Makefile`, `docs/`. `frontend/` i
  `../karta-hrvatske/apps/karta-web` samo gdje paket kaže (S5, S6). `data/raw/` se ne
  briše (`make clean-cache` samo u S7).
- **Rebuild:** `make rebuild` (od nule, `PLACES_OFFLINE=1`, bez mreže i ključa; odluka 100,
  105). Nikad `make all` poslije Placesa (nema koraka 13, pa ostanu prazni `geo_verified`/`geo_conflicts`).
  Mrežu pri mjerenju blokiraj: `HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=… ALL_PROXY=…`.
  `data/exports/` se do S5/S6 ne commita (odluka 103). Rebuild traje minute; pokreni
  ga u pozadini i javi se tek na kraju.
- **Orkestracija:** posao rade Opus 5.5 subagenti (`model: "opus"`), glavna sesija
  orkestrira. Paket razbij na dva agenta: (a) implementacija, (b) testovi + rebuild +
  `make audit`. `effort` uvijek eksplicitno (`high` kod, `medium` čitanje). Najviše 2–3
  agenta paralelno. **Fable samo kad ga korisnik izričito traži.**
- **Agentima zabrani** `TODO.md`, `docs/plan.md`, `docs/handoffs/`. Orkestrator ih
  ažurira.
- **Testovi:** bez mreže, `skipped 0`, svako novo pravilo ima test na stvarnim primjerima
  iz audita.
- **Brojke s naredbom:** svaka brojka u commitu, docsu ili handoffu dolazi iz
  `make audit` ili navedenog SQL-a.
- **Trošak:** nema `claude -p` petlji. Mrežni pozivi samo gdje paket kaže; procjena
  broja poziva prije svega iznad ~100.
- **Autonomno:** odluči sam i zapiši odluku u svoj blok; svaki zeleni korak commitaj na
  `main`. Deploy, svjež ingest i sve vanjsko ostavi korisniku (vrata).
- **Token budget:** bez Monitora za napredak. Oko 150k konteksta orkestratora zatvori
  sesiju po koraku 3.
- Istraživanja i mjerenja u `docs/research/YYYY-MM-DD-*.md`.
- **Iz `CLAUDE.md`:** pravilo jedinstvenosti, `GENERIC_TITULARS`, titular po glavi,
  sidro ≠ vlastita crkva, `13` mora biti ponovljiv, redoslijed 11→12→13→14→11→20. Prije
  izmjene matchera pročitaj `docs/2026-08-15-izgradnja-kataloga.md`; prije izmjene
  lokacija župa `docs/2026-08-17-revizija-lokacija-zupa.md`.
