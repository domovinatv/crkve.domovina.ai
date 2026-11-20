# S2: konfesija — normalizacija i pravilo veze, izmjereno (2026-11-20)

Kod: `d73ad41` (normalizacija, `match.compatible`) + ovaj commit (`match.weak_claim`, redoslijed
1. prolaza u `scripts/11`). Polazna baza: rebuild prije S2 (commit `21a9524`), kopija u
scratchpadu kao `crkve-pre-s2.db`. Sve brojke su s `make rebuild` od nule, mreža blokirana.

## Ukratko

- Ciljevi S2 ispunjeni: `konfesija_nenormalizirana` 1175 → 0, `nekatolicke_na_katolickim`
  72 → 0, `nekatolicke_zupne_crkve` 2 → 0.
- Pravilo je odspojilo 76 veza: 71 nekatolička građevina s katoličke pravne osobe i 5
  katoličkih građevina sa srpskopravoslavnih crkvenih općina (obrnuti smjer pravila). Sve
  su bile filijale iz 2. prolaza, osim pravoslavne sv. Nikole u Rijeci (župna crkva).
- Pravilo je otvorilo 4 nove veze (pravoslavna konkurentica više ne ruši marginu) i jednu
  regresiju: trsatski franjevački samostan prešao je na krivu pravnu osobu. Popravljeno
  općenito (`match.weak_claim`), ne iznimkom. Isti popravak premjestio je još dvije ranije krive
  veze: Sesvete (sad točno) i zagrebački „Samostan” (bliže, ali još u `geo_conflicts`).
- Katolička „ŽUPA SV. NIKOLE B.” u Rijeci ostaje bez župne crkve (margina između sv. Nikole
  biskupa i sv. Nikole Tavelića); sjedište joj više ne leži na pravoslavnoj crkvi nego 0,29 km
  od katoličke sv. Nikole biskupa.
- Pravoslavne pravne osobe: postojeći matcher po nazivu spaja samo 7 od 434 (svi manastiri,
  7/7 točno). Crkvene općine trebaju pravilo po mjestu, ne po nazivu: 172 jednoznačna para,
  uzorak 20 → 17 točno, 0 krivo, 3 nejasno. Nije uključeno; prijedlog dolje.

## Naredbe

```bash
cp data/crkve.db "$SCRATCH/crkve-pre-s2.db"          # rebuild prije S2
export HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9
make rebuild && make audit                            # 2×, usporedba sha
uv run python diff_veza.py crkve-pre-s2.db data/crkve.db       # skripte u scratchpadu, ne u repou
uv run python pravoslavni.py data/crkve.db 20261120
uv run python pravoslavni_mjesto.py data/crkve.db 20261120
```

Skripte za diff veza i pravoslavna mjerenja bile su jednokratne (scratchpad), logika je
opisana u odgovarajućem odjeljku.

## Metrike prije → poslije

`make audit` na `make rebuild` (od nule, offline). „Prije” = rebuild na `21a9524`.

| metrika | prije | poslije | napomena |
|---|---:|---:|---|
| `nekatolicke_na_katolickim` | 72 | **0** | cilj |
| `nekatolicke_zupne_crkve` | 2 | **0** | cilj; Rijeka sv. Nikola (pravilo), Đakovo Svih Svetih (kind) |
| `konfesija_nenormalizirana` | 1175 | **0** | cilj; crkve 1051 → 0, pravne osobe 109 → 0, biskupije 15 → 0 |
| `titular_genitiv` | 302 | 302 | S3 |
| `node_way_duplikati` | 40 | 40 | S4 |
| `places_koordinate_u_exportu` | 991 | 988 | 3 župe sad nasljeđuju koordinate svoje crkve umjesto Placesa |
| `parish_count_razlika` | 2 | 2 | |
| `wikidata_dijeljen` | 4 | 4 | |
| `engleski_nazivi` | 32 | 32 | |
| `bez_zupanije` | 9 | 9 | |
| `crkve_dalje_20km_od_zupe` | 9 | 6 | 3 od njih bile su nekatoličke filijale |

