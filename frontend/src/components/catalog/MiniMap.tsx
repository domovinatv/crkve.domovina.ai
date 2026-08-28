import { useEffect, useRef } from "react";
import type { Map as MlMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { loadMapLibre } from "@/lib/maplibre";

const STYLE_LIGHT = "https://tiles.openfreemap.org/styles/positron";

/**
 * Jedna točka na detaljnoj stranici. Ne dohvaća indeks — koordinate dolaze
 * iz već učitanog zapisa, pa je ovo najjeftinija karta koju stranica može
 * imati (samo pločice basemapa).
 */
export function MiniMap({
  lat,
  lng,
  label,
  zoom = 15,
  className = "h-64",
}: {
  lat: number;
  lng: number;
  label: string;
  zoom?: number;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MlMap | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let cancelled = false;

    void (async () => {
      // Uvijek kroz `loadMapLibre` — inače worker ostane nezapakiran i karta
      // se u buildu tiho ne učita (objašnjeno u `@/lib/maplibre`).
      const maplibregl = await loadMapLibre();
      if (cancelled || !containerRef.current) return;

      const map = new maplibregl.Map({
        container: containerRef.current,
        style: STYLE_LIGHT,
        center: [lng, lat],
        zoom,
        attributionControl: { compact: true },
      });
      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      new maplibregl.Marker({
        color:
          getComputedStyle(document.documentElement).getPropertyValue("--map-crkva").trim() ||
          "#4a5da8",
      })
        .setLngLat([lng, lat])
        .addTo(map);
    })();

    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [lat, lng, zoom]);

  return (
    <div
      ref={containerRef}
      className={`w-full overflow-hidden rounded-2xl border border-border bg-muted ${className}`}
      role="img"
      aria-label={`Karta: ${label}`}
    />
  );
}
