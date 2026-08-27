import { createFileRoute } from "@tanstack/react-router";

import { MediaPlaceholder, Section, SectionHeading } from "@/components/site/Bits";
import { LeadDialog } from "@/components/site/LeadDialog";
import { site } from "@/data/site";
import { pageHead } from "@/lib/seo";

export const Route = createFileRoute("/")({
  head: () =>
    pageHead({
      title: `${site.name} ${site.city} | TODO kratki opis djelatnosti`,
      description: "TODO 140–160 znakova. Što radite, za koga, u kojem gradu.",
      path: "/",
    }),
  component: HomePage,
});

function HomePage() {
  return (
    <>
      <Section className="pb-0">
        <div className="grid items-center gap-10 md:grid-cols-2">
          <div>
            <p className="eyebrow">{site.city}</p>
            <h1 className="mt-3 text-3xl md:text-5xl">TODO glavni naslov</h1>
            <p className="mt-4 text-base text-muted-foreground md:text-lg">
              TODO podnaslov — jedna rečenica o tome što nudite i kome.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <LeadDialog />
            </div>
          </div>
          <MediaPlaceholder label={`Fotografija — ${site.name}`} />
        </div>
      </Section>

      <Section>
        <SectionHeading
          eyebrow="Usluge"
          title="TODO naslov sekcije"
          lead="TODO kratak uvod u ponudu."
        />
        <p className="mt-6 text-sm text-muted-foreground">
          Zamijeni ovu sekciju karticama usluga (<code>ServiceCard</code> iz Bits.tsx).
        </p>
      </Section>
    </>
  );
}
