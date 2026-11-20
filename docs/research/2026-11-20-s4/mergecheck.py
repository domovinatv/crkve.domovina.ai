"""Za svaki spojeni čvor: veze (župa, baština, wikidata) prije na čvoru i wayu → poslije na preživjelom."""
import sqlite3, sys
old, new = sys.argv[1], sys.argv[2]
o = sqlite3.connect(old); o.row_factory = sqlite3.Row
n = sqlite3.connect(new); n.row_factory = sqlite3.Row
Q = """select c.slug, p.slug ps, c.is_parish_church pc, c.heritage_id h, c.wikidata_id wd, c.commons_image img from churches c left join parishes p on p.id=c.parish_id where c.slug=?"""
from collections import Counter
cnt = Counter()
for m in n.execute("select m.slug ns, c.slug ws from church_merged m join churches c on c.id=m.church_id order by m.slug"):
    on, ow, nw = o.execute(Q, (m['ns'],)).fetchone(), o.execute(Q, (m['ws'],)).fetchone(), n.execute(Q, (m['ws'],)).fetchone()
    for k in ('ps', 'pc', 'h', 'wd', 'img'):
        vals = (on[k], ow[k], nw[k])
        if vals[0] == vals[1] == vals[2]:
            continue
        if vals[2] in (vals[0], vals[1]) and (vals[0] in (None, 0, vals[2]) or vals[1] in (None, 0, vals[2])) and not (vals[0] and vals[1] and vals[0] != vals[1]):
            tag = 'ok'
        else:
            tag = 'PROVJERI'
        cnt[(k, tag)] += 1
        print(f"{tag:8} {k:3} čvor={vals[0]!s:45.45} way={vals[1]!s:45.45} -> {vals[2]!s:45.45} | {m['ns']} -> {m['ws']}")
print(sorted(cnt.items()), file=sys.stderr)
