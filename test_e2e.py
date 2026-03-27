"""End-to-end flow test — simulates what a real user would do."""
import json
import sys
sys.path.insert(0, '.')

from borg.core.search import guild_search, guild_try, guild_pull, check_for_suggestion
from borg.core.apply import apply_handler

print("=== 1. SEARCH ===")
result = guild_search("debugging")
data = json.loads(result)
print(f"Success: {data.get('success')}")
print(f"Matches: {len(data.get('matches', []))}")
if data.get('matches'):
    for m in data['matches'][:3]:
        print(f"  - {m.get('name', m.get('id', '?'))}: {m.get('confidence', '?')} ({m.get('tier', '?')})")

print("\n=== 2. TRY ===")
result = guild_try("borg://systematic-debugging")
data = json.loads(result)
print(f"Success: {data.get('success')}")
if data.get('error'):
    print(f"Error: {data['error']}")
if data.get('pack_name'):
    print(f"Pack: {data['pack_name']}")
    print(f"Phases: {data.get('phase_count', '?')}")

print("\n=== 3. AUTO-SUGGEST ===")
result = check_for_suggestion(
    conversation_context="I keep getting TypeError and the test keeps failing, stuck in a loop",
    failure_count=3
)
data = json.loads(result)
print(f"Has suggestion: {data.get('has_suggestion')}")
if data.get('suggestions'):
    for s in data['suggestions'][:3]:
        print(f"  - {s.get('pack_name')}: {s.get('why_relevant', '?')}")

print("\n=== 4. CONVERT ===")
from borg.core.convert import convert_skill
import tempfile, os
# Create a sample SKILL.md
skill_content = '''---
name: test-skill
description: A test skill for debugging
tags: [testing, debugging]
---
## Step 1: Reproduce
Reproduce the issue consistently.
## Step 2: Investigate  
Look at logs and traces.
## Step 3: Fix
Apply the fix and verify.
'''
with tempfile.NamedTemporaryFile(mode='w', prefix='SKILL', suffix='.md', delete=False, dir='/tmp') as f:
    f.write(skill_content)
    tmp = f.name
try:
    pack = convert_skill(tmp)
    print(f"Converted: {pack.get('id', '?')}")
    print(f"Phases: {len(pack.get('phases', []))}")
    print(f"Problem class: {pack.get('problem_class', '?')}")
finally:
    os.unlink(tmp)

print("\n=== DONE ===")