| kontekst | prije | poslije | razlika |
|---|---:|---:|---:|
| `crkve_ukupno` | 6966 | 6966 | 0 |
| `crkve_sa_zupom` | 2929 | 2857 | −72 |
| `zupne_crkve` | 1151 | 1154 | +3 |
| `zupe_aktivne` | 1561 | 1561 | 0 |
| `zupe_bez_zupne_crkve` | 487 | 484 | −3 |
| `zupe_bez_ijedne_crkve` | 421 | 418 | −3 |

`scripts/11` (zadnji run, poslije `fix-locations`): `zupna_crkva_spojena` 1154,
`kandidat_vec_zauzet` 38, `filijala_spojena` 1703, `filijala_nekompatibilna` 79.

## Mapiranje vrijednosti

Izmjereno usporedbom baze prije S2 i poslije, po slugu (samo vrijednosti koje su se promijenile).

**`churches.denomination`** (`src/denomination.py`, `_SINONIMI`)

| prije | poslije | broj |
|---|---|---:|
| `catholic` | `roman_catholic` | 1022 |
| `adventist` | `seventh_day_adventist` | 7 |
| `hungarian_reformed` | `reformed` | 2 |
| `united_reformed` | `reformed` | 1 |
| `roman_catholicadded` | `roman_catholic` | 2 |
| `katolička` | `roman_catholic` | 1 |
| `benedictine_sisters` | `roman_catholic` | 1 |
| `neo-pentecostal`, `philadelphian` | `pentecostal` | 1 + 1 |
| `church_of_christ`, `episcopal` | `protestant` | 1 + 1 |
| `serbian_orthodox;orthodox` | `serbian_orthodox` | 1 |
| `hare_krishna`, `old_paneuropean`, `sv. florijan`, `sv. petar i pavel` | NULL | 4 |

**`churches.religion`**: `krščanstvo1` (3), `krščanstvo2` (1) → `christian`; `bogomilism` (2) → NULL.

**`parishes`** (evidencija vjerskih zajednica, `scripts/03` → `community_denomination`)

| prije | poslije | broj |
|---|---|---:|
| `adventist` | `seventh_day_adventist` | 106 |
| `protestant` | `old_catholic` (Katolička Stara Crkva) | 5 |
| `evangelical` | `methodist` | 2 |
| `protestant` | NULL (scijentolozi) | 2 |
| `buddhist`, `hindu`, `jewish` kao denominacija | NULL (religija ostaje) | 3 |
| religija NULL | `hindu` | 8 |
| religija `christian` | NULL (scijentolozi) | 2 |

**`dioceses`**: `jewish` kao denominacija → NULL (12); `protestant` → `mormon`, `new_apostolic`,
`old_catholic` (po 1), scijentolozi → NULL; `evangelical` → `methodist`, `waldensian`;
`adventist` i `reformed` (Reformni pokret adventista) → `seventh_day_adventist`;
`buddhist`, `hindu` kao denominacija → NULL.

**`churches.kind`** (`kinds._christian_evidence`): `svih-svetih-dakovo-w522826735` dzamija →
crkva, `evandeoska-pentakostalna-crkva-radosne-vijesti-osijek-w555206682` sinagoga → crkva,
`svetih-petra-i-pavla-daruvarski-brestovac-w1183891549` crkva → pravoslavna-crkva (konfesija
`serbian_orthodox;orthodox` sad prepoznata). Ukupno: džamija 20 → 19, sinagoga 16 → 15,
pravoslavna-crkva 288 → 289; nijedna druga promjena kinda.

## Diff veza crkva → pravna osoba

Usporedba po slugu crkve (`churches.parish_id` → `parishes.slug`), baza prije S2 naspram
konačne. Nijedna građevina nije nestala ni nastala (6966 = 6966).

| | broj |
|---|---:|
| odspojene, nekatolička građevina s katoličke pravne osobe | 71 |
| odspojene, katolička građevina sa srpskopravoslavne crkvene općine | 5 |
| nove veze | 4 |
| premještene na drugu pravnu osobu | 3 |
| ista pravna osoba, promijenjen `is_parish_church` | 0 |

**Uvjet iz plana** („pad spojenih ≤ broj odspojenih nekatoličkih”): pad je 72 = 76 odspojenih
− 4 nove. To je za 1 više od 71 nekatoličke, jer pravilo radi u oba smjera (odluka 4) i
odspojilo je i 5 katoličkih filijala sa SPC crkvenih općina. Svih 76 odspojenih veza pravilo
izričito zabranjuje; nijedna nije izgubljena iz drugog razloga.

