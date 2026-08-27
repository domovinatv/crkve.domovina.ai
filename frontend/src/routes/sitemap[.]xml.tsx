import { createFileRoute } from "@tanstack/react-router";

/**
 * Ručni popis ruta. Kad dodaš novu stranicu, dodaj je i ovdje —
 * TanStack ne generira sitemap automatski.
 */
const paths = ["/", "/o-nama", "/kontakt", "/privatnost"];

export const Route = createFileRoute("/sitemap.xml")({
  server: {
    handlers: {
      GET: ({ request }) => {
        const origin = new URL(request.url).origin;
        const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${paths.map((path) => `  <url><loc>${origin}${path}</loc></url>`).join("\n")}
</urlset>`;
        return new Response(body, {
          headers: { "Content-Type": "application/xml; charset=utf-8" },
        });
      },
    },
  },
});
