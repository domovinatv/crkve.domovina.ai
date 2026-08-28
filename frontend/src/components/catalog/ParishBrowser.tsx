import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Search } from "lucide-react";

import type { ParishIndexItem } from "@/lib/catalog";
import { PARISH_KIND_LABEL, broj, foldHr, num } from "@/lib/format";
import { Chip } from "@/components/catalog/Bits";

const PAGE = 60;

/** Pretraga i popis pravnih osoba. Klijentski, iz istog razloga kao ChurchBrowser. */
export function ParishBrowser({ initialDiocese }: { initialDiocese?: string | undefined }) {
  const [items, setItems] = useState<ParishIndexItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [diocese, setDiocese] = useState(initialDiocese ?? "");
  const [onlyGaps, setOnlyGaps] = useState(false);
  const [limit, setLimit] = useState(PAGE);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/data/zupe-index.json", { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d: { items: ParishIndexItem[] }) => setItems(d.items))
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => ctrl.abort();
  }, []);

  const dioceses = useMemo(() => {
    const set = new Set<string>();
    for (const p of items ?? []) if (p.diocese) set.add(p.diocese);
    return [...set].sort((a, b) => a.localeCompare(b, "hr"));
  }, [items]);

  const results = useMemo(() => {
    if (!items) return [];
    const needle = foldHr(q.trim());
    return items.filter((p) => {
      if (diocese && p.diocese !== diocese) return false;
      if (onlyGaps && p.has_parish_church === 1) return false;
      if (!needle) return true;
      return (
        foldHr(p.name).includes(needle) ||
        (p.short_name ? foldHr(p.short_name).includes(needle) : false) ||
        (p.city ? foldHr(p.city).includes(needle) : false)
      );
    });
  }, [items, q, diocese, onlyGaps]);

  useEffect(() => setLimit(PAGE), [q, diocese, onlyGaps]);

  if (error) {
    return (
      <p className="text-sm text-muted-foreground">
        Popis se nije učitao ({error}). Pokušajte osvježiti stranicu.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <label className="relative">
          <span className="sr-only">Pretraga po nazivu ili mjestu</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Naziv ili mjesto — npr. sv. Marka, Vrgorac"
            className="h-11 w-full rounded-full border border-input bg-card pl-9 pr-4 text-sm"
          />
        </label>
        <label>
          <span className="sr-only">Biskupija ili zajednica</span>
          <select
            value={diocese}
            onChange={(e) => setDiocese(e.target.value)}
            className="h-11 w-full rounded-full border border-input bg-card px-4 text-sm sm:w-72"
          >
            <option value="">Sve biskupije i zajednice</option>
            {dioceses.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="flex w-fit items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={onlyGaps}
          onChange={(e) => setOnlyGaps(e.target.checked)}
          className="size-4 rounded border-input"
        />
        Samo one bez spojene župne crkve
      </label>

      <p className="text-sm text-muted-foreground" aria-live="polite">
        {items ? (
          <>
            {broj(results.length, "pravna osoba", "pravne osobe", "pravnih osoba")}
            {results.length !== items.length && <> od ukupno {num(items.length)}</>}
          </>
        ) : (
          "Učitavam katalog…"
        )}
      </p>

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {results.slice(0, limit).map((p) => (
          <li key={`${p.route}/${p.slug}`}>
            <Link
              to={p.route === "zupa" ? "/zupa/$slug" : "/ustanova/$slug"}
              params={{ slug: p.slug }}
              className="surface-card block h-full p-4 transition-shadow hover:shadow-[var(--shadow-lift)]"
            >
              <p className="font-semibold leading-snug">{p.short_name ?? p.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {[PARISH_KIND_LABEL[p.kind] ?? p.kind, p.city, p.diocese ?? p.community]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {p.church_count > 0 ? (
                  <Chip>{broj(p.church_count, "građevina", "građevine", "građevina")}</Chip>
                ) : (
                  <Chip tone="gap">Nema spojene građevine</Chip>
                )}
                {p.church_count > 0 && p.has_parish_church === 0 && (
                  <Chip tone="gap">Bez župne crkve</Chip>
                )}
              </div>
            </Link>
          </li>
        ))}
      </ul>

      {results.length > limit && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={() => setLimit((l) => l + PAGE * 2)}
            className="rounded-full border border-border px-5 py-2.5 text-sm font-semibold"
          >
            Prikaži još ({num(results.length - limit)})
          </button>
        </div>
      )}

      {items && results.length === 0 && (
        <p className="text-sm text-muted-foreground">Nijedna pravna osoba ne odgovara upitu.</p>
      )}
    </div>
  );
}