**71 nekatolička odspojena**: 70 filijala i 1 župna crkva (pravoslavna sv. Nikola, Rijeka, na
„ŽUPA SV. NIKOLE B.”). Po vrsti: pravoslavna-crkva 52 (38 `serbian_orthodox`, 14 `orthodox`),
manastir/kapela pravoslavne konfesije 5 (Pakra, Gomirje, Lipovo Polje, Koreničani, Glogovac),
džamija 4 (Maljevac, Gunja, Bogovolja, Umag), baptisti 4 (Severin na Kupi, Pušćine, Sirač,
Donji Sređani), adventisti 2 (Belišće, Virje), pentekostni 2 (Belišće, Koška), Jehovini
svjedoci 2 (Poreč, Tribalj).

**5 katoličkih odspojenih sa SPC crkvenih općina** (bile filijale): Sveti Matej, Kućanci;
Svih Svetih, Razvođe; Svih Svetih, Erdut; sv. Ivan Krstitelj, Severin; sv. Vendelin, Jagodnjak.

**Nove veze (sve)** — u prolazu 1 pravoslavna konkurentica istog titulara više ne ruši marginu:

| građevina | pravna osoba | `is_parish_church` |
|---|---|---|
| `svetog-nikole-tavelica-rijeka-w271740401` crkva sv. Nikole Tavelića | ŽUPA SV. NIKOLE TAVELIĆA, Rijeka | 1 |
| `preobrazenja-gospodnjeg-petrinja-w891075661` crkva Preobraženja Gospodnjeg | ŽUPA PREOBRAŽENJA GOSPODNJEG, Petrinja | 1 |
| `svetog-nikole-biskupa-vinkovci-w1241791410` crkva sv. Nikole biskupa | ŽUPA SV. NIKOLE BISKUPA, Vinkovci | 1 |
| `svetog-kriza-zagreb-w891857715` crkva Svetog Križa (`old_catholic`) | ŽUPA SV. KRIŽA, Zagreb, Kneza Branimira 11 (`old_catholic`, evidencija vjerskih zajednica) | 1 |

**Premještene (sve)**:

| građevina | prije | poslije | ocjena |
|---|---|---|---|
| `svetih-cirila-i-metoda-rijeka-w1190425628` (`roman_catholic`) | ŽUPA SV. ĆIRILA I METODA - RIJEKA (`old_catholic`, Korzo 2A) | ŽUPA SV. ĆIRILA I METODA (`roman_catholic`, Bulevar oslobođenja 26a) | točno po pravilu: građevina je u OSM-u `roman_catholic`; Places obje pravne osobe stavlja na istu točku, pa adresa ne razlikuje |
| `isusova-uskrsnuca-sesvete-w416430719`, Dugoselska cesta 4 | ŽUPA USKRSNUĆA ISUSOVA (Zagreb, Hrastin prilaz bb) | ŽUPA ISUSOVA USKRSNUĆA (Sesvete, Dugoselska 4) | točno: adresa se poklapa doslovno |
| `samostan-zagreb-w76205395` „Samostan”, Av. Marina Držića 31/2 | DRUŽBA KĆERI MILOSRĐA … SAMOSTAN SV. OBITELJI (Šestinski vijenac 3, ~6 km sjeverno) | URŠULINSKI SAMOSTAN (Barčev trg 9) | stara veza kriva (Places konflikt 6,7 km); nova je bolja, ali i sama u `geo_conflicts` (1,7 km od Places točke, koja je za sve tri zagrebačke uršulinske pravne osobe ista: Vlaška 75) — ostaje na pregledu |

Zadnja dva premještanja su posljedica `weak_claim` (ispod), ne pravila konfesije.

**Places kao nezavisna provjera** (`geo-konflikti.csv`, 40 → 39 redaka): nestala su dva
konflikta — Kćeri milosrđa → „Samostan” (6,7 km) i ŽUPA SV. NIKOLE B. → pravoslavna sv. Nikola
(3,4 km; Places tu župu nalazi kao „Župa sv. Nikole biskupa”, Smolikara 22). Novi je jedan:
Uršulinski samostan → „Samostan” (1,7 km).

