import json, glob, pickle, sys
els = {}
for f in glob.glob('data/raw/osm/*.json'):
    d = json.load(open(f))
    for e in d.get('elements', []):
        els[(e['type'], e['id'])] = e.get('tags') or {}
pickle.dump(els, open(sys.argv[1],'wb'))
print(len(els))
