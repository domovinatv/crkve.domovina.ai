import { createFileRoute, Link } from "@tanstack/react-router";

import { loadDiocese } from "@/lib/data";
import { breadcrumbLd, pageHead } from "@/lib/seo";
import { broj, km2, num, pct } from "@/lib/format";
import { Chip, Crumbs, Gap, Row, Section } from "@/components/catalog/Bits";

export const Route = createFileRoute("/biskupija/$slug")({
  loader: ({ params }) => loadDiocese(params.slug),
  head: ({ loaderData }) => {
    const d = loaderData;
    if (!d) return {};
    const path = `/biskupija/${d.slug}`;
    const n = d.listed_parish_count ?? d.parish_count ?? 0;
    return {
      ...pageHead({
        title: `${d.name} — župe, građevine i teritorij`,
        description: `${d.name}${d.seat ? `, sjedište ${d.seat}` : ""} — ${num(n)} pravnih osoba u katalogu, s popisom župa i deriviranim teritorijem.`,
        path,
      }),
      scripts: [
        breadcrumbLd([
          { name: "Naslovnica", path: "/" },
          { name: "Biskupije", path: "/biskupije" },
          { name: d.name, path },
        ]),
      ],
    };
  },
  component: BiskupijaPage,
});

function BiskupijaPage() {
  const d = Route.useLoaderData();
  const parishes = d.parishes ?? [];
  const gaps = parishes.filter((p) => p.has_parish_church === 0).length;

  return (
    <Section>
      <Crumbs
        items={[
          { name: "Naslovnica", path: "/" },
          { name: "Biskupije", path: "/biskupije" },
          { name: d.name, path: `/biskupija/${d.slug}` },
        ]}
      />

      <h1 className="mt-4 text-3xl md:text-4xl">{d.name}</h1>
      {d.seat && <p className="mt-1 text-sm text-muted-foreground">Sjedište: {d.seat}</p>}

      <div className="mt-4 flex flex-wrap gap-2">
        {d.kind && <Chip tone="primary">{d.kind}</Chip>}
        <Chip>
          {broj(parishes.length, "pravna osoba", "pravne osobe", "pravnih osoba")} u katalogu
        </Chip>
        {gaps > 0 && <Chip tone="gap">{num(gaps)} bez župne crkve</Chip>}
      </div>

      {d.has_area === 1 ? (
        <div className="mt-8 max-w-3xl">
          <h2 className="text-lg">Teritorij je izračunat, ne preslikan</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Granice biskupija nisu javno dostupne kao podatak. Ova je izvedena iz sjedišta župa
            preko granica naselja, pa uz nju uvijek ide i mjera koliko se slaže s neovisnim izvorom.
          </p>
          <dl className="mt-4">
            <Row label="Postupak">{d.method}</Row>
            <Row label="Slaganje s OSM granicom">
              {d.osm_agreement !== undefined ? pct(d.osm_agreement) : undefined}
            </Row>
            <Row label="Površina">{d.area_km2 !== undefined ? km2(d.area_km2) : undefined}</Row>
            <Row label="Naselja">
              {d.settlement_count !== undefined ? num(d.settlement_count) : undefined}
            </Row>
            <Row label="Stanovnika na području">
              {d.population !== undefined ? num(d.population) : undefined}
            </Row>
            <Row label="Župa na području">
              {d.area_parish_count !== undefined ? num(d.area_parish_count) : undefined}
            </Row>
            <Row label="Građevina na području">
              {d.area_church_count !== undefined ? num(d.area_church_count) : undefined}
            </Row>
          </dl>
          {d.osm_agreement === undefined && (
            <div className="mt-4">
              <Gap>
                Za ovu biskupiju OpenStreetMap nema granicu, pa se derivirani teritorij nema o što
                mjeriti. Prikazan je, ali bez potvrde.
              </Gap>
            </div>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            Broj stanovnika je stanovništvo na području, ne broj vjernika — to nije isti podatak i
            katalog ga nema.
          </p>
        </div>
      ) : (
        <div className="mt-8 max-w-3xl">
          <Gap>
            Ova zajednica nema deriviran teritorij. Ili nije teritorijalna (redovnička provincija,
            vjerska zajednica), ili se preklapa s latinskim biskupijama pa bi je particija
            izobličila.
          </Gap>
        </div>
      )}

      <dl className="mt-8 max-w-3xl">
        <Row label="OIB">{d.oib}</Row>
        <Row label="Konfesija">{d.denomination}</Row>
      </dl>

      {parishes.length > 0 && (
        <>
          <h2 className="mt-10 text-lg">Pravne osobe ({num(parishes.length)})</h2>
          <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {parishes
              .slice()
              .sort((a, b) => (a.short_name ?? a.name).localeCompare(b.short_name ?? b.name, "hr"))
              .map((p) => (
                <li key={`${p.route}/${p.slug}`}>
                  <Link
                    to={p.route === "zupa" ? "/zupa/$slug" : "/ustanova/$slug"}
                    params={{ slug: p.slug }}
                    className="surface-card block h-full p-3.5 text-sm hover:shadow-[var(--shadow-lift)]"
                  >
                    <span className="font-semibold">{p.short_name ?? p.name}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {[p.city, broj(p.church_count, "građevina", "građevine", "građevina")]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                    {p.has_parish_church === 0 && (
                      <span className="mt-2 block">
                        <Chip tone="gap">Bez župne crkve</Chip>
                      </span>
                    )}
                  </Link>
                </li>
              ))}
          </ul>
        </>
      )}
    </Section>
  );
}
