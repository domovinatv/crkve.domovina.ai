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

## S3 (2026-11-20)

300. **Niz „X i Y” je cijeli u nominativu, a kanonski oblik je „sv. Petar i Pavao”, bez
   „apostoli”.** Zajednički naslov ispred niza („Svetih Apostola Petra i Pavla”, „Ap.”,
   „Arhanđela Mihaila i Gavrila”, „mučenika Srđa i Baha”) i zajednički epitet iza drugog imena
   („apostola”, „AP.”, „mučenika”, „MM.”) padaju (`titular._SERIES_TITLE`, `_GROUP_EPITHET`).
   Razlog: izvori ih pišu nedosljedno (s njima, bez njih, iza zareza), a puni titular nosi bonus
   +8 u matcheru samo kad je jednak; glava mora biti prvo ime, ne „sv apostola”. „I” koji veže
   epitete jednog sveca („Katarine djevice i mučenice”, „Stjepana I. pape i mučenika”) ostaje i
   dobiva nominativ. Izmjereno simulacijom 1. prolaza `scripts/11` nad `baseline-s2.db`: Bribir
   (`AP.`) 91,4 → 99,4, Grobnik 92,3 → 100, nijedan spoj izgubljen. Revizija: ako prikaz treba
   „apostoli” natrag, ide u zaseban stupac, ne u ključ.
301. **Imena ostaju leksikon, ne pravilo** (komentar u `titular.py`). Dodano 28 genitiva iz baze
   (`ćirila`, `metoda`, `kvirika`, `julite`, `srđa`, `baha` → Bakho …) i nominativi koje je
   audit brojao kao genitiv (`ante`, `pavle`, `carica`). Epiteti koji imaju smisla samo uz ime u
   nominativu (`pape`, `mučenice`, `kraljice`, `srca`, `žalosne`, `gospe`) dižu se samo u nizu
   (`_SERIES_EPITHETS`), jer bi inače „sv. Silvestra pape” postao miješani „sv. Silvestra Papa”.
   `head_key` nad svih 9945 naziva u `baseline-s2.db` (stari i novi kod,
   `scratchpad/keys.py` + `diff.py`): **104 razlike, sve objašnjene** — 21 Tavelić (odluka 302),
   60 genitiv prvog imena → nominativ (Ćirila 14, Margarite 9, Ladislava 7, Izidora 5 …),
   20 naslov ispred niza (`sv apostola`/`sv ap`/`sv arhanđela`/`sv mučenika` → ime),
   1 „SV.SV.”, 2 „Isusova uskrsnuća”. Nijedna druga riječ niza ne ulazi u glavu.
302. **Sv. Nikola Tavelić ima vlastitu glavu (`sv nikola tavelic`), a „B.” se ne širi u
   „Biskup”.** Tavelić je drugi svetac istog imena; s istom glavom „ŽUPA SV. NIKOLE B.” u Rijeci
   bodovala je 90 i biskupa i Tavelića (S2). S glavom Tavelića rijecka župa dobiva „crkva svetog
   Nikole biskupa” (`w159810306`, score 90), a Repušnica („TEVELIĆA”, tipfeler evidencije,
   dodan u leksikon) i dalje svoju crkvu (94,4 → 100). Širenje „B.” → „Biskup” izmjereno je i
   odbačeno: +3 spoja (Rijeka, Metković, Ustrine), ali Čakovec gubi točnu „crkva svetog Nikole”
   jer bonus +8 digne crkvu iz Novog Sela na Dravi (ista općina, druga župa) na 98 prema 100.
   „B.” uz Leopolda je Bogdan. Revizija: kad blokiranje po općini prestane miješati naselja.
303. **Mjesto koje evidencija piše bez zareza skida se u ingestu, ne u matcheru**
   (`parse(name, place=city)` u `scripts/02` i `03`). Takvih je 75 od 1496 parsanih titulara
   pravnih osoba („ŽUPA SV. KUZME I DAMJANA POLAČA”, „SV. NIKOLE B. BOŽAVA”). Matcher ključ
   računa iz naziva bez mjesta, kao i dosad; glava se nikad ne skida. Usput: otok „IŽ” više nije
   prijedlog „iz” (prijedlozi se uspoređuju s dijakritikom).
