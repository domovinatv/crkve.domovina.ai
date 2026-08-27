import { createFileRoute } from "@tanstack/react-router";

import { loadParish } from "@/lib/data";
import { breadcrumbLd, organizationLd, pageHead } from "@/lib/seo";
import { ParishDetail, parishDescription } from "@/components/catalog/ParishDetail";

export const Route = createFileRoute("/zupa/$slug")({
  loader: ({ params }) => loadParish("zupa", params.slug),
  head: ({ loaderData }) => {
    const p = loaderData;
    if (!p) return {};
    const path = `/zupa/${p.slug}`;
    return {
      ...pageHead({
        title: `${p.short_name ?? p.name}${p.city ? `, ${p.city}` : ""} — župa u katalogu`,
        description: parishDescription(p),
        path,
        type: "article",
      }),
      scripts: [
        breadcrumbLd([
          { name: "Naslovnica", path: "/" },
          { name: "Župe", path: "/zupe" },
          { name: p.short_name ?? p.name, path },
        ]),
        organizationLd({
          name: p.name,
          path,
          oib: p.oib,
          address: p.address,
          city: p.city,
          phone: p.phone,
          email: p.email,
          website: p.website,
          parent: p.diocese,
        }),
      ],
    };
  },
  component: ZupaPage,
});

function ZupaPage() {
  return <ParishDetail p={Route.useLoaderData()} />;
}
