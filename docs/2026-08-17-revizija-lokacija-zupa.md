# Revizija lokacija župa (2026-08-17)

Povod: na gis.domovina.ai dio otoka **Raba (Barbat)** bio je obojan kao
Zadarska nadbiskupija, iako klik na župu u Barbatu ispravno piše Krčka
biskupija.

Nalaz: **granice biskupija nisu krive — krive su koordinate pojedinih župa.**
Derivacija u `scripts/20_derive_diocese_areas.py` radi točno ono što piše;
ulaz joj je zagađen.

## Korijenski uzrok

Državna evidencija piše sjedište kao „Mjesto, Ulica br" **bez županije**.

1. `geo_hr.settlement_centroid()` odbija višeznačno ime (npr. „Vrh" postoji u
   Buzetu i na Krku) i vraća `None` → župa ostaje bez koordinata **i bez
   `county`**.
2. `scripts/13_places_parishes.py` ima čuvara „Places rezultat mora pasti u
   istu županiju", ali `county` je `NULL`, pa čuvar **tiho ne radi ništa**.
3. Google onda slobodno bira krivi homonim.

Dodatno, sama evidencija ponekad normalizira naziv naselja u krivi homonim
(„Barbat" → „Barbat Na Rabu", iako je župa na Pagu) ili skraćuje službeni
naziv („Kraj" umjesto „Dicmo Kraj").

## Tri detektora (nezavisna, komplementarna)

| # | Test | Hvata |
|---|------|-------|
| A | leži li točka u naselju koje piše u evidenciji | 94/1562 izvan |
| B | slaže li se biskupija sa 12 najbližih župa | 26 kandidata |
| C | medijan udaljenosti sjedišta do **vlastitih** crkava | 12 > 8 km |

C hvata homonime koje A propušta (ime se poklapa, ali je krivi homonim).

## Potvrđene krive koordinate (11) — svaka provjerena vanjskim izvorom

| reg. ID | župa | bilo | treba | izvor |
|---|---|---|---|---|
| 701708 | Bezgrešnog začeća BDM, Barbat | Barbat, **Rab** | **Zubovići**, Novalja | Adresar Zadarske nadb.: „53296 Zubovići" |
| 700502 | sv. Jakova ap., Kraj | Kraj, Mošć. Draga | **Dicmo Kraj** | smn.hr: „Župa sv. Jakova ap. – Dicmo Donje" |
| 702384 | sv. Martina | Sv. Martin na Muri | **Sveti Martin**, Sveta Nedelja (IS) | Porečka i pulska: „Sv. Martin 23, 52231 Sveta Nedelja" |
| 702189 | sv. Pelagija | Novigrad (ZD) | **Novigrad – Cittanova** | adresa „Park Novigradske biskupije" |
| 702093 | sv. Marije Magdalene | Kostanjevac (Istra) | **Kostanjevac**, Žumberak | adresa „Oštrc, Tupčina 4" |
| 701029 | Uznesenja BDM | Vrana (Pakoštane) | **Vrana**, Cres | Wikipedija: Župe Krčke biskupije, dekanat Cres |
| 702464 | sv. Juraja mč. | Zagorje (KZŽ) | **Zagorje**, Ogulin | adresa „Gornje Zagorje 10" |
| 702532 | Svih svetih, Požeške Sesvete | Sesvete (ZG) | **Sesvete**, Pleternica | naziv |
| 702103 | BDM Karmelske | Krasica – Crassiza (Buje) | **Krasica**, Bakar | Riječka nadb.; evidencija normalizirala u istarski homonim |
| 701089 | sv. Mihovila ark. | Vrh (ST) | **Vrh**, Krk | biskupijakrk.hr, „100 godina župe Vrh", Kosići |
| 701094 | sv. Mihovila ark. | Sveti Vid (ST) | **Sveti Vid‑Miholjice** | Wikipedija: župna crkva sv. Mihovila |

Još iz detektora C (za doraditi): Slivno (treba Dubrovačko‑neretvanska, ne
Omiš), Dobranje, Soline.

## Provjereno i **nije** greška

Sućuraj → Hvarska · Vrlika → Splitsko‑makarska (nije na popisu Šibenske) ·
Radošić, Lećevica, Ogorje, Marina → Šibenska · Kistanje, Ervenik → Zadarska ·
Novalja, Lun, Omišalj → Krk · Brseč, Vodice (Lanišće) → Riječka · Jablanac →
Gospićko‑senjska · Vela Luka → Dubrovačka · Vojnić, Dubranec, Šišljavić →
Sisačka · Palanka → Gospićko‑senjska · Kaniška Iva → Bjelovarsko‑križevačka.

