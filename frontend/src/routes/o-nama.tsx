import { createFileRoute } from "@tanstack/react-router";

import { Breadcrumbs, MediaPlaceholder, Section, SectionHeading } from "@/components/site/Bits";
import { site } from "@/data/site";
import { breadcrumbLd, pageHead } from "@/lib/seo";

export const Route = createFileRoute("/o-nama")({
  head: () => ({
    ...pageHead({
      title: `O nama | ${site.name} ${site.city}`,
      description: "TODO 140–160 znakova o tvrtki, iskustvu i pristupu.",
      path: "/o-nama",
      type: "article",
    }),
    scripts: [
      breadcrumbLd([
        { name: "Naslovnica", path: "/" },
        { name: "O nama", path: "/o-nama" },
      ]),
    ],
  }),
  component: AboutPage,
});

function AboutPage() {
  return (
    <Section>
      <Breadcrumbs
        items={[
          { name: "Naslovnica", to: "/" },
          { name: "O nama", to: "/o-nama" },
        ]}
      />
      <div className="mt-6 grid gap-10 md:grid-cols-[1.2fr_1fr]">
        <div>
          <SectionHeading as="h1" title={`O ${site.name}`} lead="TODO uvodna rečenica." />
          <div className="mt-6 space-y-4 text-sm text-muted-foreground md:text-base">
            <p>TODO priča. Ne izmišljaj kvalifikacije, godine iskustva ni rezultate.</p>
          </div>
        </div>
        <MediaPlaceholder label={`Fotografija — ${site.name}`} />
      </div>
    </Section>
  );
}
