#!/usr/bin/env bash
# Deploy crkve.domovina.ai na Cloudflare Worker.
#
# Podaci se REGENERIRAJU prije builda: frontend/public/data/ je gitignoran
# (9400 datoteka), pa u čistom checkoutu ne postoji. Bez ovog koraka bi se
# deployala aplikacija bez kataloga.
#
#   ./scripts/deploy.sh            # export → build → deploy
#   ./scripts/deploy.sh --skip-data  # podaci su već svježi
set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "$FRONTEND_DIR/.." && pwd)"

if [[ "${1:-}" != "--skip-data" ]]; then
  echo "▶ regeneriram public/data/ iz baze"
  # `export-web` traži svjež data/exports/stats.json (scripts/34 to provjerava
  # i odbija raditi ako je zastario), pa `stats` ide prije njega.
  make -C "$REPO_DIR" stats export-web
fi

DATA_FILES=$(find "$FRONTEND_DIR/public/data" -type f | wc -l | tr -d ' ')
if [[ "$DATA_FILES" -lt 1000 ]]; then
  echo "✗ public/data ima samo $DATA_FILES datoteka — očekivano ~9400." >&2
  echo "  Pokreni 'make -C $REPO_DIR stats export-web' i provjeri izlaz." >&2
  exit 1
fi
echo "▶ $DATA_FILES datoteka u public/data"

cd "$FRONTEND_DIR"
echo "▶ provjere"
bun run typecheck
bun run lint

echo "▶ build"
bun run build

echo "▶ deploy"
wrangler deploy | tee "$FRONTEND_DIR/.deploy.log"
DEPLOY_URL=$(grep -oE 'https://[a-z0-9.-]+workers\.dev' "$FRONTEND_DIR/.deploy.log" | head -1)
rm -f "$FRONTEND_DIR/.deploy.log"

# Provjera POSLIJE deploya, jer se jedna klasa kvarova vidi SAMO na Workeru:
# SSR loader koji fetcha vlastiti origin lokalno radi (dev server poslužuje
# assete), a na Cloudflareu se vrati u sam worker i vrati 404 — pa svaka
# stranica s loaderom postane 404 dok su one bez njega uredne. Dogodilo se.
if [[ -n "$DEPLOY_URL" ]]; then
  echo "▶ provjera na $DEPLOY_URL"
  FAILED=0
  for path in / /crkve /zupe /biskupije /brojke /karta /o-projektu; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$DEPLOY_URL$path")
    printf "  %-3s %s\n" "$code" "$path"
    [[ "$code" == "200" ]] || FAILED=1
  done
  urls=$(curl -s "$DEPLOY_URL/sitemap.xml" | grep -c "<url>" || true)
  echo "  sitemap: $urls URL-ova"
  [[ "$urls" -gt 9000 ]] || FAILED=1
  if [[ "$FAILED" -ne 0 ]]; then
    echo "✗ deploy je prošao, ali provjera nije. Ne kači domenu dok se ovo ne riješi." >&2
    exit 1
  fi
fi

echo "✓ gotovo. Domena crkve.domovina.ai kači se ručno:"
echo "  Cloudflare dashboard → Workers & Pages → crkve-domovina → Settings → Domains & Routes"
