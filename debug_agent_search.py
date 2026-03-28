#!/usr/bin/env python3
"""Debug borg_search for agent-a-debugging."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, '/root/hermes-workspace/guild-v2')

with open('/root/hermes-workspace/guild-packs/index.json') as f:
    fake_index = json.load(f)

print("=== Debug: Simulating borg_search for 'agent-a-debugging' ===\n")

with patch("borg.core.search._fetch_index", return_value=fake_index):
    with patch("borg.core.search.BORG_DIR", Path("/root/hermes-workspace/guild-packs")):
        from borg.core.search import borg_search, get_borg_dir
        import borg.core.search as search_mod

        # Trace what happens
        index = fake_index

        # Handle both index formats (same as in borg_search):
        if "packs" in index:
            all_packs = list(index["packs"])
        else:
            all_packs = []
            for uri, pack_data in index.items():
                if isinstance(pack_data, dict):
                    pack_name = uri.split("/")[-1] if "/" in uri else uri
                    pack_entry = dict(pack_data)
                    pack_entry["name"] = pack_name
                    pack_entry["id"] = pack_data.get("id", uri)
                    all_packs.append(pack_entry)

        local_names_in_index = {p.get("name", "") for p in all_packs}
        print(f"local_names_in_index: {sorted(local_names_in_index)}")

        borg_dir = Path("/root/hermes-workspace/guild-packs")
        local_yamls = []
        packs_dir = borg_dir / "packs"
        if packs_dir.exists():
            for pack_yaml in packs_dir.glob("*.yaml"):
                local_yamls.append((pack_yaml.stem, pack_yaml))

        print(f"\nLocal YAMLs found: {[name for name, _ in local_yamls]}")

        print(f"\nLocal packs NOT in remote index:")
        for local_name, pack_yaml in local_yamls:
            if local_name not in local_names_in_index:
                print(f"  Would add: {local_name} (file: {pack_yaml.name})")

        print("\n=== Running actual borg_search ===")
        result_json = borg_search("agent-a-debugging")
        result = json.loads(result_json)
        print(f"Success: {result.get('success')}")
        print(f"Matches: {len(result.get('matches', []))}")
        for m in result.get('matches', []):
            print(f"  name={m.get('name')}, id={m.get('id')}, source={m.get('source')}")