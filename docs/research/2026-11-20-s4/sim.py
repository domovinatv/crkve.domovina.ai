"""Simulacija src/dedup.plan nad prije.db + OSM tagovima (S4)."""
import sqlite3, sys, pickle
from collections import Counter
sys.path.insert(0, '.')
from src import dedup
DB, PKL = sys.argv[1], sys.argv[2]
T = pickle.load(open(PKL, 'rb'))
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
Z = []
for r in c.execute("SELECT name,osm_type,osm_id,lat,lng FROM churches WHERE osm_type IS NOT NULL"):
    t = T.get((r['osm_type'], r['osm_id']), {})
    Z.append(dedup.Zapis(r['osm_type'], r['osm_id'], r['lat'], r['lng'], r['name'], dedup.ima_ime(t),
                         dedup.uloga(t), t.get('amenity'), t.get('wikidata')))
kw = {}
if len(sys.argv) > 3: kw['prag_m'] = float(sys.argv[3])
if len(sys.argv) > 4: kw['prag_tlocrt_m'] = float(sys.argv[4])
sp = dedup.plan(Z, **kw)
print("spojeno:", len(sp), dict(Counter(s.razlog for s in sp)))
H = Counter(min(int(s.distance_m // 5) * 5, 40) for s in sp); print("histogram:", sorted(H.items()))
for s in sorted(sp, key=lambda s: s.distance_m):
    print(f"  {s.distance_m:5.1f} {s.razlog:18} {s.node.key} «{s.node.name}» -> {s.way.key} «{s.way.name}»")
# preostali kompatibilni (nakon spajanja): čvorovi koji ostaju
merged = {s.node.key for s in sp}
print("preostali parovi ≤40 m sa spojivim nazivom (čvor nije spojen):")
for d, n, w in dedup.parovi(Z, 40):
    if n.key in merged: continue
    nm = dedup.nazivi_spojivi(n, w)
    if nm is None: continue
    zap = dedup.zapreka(n, w)
    print(f"  {d:5.1f} {zap or 'KOMP':8} {n.key} «{n.name}» [{n.role}{'' if n.named else ' bezime'}] ~ {w.key} «{w.name}» [{w.role}{'' if w.named else ' bezime'}{' a='+w.amenity if w.amenity else ''}]")
