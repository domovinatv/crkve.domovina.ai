import { Link } from "@tanstack/react-router";

import type { Parish } from "@/lib/catalog";
import { KIND_LABEL, PARISH_KIND_LABEL, broj, datum, denominationLabel, num } from "@/lib/format";
import { Chip, Crumbs, Gap, Row, Section } from "@/components/catalog/Bits";
import { MiniMap } from "@/components/catalog/MiniMap";

/**
 * Detalj PRAVNE OSOBE — župe, samostana, crkvene općine, parohije, džemata.
 * Isti prikaz za obje rute (/zupa i /ustanova); razlikuje ih samo segment
 * URL-a, koji nosi `p.route`.
 */
export function ParishDetail({ p }: { p: Parish }) {
  const path = `/${p.route}/${p.slug}`;
  const kindLabel = PARISH_KIND_LABEL[p.kind] ?? p.kind;
  const parishChurch = p.churches.find((c) => c.is_parish_church);
  const others = p.churches.filter((c) => !c.is_parish_church);

  return (
    <Section>
      <Crumbs
        items={[
          { name: "Naslovnica", path: "/" },
          { name: "Župe", path: "/zupe" },
          { name: p.short_name ?? p.name, path },
        ]}
      />

      <div className="mt-4 grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0">
          <h1 className="text-3xl md:text-4xl">{p.short_name ?? p.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{p.name}</p>

          <div className="mt-4 flex flex-wrap gap-2">
            <Chip tone="primary">{kindLabel}</Chip>
            {p.diocese && <Chip>{p.diocese}</Chip>}
            {p.community && !p.diocese && <Chip>{p.community}</Chip>}
            {p.church_count === 0 ? (
              <Chip tone="gap">Nema spojene građevine</Chip>
            ) : (
              <Chip>{broj(p.church_count, "građevina", "građevine", "građevina")}</Chip>
            )}
            {p.church_count > 0 && p.has_parish_church === 0 && (
              <Chip tone="gap">Bez župne crkve</Chip>
            )}
          </div>

          {p.church_count === 0 && (
            <div className="mt-6 max-w-2xl">
              <Gap>
                Ova pravna osoba postoji u državnoj evidenciji, ali joj katalog nije spojio nijednu
                građevinu. To je rupa u podacima, ne tvrdnja da građevine nema — matcher traži
                poklapanje titulara i mjesta, pa razilaženje naziva ostavi župu bez para.
              </Gap>
            </div>
          )}

          {p.church_count > 0 && p.has_parish_church === 0 && (
            <div className="mt-6 max-w-2xl">
              <Gap>
                Katalog zna za {broj(p.church_count, "građevinu", "građevine", "građevina")} ove
                pravne osobe, ali nijedna nije prepoznata kao njezina župna crkva.
              </Gap>
            </div>
          )}

          <h2 className="mt-8 text-lg">Podaci iz evidencije</h2>
          <dl className="mt-3">
            <Row label="Vrsta">{kindLabel}</Row>
            <Row label="Titular">{p.titular}</Row>
            <Row label="Biskupija / zajednica">{p.diocese ?? p.community}</Row>
            <Row label="Konfesija">{denominationLabel(p.denomination)}</Row>
            <Row label="OIB">{p.oib}</Row>
            <Row label="Sjedište">{p.address}</Row>
            <Row label="Mjesto">{p.city}</Row>
            <Row label="Županija">{p.county}</Row>
            <Row label="Služba">{p.leader_title}</Row>
            <Row label="Evidencijski broj">{p.registry_no}</Row>
            <Row label="Upisano">{datum(p.registered_at)}</Row>
            <Row label="Status">{p.registry_status}</Row>
            <Row label="Telefon">
              {p.phone ? <a href={`tel:${p.phone}`}>{p.phone}</a> : undefined}
            </Row>
            <Row label="E-mail">
              {p.email ? <a href={`mailto:${p.email}`}>{p.email}</a> : undefined}
            </Row>
            <Row label="Web">
              {p.website ? (
                <a href={p.website} target="_blank" rel="noreferrer noopener" className="underline">
                  {p.website.replace(/^https?:\/\//, "")}
                </a>
              ) : undefined}
            </Row>
            <Row label="Koordinate">
              {p.lat !== undefined && p.lng !== undefined ? (
                <>
                  <span className="tabular-nums">
                    {p.lat.toFixed(5)}, {p.lng.toFixed(5)}
                  </span>
                  {p.geocode_source && (
                    <span className="text-muted-foreground"> · izvor: {p.geocode_source}</span>
                  )}
                </>
              ) : undefined}
            </Row>
          </dl>

          {p.churches.length > 0 && (
            <>
              <h2 className="mt-8 text-lg">Građevine ({num(p.churches.length)})</h2>
              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {[...(parishChurch ? [parishChurch] : []), ...others].map((c) => (
                  <li key={c.slug}>
                    <Link
                      to="/crkva/$slug"
                      params={{ slug: c.slug }}
                      className="surface-card block p-3.5 text-sm hover:shadow-[var(--shadow-lift)]"
                    >
                      <span className="font-semibold">{c.name}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {[KIND_LABEL[c.kind] ?? c.kind, c.city].filter(Boolean).join(" · ")}
                      </span>
                      <span className="mt-2 flex flex-wrap gap-1.5">
                        {c.is_parish_church && <Chip tone="primary">Župna crkva</Chip>}
                        {c.heritage_id && <Chip tone="heritage">Zaštićeno</Chip>}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <aside className="space-y-5">
          {p.lat !== undefined && p.lng !== undefined && (
            <MiniMap lat={p.lat} lng={p.lng} label={p.short_name ?? p.name} zoom={13} />
          )}

          {p.diocese && (
            <div className="surface-card p-5">
              <p className="eyebrow">Biskupija</p>
              <p className="mt-1.5 font-semibold">{p.diocese}</p>
              <Link to="/biskupije" className="mt-2 inline-block text-sm text-primary">
                Sve biskupije →
              </Link>
            </div>
          )}

          <div className="surface-card p-5">
            <p className="eyebrow">Izvori</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Evidencija pravnih osoba vjerskih zajednica, Ministarstvo pravosuđa i uprave, preko
              data.gov.hr.
            </p>
            {p.google_maps_uri && (
              <a
                href={p.google_maps_uri}
                target="_blank"
                rel="noreferrer noopener"
                className="mt-2 block text-sm underline"
              >
                Otvori u kartama
              </a>
            )}
            {p.source && (
              <p className="mt-3 text-xs text-muted-foreground">
                Zapis nastao iz: {p.source.join(", ")}.
              </p>
            )}
          </div>

          <div className="surface-card p-5">
            <p className="eyebrow">Sirovi podatak</p>
            <a href={`/data/${p.route}/${p.slug}.json`} className="mt-2 block text-sm underline">
              {p.route}/{p.slug}.json
            </a>
          </div>
        </aside>
      </div>
    </Section>
  );
}

/** Opis za <meta name="description"> — isti tekst za obje rute. */
export function parishDescription(p: Parish): string {
  const kindLabel = PARISH_KIND_LABEL[p.kind] ?? p.kind;
  const bits = [
    kindLabel,
    p.city ?? "",
    p.diocese ?? p.community ?? "",
    p.church_count > 0
      ? `${broj(p.church_count, "spojena građevina", "spojene građevine", "spojenih građevina")}`
      : "bez spojene građevine u katalogu",
  ].filter(Boolean);
  return `${p.short_name ?? p.name} — ${bits.join(", ")}. OIB, sjedište i popis crkava u katalogu crkve.domovina.ai.`;
}
