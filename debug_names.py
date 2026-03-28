#!/usr/bin/env python3
"""Debug the pack name extraction from index values."""
import json
import re

with open('/root/hermes-workspace/guild-packs/index.json') as f:
    index = json.load(f)

print("=== Analyzing index entries for pack names ===\n")
for uri, data in list(index.items())[:10]:
    pack_name_from_uri = uri.split('/')[-1] if '/' in uri else uri
    has_name_field = 'name' in data if isinstance(data, dict) else False
    name_field = data.get('name', 'N/A') if isinstance(data, dict) else 'N/A'
    id_field = data.get('id', 'N/A') if isinstance(data, dict) else 'N/A'

    print(f"URI: {uri}")
    print(f"  Pack name from URI: {pack_name_from_uri}")
    print(f"  Has 'name' field: {has_name_field}")
    print(f"  Name field value: {name_field}")
    print(f"  ID field value: {id_field}")
    print()