304. **Pravne osobe su u opsegu `titular_genitiv`, ništa se ne izuzima.** Lažno pozitivni iz S1:
   „Car Konstantin i Carica Elena” je nominativ (leksikon), „sv. Liberana i arheološko
   nalazište” i „Sv.Mihovile i Sv.Mario” su greške parsera (niz staje na riječi koja nije ime;
   slijepljeni „Sv.” se odvaja; vokativ „Mihovile” je u leksikonu). Simulacija titulara kako bi ih
   upisao pipeline (`scratchpad/sim_gen.py` nad `baseline-s2.db`): **0** (crkve 0, pravne
   osobe 0), polazno 302. Kratice „Dj. i Mč” ostaju (nisu genitiv). Revizija: rebuild.
305. **„MANASTIR” je `samostan`, a pravoslavni samostani se do stavke iz odluke 206 ne spajaju.**
   Pravilo je u `src/kinds.org_kind` (bilo u `scripts/03`, netestabilno): manastir ide prije
   eparhije, a „BELI MANASTIR” je grad. Nad `baseline-s2.db`: 19 zapisa `eparhija` → `samostan`
   (dvadeseti, „PRAVOSLAVNA BOGOSLOVIJA … U MANASTIRU KRKA”, nije samostan i ostaje), 3 iz Belog
   Manastira `samostan` → `ostalo` (Mjesna crkva, Crkveni okrug, pentekostna crkva; kao i njihovi
   istovrsni zapisi drugdje). Kad bi ušli u `scripts/11`, simulacija nad kopijom baze
   (`scratchpad/run11.py`) daje +8 točnih veza manastir ↔ manastirska crkva (Krka, Dalj, Pakra,
   Orahovica, Marča, Lazarica, Crnogorci, Lepavina), ali i 5 izgubljenih katoličkih filijala
   „ŽUPE SV. JURJA MČ.” u Gračacu (mjesto postane dvosmisleno) i upitne filijale Lepavine
   („kapela Svetog Križa”, Sokolovac). Zato `scripts/11` (`_IZVAN_SPAJANJA`) isključuje
   `samostan` pravoslavne konfesije; simulacija s filtrom: **0 promjena** veza. Posljedice
   izvan spajanja: 19 manastira dobiva stranicu `/ustanova/<slug>`, a 3 zapisa iz Belog Manastira
   je gube (nijedan nema spojenu građevinu; slug se ne mijenja). Revizija: stavka spajanja
   pravoslavnih (206).
306. **Križevačka eparhija je `dioceses.kind = 'eparhija'`** (`src/dioceses.kind_of`, oba mjesta
   u `scripts/02`), a zapis „KRIŽEVAČKA EPARHIJA” u `parishes` je `biskupija` (pravna osoba iste
   razine; do sada `ostalo`), pa eparhija dobiva OIB i sjedište Križevci kao i latinske
   biskupije. Slug `krizevacka-eparhija` i naziv (= `parishes.diocese`) se ne mijenjaju.
   `scripts/20` bira samo `nadbiskupija`/`biskupija`, pa je eparhija izvan particije i bez
   `OVERLAPPING_SLUGS` (ostaje kao druga brava). Export `biskupije.*` nosi `kind` doslovno;
   frontend ne filtrira po vrsti (`/biskupije` dijeli po `has_area`, `/biskupija/$slug` ispisuje
   `kind` kao oznaku), pa samo oznaka postaje „eparhija”.
307. **`parish_count_razlika` mjeri prema aktivnim i različitim župama** (`stats.AKTIV`, ista
   definicija kao `zupe_aktivne`), a broj zapisa ide u `razlika_prema_zapisima` kao kontekst.
   Podatak se ne mijenja (odluka 104). `make audit` na S2 bazi: **0** (prije 2: Gospić/Prizna,
   Šibenik/Prgomet). Export i frontend nigdje ne prikazuju broj svih zapisa: `scripts/34` izvozi
   samo aktivne i različite pravne osobe (`PARISH_SQL`), `/biskupija/$slug` ispisuje
   `parishes.length` („N pravnih osoba u katalogu”: župe + samostani + svetišta, npr. Zagrebačka
   285 naprema `parish_count` 206), a `/biskupije` u bloku „Ostale zajednice” ispisuje
   `parish_count` s oznakom „pravne osobe”, što je za Križevačku eparhiju (35) zapravo broj župa.
   To je oznaka u frontendu, ne broj: prijavljeno, nije mijenjano (`frontend/` izvan opsega S3).
