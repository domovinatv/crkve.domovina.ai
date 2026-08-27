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
 * `scripts/34_export_static.py`. Nema baze ni bindinga — Worker ih poslužuje
 * kao assete, a loader ih dohvaća fetchom.
 *
 * ZAMKA: na Cloudflare Workeru `fetch("/data/x.json")` baca (relativan URL
 * nema bazu). U pregledniku pak apsolutni URL vodi na produkcijski origin i
 * u devu bi dohvaćao živu stranicu umjesto lokalne. Otud isomorphic origin:
 * prazan string na klijentu, origin zahtjeva na serveru.
 */
const dataOrigin = createIsomorphicFn()
  .client(() => "")
  .server(() => new URL(getRequest().url).origin);

async function loadJson<T>(path: string): Promise<T> {
  const res = await fetch(`${dataOrigin()}${path}`);
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
