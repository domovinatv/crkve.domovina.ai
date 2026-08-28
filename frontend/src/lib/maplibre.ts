// Vite mora sam zapakirati workera i dati mu URL. Bez `?worker&url` Vite ne
// zna da ta datoteka uopće postoji — vidi komentar u `loadMapLibre`.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";

let workerUrlSet = false;

/**
 * Jedina dopuštena točka učitavanja MapLibrea.
 *
 * **Zašto ne `await import("maplibre-gl")` izravno u komponenti:** MapLibre v6
 * ne ugrađuje workera u glavni bundle nego ga traži kao zaseban modul, na
 * adresi koju izvede iz `import.meta.url` vlastitog chunka:
 *
 *     new URL("./maplibre-gl-worker.mjs", import.meta.url)
 *
 * To je URL sastavljen u runtimeu, pa ga bundler ne vidi kao import i datoteku
 * ne emitira. U produkciji je `/assets/maplibre-gl-worker.mjs` onda 404 (kod
 * nas SPA fallback, dakle HTML), worker se nikad ne javi i karta **tiho** stane:
 * stil se parsira, izvori se stvore, kontrole se iscrtaju — ali nijedna pločica
 * se ne dohvati (to radi worker), `map.on("load")` nikad ne okine, pa se ni naši
 * slojevi ne dodaju. Nema greške ni u konzoli ni na karti; vidi se samo prazan
 * sivi okvir. Izmjereno na živoj stranici: `dispatcher.broadcast` timeouta,
 * `tileManagers.openmaptiles.loaded() === false`, nula `.pbf` zahtjeva.
 *
 * `bun run dev` to NE hvata: ondje Vite servira `node_modules/maplibre-gl/dist/`
 * gdje worker stvarno stoji uz svoj chunk. Kvar postoji samo u buildu.
 *
 * `?worker&url` tjera Vite da workera zapakira zajedno s njegovim
 * `maplibre-gl-shared.mjs` i emitira ga kao hashiran asset, a `setWorkerUrl`
 * MapLibreu kaže gdje je. Mora se pozvati prije prve `new Map(...)`.
 */
export async function loadMapLibre() {
  const maplibregl = await import("maplibre-gl");
  if (!workerUrlSet) {
    maplibregl.setWorkerUrl(workerUrl);
    workerUrlSet = true;
  }
  return maplibregl;
}
