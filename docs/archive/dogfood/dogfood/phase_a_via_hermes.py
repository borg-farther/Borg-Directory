#!/usr/bin/env python3
"""Phase A Seeder via Hermes delegate_task — works with OAuth auth.

Instead of calling Anthropic SDK directly, this script generates
task prompts that can be dispatched via Hermes delegate_task.

Usage: Run from within a Hermes session. The orchestrator calls
delegate_task for each SWE-bench task.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Task list — 10 Django tasks with Docker images available
# (subset for Phase A seeding, handpicked for diversity)
SEED_TASKS = [
    {
        "id": "django__django-11477",
        "desc": "Translate URL patterns \u2014 Correctly handle URLs with translated patterns when same URL is used in different languages",
        "file": "django/urls/resolvers.py",
        "test_cmd": "python tests/runtests.py i18n.patterns.tests --verbosity 2",
    },
    {
        "id": "django__django-12155", 
        "desc": "Admindocs \u2014 Fix docutils table markup in admindocs view descriptions",
        "file": "django/contrib/admindocs/views.py",
        "test_cmd": "python tests/runtests.py admin_docs.test_views --verbosity 2",
    },
    {
        "id": "django__django-13449",
        "desc": "AlterField with db_column should be a noop \u2014 AlterField operation should skip when only db_column is set",
        "file": "django/db/backends/base/schema.py",
        "test_cmd": "python tests/runtests.py migrations.test_operations --verbosity 2",
    },
    {
        "id": "django__django-13925",
        "desc": "ManifestStaticFilesStorage crash \u2014 Handle missing staticfiles manifest gracefully",
        "file": "django/contrib/staticfiles/storage.py",
        "test_cmd": "python tests/runtests.py staticfiles_tests --verbosity 2",
    },
    {
        "id": "django__django-14011",
        "desc": "LSN comparison \u2014 Fix Log Sequence Number comparison in PostgreSQL replication",
        "file": "django/db/backends/postgresql/operations.py",
        "test_cmd": "python tests/runtests.py backends --verbosity 2",
    },
]


def build_prompt(task: dict) -> str:
    """Build a self-contained prompt for a Hermes subagent."""
    return f"""You are fixing a bug in Django for the Borg knowledge seeding experiment.

IMPORTANT: Before starting, use borg tools to search for guidance:
1. Run in terminal: borg debug '{task["desc"][:80]}'
2. Run in terminal: borg search 'django'
3. Use whatever guidance borg provides.

BUG: {task["desc"]}

The Django repo is at /tmp/borg_phase_a/{task["id"]}/testbed
If the workspace doesn't exist yet, set it up:
1. Check if Docker image sweb.eval.x86_64.{task["id"]}:latest exists (docker images | grep {task["id"]})
2. If it exists, extract testbed: docker create --name temp_{task["id"]} sweb.eval.x86_64.{task["id"]}:latest && docker cp temp_{task["id"]}:/testbed /tmp/borg_phase_a/{task["id"]}/testbed && docker rm temp_{task["id"]}
3. If Docker image doesn't exist, skip this task and report 'SKIP: no Docker image'

Primary file to investigate: {task["file"]}

To run tests:
docker run -v /tmp/borg_phase_a/{task["id"]}/testbed:/testbed -w /testbed sweb.eval.x86_64.{task["id"]}:latest bash -c "source /opt/miniconda3/bin/activate testbed && {task["test_cmd"]}"

After fixing (or failing), record the outcome:
- Run: borg feedback-v3 --pack systematic-debugging --success yes  (if fixed)
- Run: borg feedback-v3 --pack systematic-debugging --success no  (if not fixed)

Report: PASS or FAIL, what you changed, how borg helped (or didn't)."""


def main():
    log_path = Path("/root/hermes-workspace/borg/dogfood/phase_a_log.jsonl")
    
    print(f"Phase A Seeding — {len(SEED_TASKS)} tasks")
    print(f"Log: {log_path}")
    print()
    print("TASK PROMPTS GENERATED. Dispatch via delegate_task in batches of 3.")
    print()
    
    for i, task in enumerate(SEED_TASKS, 1):
        prompt = build_prompt(task)
        prompt_file = f"/tmp/borg_phase_a/prompts/{task['id']}.txt"
        Path(prompt_file).parent.mkdir(parents=True, exist_ok=True)
        Path(prompt_file).write_text(prompt)
        print(f"  [{i}/{len(SEED_TASKS)}] {task['id']}")
        print(f"    Prompt: {prompt_file}")
        print(f"    Bug: {task['desc'][:60]}...")
    
    print()
    print("Ready for dispatch.")


if __name__ == "__main__":
    main()
