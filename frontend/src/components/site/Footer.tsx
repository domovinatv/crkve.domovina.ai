import { Link } from "@tanstack/react-router";

import { nav, site } from "@/data/site";

export function Footer() {
  return (
    <footer className="mt-8 border-t border-border bg-cream">
      <div className="container-page grid gap-10 py-12 md:grid-cols-3">
        <div>
          <p className="text-sm font-extrabold tracking-[0.14em] uppercase">{site.name}</p>
          <p className="mt-2 text-sm text-muted-foreground">{site.slogan}</p>
          <p className="mt-4 text-xs text-muted-foreground">
            Katalog se gradi potpuno reproducibilno iz javnih izvora, bez ijednog API ključa.
          </p>
        </div>

        <div>
          <p className="eyebrow">Stranice</p>
          <ul className="mt-3 space-y-2 text-sm">
            {nav.map((item) => (
              <li key={item.to}>
                <Link to={item.to} className="hover:text-primary">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="eyebrow">Podaci</p>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <a
                href={site.repo}
                target="_blank"
                rel="noreferrer noopener"
                className="hover:text-primary"
              >
                Izvorni kod i pipeline
              </a>
            </li>
            <li>
              <a
                href={site.karta}
                target="_blank"
                rel="noreferrer noopener"
                className="hover:text-primary"
              >
                Slojevi na gis.domovina.ai
              </a>
            </li>
            <li>
              <a href="/data/crkve-index.json" className="hover:text-primary">
                crkve-index.json
              </a>
            </li>
            <li>
              <a href="/data/zupe-index.json" className="hover:text-primary">
                zupe-index.json
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-border/70">
        <div className="container-page flex flex-wrap items-center justify-between gap-2 py-5 text-xs text-muted-foreground">
          <p>
            © {new Date().getFullYear()} DOMOVINA.ai · Podaci: {site.licence}
          </p>
          <p>Podaci iz OpenStreetMapa su ODbL — izvedena baza nasljeđuje share-alike.</p>
        </div>
      </div>
    </footer>
  );
}
