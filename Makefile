# crkve.domovina.ai — orkestracija pipelinea. `make help` za popis.
# `make all` radi bez ijednog API ključa; ključ treba samo `make places`.

.PHONY: help init ingest match derive export stats all sync-karta places test clean-cache

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

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

stats: ## izvještaj o pokrivenosti (+ data/exports/stats.json)
	uv run python scripts/40_stats.py

all: init ingest match derive export sync-karta stats ## cijeli pipeline od nule (bez ključeva)

all-places: init ingest match places derive export sync-karta stats ## kao `all` + Places korak

test: ## pytest
	uv run pytest -q

clean-cache: ## obriši keš sirovih odgovora (prisili ponovni dohvat)
	rm -rf data/raw
