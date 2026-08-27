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
wrangler deploy

echo "✓ gotovo. Domena crkve.domovina.ai kači se ručno:"
echo "  Cloudflare dashboard → Workers & Pages → crkve-domovina → Settings → Domains & Routes"
