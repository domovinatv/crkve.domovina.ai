import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Menu, X } from "lucide-react";

import { LeadDialog } from "@/components/site/LeadDialog";
import { nav, site } from "@/data/site";

export function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/90 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between gap-4 md:h-20">
        <Link to="/" className="group flex items-center" aria-label={`${site.name}, naslovnica`}>
          <span className="leading-tight">
            <span className="block text-base font-extrabold tracking-[0.22em] uppercase">
              {site.name}
            </span>
            <span className="hidden text-[0.66rem] tracking-[0.12em] text-muted-foreground sm:block">
              {site.city}
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
              activeOptions={{ exact: item.to === "/" }}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="hidden lg:block">
          <LeadDialog size="sm" label="UPIT" />
        </div>

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
                activeOptions={{ exact: item.to === "/" }}
              >
                {item.label}
              </Link>
            ))}
            <div className="mt-3">
              <LeadDialog className="w-full" />
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
