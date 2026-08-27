import { createFileRoute } from "@tanstack/react-router";

import { CatalogMap } from "@/components/catalog/CatalogMap";
import { PageHeading, Section } from "@/components/catalog/Bits";
import { breadcrumbLd, pageHead } from "@/lib/seo";

export const Route = createFileRoute("/karta")({
  head: () => ({
    ...pageHead({
      title: "Karta crkava i sakralnih objekata u Hrvatskoj",
      description:
        "Interaktivna karta svih crkava, kapela, katedrala, samostana, džamija i sinagoga u Hrvatskoj. Filtriranje po vrsti, oznaka zaštićenih kulturnih dobara i župnih crkava.",
      path: "/karta",
    }),
    scripts: [
      breadcrumbLd([
        { name: "Naslovnica", path: "/" },
        { name: "Karta", path: "/karta" },
      ]),
    ],
  }),
  component: Karta,
});

function Karta() {
  return (
    <Section>
      <PageHeading
        eyebrow="Karta"
        title="Sakralni objekti na karti Hrvatske"
        lead="Svaki objekt u katalogu ima koordinate. Klik na točku otvara njezinu stranicu."
      />
      <div className="mt-6">
        <CatalogMap />
      </div>
    </Section>
  );
}
