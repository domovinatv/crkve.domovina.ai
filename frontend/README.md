# frontend — crkve.domovina.ai

Web kataloga crkava i sakralnih objekata u Hrvatskoj. TanStack Start + Nitro →
Cloudflare Worker, shadcn/ui + Tailwind v4.

Podaci nisu u ovom folderu: generira ih Python pipeline iz korijena repoa u
`public/data/` (gitignorano).

## Prvi put

```sh
cd ..                        # korijen repoa
make all                     # izgradi bazu i sve exporte, uključivo export-web
cd frontend && bun install
bun run dev                  # http://localhost:5173
```

Ako baza već postoji, dovoljno je `make stats export-web`.

## Rute

| URL                              | Što                                           |
| -------------------------------- | --------------------------------------------- |
| `/`                              | naslovnica s brojkama                         |
| `/karta`                         | MapLibre karta svih objekata, filtri po vrsti |
| `/crkve`                         | pretraga i popis građevina                    |
| `/crkva/$slug`                   | detalj građevine (6966 stranica)              |
| `/zupe`                          | pretraga i popis pravnih osoba                |
| `/zupa/$slug`                    | detalj katoličke župe (1561)                  |
| `/ustanova/$slug`                | detalj ostalih mjesnih pravnih osoba (797)    |
| `/biskupije`, `/biskupija/$slug` | biskupije i derivirani teritoriji             |
| `/brojke`                        | pokrivenost i rupe                            |
| `/o-projektu`                    | izvori, postupak, licenca                     |
| `/sitemap.xml`                   | generiran iz indeksa, ~9400 URL-ova           |

## Deploy

```sh
wrangler whoami          # račun D.O.M.
./scripts/deploy.sh
```

Skripta regenerira podatke, provjeri typecheck i lint, buildа, deploya i onda
provjeri žive rute — ne samo `workers.dev`, nego i produkcijsku domenu.

Worker se zove `crkve-domovina`, a domena `crkve.domovina.ai` je u
`wrangler.jsonc` kao `custom_domain`, pa je wrangler sam kači i radi DNS zapis.
Ništa se ne kači ručno u dashboardu.

Worker nema nijedan secret ni binding — katalog je statički JSON u assetima.

## Porijeklo

Skelet je `stepanic/hr-site-starter`. Uklonjeno je sve za lokalni biznis
(kontakt forma, Resend, `LocalBusiness` schema, `/kontakt`, `/privatnost`),
a dodan je katalog: loaderi, karta, pretraga i detaljne stranice.
