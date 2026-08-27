import { createFileRoute, Link } from "@tanstack/react-router";

import { ParishBrowser } from "@/components/catalog/ParishBrowser";
import { Gap, PageHeading, Section } from "@/components/catalog/Bits";
import { loadManifest, loadStats } from "@/lib/data";
import { breadcrumbLd, pageHead } from "@/lib/seo";
import { num } from "@/lib/format";

export const Route = createFileRoute("/zupe")({
  loader: async () => ({ stats: await loadStats(), manifest: await loadManifest() }),
  head: () => ({
    ...pageHead({
      title: "Popis župa, samostana i crkvenih općina u Hrvatskoj",
      description:
        "Pretraživ popis pravnih osoba vjerskih zajednica u Hrvatskoj: katoličke župe, samostani, crkvene općine, parohije i džemati, s OIB-om, sjedištem i biskupijom.",
      path: "/zupe",
    }),
    scripts: [
      breadcrumbLd([
        { name: "Naslovnica", path: "/" },
        { name: "Župe", path: "/zupe" },
      ]),
    ],
  }),
  component: Zupe,
});

function Zupe() {
  const { stats, manifest } = Route.useLoaderData();

  return (
    <Section>
      <PageHeading
        eyebrow="Pravne osobe"
        title="Župe, samostani i crkvene općine"
        lead={
          <>
            {num(manifest.counts.zupe)} aktivnih katoličkih župa i {num(manifest.counts.ustanove)}{" "}
            ostalih mjesnih pravnih osoba. Izvor je državna evidencija, jedini strojno čitljiv popis
            župa u Hrvatskoj.
          </>
        }
      />

      <div className="mt-6 max-w-3xl">
        <Gap>
          {num(stats.zupe_bez_zupne_crkve)} župa nema spojenu župnu crkvu, a{" "}
          {num(stats.zupe_bez_ijedne_crkve)} nema nijednu spojenu građevinu. To nije isto i nijedno
          nije razlika dviju ukupnih brojki —{" "}
          <Link to="/brojke" className="font-semibold underline">
            objašnjeno u brojkama
          </Link>
          .
        </Gap>
      </div>

      <div className="mt-8">
        <ParishBrowser />
      </div>
    </Section>
  );
}