## Trsat i Rijeka sv. Nikola

**Regresija.** Prije S2: `franjevacki-samostan-rijeka-r3560310` (OSM „Franjevački samostan”,
Trsat) bio je župna crkva pravne osobe „FRANJEVAČKI SAMOSTAN RIJEKA - TRSAT” (Frankopanski trg 12)
— točno. Nakon pravila (rebuild 1) prešao je na „FRANJEVAČKI SAMOSTAN SV. NIKOLE” (Ivekovićeva 8,
isto sjedište kao ŽUPA SV. NIKOLE TAVELIĆA; Places ga stavlja 4,5 km od Trsata). Kriva veza, a
samostan sv. Nikole je usput naslijedio trsatske koordinate (`geocode_source='church'`).

**Uzrok.** OSM naziv nema titular, pa je „franjevački samostan” podniz obaju naziva i obje pravne
osobe daju `token_set_ratio` 100. Samostan sv. Nikole (id 588) dolazi na red prije Trsata (690).
Prije S2 je njegov bazen sadržavao i pravoslavnu „crkvu svetog Nikole” (također 100), margina je
pala i on je ostao nespojen; pravilo je tu pravoslavnu maknulo i podniz je ostao sam.

**Popravak** (`src/match.py: weak_claim`, `scripts/11`): prolaz 1 najprije izračuna pogodak za
svaku pravnu osobu, a zatim ih obrađuje tako da **slabi zahtjevi idu zadnji** — pravna osoba
imenuje sveca (`head_key`), a građevina nema titular. Sortiranje je stabilno, ostali redoslijed
ostaje po id-u. Slab zahtjev se ne odbija: sam u mjestu je obično točan (prije S2 je takvih
župnih crkava bilo 9 od 1151, među njima Badija, Pridvorje, Pavlinski samostan). Mijenja se samo
tko dobiva građevinu kad je traže dvije pravne osobe. Testovi:
`test_weak_claim_trsat_ide_prije_sv_nikole`, `test_weak_claim_ne_dira_poklapanje_titulara`.

**Ishod** (rebuild 2 naspram rebuilda 1): Trsat natrag na „FRANJEVAČKI SAMOSTAN RIJEKA - TRSAT”;
samostan sv. Nikole nema građevinu i opet ima Places koordinate (Ivekovićeva 8), kao prije S2.
Ista promjena premjestila je još dvije veze (Sesvete i zagrebački „Samostan”, tablica gore); obje
su prije bile krive, a zagrebačka nova je i dalje nepotvrđena. Brojke se ne mijenjaju (premještanja, ne gubici). Napomena: Sesvete je
„slab zahtjev” samo zbog asimetrije titulara — `head_key("ŽUPA USKRSNUĆA ISUSOVA")` je
`uskrsnuce isusovo`, a `head_key("crkva Isusova uskrsnuća")` je None. Tu je pomoglo, ali je to
nalaz za S3 (titular).

**ŽUPA SV. NIKOLE B., Rijeka** (Giordana Smolikara 22): **ostaje bez župne crkve** i bez ijedne
građevine. Prije S2 joj je župna crkva bila pravoslavna sv. Nikola, a sjedište je od nje
naslijedilo koordinate (45.32584, 14.44284). Sad je sjedište iz Placesa (45.33795, 14.40278):
3,4 km od pravoslavne crkve i 0,29 km od katoličke `svetog-nikole-biskupa-rijeka-w159810306`
(„crkva svetog Nikole biskupa”), koja je gotovo sigurno njezina župna crkva. Matcher je ne spaja
jer „sv nikole b” daje 90 i s „sv. Nikole biskupa” i sa „sv. Nikole Tavelića” — margina pada.
Kratica „B.” za „biskupa” je pitanje titulara (S3); ovdje je ostavljeno nespojeno, što je pošteno.

## Pravoslavne pravne osobe (mjerenje, ništa nije uključeno)

