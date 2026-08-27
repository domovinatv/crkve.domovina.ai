import { useEffect, useMemo, useRef, useState } from "react";
import type { Map as MlMap, GeoJSONSource, MapLayerMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { ChurchIndexItem, ChurchKind } from "@/lib/catalog";
import { KIND_PLURAL, KIND_LABEL, num } from "@/lib/format";

/**
 * Karta cijelog kataloga. MapLibre GL, isti basemap kao gis.domovina.ai
 * (openfreemap positron) — bez ključa.
 *
 * KLIJENTSKA komponenta, iz dva razloga: MapLibre traži `window`, a indeks od
 * ~1,5 MB ne smije u SSR payload (TanStack serijalizira loader podatke u HTML,
 * pa bi ga posjetitelj dobio dvaput). Zato se `crkve-index.json` dohvaća ovdje.
 */

const STYLE_LIGHT = "https://tiles.openfreemap.org/styles/positron";

/** Hrvatska s otocima: [zapad, jug, istok, sjever]. */
const HR_BOUNDS: [number, number, number, number] = [13.2, 42.3, 19.5, 46.6];

const KIND_ORDER: ChurchKind[] = [
  "crkva",
  "kapela",
  "katedrala",
  "bazilika",
  "svetiste",
  "samostan",
  "pravoslavna-crkva",
  "dzamija",
  "sinagoga",
  "poklonac",
  "ostalo",
];

const CSS_VAR_BY_KIND: Record<ChurchKind, string> = {
  crkva: "--map-crkva",
  kapela: "--map-kapela",
  katedrala: "--map-katedrala",
  bazilika: "--map-bazilika",
  svetiste: "--map-svetiste",
  samostan: "--map-samostan",
  "pravoslavna-crkva": "--map-pravoslavna",
  dzamija: "--map-dzamija",
  sinagoga: "--map-sinagoga",
  poklonac: "--map-poklonac",
  ostalo: "--map-ostalo",
};

/** Boje žive u styles.css; ovdje se samo čitaju. */
function cssColor(name: string): string {
  if (typeof window === "undefined") return "#666666";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#666666";
}

function escapeHtml(s: string): string {
  return s.replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] ?? c,
  );
}

type PointFC = {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    geometry: { type: "Point"; coordinates: [number, number] };
    properties: Record<string, string | boolean>;
  }[];
};

function toFeatureCollection(items: ChurchIndexItem[]): PointFC {
  return {
    type: "FeatureCollection",
    features: items.map((c) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [c.lng, c.lat] },
      properties: {
        slug: c.slug,
        name: c.name,
        kind: c.kind,
        city: c.city ?? "",
        // MapLibreov `case` traži BOOLEAN. Broj 0/1 baca "Expected boolean but
        // found number" i obori CIJELI sloj bez greške vidljive na karti.
        heritage: c.heritage === 1,
        parish_church: c.is_parish_church === 1,
      },
    })),
  };
}

