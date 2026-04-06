#!/usr/bin/env python3
"""Debug problem_class filtering."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.pack_taxonomy import classify_error, load_pack_by_problem_class

# What does classify_error return for a TypeError?
pc = classify_error("TypeError: 'NoneType' object has no attribute 'foo'")
print(f"problem_class: {pc}")

# What does load_pack_by_problem_class return?
matched = load_pack_by_problem_class(pc)
print(f"matched pack: {matched}")

# What are the candidate names?
from borg.core.v3_integration import BorgV3
v3 = BorgV3()
candidates = v3._get_candidates()
print(f"\nTotal candidates: {len(candidates)}")
print("First 5 names:", [c.name for c in candidates[:5]])

# What names are in the guild index?
from borg.core.uri import get_available_pack_names
names = get_available_pack_names()
print(f"\nGuild pack names: {names[:10]}")

# What names are in our seed packs?
import os
from pathlib import Path
SKILLS_DIR = Path('/root/hermes-workspace/borg/skills')
seed_names = [p.stem for p in SKILLS_DIR.glob('*.md') if p.stem != 'borg']
print(f"\nSeed pack names: {seed_names}")

# Check if any seed name matches candidate name
candidate_names = set(c.name for c in candidates)
for sn in seed_names:
    if sn in candidate_names:
        print(f"  MATCH: '{sn}' found in candidates")
