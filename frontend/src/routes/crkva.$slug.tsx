import { createFileRoute, Link } from "@tanstack/react-router";

import { loadChurch } from "@/lib/data";
import { breadcrumbLd, pageHead, placeOfWorshipLd } from "@/lib/seo";
import { KIND_LABEL, denominationLabel, geomKindLabel, num } from "@/lib/format";
import { Chip, Crumbs, Row, Section } from "@/components/catalog/Bits";
import { MiniMap } from "@/components/catalog/MiniMap";
import type { Church } from "@/lib/catalog";

/** Commons Special:FilePath služi original; bez `width` to zna biti 20 MB. */
function commonsThumb(url: string, width: number) {
  return `${url}?width=${width}`;
}

function description(c: Church): string {
  const bits = [
    KIND_LABEL[c.kind] ?? "Sakralni objekt",
    c.titular ? `titular ${c.titular}` : "",
    c.city ?? c.settlement ?? "",
    c.county ?? "",
    c.year_built ? `iz ${c.year_built}.` : "",
    c.heritage_id ? "zaštićeno kulturno dobro" : "",
  ].filter(Boolean);
  return `${c.name} — ${bits.join(", ")}. Koordinate, izvori i pripadnost župi u katalogu crkve.domovina.ai.`;
}

export const Route = createFileRoute("/crkva/$slug")({
  loader: ({ params }) => loadChurch(params.slug),
  head: ({ loaderData }) => {
    const c = loaderData;
    if (!c) return {};
    const path = `/crkva/${c.slug}`;
    const place = [c.city ?? c.settlement, c.county].filter(Boolean).join(", ");
    return {
      ...pageHead({
        title: `${c.name}${place ? `, ${place}` : ""} — crkve.domovina.ai`,
        description: description(c),
        path,
        type: "article",
        image: c.commons_image ? commonsThumb(c.commons_image, 1200) : undefined,
      }),
      scripts: [
        breadcrumbLd([
          { name: "Naslovnica", path: "/" },
          { name: "Crkve", path: "/crkve" },
          { name: c.name, path },
        ]),
        placeOfWorshipLd({
          name: c.name,
          path,
          lat: c.lat,
          lng: c.lng,
          address: c.address,
          city: c.city ?? c.settlement,
          image: c.commons_image ? commonsThumb(c.commons_image, 1200) : undefined,
          description: c.heritage_desc,
        }),
      ],
    };
  },
  component: CrkvaPage,
});

