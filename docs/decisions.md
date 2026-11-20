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

## S1 (2026-11-20)

100. **Polazna točka lanca je rebuild od nule, ne deployani snimak.** `make rebuild`
   (= `clean-db` + `PLACES_OFFLINE=1 make all-places`) dvaput daje bajt-identične exporte i
   `audit.json`. Deployani snimak (2026-08-27) od njega se razlikuje u 10 župa, 1 crkvi i 3
   biskupije, jer je nastao inkrementalno (Places prije korekcije homonima). Sve sesije mjere
   prema rebuildu. Mjerenje: `docs/research/2026-11-20-audit-polazno.md`. Revizija: S7
   (svjež ingest).
101. **Dozvoljeni skup konfesija** (`src/audit.py`: `DOZVOLJENE_DENOMINACIJE`,
   `DOZVOLJENE_RELIGIJE`) je OSM vokabular, jedan za crkve, pravne osobe i biskupije.
   - Katoličke: `roman_catholic`, `greek_catholic`, `old_catholic`.
   - Pravoslavne: `orthodox` (generički, dozvoljen) i nacionalne `*_orthodox`.
   - Protestantske i druge kršćanske: `protestant`, `lutheran`, `reformed`, `evangelical`,
     `baptist`, `pentecostal`, `seventh_day_adventist` (ne `adventist`), `methodist`,
     `anglican`, `waldensian`, `jehovahs_witness`, `mormon`, `new_apostolic`.
   - Islam i budizam: `sunni`, `shia`, `zen`.

   `catholic` se svodi na `roman_catholic`. Religija upisana kao denominacija (`jewish`,
   `hindu`, `buddhist`) postaje NULL, a smeće i višestruke vrijednosti također.
   Religije: `christian`, `muslim`, `jewish`, `buddhist`, `hindu`, `pagan`. S2 to provodi u
   `src/denomination.py` i koristi `audit.is_nekatolicka`/`NEKATOLICKE_DENOMINACIJE`, da
   mjera i pravilo ne bi bili dvije definicije. Revizija: nova vrijednost iz svježeg ingesta.
102. **Pravilo `titular_genitiv`:** titular „sv. X i Y” je kriv ako je ijedna riječ niza u
   genitivu. Padež riječi određuju tri provjere, redom:
   - leksikon padeža iz `titular.py`;
   - završetak `-e` (osim `-je`);
   - desna riječ para na `-a` koja nije poznat nominativ, osim ako je lijeva riječ poznati
     nominativ na `-a`.

   Mjeri crkve i pravne osobe odvojeno. Poznata 3 lažno pozitivna su zapisana u
   istraživanju. Revizija: kad S3 doda oblike u leksikon.
103. **`data/exports/` u gitu ostaje deployani snimak do S6.** Rebuild mijenja `zupe.*`, a oni
   i dalje nose Places koordinate (odluka 5), sada 991 umjesto 989. Commit bi u javni repo dodao
   nove. Lokalno se exporti regeneriraju, a commitaju tek čisti (S5/S6). `audit.json` je
   gitignoriran: regenerira se i nosi popise slugova. Revizija: S5 (Places izbačen iz exporta).
104. **`parish_count` se ne ispravlja na broj zapisa.** `dioceses.parish_count` broji aktivne i
   različite župe, a razlika 2 su Prizna (ugašena) i duplikat Prgomet. Prema aktivnima je
   razlika 0. Stavka TODO-a „85→86, 74→75” bila je pogrešan smjer. S3 provjerava što prikazuje
   frontend (`34`) i usklađuje metriku, a ne podatak.
105. **`PLACES_OFFLINE=1`: promašaj keša je prazan rezultat, ne mreža.** Rebuild mora raditi
   bez ključa. Keš 2026-08-15 nema 4–5 varijanti upita koje današnji kod traži za homonime;
   offline one ostaju bez Places pogotka (sve imaju `naselje-centroid`). `make clean-db` ide
   prvi u `all`/`all-places`, jer `10_match_heritage` na spojenoj bazi ostavi 1115 spojenih zapisa u `heritage_unmatched` i izgubi
   840 `year_built` (nije ponovljiv, otvoreno za S7).

## S2 (2026-11-20)

200. **`catholic` → `roman_catholic` bez iznimke.** Izmjereno: od 1022 takve građevine nijedna
   nije spojena na Križevačku eparhiju (njezinih 14 spojenih: 13 `greek_catholic`, 1
   `roman_catholic`); jedina u grkokatoličkom kraju (Kostanjevac, Žumberak) spojena je na
   rimokatoličku župu. Revizija: svjež ingest donese `catholic` u eparhiji.
201. **Nepoznata ili proturječna konfesija postaje NULL, ne pretpostavka.** `X;orthodox` zadržava
   konkretni X; vrijednost koja kaže samo „nije katolička” (`episcopal`, `church_of_christ`)
   postaje `protestant`. Mapiranje i brojke: `docs/research/2026-11-20-s2-konfesija.md`.
202. **Pravilo konfesije (odluka 4) u `scripts/11`:** u 1. prolazu filtrira kandidate prije
   scoreanja; u 2. prolazu (filijale) samo odbija vezu, a jedinstvenost se i dalje broji nad svim
   pravnim osobama u mjestu. Filtar prije brojanja u 2. prolazu dodao je 190 filijala (sinagoge,
   džamije, JW na SPC općine), jer pravilo čuva samo katoličku granicu.
203. **`building=mosque|synagogue` popušta kršćanskom nazivu, religiji ili konfesiji** (`kinds.py`).
   Tag opisuje zgradu, ne današnju namjenu. Promijenila su se točno 3 kinda (Đakovo Svih Svetih,
   pentekostna crkva u bivšoj sinagogi u Osijeku, Daruvarski Brestovac → `pravoslavna-crkva`);
   nijedna stvarna džamija ni sinagoga.
204. **`old_catholic` je za spajanje nekatolička**, iako je u odluci 101 popisana među
   katoličkima (skup dozvoljenih vrijednosti se ne mijenja). Starokatolička crkva nije u
   zajedništvu s Rimom i ima vlastite pravne osobe u evidenciji vjerskih zajednica.
205. **„Slab zahtjev” ide zadnji u 1. prolazu `scripts/11`** (`match.weak_claim`: pravna osoba
   imenuje sveca, građevina ne). Ne odbija se, samo mijenja redoslijed. Razlog: Trsat
   (`r3560310`, naziv bez sveca) je nakon odspajanja pravoslavnog sv. Nikole otišao na
   „FRANJEVAČKI SAMOSTAN SV. NIKOLE” 4,5 km dalje; s pravilom je opet na „… RIJEKA - TRSAT”, a
   usput su ispravljeni Sesvete i zagrebački „Samostan”.
206. **Pravoslavne pravne osobe se u S2 ne spajaju.** Matcher po nazivu spaja 7 od 434 (svih 7
   manastira, točno), jer crkvene općine nemaju sveca u nazivu. Varijanta po naselju (općina X ↔
   jedina pravoslavna građevina u naselju X) daje 172 para, uzorak 20 (seed 20261120): 17 točno,
   0 krivo, 3 nejasno. To je zasebna stavka poslije S3, zajedno s 14 građevina nepoznate
   konfesije koje 2. prolaz danas veže na SPC općine (neke po nazivu katoličke). Revizija: kad
   se stavka uzme.
