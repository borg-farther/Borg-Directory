#!/usr/bin/env python3
"""Full Borg workflow E2E test."""
import sys
import os
import json

# Add borg to path
sys.path.insert(0, '/root/hermes-workspace/borg')
os.chdir('/root/hermes-workspace/borg')

from borg.integrations.mcp_server import (
    borg_observe, borg_search, borg_apply, borg_feedback,
    borg_recall, borg_reputation, borg_context
)

results = {}

# Step 1: borg_observe
print("=" * 60)
print("STEP 1: borg_observe(task='debug a Python import error')")
print("=" * 60)
try:
    r = borg_observe(task='debug a Python import error')
    results['step1'] = str(r)[:2000]
    print(results['step1'])
    print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
except Exception as e:
    results['step1'] = f"ERROR: {e}"
    print(results['step1'])
    print("\nRESULT: FAIL")

# Step 2: borg_search
print("\n" + "=" * 60)
print("STEP 2: borg_search(query='debugging')")
print("=" * 60)
try:
    r = borg_search(query='debugging')
    results['step2'] = str(r)[:2000]
    print(results['step2'])
    print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
except Exception as e:
    results['step2'] = f"ERROR: {e}"
    print(results['step2'])
    print("\nRESULT: FAIL")

# Step 3: borg_apply start
print("\n" + "=" * 60)
print("STEP 3: borg_apply(action='start', pack_name='systematic-debugging', task='fix ImportError in main.py')")
print("=" * 60)
try:
    r = borg_apply(action='start', pack_name='systematic-debugging', task='fix ImportError in main.py')
    results['step3'] = str(r)[:2000]
    print(results['step3'])
    # Extract session_id
    session_id = None
    if isinstance(r, str):
        for line in r.split('\n'):
            if 'session_id' in line.lower() or 'session' in line.lower():
                # Try to find session id
                import re
                match = re.search(r'[a-f0-9\-]{8,}', line)
                if match:
                    session_id = match.group(0)
                    break
        if not session_id:
            match = re.search(r'[a-f0-9\-]{8,}', r)
            if match:
                session_id = match.group(0)
    print(f"\nExtracted session_id: {session_id}")
    print("RESULT: PASS" if session_id else "RESULT: FAIL (no session_id)")
except Exception as e:
    results['step3'] = f"ERROR: {e}"
    print(results['step3'])
    session_id = None
    print("\nRESULT: FAIL")

if session_id:
    # Step 4: approval checkpoint
    print("\n" + "=" * 60)
    print(f"STEP 4: borg_apply(action='checkpoint', session_id='{session_id}', phase_name='__approval__', status='passed')")
    print("=" * 60)
    try:
        r = borg_apply(action='checkpoint', session_id=session_id, phase_name='__approval__', status='passed')
        results['step4'] = str(r)[:2000]
        print(results['step4'])
        print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
    except Exception as e:
        results['step4'] = f"ERROR: {e}"
        print(results['step4'])
        print("\nRESULT: FAIL")

    # Step 5: reproduce checkpoint
    print("\n" + "=" * 60)
    print(f"STEP 5: borg_apply(action='checkpoint', session_id='{session_id}', phase_name='reproduce', status='passed', evidence='Error reproduced')")
    print("=" * 60)
    try:
        r = borg_apply(action='checkpoint', session_id=session_id, phase_name='reproduce', status='passed', evidence='Error reproduced')
        results['step5'] = str(r)[:2000]
        print(results['step5'])
        print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
    except Exception as e:
        results['step5'] = f"ERROR: {e}"
        print(results['step5'])
        print("\nRESULT: FAIL")

    # Step 6: complete
    print("\n" + "=" * 60)
    print(f"STEP 6: borg_apply(action='complete', session_id='{session_id}', outcome='Fixed the import')")
    print("=" * 60)
    try:
        r = borg_apply(action='complete', session_id=session_id, outcome='Fixed the import')
        results['step6'] = str(r)[:2000]
        print(results['step6'])
        print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
    except Exception as e:
        results['step6'] = f"ERROR: {e}"
        print(results['step6'])
        print("\nRESULT: FAIL")

    # Step 7: feedback
    print("\n" + "=" * 60)
    print(f"STEP 7: borg_feedback(session_id='{session_id}')")
    print("=" * 60)
    try:
        r = borg_feedback(session_id=session_id)
        results['step7'] = str(r)[:2000]
        print(results['step7'])
        print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
    except Exception as e:
        results['step7'] = f"ERROR: {e}"
        print(results['step7'])
        print("\nRESULT: FAIL")
else:
    print("\nSKIPPING STEPS 4-7 (no session_id from step 3)")

# Additional tests
print("\n" + "=" * 60)
print("EXTRA 1: borg_recall(error_message='ModuleNotFoundError: No module named foo')")
print("=" * 60)
try:
    r = borg_recall(error_message='ModuleNotFoundError: No module named foo')
    results['recall'] = str(r)[:2000]
    print(results['recall'])
    print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
except Exception as e:
    results['recall'] = f"ERROR: {e}"
    print(results['recall'])
    print("\nRESULT: FAIL")

print("\n" + "=" * 60)
print("EXTRA 2: borg_reputation(action='get_profile', agent_id='test-agent')")
print("=" * 60)
try:
    r = borg_reputation(action='get_profile', agent_id='test-agent')
    results['reputation'] = str(r)[:2000]
    print(results['reputation'])
    print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
except Exception as e:
    results['reputation'] = f"ERROR: {e}"
    print(results['reputation'])
    print("\nRESULT: FAIL")

print("\n" + "=" * 60)
print("EXTRA 3: borg_context(project_path='/root/hermes-workspace/borg')")
print("=" * 60)
try:
    r = borg_context(project_path='/root/hermes-workspace/borg')
    results['context'] = str(r)[:2000]
    print(results['context'])
    print("\nRESULT: PASS" if r else "\nRESULT: FAIL")
except Exception as e:
    results['context'] = f"ERROR: {e}"
    print(results['context'])
    print("\nRESULT: FAIL")

print("\n\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for k, v in results.items():
    status = "PASS" if v and not v.startswith("ERROR") else "FAIL"
    print(f"  {k}: {status}")
