import { createFileRoute, Link } from "@tanstack/react-router";

import { loadManifest, loadStats } from "@/lib/data";
import { breadcrumbLd, pageHead } from "@/lib/seo";
import { KIND_PLURAL, denominationLabel, num } from "@/lib/format";
import { Gap, PageHeading, Section, Stat } from "@/components/catalog/Bits";
import type { ChurchKind } from "@/lib/catalog";

export const Route = createFileRoute("/brojke")({
  loader: async () => ({ stats: await loadStats(), manifest: await loadManifest() }),
  head: () => ({
    ...pageHead({
      title: "Brojke i pokrivenost kataloga crkava u Hrvatskoj",
      description:
        "Koliko objekata katalog ima, koliko ih ima titular, zaštitu i fotografiju, i gdje su rupe: župe bez crkve, nespojena baština, konflikti lokacija.",
      path: "/brojke",
    }),
    scripts: [
      breadcrumbLd([
        { name: "Naslovnica", path: "/" },
        { name: "Brojke", path: "/brojke" },
      ]),
    ],
  }),
  component: Brojke,
});

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  return (
    <li className="grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3 text-sm">
      <span className="truncate" title={label}>
        {label}
      </span>
      <span className="h-2 rounded-full bg-secondary">
        <span
          className="block h-2 rounded-full bg-primary"
          style={{ width: `${Math.max(2, (value / max) * 100)}%` }}
        />
      </span>
      <span className="tabular-nums text-muted-foreground">{num(value)}</span>
    </li>
  );
}

function Distribution({
  title,
  data,
  labelFn,
  limit,
}: {
  title: string;
  data: Record<string, number>;
  labelFn?: (key: string) => string;
  limit?: number;
}) {
  const rows = Object.entries(data)
    .filter(([k]) => k !== "?")
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);
  const max = rows[0]?.[1] ?? 1;
  return (
    <div>
      <h3 className="text-base font-bold">{title}</h3>
      <ul className="mt-3 space-y-1.5">
        {rows.map(([k, v]) => (
          <Bar key={k} label={labelFn ? labelFn(k) : k} value={v} max={max} />
        ))}
      </ul>
    </div>
  );
}

function Brojke() {
  const { stats, manifest } = Route.useLoaderData();

  return (
    <Section>
      <PageHeading
        eyebrow="Pokrivenost"
        title="Brojke"
        lead={
          <>
            Sve je izmjereno nad bazom, ne procijenjeno. Podaci su generirani{" "}
            {new Date(manifest.generated_at).toLocaleDateString("hr-HR", { dateStyle: "long" })}.
          </>
        }
      />

      <h2 className="mt-10 text-lg">Građevine</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat value={stats.crkve_ukupno} label="Ukupno" />
        <Stat
          value={stats.crkve_s_tlocrtom}
          label="S tlocrtom"
          hint="OSM way ili relation — obris građevine, ne samo točka."
        />
        <Stat value={stats.crkve_s_titularom} label="S titularom" />
        <Stat value={stats.crkve_sa_slikom} label="S fotografijom" />
        <Stat value={stats.crkve_sa_zastitom} label="Zaštićenih" tone="heritage" />
        <Stat value={stats.crkve_s_wikipedijom} label="S člankom na Wikipediji" />
        <Stat value={stats.crkve_sa_zupom} label="Spojenih s pravnom osobom" />
        <Stat
          value={stats.crkve_lokacija_potvrdjena}
          label="Lokacija potvrđena nezavisno"
          tone="verified"
          hint="Drugi izvor daje istu točku unutar 300 m."
        />
      </div>

      <h2 className="mt-12 text-lg">Pravne osobe</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat value={stats.pravne_osobe_ukupno} label="Ukupno u evidencijama" />
        <Stat
          value={stats.zupe_aktivne}
          label="Aktivnih katoličkih župa"
          hint={`Zapisa je ${num(stats.zupe_katolicke)}: jedan je ugašen, jedan je duplikat.`}
        />
        <Stat value={stats.zupe_s_oib} label="S OIB-om" />
        <Stat value={stats.zupe_s_telefonom} label="S telefonom" />
      </div>

      <h2 className="mt-12 text-lg">Rupe</h2>
      <div className="mt-4 max-w-3xl">
        <Gap>
          <strong>„Župa bez crkve" su dvije različite brojke</strong>, i nijedna nije razlika
          ukupnih brojki. {num(stats.zupne_crkve)} župnih crkava pripada pravnim osobama koje nisu
          župe (samostani, svetišta), pa oduzimanje daje krivi rezultat.
        </Gap>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat value={stats.zupe_bez_zupne_crkve} label="Župa bez spojene župne crkve" tone="gap" />
        <Stat
          value={stats.zupe_bez_ijedne_crkve}
          label="Župa bez ijedne građevine"
          tone="gap"
          hint="Uža brojka: ni župne crkve ni filijale."
        />
        <Stat
          value={stats.bastina_nespojena}
          label="Zaštićenih bez para"
          tone="gap"
          hint="Izmjereno: za 922 od 923 kandidat je postojao — matcher je gledao pa odbio."
        />
        <Stat
          value={stats.geo_konflikti}
          label="Konflikata lokacije"
          tone="gap"
          hint="Nezavisni izvor daje točku >750 m od naše. Red za pregled, ne popravak."
        />
      </div>

      <div className="mt-12 grid gap-10 md:grid-cols-2">
        <Distribution
          title="Po vrsti objekta"
          data={stats.po_tipu}
          labelFn={(k) => KIND_PLURAL[k as ChurchKind] ?? k}
        />
        <Distribution title="Po županiji" data={stats.po_zupaniji} />
        <Distribution title="Župa po biskupiji" data={stats.zupe_po_biskupiji} />
        <Distribution
          title="Po konfesiji"
          data={stats.po_konfesiji}
          labelFn={(k) => denominationLabel(k) ?? k}
        />
        <Distribution title="Najčešći titulari" data={stats.najcesci_titulari} limit={20} />
        <Distribution
          title="Odakle koordinata župe"
          data={stats.zupe_po_izvoru_koordinata}
          labelFn={(k) =>
            ({
              church: "od vlastite crkve",
              places: "iz vanjskog izvora",
              "naselje-centroid": "težište naselja",
              nominatim: "geokodiranje",
            })[k] ?? k
          }
        />
      </div>

      <p className="mt-12 text-sm text-muted-foreground">
        Sve brojke dolaze iz{" "}
        <a href="/data/stats.json" className="underline">
          stats.json
        </a>
        , koji nastaje u pipelineu — stranica ih ne računa ponovo, da se dvije brojke ne bi razišle.
        Više o postupku:{" "}
        <Link to="/o-projektu" className="underline">
          o projektu
        </Link>
        .
      </p>
    </Section>
  );
}
