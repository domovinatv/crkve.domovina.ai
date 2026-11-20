"""Analiza node+way parova nad prije.db + tagovima (S4)."""
import sqlite3, sys, pickle, math
from collections import Counter, defaultdict
sys.path.insert(0, '.')
from src.audit import haversine_m
from src.normalize import norm_key
from src.titular import head_key
DB, PKL = sys.argv[1], sys.argv[2]
MAXM = float(sys.argv[3]) if len(sys.argv) > 3 else 60
T = pickle.load(open(PKL, 'rb'))
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
rows = c.execute("SELECT slug,name,osm_type,osm_id,lat,lng,wikidata_id FROM churches WHERE osm_type IS NOT NULL").fetchall()
def role(t):
    if t.get('amenity') == 'monastery' or t.get('building') == 'monastery': return 'monastery'
    if t.get('historic') == 'wayside_shrine': return 'shrine'
    return 'worship'
def named(t): return bool(t.get('name') or t.get('official_name') or t.get('alt_name'))
R = []
for r in rows:
    t = T.get((r['osm_type'], r['osm_id']), {})
    R.append(dict(slug=r['slug'], name=r['name'], typ=r['osm_type'], id=r['osm_id'], lat=r['lat'], lng=r['lng'],
                  role=role(t), named=named(t), wd=t.get('wikidata'), amen=t.get('amenity'), bld=t.get('building'), hist=t.get('historic')))
def names(a, b):
    if not a['named'] or not b['named']: return 'bez_imena'
    ha, hb = head_key(a['name']), head_key(b['name'])
    if ha and hb and ha != hb: return None
    na = norm_key(a['name'])
    if na and na == norm_key(b['name']): return 'isti_naziv'
    if ha and ha == hb: return 'ista_glava'
    return None
CL, CG = 0.0005, 0.0007
grid = defaultdict(list)
for i, r in enumerate(R): grid[(math.floor(r['lat']/CL), math.floor(r['lng']/CG))].append(i)
pairs = []
for i, a in enumerate(R):
    if a['typ'] != 'node': continue
    ci, cj = math.floor(a['lat']/CL), math.floor(a['lng']/CG)
    for di in (-1,0,1):
        for dj in (-1,0,1):
            for j in grid.get((ci+di, cj+dj), ()):
                b = R[j]
                if b['typ'] == 'node': continue
                d = haversine_m(a['lat'], a['lng'], b['lat'], b['lng'])
                if d <= MAXM: pairs.append((d, a, b))
pickle.dump(pairs, open(sys.argv[4] if len(sys.argv) > 4 else '/dev/null', 'wb')) if len(sys.argv) > 4 else None
def lab(x): return f"{x['typ'][0]}{x['id']} «{x['name']}» [{x['role'][:4]}{'' if x['named'] else ' BEZIME'}{' a='+x['amen'] if x['amen'] else ''}{' b='+x['bld'] if x['bld'] else ''}{' wd='+x['wd'] if x['wd'] else ''}]"
mode = sys.argv[5] if len(sys.argv) > 5 else 'hist'
if mode == 'hist':
    H = Counter(); Hc = Counter()
    for d, a, b in pairs:
        nm = names(a, b); sr = a['role'] == b['role']
        wdc = a['wd'] and b['wd'] and a['wd'] != b['wd']
        cat = 'kompatibilan' if (nm and sr and not wdc) else ('uloga' if nm and not sr else ('wikidata' if nm else 'nazivi'))
        bucket = min(int(d // 5) * 5, 55)
        H[(bucket, cat)] += 1
    cats = ['kompatibilan', 'uloga', 'wikidata', 'nazivi']
    print('m      ' + ' '.join(f'{x:>12}' for x in cats))
    for bk in range(0, 60, 5):
        print(f'{bk:>2}-{bk+5:<3} ' + ' '.join(f'{H[(bk,x)]:>12}' for x in cats))
else:
    for d, a, b in sorted(pairs, key=lambda p: p[0]):
        nm = names(a, b); sr = a['role'] == b['role']
        wdc = a['wd'] and b['wd'] and a['wd'] != b['wd']
        if mode == 'komp' and not (nm and sr and not wdc): continue
        if mode == 'uloga' and not (nm and not sr): continue
        if mode == 'wd' and not (nm and sr and wdc): continue
        print(f"{d:5.1f} {nm or '-':10} {lab(a)} || {lab(b)}")
