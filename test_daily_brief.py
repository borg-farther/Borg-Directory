#!/usr/bin/env python3
"""Test daily brief E2E against seed packs."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from borg.defi.v2.seed_packs import create_seed_packs
from borg.defi.v2.daily_brief import generate_daily_brief_sync

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        packs_dir = Path(tmpdir) / "packs"
        packs_dir.mkdir(parents=True)
        
        print("Creating seed packs...")
        create_seed_packs(packs_dir)
        
        print("Generating daily brief...")
        brief = generate_daily_brief_sync(packs_dir=packs_dir)
        
        print(f"\n--- DAILY BRIEF ({len(brief)} chars) ---")
        print(brief)
        print("--- END ---\n")
        
        if len(brief) > 2000:
            print(f"ERROR: Brief is {len(brief)} chars, exceeds 2000 limit!")
            return 1
        else:
            print(f"OK: Brief is {len(brief)} chars (under 2000)")
            return 0

if __name__ == "__main__":
    sys.exit(main())