308. **Krivi OSM tag ispravlja se u ingestu, popisom s izvorom** (`src/osm_fixes.TAG_FIXES`,
   primjenjuje `scripts/01`). Prvi unos: čvor 13304771994 (kapela sv. Terezije u Trnju) nosio je
   `wikidata=Q132087369` i `wikipedia` župne crkve Svih Svetih (way 459564717; Wikidata provjerena
   2026-11-20). Čvor ne dobiva samo prazninu nego svoj entitet, **Q132079947** („Pastoralni centar
   bl. Alojzija Stepinca s kapelom sv. Terezije…”, iz keša `scripts/05`, 27 m od čvora), a
   `wikipedia` se briše pa ga `05` popuni iz Q132079947. Slika „Pastoralni centar s kapelom
   sv. Terezije … 01.jpg” na crkvi Svih Svetih (4058) curila je iz istog taga: Q132079947 nije
   imao čvor sa svojim Q, pa je u `05` prostorno (`_nearest`, 150 m) pao na najbližu građevinu bez
   proturječnog titulara — crkvu Svih Svetih (54 m; kapelu je titular isključio). U kešu su
   unutar 500 m od crkve samo ta dva entiteta, pa nakon ispravka crkva dobiva P18
   „Župna crkva Svih Svetih u Zagrebu cijela.jpg”, a kapela sliku pastoralnog centra. Očekivano
   nakon rebuilda: `wikidata_dijeljen` **3** (samo parovi crkva + samostan). Slug se ne mijenja
   (sufiks je OSM id). Otvoreno: `_nearest` smije dati entitet građevini koja već nosi DRUGI
   Wikidata Q — opće pravilo nije uvedeno jer ga bez rebuilda nije moguće izmjeriti.
309. **Engleski naziv zamjenjuje se samo hrvatskim iz izvora, a slug ostaje iz izvornog naziva.**
   `normalize.hrvatski_naziv` (ista `je_engleski` kojom mjeri audit, preseljena iz `audit.py`):
   OSM `name:hr` u `scripts/01`, naslov članka na hr.wikipediji u `scripts/05` (label je
   `"hr,en"`, pa engleski znači da hrvatskog labela nema). Izmjereno u kešu (`data/raw/osm`,
   `data/raw/wikidata`): od 32 engleska naziva hrvatski postoji za **2** — Rovinj
   (`w782348025`, `name:hr` „Crkvica Bezgrešnog Začeća”) i Ružić (Q5116856, „Crkva hrvatskih
   mučenika”); ostalih 30 nema ni `name:hr` ni hr članak i ostaju (popis:
   `docs/research/2026-11-20-s3-titulari.md`). Slug se računa iz izvornog naziva **prije**
   zamjene, pa se nijedan URL ne mijenja (sufiks OSM id / Q nosi identitet); engleski naziv ide u
   `church_aliases` (`osm:name`). Za Wikidata zapis vrsta se čita iz hrvatskog naziva
   (Ružić: `ostalo` → `crkva`). Očekivano nakon rebuilda: `engleski_nazivi` 30 (wikidata 19,
   osm 11). Revizija: svjež ingest (S7) — Wikidata labeli se dopunjuju.
310. **Naziv biskupije se uljepšava, slug ostaje iz sirovog naziva evidencije.**
   `dioceses.display_name`: „Zagrebačka nadbiskupija”, „Dubrovačka biskupija” (latinski dodatak
   iza „ - ” pada), „Križevačka eparhija”; riječ (nad)biskupija/eparhija velika je samo na
   početku („Biskupija Krk”). Piše se u `dioceses.name` **i** `parishes.diocese` jer su to ključ
   spajanja (`scripts/20`, `34`, audit), a `parish_geo._SKIP_DIOCESE` je usklađen. Slug se računa
   iz sirovog naziva (`scripts/02`, `diocese_slug`): provjereno nad S2 bazom, svih 16 katoličkih
   slugova ostaje isto (`slugify(sirovi) == slug`), uključujući
   `dubrovacka-biskupija-dioecesis-ragusina`, na koji se vežu `/biskupija/<slug>` i boje u
   karta-web (`DIOCESE_COLORS`). Mijenja se samo tekst: oznaka biskupije u
   `zupe-index.json`/`zupa/<slug>.json`, koju `listici.domovina.ai` preuzima kao prikaz (ključ mu
   je slug župe, odluka iz CLAUDE.md). Nekatoličke zajednice (`scripts/03`) se ne diraju.
   Revizija: ako se ikad odluči i za čisti slug Dubrovačke, to je preusmjeravanje URL-a, ne ovo.
