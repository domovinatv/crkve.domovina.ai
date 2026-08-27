import { createFileRoute } from "@tanstack/react-router";
import { Mail, MapPin, Phone } from "lucide-react";

import { Breadcrumbs, Section, SectionHeading } from "@/components/site/Bits";
import { LeadDialog } from "@/components/site/LeadDialog";
import { openingHours, site } from "@/data/site";
import { breadcrumbLd, pageHead } from "@/lib/seo";

export const Route = createFileRoute("/kontakt")({
  head: () => ({
    ...pageHead({
      title: `Kontakt | ${site.name} ${site.city}`,
      description: `Kontakt, adresa i radno vrijeme — ${site.fullName}, ${site.street}, ${site.city}.`,
      path: "/kontakt",
    }),
    scripts: [
      breadcrumbLd([
        { name: "Naslovnica", path: "/" },
        { name: "Kontakt", path: "/kontakt" },
      ]),
    ],
  }),
  component: ContactPage,
});

function ContactPage() {
  return (
    <Section>
      <Breadcrumbs
        items={[
          { name: "Naslovnica", to: "/" },
          { name: "Kontakt", to: "/kontakt" },
        ]}
      />
      <div className="mt-6 grid gap-10 md:grid-cols-2">
        <div>
          <SectionHeading as="h1" title="Kontakt" lead="Javite se — odgovaramo u najkraćem roku." />
          <ul className="mt-6 space-y-4 text-sm md:text-base">
            <li className="flex gap-3">
              <MapPin className="mt-1 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <address className="not-italic">
                {site.fullName}
                <br />
                {site.street}
                <br />
                {site.postalCode} {site.city}
              </address>
            </li>
            <li className="flex gap-3">
              <Phone className="mt-1 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <a href={site.phoneHref} className="font-semibold hover:text-primary">
                {site.phone}
              </a>
            </li>
            <li className="flex gap-3">
              <Mail className="mt-1 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <a href={site.emailHref} className="font-semibold break-all hover:text-primary">
                {site.email}
              </a>
            </li>
          </ul>

          {openingHours.length > 0 && (
            <>
              <p className="eyebrow mt-8">Radno vrijeme</p>
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                {openingHours.map((slot) => (
                  <li key={slot.days}>
                    <span className="font-semibold text-foreground">{slot.days}</span> {slot.hours}
                  </li>
                ))}
              </ul>
            </>
          )}

          <div className="mt-8">
            <LeadDialog />
          </div>
        </div>

        {site.mapsEmbedUrl && (
          <div className="overflow-hidden rounded-2xl border border-border">
            <iframe
              src={site.mapsEmbedUrl}
              title={`Lokacija — ${site.fullName}`}
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              className="h-full min-h-80 w-full"
            />
          </div>
        )}
      </div>
    </Section>
  );
}
