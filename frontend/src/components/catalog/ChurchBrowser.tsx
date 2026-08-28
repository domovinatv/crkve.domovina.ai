import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Search } from "lucide-react";

import type { ChurchIndexItem, ChurchKind } from "@/lib/catalog";
import { KIND_LABEL, KIND_PLURAL, broj, foldHr, num } from "@/lib/format";
import { Chip } from "@/components/catalog/Bits";

const PAGE = 60;

/**
 * Pretraga i popis građevina. Indeks (~1,5 MB, 282 KB gzip) dohvaća se na
 * KLIJENTU, ne u loaderu rute: TanStack serijalizira loader podatke u HTML,
 * pa bi ga posjetitelj dobio dvaput. SEO ne trpi jer detaljne stranice imaju
 * vlastiti SSR i sve su u sitemapu.
 */
export function ChurchBrowser({
  initialKind,
  initialCounty,
}: {
  initialKind?: ChurchKind | undefined;
  initialCounty?: string | undefined;
}) {
  const [items, setItems] = useState<ChurchIndexItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<ChurchKind | "">(initialKind ?? "");
  const [county, setCounty] = useState(initialCounty ?? "");
  const [limit, setLimit] = useState(PAGE);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/data/crkve-index.json", { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d: { items: ChurchIndexItem[] }) => setItems(d.items))
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => ctrl.abort();
  }, []);

  const counties = useMemo(() => {
    const set = new Set<string>();
    for (const c of items ?? []) if (c.county) set.add(c.county);
    return [...set].sort((a, b) => a.localeCompare(b, "hr"));
  }, [items]);

  const kinds = useMemo(() => {
    const m = new Map<ChurchKind, number>();
    for (const c of items ?? []) m.set(c.kind, (m.get(c.kind) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [items]);

  const results = useMemo(() => {
    if (!items) return [];
    const needle = foldHr(q.trim());
    return items.filter((c) => {
      if (kind && c.kind !== kind) return false;
      if (county && c.county !== county) return false;
      if (!needle) return true;
      return (
        foldHr(c.name).includes(needle) ||
        (c.titular ? foldHr(c.titular).includes(needle) : false) ||
        (c.city ? foldHr(c.city).includes(needle) : false)
      );
    });
  }, [items, q, kind, county]);

  useEffect(() => setLimit(PAGE), [q, kind, county]);

  if (error) {
    return (
      <p className="text-sm text-muted-foreground">
        Popis se nije učitao ({error}). Pokušajte osvježiti stranicu.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <label className="relative">
          <span className="sr-only">Pretraga po nazivu, titularu ili mjestu</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Naziv, titular ili mjesto — npr. sv. Nikola, Šibenik"
            className="h-11 w-full rounded-full border border-input bg-card pl-9 pr-4 text-sm"
          />
        </label>
        <label>
          <span className="sr-only">Vrsta objekta</span>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as ChurchKind | "")}
            className="h-11 w-full rounded-full border border-input bg-card px-4 text-sm sm:w-52"
          >
            <option value="">Sve vrste</option>
            {kinds.map(([k, n]) => (
              <option key={k} value={k}>
                {KIND_PLURAL[k]} ({num(n)})
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="sr-only">Županija</span>
          <select
            value={county}
            onChange={(e) => setCounty(e.target.value)}
            className="h-11 w-full rounded-full border border-input bg-card px-4 text-sm sm:w-60"
          >
            <option value="">Sve županije</option>
            {counties.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="text-sm text-muted-foreground" aria-live="polite">
        {items ? (
          <>
            {broj(results.length, "objekt", "objekta", "objekata")}
            {results.length !== items.length && <> od ukupno {num(items.length)}</>}
          </>
        ) : (
          "Učitavam katalog…"
        )}
      </p>

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {results.slice(0, limit).map((c) => (
          <li key={c.slug}>
            <Link
              to="/crkva/$slug"
              params={{ slug: c.slug }}
              className="surface-card block h-full p-4 transition-shadow hover:shadow-[var(--shadow-lift)]"
            >
              <p className="font-semibold leading-snug">{c.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {[KIND_LABEL[c.kind], c.city, c.county].filter(Boolean).join(" · ")}
              </p>
              {(c.heritage || c.is_parish_church || c.image) && (
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {c.is_parish_church && <Chip tone="primary">Župna crkva</Chip>}
                  {c.heritage && <Chip tone="heritage">Zaštićeno</Chip>}
                  {c.image && <Chip>Fotografija</Chip>}
                </div>
              )}
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
        <p className="text-sm text-muted-foreground">
          Nijedan objekt ne odgovara upitu. Pretraga ne razlikuje dijakritiku, pa „Sibenik" i
          „Šibenik" daju isto.
        </p>
      )}
    </div>
  );
}