Evidencija vjerskih zajednica: 435 zapisa `serbian_orthodox`, 434 aktivna i bez duplikata —
402 `crkvena-opcina`, 29 `eparhija`, 2 `parohija`, 1 `ostalo`. Pravoslavnih građevina
(`kind=pravoslavna-crkva` ili konfesija `*orthodox`) je 326.

**Stanje u pipelineu:** 27 građevina već je spojeno na pravoslavne pravne osobe, sve kao filijale
iz 2. prolaza (jedina pravna osoba u mjestu), nijedna kao „župna”. Od toga 13 pravoslavnih i 14
nepoznate konfesije; među tih 14 su i po nazivu vjerojatno katoličke (kapela Gospe Karmelske,
Orovac; crkva sv. Mihaela Arkanđela, Borik). Pravilo ih ne hvata jer nepoznata
konfesija ne blokira, a `nekatolicke_na_katolickim` mjeri samo katoličku stranu. Otvoreno.

**A. Isti matcher** (`best_match(index, naziv, place_key(city))`, bazen = građevine koje prolaze
`compatible(c, p)` **i** su pravoslavne): **7 od 434** spojeno, sve score 100, nijedna građevina
dvaput. Svih 7 su manastiri zapisani kao `kind=eparhija` (koji nije u `PARISH_KINDS`, pa ih
`scripts/11` ionako ne gleda): Krka (crkva sv. arhanđela Mihaila, Kistanje), Lazarica
(Zvjerinac), Crnogorci (hram sv. Vasilija Ostroškog, Krivodol), Marča, Orahovica, Pakra,
Lepavina. Ocjena: **7/7 točno**. Uzorak od 20 nije moguć (7 < 20), ocijenjeni su svi.
Ostalih 427: 306 ima pravoslavnu građevinu u bloku, ali naziv ne prolazi, 121 nema nijednu u
bloku. Razlog: naziv crkvene općine je „SRPSKA PRAVOSLAVNA CRKVA U HRVATSKOJ, EPARHIJA …,
CRKVENA OPĆINA X” — bez titulara, pa usporedba naziva nema što usporediti. Usto je `city`
adresa sjedišta (često paroh u drugom mjestu: CO Veliki Šušnjar → Petrinja), a ne X.

**B. Po mjestu** (jednokratna varijanta, nije matcher): crkvena općina X ↔ jedina pravoslavna
građevina u naselju X (`place_key` od X naspram naselja/grada građevine), a ako ih u naselju nema,
jedina u općini X. Od 402 crkvene općine: **172 jednoznačno** (167 po naselju, 5 po općini),
30 dvosmisleno (24 + 6), 200 bez pravoslavne građevine. 5 građevina dobiva po dvije općine
(treba pravilo jedinstvenosti u oba smjera).

Uzorak 20, `random.seed(20261120)`, `random.sample` nad 172 pogotka. Kriterij: građevina je u
naselju koje općina imenuje, pravoslavna je i naziv joj ne proturječi. Udaljenost je od sjedišta
pravne osobe (adresa paroha), pa nije mjera točnosti.

