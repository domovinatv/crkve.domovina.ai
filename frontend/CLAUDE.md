# CLAUDE.md — frontend/ (crkve.domovina.ai)

Web kataloga crkava. Nastao iz `stepanic/hr-site-starter` templatea, ali
**nije više klijentski marketinški web** — sadržaj ne piše čovjek, nego dolazi
iz baze. Pipeline i model podataka: `../CLAUDE.md`.

## Stack

TanStack Start + Nitro (`preset: cloudflare-module`) → Cloudflare **Worker**.
shadcn/ui + Tailwind v4, React 19, bun. Bez baze, bez auth-a, bez secreta.

```sh
bun run dev          # vite dev, port 5173
bun run typecheck    # tsc --noEmit
bun run lint         # eslint (7 react-refresh warninga iz shadcn je normalno)
bun run build        # → .output/
./scripts/deploy.sh  # export podataka → provjere → build → wrangler deploy
```

## Podaci su generirani, ne pisani

`public/data/` piše `../scripts/34_export_static.py` (`make export-web` iz
korijena repoa). **Gitignoran je** — 9400 datoteka. U čistom checkoutu ga
nema, pa `bun run dev` prije prvog `make export-web` daje prazne stranice.

| Datoteka                                                       | Što                                                     |
| -------------------------------------------------------------- | ------------------------------------------------------- |
| `crkve-index.json`                                             | 6966 slim zapisa — karta i pretraga                     |
| `zupe-index.json`                                              | pravne osobe koje imaju stranicu                        |
| `crkva/<slug>.json`                                            | detalj građevine                                        |
| `zupa/<slug>.json`, `ustanova/<slug>.json`                     | detalj pravne osobe                                     |
| `biskupija/<slug>.json`, `biskupije.json`, `biskupije.geojson` | biskupije                                               |
| `stats.json`                                                   | mjera iz `scripts/40` — **brojke se NE računaju ovdje** |
| `manifest.json`                                                | `generated_at` i brojke                                 |

Tipovi su u `src/lib/catalog.ts` i moraju pratiti export. Loaderi su u
`src/lib/data.ts`.

## Tvrda pravila

### Dvije jedinice stranice, i to je namjerno

`/crkva/$slug` je **građevina**, `/zupa/$slug` i `/ustanova/$slug` su
**pravna osoba**. To nisu isti skup (6966 : 2358, veza N:1) — jedna župa ima
župnu crkvu i filijale, a samostanska ili grobljanska crkva nema župu. Ne
spajaj ih u jednu stranicu.

`/ustanova/` postoji da URL ne laže: samostan i crkvena općina nisu župe.

### Brojke se ne računaju u komponenti

Sve brojke dolaze iz `stats.json` ili `manifest.json`. Ako negdje treba nova
brojka, doda se u `scripts/40_stats.py`, ne u JSX. Dvije brojke koje se same
računaju uvijek se raziđu — u ovom repou se to već dogodilo (vidi „župa bez
crkve" u `../CLAUDE.md`).

Ne hardkodiraj brojke u tekst. Zastare pri prvom rebuildu podataka.

### Rupa u podacima se ISPISUJE

Nula nije „nema podatka" nego nalaz. Župa bez spojene građevine dobiva
`<Gap>` s objašnjenjem, ne praznu sekciju. Ako sakriješ rupu, potrošač je ne
može ni primijetiti ni prijaviti.

### Veliki indeks NE ide u loader rute

TanStack serijalizira loader podatke u HTML. `crkve-index.json` je 1,5 MB —
u loaderu bi ga posjetitelj dobio dvaput. Indeks se dohvaća **na klijentu**
(`CatalogMap`, `ChurchBrowser`, `ParishBrowser`); loaderi smiju samo male
datoteke (detalj, stats, manifest, biskupije).

### MapLibre zamke

- **`case` traži boolean.** `["case", ["get", "heritage"], …]` s brojem 0/1
  baca „Expected boolean but found number" i **obori cijeli sloj bez greške
  vidljive na karti**. Zato `toFeatureCollection` piše prave booleane.
- **Filtar mijenja podatke izvora, ne `setFilter` na sloju** — klasteri se
  grade iz izvora, pa bi `setFilter` ostavio klastere koji broje sakrivene
  objekte.
- **`maplibre-gl` v6 nema default export.** `(await import(…)).default` je
  `undefined`; koristi imenovane (`const m = await import("maplibre-gl")`).
- **MapLibre se učitava ISKLJUČIVO kroz `@/lib/maplibre`,** nikad izravnim
  `await import("maplibre-gl")`. v6 workera drži u zasebnoj datoteci koju traži
  s `new URL("./maplibre-gl-worker.mjs", import.meta.url)` — URL sastavljen u
  runtimeu, pa ga Vite ne vidi i ne emitira. U buildu je to onda 404 i karta
  **tiho** stane: stil se parsira, kontrole se iscrtaju, ali worker ne dohvati
  nijednu pločicu, `map.on("load")` ne okine i naši slojevi se ne dodaju — bez
  ijedne greške u konzoli. `?worker&url` + `setWorkerUrl` to rješava.
- **Prazan sivi okvir ima dva uzroka i treba ih razlikovati mjerenjem.**
  Prvo `document.visibilityState`: u skrivenom tabu `requestAnimationFrame` ne
  radi, MapLibre ne dovrši stil i to nije bug nego nevidljiv prozor. Ako je tab
  `visible`, mjeri worker — `style.dispatcher.broadcast(…)` koji timeouta i
  nula `.pbf` zahtjeva znače da worker nije živ. Jedna sesija je izgubljena
  jer je prvi uzrok uzet kao objašnjenje za drugi.
- Instanca je izložena kao `window.__crkveMap` za provjeru u konzoli (isti
  obrazac kao `window._gisMap` u `../../karta-hrvatske`).

### Boje idu kroz tokene

Sve u `src/styles.css`, u oklch. Iznimka su **boje karte** (`--map-*`), koje
su namjerno u hexu: MapLibre ima vlastiti parser boja i ne jamči CSS Color 4.
Komponenta ih čita `getComputedStyle`-om, ne hardkodira.

Akcenti nose značenje: `--accent-1` zaštićeno kulturno dobro, `--accent-2`
rupa u podacima, `--accent-3` potvrđena lokacija.

### Ovo je TanStack Router, ne Next.js

Konvencije: `src/routes/README.md`. Nikad `src/pages/`, `app/layout.tsx`,
`"use client"`, `next/link`. `src/routeTree.gen.ts` je generiran.

### SEO

Svaka ruta ima `head: () => ({ ...pageHead({...}), scripts: [breadcrumbLd(...)] })`.
Točno jedan `<h1>`. Structured data: `Dataset` je globalan u `__root.tsx`
(ne `LocalBusiness` — ovo nije poslovni subjekt), `PlaceOfWorship` na
građevini, `Organization` na pravnoj osobi.

**Sitemap se generira iz indeksa** (`src/routes/sitemap[.]xml.tsx`, ~9400
URL-ova). Ručan je samo popis statičnih ruta na vrhu te datoteke — ako dodaješ
rutu, dodaj je ondje.

## Ton hrvatskog teksta

Stručan, suh, bez marketinga. Dijakritika obavezna. Ne tvrdi preciznost koju
podatak nema: derivirani teritorij uvijek ide uz svoju mjeru slaganja.

## Prije nego kažeš da si gotov

```sh
bun run typecheck && bun run lint && bun run build
```

Sva tri moraju proći; errora mora biti 0.
