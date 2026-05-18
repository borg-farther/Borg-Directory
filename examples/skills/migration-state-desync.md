---
type: workflow_pack
version: "1.0"
id: migration-state-desync
problem_class: migration_state_desync
framework: django
problem_signature:
  error_types:
    - OperationalError
    - ProgrammingError
  framework: django
  problem_description: Django thinks initial migrations have already run but they have not. The database schema and migration history disagree.
root_cause:
  category: schema_mismatch
  explanation: Django's migration history in django_migrations table disagrees with the actual database schema. Either the migration was never recorded, or the table was created manually.
investigation_trail:
  - file: django/db/migrations/executor.py
    position: FIRST
    what: How Django records and checks applied migrations. Look for MigrationExecutor.recorder and apply_migration behavior
    grep_pattern: apply_migration|unapply_migration|record_migration
  - file: django/db/backends/base/schema.py
    position: SECOND
    what: How the schema editor creates/destroys tables. Look for table existence checks and CREATE TABLE statements
    grep_pattern: create_table|execute|add_field|alter_field
  - file: django/db/migrations/autodetector.py
    position: THIRD
    what: How autodetector generates migration operations and detects changes to models
    grep_pattern: generate|CreateModel|AlterField|delete_model
resolution_sequence:
  - action: fake_initial
    command: python manage.py migrate --fake-initial
    why: Tells Django the initial migration ran when it did not, without touching the schema
  - action: manual_register
    command: "INSERT INTO django_migrations (app, name, applied) VALUES ('app_name', '0001', datetime.now())"
    why: Manually registers a migration as applied when the table exists but migration was not recorded
  - action: fake_specific
    command: "python manage.py migrate app_name --fake migration_name"
    why: Marks a specific migration as applied without running it
anti_patterns:
  - action: Deleting migration files
    why_fails: Makes things worse — Django will try to recreate them
  - action: migrate --run-syncdb
    why_fails: Bypasses migrations entirely and creates new inconsistencies
  - action: Dropping and recreating the database in production
    why_fails: Data loss
evidence:
  success_count: 18
  failure_count: 2
  success_rate: 0.90
  avg_time_to_resolve_minutes: 5.5
  uses: 20
provenance: Seed pack v1 | Updated with SWE-bench django__django-12708, django__django-12754, django__django-14500, django__django-15252 patch files | 2026-04-03
---

## When to Use This Pack

Use when you encounter:
- `OperationalError: no such table`
- `OperationalError: table already exists`
- Django says a migration is applied but the table does not exist (or vice versa)
- Migration crashes with index_together/unique_together conflicts

Do NOT use when the error is about circular dependency ordering.