311. **Kad dvije pravne osobe traže istu građevinu, prednost ima ona sa sjedištem u naselju
   građevine** (`scripts/11`, redoslijed 1. prolaza, iza `weak_claim`). Blok po mjestu spaja
   naselje, grad i općinu građevine, pa „zagreb” (Grad Zagreb) pokriva i Sesvete. Nakon S3 su
   „ŽUPA ISUSOVA USKRSNUĆA” (Sesvete, Dugoselska 4 = adresa crkve `w416430719`, OIB) i „ŽUPA
   USKRSNUĆA ISUSOVA” (Zagreb, Hrastin prilaz bb, bez OIB-a; Places ju je homonimom stavio na
   istu crkvu) dobile isti titular, a crkvu je uzeo zapis s manjim id-om. Mjereno pokretanjem
   `scripts/11` nad kopijom `after-s3.db` (staro naspram novog): 5 promjena, broj župnih crkava
   isti (1156), sve prema župi iz istog naselja — Sesvete → 0550, Račišće (umjesto dominikanskog
   samostana u Korčuli), Vrpolje (umjesto Trilja), Rožat (umjesto Dubrovnika), Boraja (umjesto
   dominikanki u Šibeniku). Nijedan slug nije posebno tretiran. Revizija: S5 (Places izlazi iz
   koordinata, homonim 701585 tada nestaje sam).
312. **„Blažene Djevice Marije” bez otajstva je generički titular „Majka Božja”, ne svetac
   „Djevica”.** Postojeći bug (i prije S3): `_SAINT_MARK` je „Blažene” čitao kao „sv.”, pa je
   „crkva Blažene Djevice Marije - Kraljice mira” imala titular „sv. Djevice Marije”. S3 je
   registru Z-2282 („Crkva Blažene Djevice Marije i župni dvor”, Granešina) skinuo „i župni dvor”,
   puni ključ se izjednačio s Kraljicom mira i pravilo jedinstvenosti ih je spojilo. Sad je to
   „Majka Božja” (u `GENERIC_TITULARS`, ne nosi jedinstvenost), samo kad je „Blažene/bl.” prva
   oznaka u nazivu; `_BDM` usput prepoznaje i „bl. Djevice Marije” (Uznesenje). `head_key` nad
   `baseline-s2.db` naspram S3 koda: 78 crkava + 3 pravne osobe `sv djevic*` → `majka bozja`
   (1 → `uznesenje bdm`), nijedan `sv djevic*` ne ostaje. Z-2282 nad `after-s3.db`
   (`best_match`, blok Zagreb): nespojen, kao u S2 — naziv ne kaže koji je marijanski zaziv.
   Odbačeno: isto pravilo za „ŽUPA B. D. MARIJE …” / „BDM …” (bez „Blažene”) — +4 spoja, ali −2
   (Belec, Zagreb „Marije Anđeoske”), jer OSM piše „svete Marije Snježne” s glavom `sv marija`.
   Simulacija 1. prolaza: Bjelovar „BLAŽENE DJEVICE MARIJE - GOSPE LURDSKE” gubi kapelu BDM u
   Trojstvenom Markovcu (prije 100; točnost tog spoja nije provjerena).
313. **„Mihajla” = „Mihaila” → „Mihailo”** (Z-6096 Vrhovine, registar „Arhangela Mihajla i
   Gavrila”, OSM „Arhangela Mihaila i Gavrila”). Nad `after-s3.db` registar opet nalazi svoju
   crkvu (score 100). `head_key`: 4 crkve + 2 pravne osobe `sv mihajla` → `sv mihailo`.
