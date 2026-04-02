---
type: workflow_pack
version: "1.0"
id: schema-drift
problem_class: schema_drift
framework: python
problem_signature:
  error_types:
    - OperationalError
    - SyncError
  framework: python
  problem_description: The database schema changed without updating the ORM model, or vice versa. SQLAlchemy or Django ORM is out of sync with the actual database.
root_cause:
  category: schema_mismatch
  explanation: The Python model and the actual database schema have diverged. Either the database was modified without updating the model, or the migration history is inconsistent.
investigation_trail:
  - file: models.py
    position: FIRST
    what: Find the model definition for the failing table
    grep_pattern: ""
  - file: "@db_schema"
    position: SECOND
    what: Query the database directly for the actual table schema
    grep_pattern: ""
  - file: "@migration_files"
    position: THIRD
    what: Check migration files for the latest schema change
    grep_pattern: ""
resolution_sequence:
  - action: create_migration
    command: python manage.py makemigrations or flask db migrate
    why: Creates a migration to bring the database in sync with the model
  - action: manual_migration
    command: "ALTER TABLE table_name ADD COLUMN column_name type;"
    why: For SQLAlchemy or when Django migrations are out of sync with actual DB
  - action: validate_model
    command: python manage.py validate or model.__table__.create() check
    why: Validates that the ORM's understanding of the schema matches the model definition
anti_patterns:
  - action: Altering the table directly without a migration
    why_fails: Loses Django/SQLAlchemy tracking and breaks future migrations
  - action: Ignoring migration history
    why_fails: The next migrate will create the same problem again
  - action: Setting nullable=True without a default on existing columns
    why_fails: May break existing rows if they violate the new constraint
evidence:
  success_count: 22
  failure_count: 4
  success_rate: 0.85
  avg_time_to_resolve_minutes: 5.0
  uses: 26
provenance: Seed pack v1 | General Python debugging | 2026-04-02
---

## When to Use This Pack

Use when you encounter:
- `OperationalError: no such column`
- `OperationalError: table has no column named`

Do NOT use when the issue is Django migration tracker state.
