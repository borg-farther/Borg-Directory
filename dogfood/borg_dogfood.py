#!/usr/bin/env python3
"""Borg V3 dogfood helper — record real task outcomes from this agent."""

import sys
import os
import json
import time

sys.path.insert(0, '/root/hermes-workspace/borg')
from borg.core.v3_integration import BorgV3

v3 = BorgV3()


def record(pack_id: str, task_category: str, success: bool,
           tokens_used: int = 0, time_taken: float = 0.0):
    """Record a task outcome."""
    v3.record_outcome(
        pack_id=pack_id,
        task_context={"task_type": task_category},
        success=success,
        tokens_used=tokens_used,
        time_taken=time_taken,
    )
    print(f"Recorded: pack={pack_id} cat={task_category} success={success}")


def dashboard():
    """Print current dashboard."""
    d = v3.get_dashboard()
    print(json.dumps(d, indent=2, default=str))


def search(query: str, task_type: str = None):
    """Search with optional context."""
    ctx = {"task_type": task_type} if task_type else None
    results = v3.search(query, task_context=ctx)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dashboard"
    if cmd == "dashboard":
        dashboard()
    elif cmd == "record":
        record(sys.argv[2], sys.argv[3], sys.argv[4].lower() == "true",
               int(sys.argv[5]) if len(sys.argv) > 5 else 0,
               float(sys.argv[6]) if len(sys.argv) > 6 else 0.0)
    elif cmd == "search":
        search(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print(f"Usage: {sys.argv[0]} [dashboard|record|search]")