export function CatalogMap({
  className = "h-[70vh] min-h-[420px]",
  /** Vrste koje su na početku ugašene. Poklonaca je 900 i zagušuju prikaz. */
  hiddenByDefault = ["poklonac"] as ChurchKind[],
}: {
  className?: string;
  hiddenByDefault?: ChurchKind[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [items, setItems] = useState<ChurchIndexItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<ChurchKind>>(() => new Set(hiddenByDefault));

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

  const counts = useMemo(() => {
    const m = new Map<ChurchKind, number>();
    for (const c of items ?? []) m.set(c.kind, (m.get(c.kind) ?? 0) + 1);
    return m;
  }, [items]);

  const visible = useMemo(() => (items ?? []).filter((c) => !hidden.has(c.kind)), [items, hidden]);

  useEffect(() => {
    if (!items || !containerRef.current || mapRef.current) return;
    let cancelled = false;

    void (async () => {
      // maplibre-gl v6 nema default export — samo imenovane.
      const maplibregl = await import("maplibre-gl");
      if (cancelled || !containerRef.current) return;

      const map = new maplibregl.Map({
        container: containerRef.current,
        style: STYLE_LIGHT,
        bounds: HR_BOUNDS,
        fitBoundsOptions: { padding: 24 },
        attributionControl: { compact: true },
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
      });
      mapRef.current = map;
      // Izložena za provjeru u pregledniku i e2e; bezopasno u produkciji.
      // Isti obrazac kao `window._gisMap` u karta-hrvatske.
      (window as unknown as { __crkveMap?: MlMap }).__crkveMap = map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }));

      const colorExpr: unknown[] = ["match", ["get", "kind"]];
      for (const kind of KIND_ORDER) colorExpr.push(kind, cssColor(CSS_VAR_BY_KIND[kind]));
      colorExpr.push(cssColor("--map-ostalo"));

      map.on("load", () => {
        map.addSource("crkve", {
          type: "geojson",
          data: toFeatureCollection(items.filter((c) => !hidden.has(c.kind))),
          cluster: true,
          clusterRadius: 46,
          clusterMaxZoom: 11,
        });

        map.addLayer({
          id: "crkve-clusters",
          type: "circle",
          source: "crkve",
          filter: ["has", "point_count"],
          paint: {
            "circle-color": cssColor("--map-cluster"),
            "circle-opacity": 0.85,
            "circle-radius": ["step", ["get", "point_count"], 14, 25, 19, 100, 25, 500, 32],
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
          },
        });

        map.addLayer({
          id: "crkve-cluster-count",
          type: "symbol",
          source: "crkve",
          filter: ["has", "point_count"],
          layout: {
            "text-field": ["get", "point_count_abbreviated"],
            // Bold glyphovi nisu zajamčeni na svim basemapima (cartocdn dark ih
            // nema, vraća 404) — vidi karta-hrvatske/useJlsLayer.
            "text-font": ["Noto Sans Regular"],
            "text-size": 12,
          },
          paint: { "text-color": "#ffffff" },
        });

        map.addLayer({
          id: "crkve-tocke",
          type: "circle",
          source: "crkve",
          filter: ["!", ["has", "point_count"]],
          paint: {
            "circle-color": colorExpr as never,
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              6,
              ["case", ["get", "parish_church"], 4, 3],
              12,
              ["case", ["get", "parish_church"], 8, 5.5],
              16,
              ["case", ["get", "parish_church"], 12, 9],
            ],
            "circle-stroke-width": ["case", ["get", "heritage"], 2, 1],
            "circle-stroke-color": [
              "case",
              ["get", "heritage"],
              cssColor("--map-parish-ring"),
              "#ffffff",
            ],
          },
        });

        map.on("click", "crkve-clusters", (e: MapLayerMouseEvent) => {
          const f = e.features?.[0];
          if (!f) return;
          const src = map.getSource("crkve") as GeoJSONSource;
          void src.getClusterExpansionZoom(f.properties["cluster_id"] as number).then((zoom) =>
            map.easeTo({
              center: (f.geometry as { coordinates: [number, number] }).coordinates,
              zoom,
            }),
          );
        });

        map.on("click", "crkve-tocke", (e: MapLayerMouseEvent) => {
          const f = e.features?.[0];
          if (!f) return;
          const p = f.properties as Record<string, string | undefined>;
          const kind = (p["kind"] as ChurchKind | undefined) ?? "ostalo";
          const meta = [KIND_LABEL[kind] ?? kind, p["city"]].filter(Boolean).join(" · ");
          new maplibregl.Popup({ offset: 12, maxWidth: "260px" })
            .setLngLat((f.geometry as { coordinates: [number, number] }).coordinates)
            .setHTML(
              `<div style="font-size:0.875rem">` +
                `<a href="/crkva/${encodeURIComponent(p["slug"] ?? "")}" style="font-weight:600;text-decoration:underline">${escapeHtml(p["name"] ?? "")}</a>` +
                `<p style="margin-top:0.25rem;font-size:0.75rem;opacity:0.7">${escapeHtml(meta)}</p>` +
                `</div>`,
            )
            .addTo(map);
        });

        for (const layer of ["crkve-clusters", "crkve-tocke"]) {
          map.on("mouseenter", layer, () => (map.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", layer, () => (map.getCanvas().style.cursor = ""));
        }
      });
    })();

    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // `hidden` se namjerno ne prati ovdje: promjena filtra ne smije rušiti i
    // ponovo graditi kartu, nego samo zamijeniti podatke izvora (efekt ispod).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  // Filtar mijenja PODATKE IZVORA, ne `setFilter` na sloju: klasteri se grade
  // iz izvora, pa bi filtar na sloju ostavio klastere koji broje sakrivene
  // objekte — brojka na karti tvrdila bi nešto što se ne vidi.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !items) return;
    const src = map.getSource("crkve") as GeoJSONSource | undefined;
    if (src) src.setData(toFeatureCollection(visible) as never);
  }, [visible, items]);

  function toggle(kind: ChurchKind) {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }

  return (
    <div className="space-y-3">
      <div
        ref={containerRef}
        className={`w-full overflow-hidden rounded-2xl border border-border bg-muted ${className}`}
        role="application"
        aria-label="Karta crkava i sakralnih objekata u Hrvatskoj"
      >
        {!items && (
          <div className="grid h-full place-items-center px-6 text-center text-sm text-muted-foreground">
            {error
              ? `Karta se nije učitala (${error}). Podaci su i dalje dostupni u popisu.`
              : "Učitavam katalog…"}
          </div>
        )}
      </div>

      {items && (
        <>
          <div className="flex flex-wrap gap-2">
            {KIND_ORDER.filter((k) => counts.get(k)).map((k) => {
              const off = hidden.has(k);
              return (
                <button
                  key={k}
                  type="button"
                  onClick={() => toggle(k)}
                  aria-pressed={!off}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
                    off
                      ? "border-border text-muted-foreground opacity-60"
                      : "border-border bg-secondary text-secondary-foreground"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className="size-2.5 rounded-full"
                    style={{ background: `var(${CSS_VAR_BY_KIND[k]})` }}
                  />
                  {KIND_PLURAL[k]}
                  <span className="tabular-nums opacity-70">{num(counts.get(k) ?? 0)}</span>
                </button>
              );
            })}
          </div>
          <p className="text-xs text-muted-foreground">
            Prikazano {num(visible.length)} od {num(items.length)} objekata. Deblji obrub označava
            zaštićeno kulturno dobro, veća točka župnu crkvu. Poklonci su na početku ugašeni jer ih
            je {num(counts.get("poklonac") ?? 0)} i zagušuju prikaz.
          </p>
        </>
      )}
    </div>
  );
}
