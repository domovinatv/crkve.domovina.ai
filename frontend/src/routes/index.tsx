import { createFileRoute, Link } from "@tanstack/react-router";

import { loadManifest, loadStats } from "@/lib/data";
import { pageHead } from "@/lib/seo";
import { num } from "@/lib/format";
import { Gap, PageHeading, Section, Stat } from "@/components/catalog/Bits";
import { site } from "@/data/site";

export const Route = createFileRoute("/")({
  loader: async () => ({
    stats: await loadStats(),
    manifest: await loadManifest(),
  }),
  head: () =>
    pageHead({
      title: "Katalog crkava i sakralnih objekata u Hrvatskoj — crkve.domovina.ai",
      description:
        "Svaka crkva, kapela, katedrala i župa u Hrvatskoj na jednom mjestu: koordinate, titular, zaštita i biskupija. Otvoreni podaci iz OSM-a, državnih evidencija i Wikidate.",
      path: "/",
    }),
  component: Home,
});

function Home() {
  const { stats, manifest } = Route.useLoaderData();

  return (
    <>
      <Section className="pb-4">
        <PageHeading
          eyebrow="Otvoreni podaci"
          title="Svaka crkva, kapela i župa u Hrvatskoj"
          lead={
            <>
              Katalog spaja <strong>građevine</strong> iz OpenStreetMapa i Registra kulturnih dobara
              s <strong>pravnim osobama</strong> iz državnih evidencija. Gradi se reproducibilno iz
              javnih izvora, bez ijednog API ključa.
            </>
          }
        >
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/karta"
              className="inline-flex items-center rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
            >
              Otvori kartu
            </Link>
            <Link
              to="/crkve"
              className="inline-flex items-center rounded-full border border-border px-5 py-2.5 text-sm font-semibold"
            >
              Pretraži {num(stats.crkve_ukupno)} objekata
            </Link>
          </div>
        </PageHeading>
      </Section>

      <Section className="pt-0">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            value={stats.crkve_ukupno}
            label="Građevina"
            hint="Crkve, kapele, katedrale, samostani, poklonci, džamije i sinagoge — sve s koordinatama."
          />
          <Stat
            value={stats.zupe_aktivne}
            label="Aktivnih katoličkih župa"
            hint="Zapisa je 1563; jedan je ugašen, jedan je duplikat u samoj evidenciji."
          />
          <Stat
            value={stats.crkve_sa_zastitom}
            label="Zaštićenih kulturnih dobara"
            tone="heritage"
            hint="Spojeno s Registrom kulturnih dobara Ministarstva kulture i medija."
          />
          <Stat
            value={manifest.counts.biskupije_s_teritorijem}
            label="Deriviranih teritorija biskupija"
            hint="Granice biskupija ne postoje kao javan podatak — izračunate su iz sjedišta župa."
          />
        </div>
      </Section>

      <Section className="pt-0">
        <h2 className="text-2xl">Dvije tablice, ne jedna</h2>
        <p className="mt-3 max-w-3xl text-sm text-muted-foreground">
          Građevina i pravna osoba nisu isti skup. Jedna župa ima župnu crkvu, filijale i kapele;
          mnoga crkva — samostanska, grobljanska, poklonac — nema župu. Zato katalog ima dvije vrste
          stranica, povezane u oba smjera.
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="surface-card p-6">
            <p className="eyebrow">Građevina</p>
            <p className="mt-2 text-3xl font-extrabold tabular-nums">
              {num(manifest.counts.crkve)}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Koordinate, titular, godina gradnje, zaštita, fotografija. Izvor: OpenStreetMap,
              Wikidata, Registar kulturnih dobara.
            </p>
            <Link to="/crkve" className="mt-4 inline-block text-sm font-semibold text-primary">
              Popis građevina →
            </Link>
          </div>
          <div className="surface-card p-6">
            <p className="eyebrow">Pravna osoba</p>
            <p className="mt-2 text-3xl font-extrabold tabular-nums">
              {num(manifest.counts.pravne_osobe_sa_stranicom)}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              OIB, biskupija, sjedište, služba. {num(manifest.counts.zupe)} katoličkih župa i{" "}
              {num(manifest.counts.ustanove)} ostalih mjesnih pravnih osoba — samostani, crkvene
              općine, parohije, džemati.
            </p>
            <Link to="/zupe" className="mt-4 inline-block text-sm font-semibold text-primary">
              Popis pravnih osoba →
            </Link>
          </div>
        </div>
      </Section>

      <Section className="pt-0">
        <h2 className="text-2xl">Što katalogu nedostaje</h2>
        <p className="mt-3 max-w-3xl text-sm text-muted-foreground">
          Rupe se ispisuju, ne skrivaju. Svaka je brojka izmjerena, ne procijenjena.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Stat
            value={stats.zupe_bez_zupne_crkve}
            label="Župa bez spojene župne crkve"
            tone="gap"
            hint="Evidencija ima župu, ali joj matcher nije našao odgovarajuću građevinu u OSM-u."
          />
          <Stat
            value={stats.zupe_bez_ijedne_crkve}
            label="Župa bez ijedne spojene građevine"
            tone="gap"
            hint="Uža brojka od prethodne: nema ni župne crkve ni filijale."
          />
          <Stat
            value={stats.bastina_nespojena}
            label="Zaštićenih objekata bez para"
            tone="gap"
            hint="Zapisi iz Registra kulturnih dobara koje matcher nije spojio ni s jednom građevinom."
          />
        </div>
        <div className="mt-6 max-w-3xl">
          <Gap>
            Lokacija {num(stats.crkve_lokacija_potvrdjena)} objekata nezavisno je provjerena drugim
            izvorom, a {num(stats.geo_konflikti)} slučaja čeka ručni pregled. Sve ostalo stoji na
            jednom izvoru.
          </Gap>
        </div>
        <Link to="/brojke" className="mt-6 inline-block text-sm font-semibold text-primary">
          Sve brojke i pokrivenost →
        </Link>
      </Section>

      <Section className="pt-0">
        <div className="surface-card flex flex-wrap items-center justify-between gap-4 p-6">
          <div>
            <h2 className="text-lg">Podaci su otvoreni</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Cijeli katalog je preuzimljiv kao JSON, a pipeline koji ga gradi je javan.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <a
              href="/data/crkve-index.json"
              className="rounded-full border border-border px-4 py-2 text-sm font-semibold"
            >
              crkve-index.json
            </a>
            <a
              href={site.repo}
              target="_blank"
              rel="noreferrer noopener"
              className="rounded-full border border-border px-4 py-2 text-sm font-semibold"
            >
              Izvorni kod
            </a>
          </div>
        </div>
      </Section>
    </>
  );
}
