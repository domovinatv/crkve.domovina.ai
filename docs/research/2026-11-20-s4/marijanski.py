import sqlite3, sys, json, glob
sys.path.insert(0,'.')
from src import titular
from src.normalize import strip_type_prefix
c=sqlite3.connect(sys.argv[1])
names=[]
for src,q in [('ch',"select name from churches"),('pa',"select name from parishes"),('hu',"select name from heritage_unmatched")]:
    for (n,) in c.execute(q):
        if n and titular.parse(n)=='Majka Božja': names.append((src,n))
for f in glob.glob('data/raw/wikidata/*.json'):
    try: d=json.load(open(f))
    except Exception: continue
    if isinstance(d,list):
        for r in d:
            n=r.get('itemLabel') if isinstance(r,dict) else None
            if n and titular.parse(n)=='Majka Božja': names.append(('wd',n))
from collections import Counter
print(Counter(s for s,_ in names))
for s,n in sorted(set(names)): print(s,'|',n)
