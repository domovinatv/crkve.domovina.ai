import { defineConfig } from "vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import { nitro } from "nitro/vite";

/**
 * Ovo je ono što @lovable.dev/vite-tanstack-config radi skriveno.
 * Raspisano namjerno — da vidiš i mijenjaš redoslijed pluginova.
 *
 * REDOSLIJED JE BITAN:
 *   tsConfigPaths → tailwindcss → tanstackStart → viteReact → nitro
 *
 * tanstackStart mora doći PRIJE viteReact (generira rute koje React plugin
 * zatim transformira), a nitro POSLJEDNJI (pakira gotov server build).
 *
 * tanstackStart u ovoj verziji NE dodaje @vitejs/plugin-react sam —
 * zato ga dodajemo eksplicitno. Ako nakon upgradea dobiješ grešku o
 * duplim React pluginovima, makni viteReact() odavde.
 */
export default defineConfig({
  plugins: [
    tsConfigPaths({ projects: ["./tsconfig.json"] }),
    tailwindcss(),
    tanstackStart({
      // Preusmjerava server entry na src/server.ts (naš SSR error wrapper).
      server: { entry: "server" },
    }),
    viteReact(),
    nitro({
      // Cloudflare Workers module format. Zamijeni za drugu platformu:
      // "node-server" | "vercel" | "bun" | "deno-deploy" | "aws-lambda"
      preset: "cloudflare-module",
    }),
  ],
  server: {
    port: 5173,
  },
});
