#!/usr/bin/env python3
"""CLI feedback → trace wiring. When borg_feedback-v3 fires, also save a trace."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

# Test: can we save a trace from feedback-v3 data?
from borg.core.traces import save_trace, _get_db

# Simulate what _cmd_feedback_v3 would pass
trace = {
    "task_description": "Django migration for model field change",
    "outcome": "success",
    "root_cause": "Field migration was missing null=True constraint",
    "approach_summary": "Added null=True to field definition after checking migration",
    "files_read": '["/testbed/django/db/models/__init__.py"]',
    "files_modified": "[]",
    "key_files": '["/testbed/django/db/models/__init__.py"]',
    "tool_calls": 13,
    "errors_encountered": "[]",
    "dead_ends": "[]",
    "keywords": "django field fix migration model",
    "technology": "django",
    "error_patterns": "django migration field null",
    "agent_id": "borg-cli",
    "source": "feedback-v3",
}

trace_id = save_trace(trace)
print(f"Saved trace: {trace_id}")

# Verify
db = _get_db()
cur = db.cursor()
cur.execute("SELECT id, task_description, outcome, technology, source FROM traces WHERE id = ?", (trace_id,))
r = cur.fetchone()
print(f"Verified: {r}")

# Now test: can we extract a pack from this trace using MiniMax M2.7?
print("\n--- Testing trace → pack extraction ---")
from borg.core.pack_taxonomy import classify_error

# Classify the trace's error pattern
pc = classify_error("Django migration field null constraint")
print(f"problem_class: {pc}")

# The actual extraction pipeline would:
# 1. Read the trace (task_description, root_cause, approach_summary)
# 2. Call LLM with: "Given this trace, generate a Borg workflow pack YAML"
# 3. Validate and save as CANDIDATE
# Let's verify the prompt would work

prompt = f"""Given this successful debugging trace, generate a Borg workflow pack YAML.

Task: {trace['task_description']}
Root cause: {trace['root_cause']}
Approach: {trace['approach_summary']}
Technology: {trace['technology']}
Keywords: {trace['keywords']}

Output ONLY valid YAML for a Borg pack with these fields:
- id: pack identifier
- name: human-readable name
- problem_class: the problem category (use: {pc})
- description: 1-2 sentence summary
- investigation_trail: list of grep commands or investigation steps
- resolution_sequence: list of fix commands or resolution steps
- anti_patterns: list of what NOT to do

Format as clean YAML. No markdown code blocks."""


print("Extraction prompt would be:")
print(prompt[:500] + "...")
print(f"\nPrompt length: {len(prompt)} chars")

# Check what LLM would generate
from borg.core.v3_integration import BorgV3
v3 = BorgV3()
print("\nChecking if we can call the model for extraction...")
print("v3._model available:", hasattr(v3, '_model'))