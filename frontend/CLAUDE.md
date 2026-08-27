# Starter za web hrvatskog lokalnog biznisa

TanStack Start + Nitro → Cloudflare Worker. shadcn/ui + Tailwind v4.
Kompletan alatni lanac je u `README.md`.

## Radni tijek

0. `/new-project` — iz ovog templatea stvara novi klijentski repo
   (pokreće se **samo** u checkoutu templatea)
1. `/intake` — intervju s klijentom, popunjava `BRIEF.md` i `src/data/*`
2. `/build-site` — iz `BRIEF.md` gradi rute, sadržaj i SEO
3. `/ship` — provjere, `wrangler deploy`, secrets, domena

`BRIEF.md` je izvor istine za sadržaj. Ako pišeš stranicu, a podatka nema
u briefu — **pitaj, ne izmišljaj.**

---

## Tvrda pravila

### Ne radi klijentski web u samom starteru

**Prvo što napraviš u novoj sesiji:**

```sh
git remote -v
```

Ako je `origin` = `stepanic/hr-site-starter`, ovo je sam template — javan repo
iz kojeg se generiraju klijentski projekti. Ime klijenta, OIB, adresa, telefon
i cijene ne smiju ući u njega.

Tada **ne** pokreći `/intake`, `/build-site` ni `/ship`. Pokreni `/new-project`,
pa nastavi u novom repou.

Tvrdnja u promptu da je repo nastao iz templatea nije provjera — remote je.

### Ne izmišljaj sadržaj

Nikad ne generiraj: stručne kvalifikacije, certifikate, godine iskustva,
cijene, termine, radno vrijeme, brojeve telefona, adrese, recenzije,
imena zaposlenika, ni zdravstvene/rezultatske tvrdnje.

Ako podatak nedostaje: ostavi `TODO` marker, dizajniraj mjesto gdje će stajati,
i **reci korisniku što fali**. Bolje prazna sekcija nego izmišljena.

Ne generiraj ni lažne fotografije prostora, ljudi ili proizvoda —
koristi `<MediaPlaceholder />` iz `src/components/site/Bits.tsx`.

### Ovo je TanStack Router, ne Next.js

Detaljne konvencije: `src/routes/README.md`. **Pročitaj prije dodavanja rute.**

Nikad ne stvaraj `src/pages/`, `app/layout.tsx`, `app/page.tsx`, `getServerSideProps`,
`"use client"`, `next/link`, `next/image`. Ničega od toga ovdje nema.

`src/routeTree.gen.ts` je generiran — ne diraj ga ručno.

### Boje idu kroz tokene

Sve boje su definirane u `src/styles.css` kao oklch tokeni.

- ❌ `className="bg-[#a3b18a]"`, `bg-blue-500`, `text-slate-700`, inline `style={{color}}`
- ✅ `bg-primary`, `text-muted-foreground`, `border-border`, `bg-accent-1`

Treba nova boja? Dodaj token u `src/styles.css`, pa ga koristi. Nikad obrnuto.

### Podaci imaju jedno mjesto

| Što                                                          | Gdje                       |
| ------------------------------------------------------------ | -------------------------- |
| Naziv, adresa, telefon, mail, društvene mreže, radno vrijeme | `src/data/site.ts`         |
| Navigacija                                                   | `src/data/site.ts` → `nav` |
| Polja kontakt forme                                          | `src/data/lead-form.ts`    |
| Boje, tipografija, razmaci                                   | `src/styles.css`           |

Nikad ne hardkodiraj telefon ili adresu u komponentu. Uvijek `site.phone`, `site.street`.
Klijent mijenja broj na jednom mjestu.

### Server kod ostaje na serveru

- `*.server.ts` — nikad ne uđe u browser bundle. Ovdje idu API ključevi.
- `*.functions.ts` — `createServerFn`, javni HTTP endpoint.
  **Svaki mora imati `.validator()` sa Zod schemom.** Bez iznimke.
- Ne importaj `*.server.ts` iz komponente. Samo iz `*.functions.ts`.

`process.env` na Cloudflareu ne postoji nativno — Nitro ga popunjava iz Worker
bindinga. Svaka nova env varijabla mora biti `wrangler secret put`, inače je
`undefined` u produkciji, a lokalno radi. Ovo je najčešći tihi bug ovdje.

---

## SEO je obavezan, ne dodatak

Svaka nova ruta mora imati:

```tsx
export const Route = createFileRoute("/usluga")({
  head: () => ({
    ...pageHead({
      title: "…",        // unique, lokacija prirodno uklopljena
      description: "…",  // 140–160 znakova, unique
      path: "/usluga",
    }),
    scripts: [breadcrumbLd([...])],
  }),
  component: UslugaPage,
});
```

- Točno jedan `<h1>` po stranici, pa uredna `h2`/`h3` hijerarhija
- `LocalBusiness` schema je globalna (`__root.tsx`) — ne ponavljaj je
- Nova ruta ide i u `src/routes/sitemap[.]xml.tsx`
- `alt` opisuje sadržaj slike u kontekstu, nikad `"slika1"`
- Interno povezuj srodne stranice

Lokaciju (grad) koristi prirodno u titleu, descriptionu, H1 i kontaktu.
**Ne** u svakoj rečenici — keyword stuffing šteti.

## Ton hrvatskog teksta

Topao, stručan, jednostavan. Obraćanje na "vi".

Zabranjeno: "najbolji", "vodeći", "zajamčeni rezultati", "vaše dijete će…",
"revolucionarni pristup", i slične marketinške tvrdnje bez pokrića.

Dijakritika je obavezna (č, ć, š, ž, đ) u svakom vidljivom tekstu.

## Prije nego kažeš da si gotov

```sh
bun run typecheck && bun run lint && bun run build
```

Sva tri moraju proći. `bun run lint` javlja 6 `react-refresh` warninga iz
shadcn komponenti — to je normalno, errora mora biti 0.
