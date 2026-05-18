---
type: workflow_pack
version: '1.0'
id: missing-foreign-key
problem_class: missing_foreign_key
framework: django
problem_signature:
  error_types:
  - IntegrityError
  - OperationalError
  framework: django
  problem_description: A record references another record that does not exist. Either
    the referenced record was deleted, or the foreign key value is wrong.
root_cause:
  category: schema_mismatch
  explanation: A foreign key constraint requires a referenced record to exist. Either
    the referenced record was deleted without cascading, or the foreign key value
    is invalid.
investigation_trail:
- file: django/core/management/commands/inspectdb.py
  position: FIRST
  what: inspectdb generates ForeignKey references — check if FK references a column
    that does not exist in parent table
  grep_pattern: ForeignKey|inspectdb|column
- file: django/db/backends/base/schema.py
  position: SECOND
  what: Schema editor FK constraint — check if foreign_key references a non-existent
    column
  grep_pattern: foreign_key|add_field|column
resolution_sequence:
- action: insert_parent
  command: Insert the missing parent record before inserting the child
  why: FK constraint requires the parent record to exist first
- action: set_null
  command: Set foreign_key = None (if null=True is allowed)
  why: Releases the constraint when the relationship is optional
- action: use_cascade
  command: on_delete=models.CASCADE on the ForeignKey field
  why: Automatically deletes child records when the parent is deleted
- action: fix_reference_value
  command: Update the foreign key value to point to the correct existing record
  why: The value was incorrect, not the missing parent
anti_patterns:
- action: Setting foreign key to 0 or -1
  why_fails: Creates an invalid reference that fails later
- action: Disabling foreign key checks
  why_fails: Masks the problem and creates worse data
- action: Deleting child records without understanding why
  why_fails: Data loss without fixing the underlying bug
evidence:
  success_count: 25
  failure_count: 3
  success_rate: 0.89
  avg_time_to_resolve_minutes: 3.0
  uses: 28
provenance: Seed pack v1 | Updated with SWE-bench patch file analysis | 2026-04-03
---


## When to Use This Pack

Use when you encounter:
- `IntegrityError: FOREIGN KEY constraint failed`
- Errors about missing related objects

Do NOT use when the issue is migration ordering.
