import { createFileRoute } from "@tanstack/react-router";

import { loadChurchIndex, loadDioceseIndex, loadParishIndex } from "@/lib/data";

/**
 * Sitemap se GENERIRA iz indeksa, ne održava ručno. Katalog ima ~9400
 * stranica; ručni popis bi zastario prvim rebuildom podataka.
 *
 * Statične rute su niže popisane i JESU ručne — njih je desetak i mijenjaju
 * se samo kad se doda ruta. Ako dodaješ rutu, dodaj je ovdje.
 */
const STATIC_PATHS = ["/", "/karta", "/crkve", "/zupe", "/biskupije", "/brojke", "/o-projektu"];

function xmlEscape(s: string) {
  return s.replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[c] ?? c,
  );
}

export const Route = createFileRoute("/sitemap.xml")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const origin = new URL(request.url).origin;

        // Isti loaderi kao rute — dijele ispravak s ASSETS bindingom.
        // Vlastiti `fetch(origin + path)` ovdje bi na Workeru vratio 404.
        const [churches, parishes, dioceses] = await Promise.all([
          loadChurchIndex(),
          loadParishIndex(),
          loadDioceseIndex(),
        ]);

        const urls: { loc: string; priority: string }[] = [
          ...STATIC_PATHS.map((p) => ({ loc: `${origin}${p}`, priority: "0.9" })),
          ...churches.items.map((c) => ({
            loc: `${origin}/crkva/${encodeURIComponent(c.slug)}`,
            priority: "0.7",
          })),
          ...parishes.items.map((p) => ({
            loc: `${origin}/${p.route}/${encodeURIComponent(p.slug)}`,
            priority: "0.7",
          })),
          ...dioceses.items.map((d) => ({
            loc: `${origin}/biskupija/${encodeURIComponent(d.slug)}`,
            priority: "0.6",
          })),
        ];

        const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `  <url><loc>${xmlEscape(u.loc)}</loc><priority>${u.priority}</priority></url>`).join("\n")}
</urlset>`;

        return new Response(body, {
          headers: {
            "Content-Type": "application/xml; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
          },
        });
      },
    },
  },
});
