"""Kategorije node+way parova ≤40 m (prije.db + tagovi): stara definicija audita vs. dedup predikati."""
import sqlite3, sys, pickle
from collections import Counter
sys.path.insert(0, '.')
from src import dedup
from src.audit import _ista_zgrada
T = pickle.load(open(sys.argv[2], 'rb'))
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
Z = []
for r in c.execute("SELECT name,osm_type,osm_id,lat,lng FROM churches WHERE osm_type IS NOT NULL"):
    t = T.get((r['osm_type'], r['osm_id']), {})
    Z.append(dedup.Zapis(r['osm_type'], r['osm_id'], r['lat'], r['lng'], r['name'], dedup.ima_ime(t), dedup.uloga(t), t.get('amenity'), t.get('wikidata')))
merged = {(s.node.key, s.way.key): s for s in dedup.plan(Z)}
C = Counter(); E = {}
for d, n, w in dedup.parovi(Z, 40):
    stari = bool(_ista_zgrada({'name': n.name}, {'name': w.name}))
    nm = dedup.nazivi_spojivi(n, w)
    if (n.key, w.key) in merged: kat = 'SPOJENO ' + merged[(n.key, w.key)].razlog
    elif nm is None: kat = 'nazivi nespojivi (različita glava / različit naziv)'
    elif n.role != w.role: kat = f'različita uloga ({"/".join(sorted({n.role, w.role}))})'
    elif (n.key, w.key) in merged: kat = 'SPOJENO ' + merged[(n.key, w.key)].razlog
    else: kat = 'ista uloga, spojivo, nije spojeno'
    C[('40' if stari else '131', kat)] += 1
    E.setdefault(('40' if stari else '131', kat), []).append(f"{d:.0f} m {n.key} «{n.name}» ~ {w.key} «{w.name}»")
for k in sorted(C): print(k, C[k])
print(sum(v for k, v in C.items() if k[0] == '131'), sum(v for k, v in C.items() if k[0] == '40'))
if len(sys.argv) > 3:
    for k in sorted(E):
        if k[0] == sys.argv[3]:
            print('##', k); print('\n'.join(E[k]))