| # | crkvena općina | sjedište (evidencija) | građevina | naselje / općina | razina | d | ocjena |
|---|---|---|---|---|---|---:|---|
| 1 | Budimci | Budimci | crkva Vaznesenja Gospodnjeg | Budimci / Podgorač | naselje | 1,2 km | točno |
| 2 | Đakovo | Vladislavci (Dopsin) | Crkva Uznesenja Gospodnjeg | Đakovo | naselje | 35,7 km | točno |
| 3 | Zelovo | Split | Sv. Ilija | Zelovo / Muć | naselje | 25,3 km | točno |
| 4 | Debelo Brdo | Korenica | „Sakralni objekt” (bez naziva) | Debelo Brdo / Udbina | naselje | 9,6 km | nejasno |
| 5 | Vrlika | Vrlika | Crkva sv. Nikole | Vrlika | naselje | 0,4 km | točno |
| 6 | Pula | Peroj | Crkva Sv. Nikole | Pula | naselje | 9,6 km | točno |
| 7 | Novi Pavljani | Bjelovar | Parohijska crkva Sv. Pavla | Novi Pavljani / Bjelovar | naselje | 4,6 km | točno |
| 8 | Sinj | Glavina Donja | Crkva sv. apostola Petra i Pavla | Sinj | naselje | 53,7 km | točno |
| 9 | Dopsin | Dopsin | crkva sv. Petra i Pavla | Dopsin / Vladislavci | naselje | 0,8 km | točno |
| 10 | Stara Gradiška | Stara Gradiška | crkva svete Petke | Gređani / Stara Gradiška | općina | 8,7 km | nejasno |
| 11 | Novoseljani | Bjelovar | crkva sv. Ilije | Novoseljani / Bjelovar | naselje | 2,6 km | točno |
| 12 | Veliki Pašijan | Garešnica | crkva sv. Đurađ | Veliki Pašijan / Garešnica | naselje | 6,2 km | točno |
| 13 | Nebljusi | Donji Lapac | „Sakralni objekt” (bez naziva) | Nebljusi / Donji Lapac | naselje | 11,9 km | nejasno |
| 14 | Benkovac | Benkovac | Sv. Jovana | Benkovac | naselje | 0,0 km | točno |
| 15 | Blatuša | Glina | hram svetog oca Nikolaja | Blatuša / Gvozd | naselje | 16,4 km | točno |
| 16 | Mlakva | Plaški | Hram Rođenja Presvete Bogorodice „Mlada Neđelja” | Mlakva / Perušić | naselje | 39,1 km | točno |
| 17 | Lipovo Polje | Vranovača | Crkva Sv. Arhangela Mihaila | Lipovo Polje / Perušić | naselje | 36,7 km | točno |
| 18 | Velika Bršljanica | Veliko Vukovje | parohijska crkva sv. Oca Nikolaja | Velika Bršljanica / Garešnica | naselje | 8,8 km | točno |
| 19 | Mutilić | Korenica | Crkva Preobraženja Gospodnjeg | Mutilić / Udbina | naselje | 26,1 km | točno |
| 20 | Otočac | Otočac | crkva svetog Georgija | Otočac | naselje | 2,5 km | točno |

**17 točno, 0 krivo, 3 nejasno** (dvije neimenovane građevine, jedna na razini općine u drugom
naselju). Ocjena je prema podacima u bazi i nazivu, ne terenska.

**Preporuka:** spajanje pravoslavnih ne uključivati ni u S2 ni kao proširenje postojećeg
matchera — matcher po nazivu za crkvene općine ne radi (7/434). Pravilo po mjestu izgleda
precizno, ali je novo pravilo s vlastitim odlukama (samo razina naselja ili i općine; što s
neimenovanim objektima; jedinstvenost u oba smjera; `is_parish_church` za pravoslavne nema
smisla — „parohijska crkva” bi bila nova kolona ili značenje). Predlažem zasebnu stavku poslije
S3 (ili otvoreno u `TODO.md`), uz uvjet da se istim korakom riješi i 14 građevina nepoznate
konfesije koje 2. prolaz danas lijepi na SPC općine. Usputni nalaz: `scripts/03` 20 zapisa s „MANASTIR”
u nazivu klasificira kao `eparhija`, a ne `samostan`.

## Reproducibilnost

Konačni kod, dva uzastopna `make rebuild` od prazne baze s mrtvim proxyjem (0 mrežnih pokušaja u
logu): `data/exports/*` i `audit.json` **bajt-identični**. Sha256 (prvih 12 znakova):

| datoteka | rebuild 2 = rebuild 3 |
|---|---|
| audit.json | `7e22812a2a9c` |
| crkve.geojson | `41ce66085cef` |
| zupe.geojson | `8d8401a11309` |
| biskupije.geojson | `a00419b8cee6` |
| crkve.csv | `68c36d8de5b5` |
| zupe.csv | `d0c2105a58b3` |
| biskupije.csv | `c44af03a9a1a` |
| bastina-nespojeno.csv | `7522585224e5` |
| geo-konflikti.csv | `b9fe1035f11e` |
| stats.json | `a8b58b6cce3b` |

Treći rebuild (rebuild 4) dao je iste sha za sve gore. `frontend/public/data/` (9400 datoteka):
identičan između rebuilda 3 i 4 osim `manifest.json`, koji namjerno nosi `generated_at`
(`scripts/34`). Sama `data/crkve.db` nije bajt-identična (`updated_at` = vrijeme runa), što
exporti ne prenose.
