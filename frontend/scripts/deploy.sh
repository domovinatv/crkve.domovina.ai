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
# `|| true` je OBAVEZAN: bez pogotka grep vrati 1, a `set -euo pipefail` bi
# skriptu tiho ugasio prije provjere — tako je jedan deploy prošao neprovjeren.
WORKERS_DEV=$(grep -oE 'https://[a-z0-9.-]+workers\.dev' "$FRONTEND_DIR/.deploy.log" | head -1 || true)
rm -f "$FRONTEND_DIR/.deploy.log"

# Provjera POSLIJE deploya, jer se jedna klasa kvarova vidi SAMO na Workeru:
# SSR loader koji fetcha vlastiti origin lokalno radi (dev server poslužuje
# assete), a na Cloudflareu se vrati u sam worker i vrati 404 — pa svaka
# stranica s loaderom postane 404 dok su one bez njega uredne. Dogodilo se.
FAILED=0

smoke() {
  local base="$1" hard="$2" bad=0
  echo "▶ provjera na $base"
  for path in / /crkve /zupe /biskupije /brojke /karta /o-projektu; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$base$path" || true)
    printf "  %-3s %s\n" "${code:-000}" "$path"
    [[ "$code" == "200" ]] || bad=1
  done
  urls=$(curl -s --max-time 60 "$base/sitemap.xml" | grep -c "<url>" || true)
  echo "  sitemap: $urls URL-ova"
  [[ "${urls:-0}" -gt 9000 ]] || bad=1
  if [[ "$bad" -ne 0 && "$hard" == "hard" ]]; then FAILED=1; fi
  return 0
}

[[ -n "$WORKERS_DEV" ]] && smoke "$WORKERS_DEV" hard

# Produkcijska domena je "soft": poslije prvog deploya s novom domenom
# certifikat zna trebati koju minutu, pa neuspjeh ovdje nije razlog za pad.
smoke "https://crkve.domovina.ai" soft

if [[ "$FAILED" -ne 0 ]]; then
  echo "✗ deploy je prošao, ali provjera nije." >&2
  exit 1
fi

echo "✓ gotovo."
