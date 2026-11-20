# Odluke — lanac kvalitete podataka

Svaka odluka ima broj, datum, razlog i uvjet revizije. Odluka se ne briše nego zamjenjuje
novom koja se poziva na staru. Blokovi: S0 1–99, S1 100–199, S2 200–299 … S7 700–799.

## S0 (2026-11-20)

1. **Opseg.** Ispravci iz audita 2026-11-20 i jedan svjež ingest. Nisu u opsegu: kontakti
   župa (Firecrawl), fotografije, `heritage_unmatched`, novi slojevi, automatsko
   periodičko osvježavanje. Revizija: kad korisnik doda stavku.
2. **Ispravak ide u pipeline, ne u bazu.** Baza se gradi od nule; ručni ispravak nestane
   na idućem `make all`. Ručne iznimke idu u kod s izvorom (kao `parish_geo.OVERRIDES`).
3. **Mjerilo je `make audit`.** Svaka metrika iz audita ima ime i ciljnu vrijednost;
   „gotovo kad” svakog paketa poziva se na nju. Uvodi ga S1.
4. **Konfesija je tvrdi uvjet veze, ne bonus na score.** Građevina poznate nekatoličke
   konfesije (ili kinda `pravoslavna-crkva`/`dzamija`/`sinagoga`) ne smije na katoličku
   pravnu osobu i obrnuto. Nepoznata konfesija ne blokira. Revizija: ako mjerenje u S2
   pokaže stvarne veze koje pravilo ruši (npr. bivša džamija koja je danas crkva).
5. **Google Places ne daje objavljene koordinate.** Uvjeti Google Maps Platforma ne
   dopuštaju redistribuciju lat/lng; katalog je ODbL/CC-BY. Places smije ostati kao
   interna nezavisna provjera matchera (`geo_verified`, `geo_conflicts`), ali vlastitih
   koordinata ni linka ne izvozi. Zamjena: DGU INSPIRE AD WFS. Revizija: samo uz pravno
   mišljenje koje kaže drukčije.
6. **Dedup čuva oba OSM identiteta.** Spojeni zapis zadržava tlocrt (way/relation) kao
   geometriju, a OSM ID i slug točke ostaju zapisani (gdje točno: odluka S4; postojeći
   `church_aliases` drži samo nazive) da sljedeći ingest ne vrati duplikat i da stari slug
   ne da 404.
7. **Deploy i svjež ingest su vrata.** Sesija pripremi, upiše pitanje na vrh sljedećeg
   handoffa i staje.
8. **Testovi bez mreže.** Fixture iz keša ili ručno napisani primjeri; `skipped 0`.
10. **Places koordinate su i u git povijesti.** `data/exports/` je commitan u javni repo,
   pa su `zupe.geojson`/`zupe.csv` s koordinatama iz Placesa u povijesti od 2026-08-15.
   S5 ih uklanja iz idućih commitova; prepisivanje povijesti (`git filter-repo`, force
   push) je nepovratno i korisnikova odluka — pitanje ide u vrata S6. Revizija: ako
   korisnik odluči da je uklanjanje iz HEAD-a dovoljno.
9. **Plan je javan** (repo je javan); u njemu nema ključeva, IP-ova iz allowliste ni
   pravnih procjena izvan odluke 5.
