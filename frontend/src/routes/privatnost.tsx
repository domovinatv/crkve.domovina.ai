import { createFileRoute } from "@tanstack/react-router";

import { Breadcrumbs, Section, SectionHeading } from "@/components/site/Bits";
import { leadFields } from "@/data/lead-form";
import { site } from "@/data/site";
import { pageHead } from "@/lib/seo";

export const Route = createFileRoute("/privatnost")({
  head: () =>
    pageHead({
      title: `Privatnost | ${site.name}`,
      description: `Kako ${site.fullName} obrađuje osobne podatke poslane putem obrasca na web stranici.`,
      path: "/privatnost",
    }),
  component: PrivacyPage,
});

function PrivacyPage() {
  return (
    <Section>
      <Breadcrumbs
        items={[
          { name: "Naslovnica", to: "/" },
          { name: "Privatnost", to: "/privatnost" },
        ]}
      />
      <div className="mt-6 max-w-2xl">
        <SectionHeading as="h1" title="Izjava o privatnosti" />
        <div className="mt-6 space-y-5 text-sm text-muted-foreground md:text-base">
          <p>
            Voditelj obrade je {site.legalName || site.fullName}, {site.street}, {site.postalCode}{" "}
            {site.city}
            {site.oib && `, OIB ${site.oib}`}.
          </p>

          <div>
            <h2 className="text-base font-bold text-foreground">Koje podatke prikupljamo</h2>
            <p className="mt-2">
              Putem obrasca na ovoj stranici prikupljamo isključivo podatke koje sami unesete:{" "}
              {leadFields.map((f) => f.label.toLowerCase()).join(", ")}.
            </p>
          </div>

          <div>
            <h2 className="text-base font-bold text-foreground">Svrha i pravna osnova</h2>
            <p className="mt-2">
              Podatke koristimo isključivo za odgovor na vaš upit. Pravna osnova je vaš privola dana
              slanjem obrasca.
            </p>
          </div>

          <div>
            <h2 className="text-base font-bold text-foreground">Kome se podaci prosljeđuju</h2>
            <p className="mt-2">
              Sadržaj obrasca dostavlja se na našu e-mail adresu putem servisa Resend (Resend,
              Inc.). Web stranica se poslužuje putem Cloudflare mreže. Podatke ne prodajemo niti
              prosljeđujemo trećima u marketinške svrhe.
            </p>
          </div>

          <div>
            <h2 className="text-base font-bold text-foreground">Koliko dugo ih čuvamo</h2>
            <p className="mt-2">TODO — npr. do rješavanja upita i najviše 12 mjeseci nakon toga.</p>
          </div>

          <div>
            <h2 className="text-base font-bold text-foreground">Vaša prava</h2>
            <p className="mt-2">
              Imate pravo na pristup, ispravak, brisanje i ograničenje obrade svojih podataka te
              pravo na prigovor. Zahtjev pošaljite na{" "}
              <a href={site.emailHref} className="font-semibold text-foreground hover:text-primary">
                {site.email}
              </a>
              . Pritužbu možete podnijeti Agenciji za zaštitu osobnih podataka (AZOP).
            </p>
          </div>

          <div>
            <h2 className="text-base font-bold text-foreground">Kolačići</h2>
            <p className="mt-2">
              Stranica ne koristi kolačiće za praćenje ni analitiku. Cloudflare postavlja tehnički
              kolačić nužan za sigurnost prometa.
            </p>
          </div>
        </div>
      </div>
    </Section>
  );
}
