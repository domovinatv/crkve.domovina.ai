import { createFileRoute, Link } from "@tanstack/react-router";

import { loadDioceseIndex } from "@/lib/data";
import { breadcrumbLd, pageHead } from "@/lib/seo";
import { broj, km2, num, pct } from "@/lib/format";
import { Chip, PageHeading, Section } from "@/components/catalog/Bits";

export const Route = createFileRoute("/biskupije")({
  loader: async () => ({ index: await loadDioceseIndex() }),
  head: () => ({
    ...pageHead({
      title: "Biskupije, nadbiskupije i vjerske zajednice u Hrvatskoj",
      description:
        "Popis (nad)biskupija, eparhija i vjerskih zajednica u Hrvatskoj s brojem župa. Teritoriji biskupija su derivirani iz sjedišta župa jer ne postoje kao javan podatak.",
      path: "/biskupije",
    }),
    scripts: [
      breadcrumbLd([
        { name: "Naslovnica", path: "/" },
        { name: "Biskupije", path: "/biskupije" },
      ]),
    ],
  }),
  component: Biskupije,
});

function Biskupije() {
  const { index } = Route.useLoaderData();
  const withArea = index.items.filter((d) => d.has_area === 1);
  const rest = index.items
    .filter((d) => d.has_area !== 1)
    .sort((a, b) => (b.parish_count ?? 0) - (a.parish_count ?? 0));

  return (
    <Section>
      <PageHeading
        eyebrow="Teritorij"
        title="Biskupije i vjerske zajednice"
        lead={
          <>
            Granice biskupija ne postoje kao javan podatak — OpenStreetMap ima 3 od 15, Wikidata
            nijednu. Katalog ih zato <strong>derivira</strong> iz sjedišta župa preko granica
            naselja, a te tri OSM relacije služe kao mjera točnosti.
          </>
        }
      />

      <h2 className="mt-10 text-lg">S deriviranim teritorijem ({num(withArea.length)})</h2>
      <ul className="mt-4 grid gap-3 md:grid-cols-2">
        {withArea
          .sort((a, b) => (b.area_parish_count ?? 0) - (a.area_parish_count ?? 0))
          .map((d) => (
            <li key={d.slug}>
              <Link
                to="/biskupija/$slug"
                params={{ slug: d.slug }}
                className="surface-card block h-full p-5 hover:shadow-[var(--shadow-lift)]"
              >
                <p className="font-semibold">{d.name}</p>
                {d.seat && (
                  <p className="mt-0.5 text-xs text-muted-foreground">Sjedište: {d.seat}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Chip>{broj(d.area_parish_count ?? 0, "župa", "župe", "župa")}</Chip>
                  <Chip>
                    {broj(d.area_church_count ?? 0, "građevina", "građevine", "građevina")}
                  </Chip>
                  {d.area_km2 !== undefined && <Chip>{km2(d.area_km2)}</Chip>}
                  {d.osm_agreement !== undefined && (
                    <Chip tone="verified" title="Slaganje derivirane granice s OSM relacijom">
                      {pct(d.osm_agreement)} slaganja s OSM-om
                    </Chip>
                  )}
                </div>
              </Link>
            </li>
          ))}
      </ul>

      <h2 className="mt-12 text-lg">Ostale zajednice i tijela ({num(rest.length)})</h2>
      <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
        Bez teritorija — ili zato što nisu teritorijalne (vjerske zajednice, redovničke provincije),
        ili zato što se preklapaju s latinskim biskupijama. Križevačka eparhija je namjerno izvan
        particije: grkokatolička je, teritorij joj se preklapa sa svima, a župe su joj razasute po
        cijeloj zemlji.
      </p>
      <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {rest.map((d) => (
          <li key={d.slug}>
            <Link
              to="/biskupija/$slug"
              params={{ slug: d.slug }}
              className="surface-card block h-full p-3.5 text-sm hover:shadow-[var(--shadow-lift)]"
            >
              <span className="font-semibold">{d.name}</span>
              {(d.parish_count ?? 0) > 0 && (
                <span className="mt-0.5 block text-xs text-muted-foreground">
                  {broj(d.parish_count ?? 0, "pravna osoba", "pravne osobe", "pravnih osoba")}
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </Section>
  );
}