314. **Wikidata entitet se ne spaja na građevinu koja već nosi DRUGI Q** (`scripts/05`,
   `_nearest(drugi_q=True)`). Q133733258 „BDM Bezgrešne na Knežiji” (2006) stopio se u
   w246443250 „BDM Pomoćnice” (1929, Q125578862), 20 m dalje, i nestao iz kataloga. Simulacija
   prostornog spajanja (OSM građevine iz `after-s3b.db`, Q iz keša Overpassa s `osm_fixes`,
   keš Wikidate; `scratchpad/sim05.py`): spojeno 277 → 261. Od 16 promjena 14 postaju zasebne
   građevine — među njima i do sada krivi spojevi (sinagoge Rijeka i Bjelovar na crkve, Kosi
   toranj Rijeka, Nadbiskupska palača i ostaci sv. Mihovila u Splitu, kapucinski samostan na
   konkatedralu sv. Ćirila i Metoda), ali i parovi kompleks/crkva s dva Q (Trogir sv. Ivan
   Krstitelj, Čakovec sv. Nikola, Split sv. Frane, Čiovo sv. Križ, Sveta Nedelja sv. Rok) —
   mogući duplikati za S4. 2 se preusmjeravaju na drugu građevinu bez Q (Split Lovre i Gospa od
   Zvonika → Mesdžid, i dalje krivo; Marija Bistrica Q107013115 → „Kapela”), otvoreno.
   Čabar Q138496303 i ostala 3 S3 spoja ostaju (oni idu po tagu ili na građevinu bez Q).
   Pravilo (b) „generički titular nije slaganje” izmjereno i odbačeno: −22 spoja, gubi točne
   Čabar i Križevci („Majke Božje Koruške”). Revizija: S4 (dedup).
   **POVUČENA u S3 (kod vraćen).** Rebuild S3c (`docs/research/2026-11-20-s3-rebuild.md`,
   commit 71d0a1b) dao je, uz ispravljenu Knežiju i 4 ispravno zasebne građevine, 3 regresije
   baštine (Z-4687 Split sv. Frane, Z-1405 Trogir sv. Ivan Krstitelj, Z-1458 Sveta Nedelja sv.
   Rok, svaka zbog novog Wikidata duplikata na 0,00 km), krivu župnu crkvu (Čakovec q113964584
   s koordinatama u Varaždinu → župna crkva franjevačkog samostana Varaždin) i regresiju Marije
   Bistrice (Q107013115 na „Kapela”, bazilika gubi sliku). To su duplikati, a njih rješava S4;
   pravilo se uzima tamo zajedno s dedupom i mjeri na istom rebuildu. Do tada Knežija
   (Q133733258) ostaje stopljena — poznata regresija S3, prva stavka S4.

## S4 (2026-11-20)

400. **OSM čvor i tlocrt iste zgrade spajaju se u ingestu, po ulozi, nazivu i udaljenosti**
   (`src/dedup.py`, poziva ga kraj `scripts/01`, prije `05` i 10/11). Uloga iz tagova:
   samostan (`amenity|building=monastery`), poklonac (`historic=wayside_shrine`), bogoslužje;
   različita uloga = dvije zgrade (17 takvih parova je na ≤ 20 m). Nazivi: isti `norm_key`, ista
   glava ili jedna strana bez OSM `name` (`osm_named = 0`; „generičko” znači placeholder iz
   `01`, ne naziv bez titulara); različite glave nikad. Preživljava way/relation (id, slug,
   koordinate, `geom_kind`, OSM id); ostalo `COALESCE(way, čvor)`; naziv i titular s čvora kad
   way nema imena; kind ostaje wayev (`building=chapel` je jači dokaz od `amenity` bez
   `building`) osim kad ga je izveo naziv čvora ili je wayev `ostalo` — prva verzija koja je
   kind uvijek uzimala s čvora pokvarila je 6 kapela. Naziv čvora koji se razlikuje ide u
   `church_aliases` (`osm-dedup`). Uloga, „ima ime” i `amenity` su kolone `osm_role`,
   `osm_named`, `osm_amenity`, jer ih audit mora računati nad bazom istim predikatima.
   Dodjela: čvor → najbliži dopušteni way (izjednačenje po OSM id-u); way prima više čvorova
   samo dok su međusobno spojivi. Izmjereno: 73 spoja, crkava 6961 → 6889
   (`docs/research/2026-11-20-s4-dedup.md`).
401. **Prag 20 m; do 40 m samo za čisti tlocrt s jedinim kandidatom.** Spojivih parova je 67
   na ≤ 20 m i 9 na 20–40 m, od kojih nijedan nije dokaziv bez poligona (ingest ima samo
   `center`). Prošireni prag vrijedi kad way nema ni imena ni `amenity` i par je jedini
   kompatibilni s obje strane; hvata točno Samostan sv. Vinka (23 m). Bez uvjeta
   jedinstvenosti bezimeni tlocrt u Velom Lošinju primio bi i Sv. Križ (28 m) uz Navještenje
   (0,4 m). Prag 40 m za sve dao bi +7 spojeva, od toga 2 vjerojatno krive (kapela ↔ crkva iste
   glave, različite župe). Revizija: kad ingest dobije geometriju (`out geom`) — onda točka u
   poligonu.
