# crkve.domovina.ai — orkestracija pipelinea. `make help` za popis.
# `make all` radi bez ijednog API ključa; ključ treba samo `make places`.

.PHONY: help clean-db rebuild init ingest match fix-locations derive export export-web stats audit all sync-karta places test clean-cache

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# Baza se gradi OD NULE. `init` je idempotentan i NE briše postojeću bazu, a
# 10_match_heritage na već spojenoj bazi sve kandidate vidi kao zauzete:
# heritage_unmatched ostane 2038 umjesto 923, year_built padne s 1499 na 659
# (izmjereno 2026-11-20, docs/research/2026-11-20-audit-polazno.md). Zato
# `all` i `all-places` počinju s `clean-db`.
clean-db: ## obriši data/crkve.db (izvedena je; keš data/raw ostaje)
	rm -f data/crkve.db data/crkve.db-wal data/crkve.db-shm

init: ## kreiraj SQLite shemu
	uv run python scripts/00_init_db.py

ingest: ## dohvati sve izvore (OSM, data.gov.hr ×3, Wikidata)
	uv run python scripts/01_ingest_osm.py
	uv run python scripts/02_ingest_parishes_catholic.py
	uv run python scripts/03_ingest_religious_communities.py
	uv run python scripts/04_ingest_heritage.py
	uv run python scripts/05_ingest_wikidata.py

match: ## spoji baštinu i župe na građevine + geokodiraj ostatak župa
	uv run python scripts/10_match_heritage.py
	uv run python scripts/11_match_parishes.py
	uv run python scripts/12_geocode_parishes.py
	$(MAKE) fix-locations

fix-locations: ## premjesti župe koje su sjele na krivi homonim, pa ponovi match
	uv run python scripts/14_fix_parish_locations.py
	uv run python scripts/11_match_parishes.py

places: ## Google Places: precizne koordinate župa + nezavisna provjera (TREBA KLJUČ)
	uv run python scripts/13_places_parishes.py $(ARGS)

derive: ## deriviraj teritorije biskupija iz sjedišta župa (+ mjeri se o OSM)
	uv run python scripts/20_derive_diocese_areas.py $(ARGS)

export: ## FTS + GeoJSON + CSV
	uv run python scripts/30_build_fts.py
	uv run python scripts/31_export_geojson.py
	uv run python scripts/32_export_csv.py

sync-karta: ## preslikaj GeoJSON u ../karta-hrvatske (gis.domovina.ai)
	uv run python scripts/33_sync_karta.py

# Ide POSLIJE `stats`: 34 ne računa brojke sam nego preuzima data/exports/stats.json
# (jedino mjesto gdje se npr. "487 župa bez župne crkve" računa) i odbija raditi
# ako je zastario. Dvije brojke koje se same računaju razišle bi se.
export-web: ## statički JSON za frontend/ (traži prethodni `make stats`)
	uv run python scripts/34_export_static.py

stats: ## izvještaj o pokrivenosti (+ data/exports/stats.json)
	uv run python scripts/40_stats.py

audit: ## metrike grešaka u podacima (+ data/exports/audit.json); ARGS="--db … --out …"
	uv run python scripts/41_audit.py $(ARGS)

all: clean-db init ingest match derive export sync-karta stats export-web ## cijeli pipeline od nule (bez ključeva)

all-places: clean-db init ingest match places fix-locations derive export sync-karta stats export-web ## kao `all` + Places korak

rebuild: ## all-places iz keša: bez mreže i bez ključa (PLACES_OFFLINE=1)
	PLACES_OFFLINE=1 $(MAKE) all-places

test: ## pytest
	uv run pytest -q

clean-cache: ## obriši keš sirovih odgovora (prisili ponovni dohvat)
	rm -rf data/raw
