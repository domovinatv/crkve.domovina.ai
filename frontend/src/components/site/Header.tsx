import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Menu, X, Search } from "lucide-react";

import { nav, site } from "@/data/site";

export function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/90 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2.5" aria-label={`${site.name}, naslovnica`}>
          <span aria-hidden="true" className="text-xl leading-none">
            ⛪
          </span>
          <span className="leading-tight">
            <span className="block text-sm font-extrabold tracking-[0.14em] uppercase">
              crkve<span className="text-muted-foreground">.domovina.ai</span>
            </span>
            <span className="hidden text-[0.66rem] tracking-[0.1em] text-muted-foreground sm:block">
              Katalog sakralnih objekata
            </span>
          </span>
        </Link>

        <nav aria-label="Glavna navigacija" className="hidden items-center gap-1 lg:flex">
          {nav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-full px-3 py-2 text-sm font-semibold text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              activeProps={{ className: "bg-accent text-accent-foreground" }}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            to="/crkve"
            className="hidden items-center gap-2 rounded-full border border-border px-3.5 py-2 text-sm font-semibold text-muted-foreground hover:text-foreground sm:inline-flex"
          >
            <Search className="size-4" aria-hidden="true" />
            Pretraži
          </Link>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="grid size-10 place-items-center rounded-full border border-border lg:hidden"
            aria-expanded={open}
            aria-label={open ? "Zatvori navigaciju" : "Otvori navigaciju"}
          >
            {open ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-border bg-background lg:hidden">
          <nav
            aria-label="Mobilna navigacija"
            className="container-page flex max-h-[calc(100svh-4rem)] flex-col overflow-y-auto overscroll-contain py-3"
          >
            {nav.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setOpen(false)}
                className="rounded-lg px-2 py-3 text-base font-semibold text-foreground/85"
                activeProps={{ className: "text-primary" }}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