402. **Različit `wikidata` tag na čvoru i wayu = ne spaja se** (0 takvih parova danas; pravilo
   je zaštita za ponovni ingest). Ručne iznimke su u kodu s razlogom: `dedup.SPOJI` 7 parova
   (2 poklonca u središtu tlocrta kapelice na 0,3/0,6 m; 5 istih svetaca drukčije napisanih —
   Salvatore/Salvadur, Petar/„S. Pietro”, Križ/„Kris”, Pelegrin/„Peegrin”, Grabrovica Sv.
   Marija/Materinstvo Majke Božje, svi ≤ 7 m), `NAZIV_S_CVORA` kad je naziv waya tipfeler ili
   talijanski, `NE_SPAJAJ` (prazan) i `OSTAVLJENI` 7 neodlučivih parova na 27–40 m.
403. **Identitet spojenog čvora živi u tablici `church_merged`** (odluka 6): `church_id` →
   preživjeli, `osm_type`/`osm_id`, stari `slug`, naziv čvora, razlog, udaljenost. Ponovni
   ingest ga deterministički ponovo spaja i upsertom osvježava red; red čiji se čvor vratio u
   `churches` (pravilo ga više ne spaja) briše se, da stari slug ne vodi na dva mjesta.
   `church_aliases` ostaje samo za nazive.
404. **Stari slug daje 301, ne 404; `node_way_duplikati` broji samo ono što je pravilo
   propustilo.** `scripts/34` piše `crkva/<stari>.json` = `{"redirect": novi}` (izvan indeksa
   i sitemapa), ruta `/crkva/$slug` baca `redirect(statusCode: 301)`; provjereno na
   `wrangler dev --local`. Metrika koristi dedupove predikate na ≤ 40 m (uključujući stranu bez
   imena, koju stara definicija nije vidjela): `value` = spojiv par iste uloge koji nije spojen
   i nije u `OSTAVLJENI`; različita uloga, različit `wikidata` i `OSTAVLJENI` idu u
   `namjerno_ostavljeni` (45), broj spojenih u `spojeno`. Poslije: 0; po staroj definiciji 7.
405. **Marijanski zaziv proturječi, ali ne ulazi u ključ titulara** (`titular.zaziv`,
   `zazivi_u_sukobu`; `scripts/05._nearest` i `match._score`). Generički „Majka Božja”
   (odluka 312) je spajao Q133733258 „BDM Bezgrešne na Knežiji” (2006) u w246443250 „BDM
   Pomoćnice” (1929). Zaziv je skup osnova riječi („od Snijega” = „Snježna”, leksikon
   sinonima); sukob je samo kad oba naziva imaju zaziv bez zajedničke riječi, pa je gola BDM
   spojiva sa svime (pravilo (b) iz 314 ostaje odbačeno). Ključ sa zazivom odbijen mjerenjem:
   Z-834 bi i dalje bio izjednačen (svetište i gola „Kapela BDM” oba 100, bonus odrezan na
   100), a mijenjao bi `churches.titular` i opseg pravila jedinstvenosti. Rebuild prema
   95a2bc9: +1 građevina (Knežija), veze +1/−1 (Pula Gospe od Mora točno, Places potvrdio;
   Stobreč Gospe od Mira ← Župa Gospe od Milosrđa bio kriv, `geo_conflicts` 2,7 km), baština
   +2 točna (Z-834, Z-4568), a 5 krivih starih spojeva postaje nespojeno (Z-1412, Z-4858,
   Z-5435, Z-2392, Z-321; Z-1412 ustupa crkvu Z-4568). Sinonim `milosrd → milost` čuva
   RST-1286 Suđurađ (jedina marijanska crkva u naselju). Audit: samo `crkve_ukupno` +1.
   `docs/research/2026-11-20-s4-titular.md`.
406. **Isti zaziv pobjeđuje samo golu BDM, ne nemarijanske kandidate** (`ZAZIV_BONUS = 8`,
   samo za marginu). Kad u bloku postoji kandidat istog zaziva, kandidat s ključem „majka
   bozja” bez zaziva se spušta za 8; prag i vraćeni score ostaju. Z-834 → Svetište Majke Božje
   Svetogorske (Mali Lug). Inačica s bonusom prema svima izmjerena i odbačena: kapucinski
   samostan u Rijeci oteo je crkvu Gospe Lurdske župi, a bazilika Marija Bistrica postala
   „župna crkva” Karmela (oba para izjednačena sa samostanskom zgradom bez titulara).
