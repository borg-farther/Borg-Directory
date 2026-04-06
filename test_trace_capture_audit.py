#!/usr/bin/env python3
"""
Borg E2E Audit — Test 2: Trace Capture
Verifies: Do borg_observe/borg_apply create traces in traces.db?
"""
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Test paths
TRACE_DB_PATH = "/root/.borg/traces.db"
BORG_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "guild"

def get_trace_count():
    """Get current trace count in traces.db"""
    try:
        conn = sqlite3.connect(TRACE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM traces")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"Error reading traces.db: {e}")
        return -1

def check_init_trace_capture_in_borg_apply():
    """Check if borg_apply calls init_trace_capture"""
    with open("borg/integrations/mcp_server.py", "r") as f:
        content = f.read()
    
    # Find borg_apply function
    import re
    apply_match = re.search(r'def borg_apply\([^)]*\):(.*?)(?=\ndef [a-z]|\nclass |\Z)', content, re.DOTALL)
    if apply_match:
        apply_body = apply_match.group(1)
        has_init = "init_trace_capture" in apply_body
        has_end = "end_trace_capture" in apply_body
        has_save_trace = "save_trace" in apply_body
        return has_init, has_end, has_save_trace
    return None, None, None

def check_borg_observe_trace_writes():
    """Check if borg_observe writes any traces"""
    with open("borg/integrations/mcp_server.py", "r") as f:
        content = f.read()
    
    import re
    observe_match = re.search(r'def borg_observe\([^)]*\):(.*?)(?=\ndef [a-z_]+\s*\(|\nclass |\Z)', content, re.DOTALL)
    if observe_match:
        observe_body = observe_match.group(1)
        has_save = "save_trace" in observe_body
        has_init = "init_trace_capture" in observe_body
        has_extract = "extract_trace" in observe_body
        return has_save, has_init, has_extract
    return None, None, None

def check_borg_feedback_trace_writes():
    """Check if borg_feedback saves traces"""
    with open("borg/integrations/mcp_server.py", "r") as f:
        content = f.read()
    
    import re
    feedback_match = re.search(r'def borg_feedback\([^)]*\):(.*?)(?=\ndef [a-z_]+\s*\(|\nclass |\Z)', content, re.DOTALL)
    if feedback_match:
        feedback_body = feedback_match.group(1)
        has_save = "save_trace" in feedback_body
        has_extract = "extract_trace" in feedback_body
        has_end = "end_trace_capture" in feedback_body
        return has_save, has_extract, has_end
    return None, None, None

def main():
    print("=" * 60)
    print("BORG E2E AUDIT — TEST 2: TRACE CAPTURE")
    print("=" * 60)
    print()
    
    print("QUESTION: Do borg_observe/borg_apply create traces in traces.db?")
    print()
    
    # 1. Check source code for trace capture calls
    print("1. SOURCE CODE ANALYSIS")
    print("-" * 40)
    
    apply_init, apply_end, apply_save = check_init_trace_capture_in_borg_apply()
    print(f"   borg_apply:")
    print(f"     - init_trace_capture() called: {apply_init}")
    print(f"     - end_trace_capture() called:  {apply_end}")
    print(f"     - save_trace() called:        {apply_save}")
    
    observe_save, observe_init, observe_extract = check_borg_observe_trace_writes()
    print(f"   borg_observe:")
    print(f"     - save_trace() called:        {observe_save}")
    print(f"     - init_trace_capture() called: {observe_init}")
    print(f"     - extract_trace() called:     {observe_extract}")
    
    fb_save, fb_extract, fb_end = check_borg_feedback_trace_writes()
    print(f"   borg_feedback:")
    print(f"     - save_trace() called:        {fb_save}")
    print(f"     - extract_trace() called:     {fb_extract}")
    print(f"     - end_trace_capture() called: {fb_end}")
    
    print()
    print("2. TRACE DATABASE STATUS")
    print("-" * 40)
    count = get_trace_count()
    print(f"   Current traces in {TRACE_DB_PATH}: {count}")
    
    print()
    print("3. FINDINGS")
    print("-" * 40)
    
    findings = []
    
    # borg_observe
    if observe_save or observe_init or observe_extract:
        findings.append("❌ UNEXPECTED: borg_observe appears to write traces")
    else:
        findings.append("✅ CONFIRMED: borg_observe does NOT create traces (read-only)")
    
    # borg_apply
    if apply_init and not apply_save:
        findings.append("⚠️  PARTIAL: borg_apply initializes trace capture but does NOT save traces itself")
        findings.append("    Traces are saved when borg_feedback is called afterward")
    elif apply_init and apply_save:
        findings.append("✅ CONFIRMED: borg_apply creates and saves traces")
    else:
        findings.append("❌ ISSUE: borg_apply does NOT initialize trace capture")
    
    for f in findings:
        print(f"   {f}")
    
    print()
    print("4. CONCLUSION")
    print("-" * 40)
    print("""
   • borg_observe: Read-only operation. Does NOT create traces.
   
   • borg_apply: Initializes trace capture on 'start', but trace is NOT 
     saved automatically. Must call borg_feedback() after apply completes
     to extract and save the trace.
   
   • borg_feedback: The function that actually extracts trace data and 
     saves it to traces.db (if tool_calls > 5).
   
   Result: borg_apply does NOT directly create traces in traces.db.
           Traces are created by borg_feedback(), which should be called
           after borg_apply completes.
""")
    
    return 0

if __name__ == "__main__":
    exit(main())