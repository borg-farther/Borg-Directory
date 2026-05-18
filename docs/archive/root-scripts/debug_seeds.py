#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.seeds import get_seed_packs, is_seeds_disabled, SEEDS_DIR
print(f"seeds_disabled: {is_seeds_disabled()}")
print(f"SEEDS_DIR: {SEEDS_DIR}")

import os
print(f"SEEDS_DIR exists: {os.path.exists(SEEDS_DIR)}")
if os.path.exists(SEEDS_DIR):
    print(f"Contents: {os.listdir(SEEDS_DIR)}")

packs = get_seed_packs()
print(f"seed packs: {len(packs)}")
for p in packs[:5]:
    print(f"  - {p.name}: {p.problem_class}")