Pag je uistinu podijeljen: Novalja i Lun su Krčka, a Kolan i Barbat
(Zubovići/Kustići/Vidalići/Metajna) Zadarska — to na karti mora ostati.

## Zasebna greška: crkva → župa preko homonima

`scripts/11_match_parishes.py` spaja po imenu mjesta bez provjere udaljenosti,
pa crkve u istarskom Lupoglavu vise na zagrebačkoj župi (180 km), Soline s
Mljeta na zadarskoj (319 km), Kostanjevac iz Berka na žumberačkoj (228 km).
Mjereno: 29 crkava > 25 km od sjedišta svoje župe, 125 > 10 km.

## Ostalo

Dvostruki upisi u evidenciji (napuhuju `parish_count`): sv. Ivana Krstitelja
Prizna, sv. Stjepana Prgomet.

---

# Dovršetak (2026-08-27)

Gornji nalaz je bio točan, ali implementacija je imala dva kvara koja su se
vidjela tek na **drugom** runu. Oba su nađena tako da se korekcija pokrenula
dvaput zaredom i tražilo da drugi put ne napravi ništa.

## Kvar 1: prag „2 župe po županiji" rušio je ispravan podatak

Izvod dozvoljenih županija tražio je **dvije** sigurno smještene župe da bi
biskupiji pripisao županiju. Namjera je bila dobra — jedna krivo smještena
župa ne smije sama sebi napisati dozvolu. Posljedica nije.

**Riječka nadbiskupija u Istarskoj županiji ima točno jednu župu**: sv.
Martina u Vodicama (Lanišće, Ćićarija). Ista ona koja u popisu gore stoji pod
„provjereno i nije greška". Čim je override odselio bujsku Krasicu iz Istre,
potpora Istarskoj pala je s 2 na 1 → ispod praga → sljedeći run je Vodice
htio premjestiti **58 km** u istoimeno naselje u Primorsko-goranskoj.

Korekcija je, dakle, sama sebi proizvodila greške, i to **kaskadno**: svaki
run drugačiji ulaz, drugačiji rezultat. Podatak koji bi se commitao ovisio bi
o tome koliko je puta netko pokrenuo `make fix-locations`.

Popravak je u dva poteza:

1. **Prag je spušten na 1.** Asimetrično i svjesno: propuštena greška ostaje
   greška, ali se ispravan podatak ne kvari. Cijena je da usamljena krivo
   smještena župa sama sebi otvori županiju i time se zaštiti.
2. **Tri župe koje su time izgubile pokriće dobile su OVERRIDE**, svaka s
   izvorom: Novigrad (702189), Vrana/Cres (701029), Požeške Sesvete (702532).
   Bez toga bi ispale iz korekcije — mjereno, 11 → 9 ispravaka.

Uz to se **izvod županija računa nad ISPRAVLJENIM odredištima**: župa pod
override-om broji se u županiju u koju pripada, bez obzira gdje joj je točka
trenutno. Bez toga izvod ovisi o tome je li korekcija već pokrenuta — što je i
bio izvor kaskade.

## Kvar 2: 84 naselja imalo je „vlastitu" točku koja u njima nije

