import sqlite3, sys, math
old, new = sys.argv[1], sys.argv[2]
def load(db):
    c = sqlite3.connect(db)
    ch = {r[0]: r for r in c.execute("""select c.slug, p.slug, c.is_parish_church, c.name, c.titular,
       coalesce(c.settlement,c.city,c.municipality), p.name, c.lat,c.lng,p.lat,p.lng, c.heritage_id, c.year_built,
       p.city, p.kind, c.kind, c.commons_image, c.wikidata_id
       from churches c left join parishes p on p.id=c.parish_id""")}
    pa = {r[0]: r for r in c.execute("select slug, kind, name from parishes")}
    hu = c.execute("select count(*) from heritage_unmatched").fetchone()[0]
    return ch, pa, hu
def km(a,b,c_,d):
    if None in (a,b,c_,d): return None
    R=6371; p=math.radians
    x=math.sin(p(c_-a)/2)**2+math.cos(p(a))*math.cos(p(c_))*math.sin(p(d-b)/2)**2
    return round(2*R*math.asin(math.sqrt(x)),2)
oc, op, ohu = load(old); nc, np_, nhu = load(new)
print("churches slugs removed:", sorted(set(oc)-set(nc)))
print("churches slugs added:", sorted(set(nc)-set(oc)))
print("parish slugs removed:", sorted(set(op)-set(np_)))
print("parish slugs added:", sorted(set(np_)-set(op)))
print("parish kind changes:")
for s in sorted(set(op)&set(np_)):
    if op[s][1]!=np_[s][1]: print("  ", s, op[s][1], "->", np_[s][1], "|", op[s][2], "->", np_[s][2])
print("parish name changes:", sum(1 for s in set(op)&set(np_) if op[s][2]!=np_[s][2]))
cats = {"new":[], "lost":[], "moved":[], "flag":[]}
for s in sorted(set(oc)&set(nc)):
    o, n = oc[s], nc[s]
    if o[1]==n[1]:
        if o[1] and o[2]!=n[2]: cats["flag"].append(s)
    elif o[1] is None: cats["new"].append(s)
    elif n[1] is None: cats["lost"].append(s)
    else: cats["moved"].append(s)
for k,v in cats.items():
    print(f"== {k}: {len(v)}")
    for s in v:
        o,n=oc[s],nc[s]
        print(f"  {s} | {n[3]} | tit={n[4]} | {n[5]} | kind {o[15]}->{n[15]}")
        print(f"     old: {o[1]} pc={o[2]} {o[6]} d={km(o[7],o[8],o[9],o[10])}")
        print(f"     new: {n[1]} pc={n[2]} {n[6]} d={km(n[7],n[8],n[9],n[10])}")
print("== heritage changes")
hc=0
for s in sorted(set(oc)&set(nc)):
    if oc[s][11]!=nc[s][11]:
        hc+=1; print(f"  {s} | {nc[s][3]} | {nc[s][5]} | {oc[s][11]} -> {nc[s][11]} | yb {oc[s][12]} -> {nc[s][12]}")
print("heritage changed:", hc, "heritage_unmatched", ohu, "->", nhu)
print("heritage_id count", sum(1 for r in oc.values() if r[11]), "->", sum(1 for r in nc.values() if r[11]))
print("year_built count", sum(1 for r in oc.values() if r[12]), "->", sum(1 for r in nc.values() if r[12]))
yb=[s for s in set(oc)&set(nc) if oc[s][12]!=nc[s][12]]
print("year_built value changes:", len(yb), sorted(yb)[:20])
print("== church kind changes")
for s in sorted(set(oc)&set(nc)):
    if oc[s][15]!=nc[s][15]: print("  ", s, nc[s][3], oc[s][15], "->", nc[s][15])
print("== church name changes:", sum(1 for s in set(oc)&set(nc) if oc[s][3]!=nc[s][3]))
print("== image changes:", [(s, oc[s][16], nc[s][16]) for s in set(oc)&set(nc) if oc[s][16]!=nc[s][16]])
print("== wikidata changes:", [(s, oc[s][17], nc[s][17]) for s in set(oc)&set(nc) if oc[s][17]!=nc[s][17]])