function CrkvaPage() {
  const c = Route.useLoaderData();
  const osmUrl =
    c.osm_type && c.osm_id ? `https://www.openstreetmap.org/${c.osm_type}/${c.osm_id}` : undefined;

  return (
    <Section>
      <Crumbs
        items={[
          { name: "Naslovnica", path: "/" },
          { name: "Crkve", path: "/crkve" },
          { name: c.name, path: `/crkva/${c.slug}` },
        ]}
      />

      <div className="mt-4 grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0">
          <h1 className="text-3xl md:text-4xl">{c.name}</h1>
          {c.name_official && c.name_official !== c.name && (
            <p className="mt-1 text-sm text-muted-foreground">Službeni naziv: {c.name_official}</p>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <Chip tone="primary">{KIND_LABEL[c.kind] ?? c.kind}</Chip>
            {c.is_parish_church && <Chip>Župna crkva</Chip>}
            {c.heritage_id && (
              <Chip tone="heritage" title={c.heritage_status}>
                Zaštićeno kulturno dobro
              </Chip>
            )}
            {c.unesco && <Chip tone="heritage">UNESCO</Chip>}
            {c.geo_verified && (
              <Chip
                tone="verified"
                title={
                  c.geo_verify_m !== undefined
                    ? `Nezavisni izvor daje točku ${Math.round(c.geo_verify_m)} m od naše`
                    : undefined
                }
              >
                Lokacija potvrđena
              </Chip>
            )}
          </div>

          {c.commons_image && (
            <figure className="mt-6">
              <img
                src={commonsThumb(c.commons_image, 1200)}
                alt={`${c.name}${c.city ? `, ${c.city}` : ""}`}
                loading="lazy"
                className="w-full rounded-2xl border border-border object-cover"
              />
              <figcaption className="mt-2 text-xs text-muted-foreground">
                Fotografija: Wikimedia Commons.
              </figcaption>
            </figure>
          )}

          {c.heritage_desc && (
            <div className="mt-6">
              <h2 className="text-lg">Iz Registra kulturnih dobara</h2>
              <p className="mt-2 text-sm leading-relaxed text-foreground/85">{c.heritage_desc}</p>
            </div>
          )}

          <h2 className="mt-8 text-lg">Podaci</h2>
          <dl className="mt-3">
            <Row label="Vrsta">{KIND_LABEL[c.kind] ?? c.kind}</Row>
            <Row label="Titular">{c.titular}</Row>
            <Row label="Konfesija">{denominationLabel(c.denomination)}</Row>
            <Row label="Adresa">{c.address}</Row>
            <Row label="Naselje">{c.city ?? c.settlement}</Row>
            <Row label="Općina / grad">{c.municipality}</Row>
            <Row label="Županija">{c.county}</Row>
            <Row label="Godina gradnje">{c.year_built}</Row>
            <Row label="Arhitekt">{c.architect}</Row>
            <Row label="Stil">{c.style}</Row>
            <Row label="Zaštita">{c.heritage_status}</Row>
            <Row label="Klasifikacija">{c.heritage_class}</Row>
            <Row label="Oznaka dobra">{c.heritage_id}</Row>
            <Row label="Telefon">
              {c.phone ? <a href={`tel:${c.phone}`}>{c.phone}</a> : undefined}
            </Row>
            <Row label="Web">
              {c.website ? (
                <a href={c.website} target="_blank" rel="noreferrer noopener" className="underline">
                  {c.website.replace(/^https?:\/\//, "")}
                </a>
              ) : undefined}
            </Row>
            <Row label="Koordinate">
              <span className="tabular-nums">
                {c.lat.toFixed(5)}, {c.lng.toFixed(5)}
              </span>
              {geomKindLabel(c.geom_kind) && (
                <span className="text-muted-foreground"> · {geomKindLabel(c.geom_kind)}</span>
              )}
            </Row>
          </dl>

          {c.siblings && c.siblings.length > 0 && (
            <>
              <h2 className="mt-8 text-lg">
                Ostale građevine iste župe ({num(c.siblings.length)})
              </h2>
              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {c.siblings.map((s) => (
                  <li key={s.slug}>
                    <Link
                      to="/crkva/$slug"
                      params={{ slug: s.slug }}
                      className="surface-card block p-3 text-sm hover:shadow-[var(--shadow-lift)]"
                    >
                      <span className="font-semibold">{s.name}</span>
                      <span className="block text-xs text-muted-foreground">
                        {KIND_LABEL[s.kind] ?? s.kind}
                        {s.is_parish_church ? " · župna crkva" : ""}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <aside className="space-y-5">
          <MiniMap lat={c.lat} lng={c.lng} label={c.name} />

          {c.parish && (
            <div className="surface-card p-5">
              <p className="eyebrow">Pravna osoba</p>
              {c.parish.route ? (
                <Link
                  to={c.parish.route === "zupa" ? "/zupa/$slug" : "/ustanova/$slug"}
                  params={{ slug: c.parish.slug }}
                  className="mt-1.5 block font-semibold text-primary"
                >
                  {c.parish.short_name ?? c.parish.name}
                </Link>
              ) : (
                <p className="mt-1.5 font-semibold">{c.parish.short_name ?? c.parish.name}</p>
              )}
              {c.parish.diocese && (
                <p className="mt-1 text-sm text-muted-foreground">{c.parish.diocese}</p>
              )}
            </div>
          )}

          <div className="surface-card p-5">
            <p className="eyebrow">Izvori</p>
            <ul className="mt-2 space-y-1.5 text-sm">
              {osmUrl && (
                <li>
                  <a href={osmUrl} target="_blank" rel="noreferrer noopener" className="underline">
                    OpenStreetMap
                  </a>
                </li>
              )}
              {c.wikidata_id && (
                <li>
                  <a
                    href={`https://www.wikidata.org/wiki/${c.wikidata_id}`}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="underline"
                  >
                    Wikidata {c.wikidata_id}
                  </a>
                </li>
              )}
              {c.wikipedia_url && (
                <li>
                  <a
                    href={c.wikipedia_url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="underline"
                  >
                    Wikipedija
                  </a>
                </li>
              )}
              <li>
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${c.lat},${c.lng}`}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline"
                >
                  Otvori u kartama
                </a>
              </li>
            </ul>
            {c.source && (
              <p className="mt-3 text-xs text-muted-foreground">
                Zapis nastao iz: {c.source.join(", ")}.
              </p>
            )}
          </div>

          <div className="surface-card p-5">
            <p className="eyebrow">Sirovi podatak</p>
            <a href={`/data/crkva/${c.slug}.json`} className="mt-2 block text-sm underline">
              crkva/{c.slug}.json
            </a>
          </div>
        </aside>
      </div>
    </Section>
  );
}
