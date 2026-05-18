#!/usr/bin/env python3
"""Clean up debug/test scripts from borg root."""
import os
from pathlib import Path

root = Path("/root/hermes-workspace/borg")
patterns = ["debug_", "test_search", "test_borg", "test_minimax", "test_pc", "test_debug", "test_quickstart", "audit_", "check_", "scan_", "validate_", "measure_", "inspect_", "cleanup_"]

removed = []
for f in root.glob("*.py"):
    name = f.name
    for p in patterns:
        if name.startswith(p) or name.startswith("test_functional") or name.startswith("test_e2e") or name.startswith("test_feedback") or name.startswith("test_ab") or name.startswith("test_generate") or name.startswith("test_mcp") or name.startswith("test_thompson") or name.startswith("test_trace") or name.startswith("test_tool") or name.startswith("test_task") or name.startswith("test_timing") or name.startswith("test_prompt") or name.startswith("test_multiturn") or name.startswith("test_problem"):
            if f.name not in ("run_c3_replay.py", "run_perf_tests.py", "run_tests.py", "run_i_tests.py", "test_agentskills_converter.py"):
                removed.append(f.name)
                f.unlink()
                break

print(f"Removed {len(removed)} debug files:")
for n in sorted(removed):
    print(f"  - {n}")
