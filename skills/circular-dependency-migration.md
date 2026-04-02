---
type: workflow_pack
version: "1.0"
id: circular-dependency-migration
problem_class: circular_dependency
framework: django
problem_signature:
  error_types:
    - IntegrityError
    - InvalidMoveError
  framework: django
  problem_description: Django raises IntegrityError when a migration tries to reference a table that does not exist yet due to circular dependency ordering in the migration graph.
root_cause:
  category: circular_dependency
  explanation: Migration B depends on migration A, but Django determines A must run after B because A depends on something B provides. Neither can run first.
investigation_trail:
  - file: django/db/migrations/graph.py
    position: FIRST
    what: Find where Django raises the circular dependency error and how it resolves the migration dependency graph
    grep_pattern: CircularDependency|requires|get_dependencies|StateMachine
  - file: django/db/migrations/state.py
    position: SECOND
    what: Check if a swappable model (AUTH_USER_MODEL) or model base creates an implicit circular dependency through the app registry
    grep_pattern: swappable|app_config|get_model|render
  - file: django/db/migrations/autodetector.py
    position: THIRD
    what: Check if autodetector is generating dependencies that create a cycle between two apps' migrations
    grep_pattern: dependencies|generate|AlterField|CreateModel
resolution_sequence:
  - action: add_explicit_depends_on
    command: "Edit the later migration file. Add to the top: dependencies = [('app_name', 'migration_name')]"
    why: Explicit dependencies override Django graph inference and force correct ordering
  - action: squash_migrations
    command: python manage.py squashmigrations app_name 0001 0002 --no-header
    why: Collapses intermediate migrations so Django rebuilds the dependency graph
  - action: split_migration
    command: Split the migration into two separate files, one per app
    why: If one migration has operations for two apps, Django cannot order them correctly
anti_patterns:
  - action: Deleting migration files and re-creating them
    why_fails: Re-creates the same ordering problem
  - action: Running migrate --fake
    why_fails: Skips execution but does not fix the ordering
  - action: Using --run-syncdb
    why_fails: Bypasses the migration system entirely and creates worse inconsistencies
evidence:
  success_count: 23
  failure_count: 3
  success_rate: 0.88
  avg_time_to_resolve_minutes: 4.2
  uses: 26
provenance: Seed pack v1 | Updated with SWE-bench django__django-10554, django__django-12754 patch files | 2026-04-03
---

## When to Use This Pack

Use when you encounter:
- `django.db.utils.IntegrityError` during migration
- `InvalidMoveError` related to migration ordering
- A traceback referencing `django/db/migrations/graph.py`

Do NOT use for general database errors unrelated to migration ordering.

## How to Use

1. Read the traceback carefully. Find which TWO migration files are involved in the cycle.
2. Check `django/db/migrations/graph.py` — find the method that resolves dependencies.
3. Check if either migration has explicit `dependencies` — if not, add them.
4. Run `python manage.py showmigrations --plan` to see the full migration order.
5. Add `depends_on` to the later migration to force correct ordering.
6. Verify with `python manage.py migrate`.
