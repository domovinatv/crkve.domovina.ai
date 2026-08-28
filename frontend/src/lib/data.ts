import { createIsomorphicFn } from "@tanstack/react-start";
import { getRequest } from "@tanstack/react-start/server";
import { notFound } from "@tanstack/react-router";

import type {
  Church,
  Diocese,
  IndexFile,
  Manifest,
  Parish,
  ChurchIndexItem,
  ParishIndexItem,
  Stats,
} from "./catalog";

/**
 * Podaci su statičke datoteke u `public/data/`, koje piše
 * `scripts/34_export_static.py`. Nema baze ni bindinga u konfiguraciji —
 * Worker ih poslužuje kao assete.
 *
 * ZAMKA KOJA JE KOŠTALA JEDNOG DEPLOYA: na Cloudflareu `fetch` na vlastiti
 * origin NE dolazi do sloja s assetima nego se vrati u sam Worker, koji za
 * `/data/*` nema rutu — pa loader dobije 404 i svaka stranica s loaderom
 * postane 404. Vidjelo se tek u produkciji: lokalno (vite dev) isti kod radi
 * jer ondje asete poslužuje dev server.
 *
 * Ispravan put je `env.ASSETS.fetch()`. Nitroov cloudflare preset zakači
 * `{ env, context }` na `request.runtime.cloudflare`, pa se do bindinga dolazi
 * kroz zahtjev. Ako bindinga nema (vite dev), pada se na obični fetch.
 */
type CloudflareRequest = Request & {
  runtime?: { cloudflare?: { env?: { ASSETS?: { fetch: (req: Request) => Promise<Response> } } } };
};

const fetchData = createIsomorphicFn()
  .client((path: string) => fetch(path))
  .server((path: string) => {
    const req = getRequest() as CloudflareRequest;
    const url = new URL(path, req.url);
    const assets = req.runtime?.cloudflare?.env?.ASSETS;
    return assets ? assets.fetch(new Request(url)) : fetch(url);
  });

async function loadJson<T>(path: string): Promise<T> {
  const res = await fetchData(path);
  if (res.status === 404) throw notFound();
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const loadManifest = () => loadJson<Manifest>("/data/manifest.json");
export const loadStats = () => loadJson<Stats>("/data/stats.json");

export const loadChurchIndex = () => loadJson<IndexFile<ChurchIndexItem>>("/data/crkve-index.json");
export const loadParishIndex = () => loadJson<IndexFile<ParishIndexItem>>("/data/zupe-index.json");
export const loadDioceseIndex = () => loadJson<IndexFile<Diocese>>("/data/biskupije.json");

export const loadChurch = (slug: string) =>
  loadJson<Church>(`/data/crkva/${encodeURIComponent(slug)}.json`);
export const loadParish = (route: "zupa" | "ustanova", slug: string) =>
  loadJson<Parish>(`/data/${route}/${encodeURIComponent(slug)}.json`);
export const loadDiocese = (slug: string) =>
  loadJson<Diocese>(`/data/biskupija/${encodeURIComponent(slug)}.json`);

/** GeoJSON teritorija biskupija — samo karta ga treba, pa se ne tipizira šire. */
export type DioceseAreas = {
  type: "FeatureCollection";
  features: { type: "Feature"; id: number; geometry: unknown; properties: Diocese }[];
};

export const loadDioceseAreas = () => loadJson<DioceseAreas>("/data/biskupije.geojson");