Reprezentativna točka naselja bila je težište najvećeg prstena, a kad težište
padne izvan (razvedeno, „U"-oblik) fallback je bio **prvi vrh poligona**. Vrh
leži NA granici, a `_in_ring` rubnu točku odbija. Rezultat: 84 od 6759
naselja tvrdilo je da ne sadrži samo sebe.

Nije kozmetika. Sveti Vid-Miholjice je jedno od tih 84, pa je njegov override
na **svakom** runu javljao „premjesti" i gazio koordinatu razine zgrade
težištem naselja. To je drugi izvor neidempotentnosti.

Zamijenjeno `representative_point()`: težište ako je unutra, inače sredina
najšireg unutarnjeg raspona na vodoravnici (parnost presjeka sa svim
prstenovima, pa se ni rupa ne može odabrati). Nakon toga **0 od 6759**.

## Stanje nakon dovršetka

```
14_fix_parish_locations   11 premješteno, 1551 ostaje
  ponovljeni run          0 premješteno          ← idempotentno
11_match_parishes         1151 župnih crkava, 1771 filijala,
                          28 filijala odbijeno kao > 25 km
20_derive_diocese_areas   96,9 % / 99,3 % / 98,7 % o OSM granicama
                          (bilo 96,6–98,6 %)
```

Provjereno na spornim mjestima nad `biskupije.geojson`:

| naselje | izvedena biskupija | ispravno |
|---|---|---|
| Barbat, Rab | Biskupija Krk | ✔ (bio Zadarska — povod cijele revizije) |
| Rab, Lopar | Biskupija Krk | ✔ |
| Zubovići, Kolan, Metajna (Pag) | Zadarska | ✔ (Pag je uistinu podijeljen) |
| Vodice, Lanišće | Riječka | ✔ (istarska eksklava) |
| Vrana, Cres | Biskupija Krk | ✔ |
| Vrana, Pakoštane | Zadarska | ✔ |

## Ostaje otvoreno

- Detektor C: Slivno (treba Dubrovačko-neretvanska), Dobranje, Soline.
- Dvostruki upisi u evidenciji: sv. Ivana Krstitelja Prizna, sv. Stjepana
  Prgomet — napuhuju `parish_count`.
- Usamljena krivo smještena župa i dalje se može sama zaštititi (posljedica
  praga 1). Hvata se samo ručno, OVERRIDE-om s izvorom.

---

# Drugi krug: preostale greške (2026-08-27)

Sva tri detektora vraćena su na **aktualne** podatke, umjesto da se popravlja
lista imena iz prvog kruga. Ta lista je bila zastarjela: Slivno, Dobranje i
Soline u međuvremenu sjede točno.

| detektor | prije | sada | nalaz |
|---|---|---|---|
| A — točka izvan imenovanog naselja | 94 | 85 | većina je normalno (župni ured izvan naselja); tek 17 je > 8 km |
| B — biskupija se ne slaže sa susjedima | 26 | 1 | Sućuraj, i to je **ispravno** (Hvar, a susjedi na kopnu) |
| C — medijan do vlastitih crkava > 8 km | 12 | 5 | svih 5 ispravno: Senj, Gračac, Klis, Plitvice, Oprisavci — velike ruralne župe |

## Odbačena ideja: „adresa imenuje naselje"

Evidencija u `address` često piše pravo mjesto („Sveti Petar Čvrstec 39" dok
`city` kaže „Križevci"). Izgledalo je kao pravilo koje bi riješilo ostatak
automatski. **Izmjereno: ne.** Od 540 župa čija adresa jednoznačno pogađa
neko naselje, 43 ima točku izvan njega — a od 17 najvećih odstupanja **16 je
lažno**, jer je riječ o ulici koja se zove kao neko naselje:

| adresa | stvarno | pravilo bi odvuklo u |
|---|---|---|
| „Kaptol 3", Zagreb | zagrebački Kaptol | Kaptol kod Požege, 142 km |
| „Dubovac 7", Karlovac | karlovački Dubovac | Dubovac kod G. Bogićevaca, 135 km |
| „Malo Selo 3", Mokošica | ulica u Dubrovniku | Malo Selo kod Delnica, 409 km |
| „Stari grad 76", Lovran | ulica u Lovranu | Stari Grad na Hvaru, 299 km |

Ostaje kao **detektor**, nikad kao popravljač.

## Novo pravilo: točka koja nije ni blizu (`Drop`)

Umjesto adrese, mjera je udaljenost do najbližeg naselja **imena koje piše u
evidenciji**. Raspodjela nad svih 1562 župe:

```
> 10 km: 17     > 20 km: 6      > 30 km: 4
> 15 km:  7     > 25 km: 5      > 60 km: 4
```

Iznad 30 km ostaju četiri, a tri su naši vlastiti (ispravni) OVERRIDE-i.
Četvrti je prava greška. Ispod 30 km upada Žirje (upisano na „Šibenik", otok
je 22 km od grada) — zato prag baš ondje.

Ishod je nov: ako je kandidat jedan → premjesti; ako ih je više → **obriši
koordinatu**. Prazna koordinata je poštena („ne znamo"), a izmišljena na
karti izgleda jednako uvjerljivo kao i sve ostale.

Time je pokrivena i **Križevačka eparhija**, koju izvod županija namjerno
preskače (preklapa se sa svim latinskim biskupijama) pa joj dotad nitko nije
provjeravao sjedišta. Njezina župa sv. Mihajla Arkanđela u Prgomelju sjedila
je u **Dubrovniku, 314 km** od oba Prgomelja (Pakrac i Bjelovar). Koje je
pravo, evidencija ne kaže — koordinata je odbačena.

## Šest ispravaka unutar iste biskupije

Ove izvod županija ne može vidjeti jer je i kriva i prava lokacija u istoj
županiji; greška je 9–15 km, ne 200. Svaka je provjerena u adresaru nadležne
biskupije.

| reg. ID | župa | bilo | treba | izvor |
|---|---|---|---|---|
| 701383 | Male Gospe | Bol (Brač) | **Selca kod Starog Grada** (Hvar) | hvarskabiskupija.hr: „Selca kod Starog Grada br. 20, 21460 Stari Grad" |
| 701272 | sv. Ivana Krstitelja | Povlja | **Bol** | hvarskabiskupija.hr: „Pjaca Joze Bodlovića 1, 21420 Bol" — ista adresa kao u evidenciji; povaljska ima „Lokva 1" |
| 702192 | Rođenja Marijina | Labin | **Rakalj** | biskupija-porecko-pulska.hr: „RAKALJ — župa Rođenja BDM" |
| 702428 | sv. Ivana Krstitelja | Labinci | **Majkusi** | isto: „SVETI IVAN OD ŠTERNE, Majkusi 1, 52463 Višnjan" |
| 700625 | sv. Ivana Krst. | Katuni | **Slime** | smn.hr/slime |
| 702420 | Uzvišenja sv. Križa | Perušić | **Gornji Vaganac** | gospicko-senjska-biskupija.hr (uprava iz Drežnik Grada) + u OSM-u crkva istog titulara ondje |

Zadnji je zanimljiv: adresar kaže „Vaganac", a DGU ima tri (Vaganac kod
Gospića te Donji i Gornji Vaganac kod Plitvica). Presudio je **vlastiti
katalog** — OSM ima „crkva Uzvišenja Svetog Križa" u Gornjem Vagancu.

## Dvostruki upisi: tvrdnja iz prvog kruga bila je preširoka

Prvi krug je naveo dva („Prizna", „Prgomet"). Izmjereno:

- **Prizna nije problem** — jedan od dva upisa ima `registry_status =
  PRESTANAK`, pa ga svi filtri ionako izbacuju.
- **Prgomet jest** — dva evidencijska broja (1.617 i 1.1296), ista adresa,
  tri mjeseca razmaka, oba AKTIVAN, nijedan nema OIB.

To je **jedina** prava dvostrukost među župama. Rješava je kolona
`parishes.duplicate_of` — zasebna, jer je to naša prosudba, a ne podatak:
država za oba upisa doista piše AKTIVAN. Signatura je stroga (isti
kind + naziv + mjesto + **adresa**, nijedan bez OIB-a); labavija bi spojila
dvije stvarne zagrebačke „ŽUPA SV. MARKA EVANĐELISTE" i tiho izgubila 6
zapisa.

## Stanje

```
14_fix_parish_locations   17 premješteno, 1 koordinata odbačena
  ponovljeni run          0                    ← i dalje idempotentno
katoličkih župa           1563 zapisa → 1561 aktivnih i različitih
župa bez župne crkve      487 (bez ijedne: 421)   ← bilo 489 / 424
```

## Ostaje otvoreno

- **702309, ŽUPA SV. JURJA, „Brdo - Berda"** — evidencija normalizirala naziv
  u bujsko Brdo-Berda, a Porečka i pulska ima „BRDO — župa Sv. Jurja
  mučenika, Brdo, **52232 Kršan**". To Brdo **nije DGU naselje** (zaselak),
  pa nema valjanog odredišta. Točka je zasad u Oprtlju.
- Usamljena krivo smještena župa i dalje se može sama zaštititi (posljedica
  praga 1 u izvodu županija). Hvata se samo OVERRIDE-om, s izvorom.
- Detektor A ima još 10-ak slučajeva u pojasu 8–15 km gdje se pola pokaže
  ispravnim (Zagreb→Sesvete, Križevci→Sveti Petar Čvrstec, Raša→Koromačno
  — svima adresa potvrđuje točku). Nije ih sigurno automatizirati.
