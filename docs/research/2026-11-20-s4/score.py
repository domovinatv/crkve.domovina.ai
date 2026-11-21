"""score2.py DB 'naziv' 'mjesto1' ['mjesto2'] — kandidati po bloku, s/bez zaziva."""
import sqlite3, sys
sys.path.insert(0,'.')
from rapidfuzz import fuzz
from src import match, titular
from src.match import build_index, place_key
from src.normalize import norm_key
db,name,*tiers=sys.argv[1:]
c=sqlite3.connect(db); c.row_factory=sqlite3.Row
idx=build_index(c.execute("SELECT id,slug,name,kind,city,settlement,municipality,religion,denomination FROM churches"))
slug={r[0]:r[1] for r in c.execute("select id,slug from churches")}
wz=titular.zaziv(name); print(name,'| tk',titular.key(name),'| z',wz)
for t in tiers:
    pool={}
    for p in place_key(t):
        for cc in idx.get(p,[]): pool[cc.id]=cc
    print('tier',t,len(pool))
    for cc in sorted(pool.values(), key=lambda x:x.id):
        if titular.head_key(name) and cc.hkey and cc.hkey!=titular.head_key(name): continue
        s=fuzz.token_set_ratio(norm_key(name),cc.nkey)
        if cc.tkey and cc.tkey==titular.key(name): s=min(100,s+8)
        sk='SUKOB' if titular.zazivi_u_sukobu(wz,cc.zaziv) else ''
        print(f'   {s:5.1f} {sk:5} z={set(cc.zaziv or [])} {slug[cc.id]}')
match_new=match.best_match(idx,name,*[place_key(t) for t in tiers])
print('NEW ->', match_new and slug[match_new[0].id])
match.zazivi_u_sukobu=lambda a,b: False; match.ZAZIV_BONUS=0
m=match.best_match(idx,name,*[place_key(t) for t in tiers]); print('OLD ->', m and slug[m[0].id])
