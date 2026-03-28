import json
with open('/root/hermes-workspace/guild-packs/index.json') as f:
    d = json.load(f)
keys = list(d.keys())
print('Number of keys:', len(keys))
print('Sample keys:', keys[:5])
print()
first_key = keys[0]
print('Sample entry for', first_key, ':')
print(json.dumps(d[first_key], indent=2)[:500])
print()
# Show 'packs' structure
if 'packs' in d:
    print('Has packs key')
    print('First pack:', json.dumps(d['packs'][0], indent=2)[:300] if d['packs'] else 'empty')
else:
    print('No packs key - keys are URIs')