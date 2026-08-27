import { Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Privremeni vizualni placeholder umjesto fotografije.
 * NIKAD ne generiraj lažne fotografije prostora, ljudi ili proizvoda —
 * koristi ovo dok klijent ne dostavi prave slike.
 */
export function MediaPlaceholder({
  label,
  text,
  className,
  ratio = "aspect-[4/3]",
}: {
  label: string;
  text?: string | undefined;
  className?: string | undefined;
  ratio?: string | undefined;
}) {
  return (
    <div
      role="img"
      aria-label={label}
      className={cn(
        "relative overflow-hidden rounded-2xl border border-border bg-cream",
        ratio,
        className,
      )}
    >
      <div className="organic-blob absolute -right-8 -top-10 size-40 bg-accent opacity-70" />
      <div className="organic-blob absolute -bottom-12 -left-10 size-44 bg-sand opacity-80" />
      <div className="absolute inset-0 grid place-items-center p-6 text-center">
        <span className="eyebrow text-muted-foreground/80">{text ?? "Fotografija uskoro"}</span>
      </div>
    </div>
  );
}

export function Section({
  children,
  className,
  id,
}: {
  children: ReactNode;
  className?: string | undefined;
  id?: string | undefined;
}) {
  return (
    <section id={id} className={cn("container-page py-14 md:py-20", className)}>
      {children}
    </section>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  lead,
  as: As = "h2",
}: {
  eyebrow?: string;
  title: string;
  lead?: string;
  as?: "h1" | "h2";
}) {
  return (
    <div className="max-w-2xl">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <As className="mt-3 text-2xl md:text-4xl">{title}</As>
      {lead && <p className="mt-4 text-base text-muted-foreground md:text-lg">{lead}</p>}
    </div>
  );
}

export function Breadcrumbs({ items }: { items: { name: string; to: string }[] }) {
  return (
    <nav aria-label="Staza navigacije" className="text-xs text-muted-foreground">
      <ol className="flex flex-wrap items-center gap-1">
        {items.map((item, i) => (
          <li key={item.to} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="size-3" aria-hidden="true" />}
            {i === items.length - 1 ? (
              <span aria-current="page" className="text-foreground/70">
                {item.name}
              </span>
            ) : (
              <Link to={item.to} className="hover:text-primary">
                {item.name}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** Kartica usluge/programa. Link `to` mora biti postojeća ruta. */
export function ServiceCard({
  to,
  eyebrow,
  title,
  tagline,
  summary,
  media,
  cta = "Saznajte više",
}: {
  to: string;
  eyebrow?: string;
  title: string;
  tagline?: string;
  summary: string;
  media?: ReactNode;
  cta?: string;
}) {
  return (
    <Link
      to={to}
      className="surface-card group flex flex-col overflow-hidden p-5 transition-shadow hover:shadow-lift focus-visible:shadow-lift"
    >
      {media ?? <MediaPlaceholder label={title} ratio="aspect-[16/10]" />}
      <div className="mt-5 flex flex-1 flex-col">
        {eyebrow && (
          <span className="inline-flex w-fit items-center gap-2 rounded-full bg-accent px-3 py-1 text-[0.7rem] font-bold tracking-wide text-accent-foreground">
            <span className="size-1.5 rounded-full bg-primary" />
            {eyebrow}
          </span>
        )}
        <h3 className="mt-3 text-lg font-bold">{title}</h3>
        {tagline && <p className="mt-1 text-sm font-semibold text-muted-foreground">{tagline}</p>}
        <p className="mt-3 flex-1 text-sm text-muted-foreground">{summary}</p>
        <span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-primary">
          {cta}
          <ChevronRight className="size-4 transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}

export function FactList({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="grid gap-4 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="rounded-xl border border-border bg-card p-4">
          <dt className="eyebrow">{item.label}</dt>
          <dd className="mt-1.5 text-sm font-semibold">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2.5">
      {items.map((item) => (
        <li key={item} className="flex gap-3 text-sm text-muted-foreground md:text-base">
          <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden="true" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
