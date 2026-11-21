import sys
sys.path.insert(0,'.')
from collections import Counter
from src import titular as T
cnt=Counter(); ex={}
for line in open(sys.argv[1]):
    if ' | ' not in line: continue
    src,n=line.rstrip('\n').split(' | ',1)
    z=T.zaziv(n); cnt[z]+=1; ex.setdefault(z,[]).append(src+':'+n[:50])
for k,v in sorted(cnt.items(), key=lambda x:-x[1]): print(v, k, '|', ' ; '.join(ex[k][:3]))
