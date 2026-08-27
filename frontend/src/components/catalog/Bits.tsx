import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { num } from "@/lib/format";

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
    <section id={id} className={cn("container-page py-10 md:py-14", className)}>
      {children}
    </section>
  );
}

export function PageHeading({
  eyebrow,
  title,
  lead,
  children,
}: {
  eyebrow?: string | undefined;
  title: string;
  lead?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="max-w-3xl">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1 className="mt-2 text-3xl md:text-4xl">{title}</h1>
      {lead && <div className="mt-3 text-base text-muted-foreground">{lead}</div>}
      {children}
    </div>
  );
}

/**
 * Brojka s objašnjenjem. `hint` postoji jer nijedna brojka u ovom katalogu ne
 * stoji sama — "487 župa bez župne crkve" bez objašnjenja izgleda kao greška.
 */
export function Stat({
  value,
  label,
  hint,
  tone = "default",
}: {
  value: number | string;
  label: string;
  hint?: string | undefined;
  tone?: "default" | "gap" | "heritage" | "verified";
}) {
  const toneClass = {
    default: "text-foreground",
    gap: "text-[var(--accent-2)]",
    heritage: "text-[var(--accent-1)]",
    verified: "text-[var(--accent-3)]",
  }[tone];

  return (
    <div className="surface-card p-5">
      <p className={cn("text-3xl font-extrabold tabular-nums", toneClass)}>
        {typeof value === "number" ? num(value) : value}
      </p>
      <p className="mt-1 text-sm font-semibold">{label}</p>
      {hint && <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{hint}</p>}
    </div>
  );
}

/** Redak "naziv → vrijednost". Prazna vrijednost = nema retka. */
export function Row({ label, children }: { label: string; children?: ReactNode }) {
  if (children === undefined || children === null || children === "") return null;
  return (
    <div className="grid grid-cols-[9.5rem_1fr] gap-3 border-b border-border/60 py-2.5 text-sm last:border-0 sm:grid-cols-[12rem_1fr]">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words font-medium">{children}</dd>
    </div>
  );
}

export function Chip({
  children,
  tone = "default",
  title,
}: {
  children: ReactNode;
  tone?: "default" | "gap" | "heritage" | "verified" | "primary";
  title?: string | undefined;
}) {
  const toneClass = {
    default: "border-border bg-secondary text-secondary-foreground",
    primary: "border-transparent bg-primary text-primary-foreground",
    gap: "border-[var(--accent-2)]/35 bg-[var(--accent-2)]/10 text-[var(--accent-2)]",
    heritage: "border-[var(--accent-1)]/35 bg-[var(--accent-1)]/10 text-[var(--accent-1)]",
    verified: "border-[var(--accent-3)]/35 bg-[var(--accent-3)]/10 text-[var(--accent-3)]",
  }[tone];

  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        toneClass,
      )}
    >
      {children}
    </span>
  );
}

export function Crumbs({ items }: { items: { name: string; path: string }[] }) {
  return (
    <nav aria-label="Putanja" className="text-xs text-muted-foreground">
      <ol className="flex flex-wrap items-center gap-1.5">
        {items.map((item, i) => (
          <li key={item.path} className="flex items-center gap-1.5">
            {i > 0 && <span aria-hidden="true">/</span>}
            {i === items.length - 1 ? (
              <span className="font-semibold text-foreground">{item.name}</span>
            ) : (
              <Link to={item.path} className="hover:text-primary">
                {item.name}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/**
 * Nalaz, ne greška. Rupa u podacima ispisuje se kao rupa — ne skriva se i ne
 * zamjenjuje praznim prostorom, jer je i sama podatak (421 župa nema nijednu
 * spojenu građevinu).
 */
export function Gap({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl border border-[var(--accent-2)]/30 bg-[var(--accent-2)]/10 px-4 py-3 text-sm text-foreground/85">
      {children}
    </p>
  );
}
