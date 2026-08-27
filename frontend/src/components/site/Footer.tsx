import { Link } from "@tanstack/react-router";
import { Mail, MapPin, Phone } from "lucide-react";

import { nav, openingHours, site } from "@/data/site";

export function Footer() {
  const socials = [
    { label: "Instagram", href: site.instagram },
    { label: "Facebook", href: site.facebook },
  ].filter((s) => s.href);

  return (
    <footer className="mt-8 border-t border-border bg-cream">
      <div className="container-page grid gap-10 py-12 md:grid-cols-3">
        <div>
          <p className="text-base font-extrabold tracking-[0.22em] uppercase">{site.name}</p>
          {site.slogan && <p className="mt-2 text-sm text-muted-foreground">{site.slogan}</p>}
          {socials.length > 0 && (
            <ul className="mt-4 flex gap-4 text-sm font-semibold">
              {socials.map((s) => (
                <li key={s.label}>
                  <a
                    href={s.href}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="hover:text-primary"
                  >
                    {s.label}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <p className="eyebrow">Kontakt</p>
          <ul className="mt-3 space-y-2.5 text-sm">
            <li className="flex gap-2.5">
              <MapPin className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <address className="not-italic">
                {site.street}
                <br />
                {site.postalCode} {site.city}
              </address>
            </li>
            <li className="flex gap-2.5">
              <Phone className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <a href={site.phoneHref} className="hover:text-primary">
                {site.phone}
              </a>
            </li>
            <li className="flex gap-2.5">
              <Mail className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <a href={site.emailHref} className="break-all hover:text-primary">
                {site.email}
              </a>
            </li>
          </ul>

          {openingHours.length > 0 && (
            <>
              <p className="eyebrow mt-6">Radno vrijeme</p>
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                {openingHours.map((slot) => (
                  <li key={slot.days}>
                    <span className="font-semibold text-foreground">{slot.days}</span> {slot.hours}
                  </li>
                ))}
              </ul>
            </>
          )}
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
            <li>
              <Link to="/privatnost" className="hover:text-primary">
                Privatnost
              </Link>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-border/70">
        <div className="container-page flex flex-wrap items-center justify-between gap-2 py-5 text-xs text-muted-foreground">
          <p>
            © {new Date().getFullYear()} {site.legalName || site.fullName}
            {site.oib && ` · OIB ${site.oib}`}
          </p>
          <p>{site.city}, Hrvatska</p>
        </div>
      </div>
    </footer>
  );
}
