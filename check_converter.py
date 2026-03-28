#!/usr/bin/env python3
import yaml
import sys
import re
sys.path.insert(0, '/root/hermes-workspace/guild-v2')

from borg.core.convert import convert_pack_to_openclaw_ref

with open('/root/hermes-workspace/guild-packs/packs/systematic-debugging.workflow.yaml') as f:
    pack = yaml.safe_load(f)

ref = convert_pack_to_openclaw_ref(pack)
print("=== Full reference for systematic-debugging.workflow ===")
print(ref)
print()
print("=== Phase detection ===")
pattern1 = re.compile(r"^#{1,3}\s+Phase\s+\d+:", re.MULTILINE)
matches = pattern1.findall(ref)
print(f"Pattern '## Phase N:' found: {len(matches)}")

pattern2 = re.compile(r"(?i)\*\*Phase\s+\d+\*\*:", re.MULTILINE)
matches2 = pattern2.findall(ref)
print(f"Pattern '**Phase N:**' found: {len(matches2)}")

# Show lines with "Phase" in them
for i, line in enumerate(ref.splitlines()):
    if re.search(r"(?i)phase", line):
        print(f"Line {i}: {line[:100]}")
