import { createFileRoute } from "@tanstack/react-router";

import { ChurchBrowser } from "@/components/catalog/ChurchBrowser";
import { PageHeading, Section } from "@/components/catalog/Bits";
import { loadStats } from "@/lib/data";
import { breadcrumbLd, pageHead } from "@/lib/seo";
import { KIND_PLURAL, num } from "@/lib/format";
import type { ChurchKind } from "@/lib/catalog";

export const Route = createFileRoute("/crkve")({
  loader: async () => ({ stats: await loadStats() }),
  head: () => ({
    ...pageHead({
      title: "Popis crkava, kapela i sakralnih objekata u Hrvatskoj",
      description:
        "Pretraživ popis svih sakralnih objekata u Hrvatskoj po nazivu, titularu, mjestu, vrsti i županiji. Crkve, kapele, katedrale, samostani, džamije i sinagoge.",
      path: "/crkve",
    }),
    scripts: [
      breadcrumbLd([
        { name: "Naslovnica", path: "/" },
        { name: "Crkve", path: "/crkve" },
      ]),
    ],
  }),
  component: Crkve,
});

function Crkve() {
  const { stats } = Route.useLoaderData();
  const kinds = Object.entries(stats.po_tipu) as [ChurchKind, number][];
  const counties = Object.entries(stats.po_zupaniji).filter(([name]) => name !== "?");

  return (
    <Section>
      <PageHeading
        eyebrow="Građevine"
        title="Sakralni objekti u Hrvatskoj"
        lead={`${num(stats.crkve_ukupno)} građevina, sve s koordinatama. Pretraga ne razlikuje dijakritiku.`}
      />

      <div className="mt-8">
        <ChurchBrowser />
      </div>

      {/* Statički popis za pretraživače i za orijentaciju bez JavaScripta. */}
      <div className="mt-14 grid gap-8 border-t border-border pt-8 md:grid-cols-2">
        <div>
          <h2 className="text-lg">Po vrsti</h2>
          <ul className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
            {kinds.map(([kind, n]) => (
              <li key={kind} className="flex justify-between gap-3">
                <span>{KIND_PLURAL[kind] ?? kind}</span>
                <span className="tabular-nums text-muted-foreground">{num(n)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-lg">Po županiji</h2>
          <ul className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
            {counties.map(([name, n]) => (
              <li key={name} className="flex justify-between gap-3">
                <span>{name}</span>
                <span className="tabular-nums text-muted-foreground">{num(n)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  );
}
