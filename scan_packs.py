#!/usr/bin/env python3
import yaml
from pathlib import Path
from borg.core.safety import scan_pack_safety
from borg.core.schema import validate_pack

packs_dir = Path('/root/hermes-workspace/guild-packs/packs')
results = []

for pack_file in sorted(packs_dir.glob('*.yaml')):
    try:
        pack = yaml.safe_load(pack_file.read_text())
        safety_threats = scan_pack_safety(pack)
        validation_errors = validate_pack(pack)
        
        # Separate warnings from threats
        warnings = [t for t in safety_threats if 'warning' in t.lower() or 'informational' in t.lower()]
        threats = [t for t in safety_threats if 'warning' not in t.lower() and 'informational' not in t.lower()]
        
        status = 'PASS' if not threats and not validation_errors else 'FAIL'
        
        if threats:
            for t in threats[:3]:
                results.append(f'{pack_file.name}: {status} [THREAT] - {t[:80]}')
        elif warnings:
            for w in warnings[:2]:
                results.append(f'{pack_file.name}: {status} [INFO] - {w[:80]}')
        elif validation_errors:
            for e in validation_errors[:2]:
                results.append(f'{pack_file.name}: {status} - {e[:80]}')
        else:
            results.append(f'{pack_file.name}: {status}')
    except Exception as e:
        results.append(f'{pack_file.name}: ERROR - {e}')

print('=== PACK SCAN RESULTS ===')
for r in results:
    print(r)
print(f'\nTotal: {len(results)} packs scanned')