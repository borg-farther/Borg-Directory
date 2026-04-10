#!/usr/bin/env python3
"""
build_corpus.py — Generates the 50-query cold-start benchmark corpus.

Produces: error_corpus.jsonl
  One JSON object per line. Each object contains:
    - query_id (int, 1-50)
    - query (str, diverse real-world phrasing)
    - expected_problem_class (str)
    - min_relevant_hits (int, 1 or 5 per G1/G2)
    - category (str, one of the five benchmark categories)
    - difficulty (str: easy/medium/hard, Zipf-distributed)

The 50 queries are drawn from:
  - Django error patterns (12 queries)
  - Python stdlib errors (15 queries)
  - Git/Docker/bash workflows (8 queries)
  - Framework-specific (Flask, pytest, etc.) (10 queries)
  - Edge cases: race conditions, timeouts, permission errors (5 queries)

Run:
    python build_corpus.py
Output:
    error_corpus.jsonl  (in same directory as script)
"""

import json
import pathlib

OUTPUT_PATH = pathlib.Path(__file__).parent / "error_corpus.jsonl"

# The 50 benchmark queries
# Each query is real-world phrasing from developer errors, stack traces,
# and common workflow problems. Mapped to the problem_class it should match.
CORPUS = [
    # === Category 1: Django errors (12 queries) ===
    {
        "query_id": 1,
        "query": "django.db.utils.IntegrityError: FOREIGN KEY constraint failed during migrate",
        "expected_problem_class": "circular_dependency",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "medium",
    },
    {
        "query_id": 2,
        "query": "django.core.exceptions.ImproperlyConfigured: SECRET_KEY environment variable not set",
        "expected_problem_class": "configuration_error",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "easy",
    },
    {
        "query_id": 3,
        "query": "OperationalError: no such table: django_migrations after migrate",
        "expected_problem_class": "migration_state_desync",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "medium",
    },
    {
        "query_id": 4,
        "query": "IntegrityError: duplicate key value violates unique constraint for user_id",
        "expected_problem_class": "missing_foreign_key",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "medium",
    },
    {
        "query_id": 5,
        "query": "AttributeError: 'NoneType' object has no attribute 'objects' in Django view",
        "expected_problem_class": "null_pointer_chain",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "easy",
    },
    {
        "query_id": 6,
        "query": "django.db.utils.OperationalError: no such column: profile_user_id",
        "expected_problem_class": "schema_drift",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "medium",
    },
    {
        "query_id": 7,
        "query": "InvalidMoveError: cannot reverse migration direction",
        "expected_problem_class": "circular_dependency",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "hard",
    },
    {
        "query_id": 8,
        "query": "Applied missing migrations: cannot apply, database schema mismatch",
        "expected_problem_class": "migration_state_desync",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "hard",
    },
    {
        "query_id": 9,
        "query": "TypeError: expected str, bytes or os.PathLike object, not DeferredAttribute",
        "expected_problem_class": "type_mismatch",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "medium",
    },
    {
        "query_id": 10,
        "query": "PermissionError: Access to path /var/www/media denied during file upload",
        "expected_problem_class": "permission_denied",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "easy",
    },
    {
        "query_id": 11,
        "query": "TimeoutError: Django runserver hanging on first request after migrate",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "medium",
    },
    {
        "query_id": 12,
        "query": "Relation does not exist: FOREIGN KEY constraint failed on PostgreSQL after schema change",
        "expected_problem_class": "schema_drift",
        "min_relevant_hits": 1,
        "category": "django",
        "difficulty": "hard",
    },
    # === Category 2: Python stdlib errors (15 queries) ===
    {
        "query_id": 13,
        "query": "ModuleNotFoundError: No module named 'cv2' despite pip install opencv-python",
        "expected_problem_class": "missing_dependency",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "easy",
    },
    {
        "query_id": 14,
        "query": "ImportError: cannot import name 'cache' from 'functools' in Python 3.9",
        "expected_problem_class": "import_cycle",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "medium",
    },
    {
        "query_id": 15,
        "query": "TypeError: 'NoneType' object has no attribute 'get' when parsing JSON",
        "expected_problem_class": "null_pointer_chain",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "easy",
    },
    {
        "query_id": 16,
        "query": "TypeError: expected bytes, str or Path-like object, got int instead",
        "expected_problem_class": "type_mismatch",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "easy",
    },
    {
        "query_id": 17,
        "query": "ModuleNotFoundError: No module named 'psycopg2' in virtual environment",
        "expected_problem_class": "missing_dependency",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "easy",
    },
    {
        "query_id": 18,
        "query": "ImportError: circular import between auth.py and models.py",
        "expected_problem_class": "import_cycle",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "medium",
    },
    {
        "query_id": 19,
        "query": "AttributeError: 'module' object has no attribute 'something' after pip install upgrade",
        "expected_problem_class": "null_pointer_chain",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "medium",
    },
    {
        "query_id": 20,
        "query": "TypeError: argument of type 'NoneType' is not iterable in template context",
        "expected_problem_class": "null_pointer_chain",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "medium",
    },
    {
        "query_id": 21,
        "query": "PermissionError: [Errno 13] Permission denied writing to /etc/hosts",
        "expected_problem_class": "permission_denied",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "easy",
    },
    {
        "query_id": 22,
        "query": "RuntimeError: dictionary changed size during iteration in multiprocessing loop",
        "expected_problem_class": "race_condition",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "hard",
    },
    {
        "query_id": 23,
        "query": "TimeoutError: connectionpool connection pool exhausted after 30 seconds",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "medium",
    },
    {
        "query_id": 24,
        "query": "ModuleNotFoundError: No module named 'yaml' after pyproject.toml install",
        "expected_problem_class": "missing_dependency",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "easy",
    },
    {
        "query_id": 25,
        "query": "TypeError: cannot use a bytes pattern on a buffer in Python 3 socket module",
        "expected_problem_class": "type_mismatch",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "medium",
    },
    {
        "query_id": 26,
        "query": "ImportError: cannot import name 'BaseCommand' from 'django.core.management'",
        "expected_problem_class": "import_cycle",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "hard",
    },
    {
        "query_id": 27,
        "query": "AttributeError: 'NoneType' object has no attribute 'encode' for SMS gateway",
        "expected_problem_class": "null_pointer_chain",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "easy",
    },
    # === Category 3: Git/Docker/bash workflows (8 queries) ===
    {
        "query_id": 28,
        "query": "git merge conflict in feature/auth.py — how to resolve using ours strategy",
        "expected_problem_class": "schema_drift",  # closest match in existing seeds
        "min_relevant_hits": 1,
        "category": "git",
        "difficulty": "medium",
    },
    {
        "query_id": 29,
        "query": "docker build fails with 'cannot verify non-leaf node' in Dockerfile multi-stage",
        "expected_problem_class": "configuration_error",
        "min_relevant_hits": 1,
        "category": "docker",
        "difficulty": "hard",
    },
    {
        "query_id": 30,
        "query": "bash script exits with code 126 — permission denied on executable script",
        "expected_problem_class": "permission_denied",
        "min_relevant_hits": 1,
        "category": "bash",
        "difficulty": "easy",
    },
    {
        "query_id": 31,
        "query": "git stash pop fails with CONFLICT — auto-merge failed in package-lock.json",
        "expected_problem_class": "race_condition",
        "min_relevant_hits": 1,
        "category": "git",
        "difficulty": "medium",
    },
    {
        "query_id": 32,
        "query": "docker compose up hangs on starting service — connection refused on port 5432",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "docker",
        "difficulty": "medium",
    },
    {
        "query_id": 33,
        "query": "bash: ./run.sh: Permission denied after chmod +x — filesystem ACL issue",
        "expected_problem_class": "permission_denied",
        "min_relevant_hits": 1,
        "category": "bash",
        "difficulty": "easy",
    },
    {
        "query_id": 34,
        "query": "git rebase -i freezes or hangs waiting for editor to open",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "git",
        "difficulty": "hard",
    },
    {
        "query_id": 35,
        "query": "docker build step hangs indefinitely on COPY command with large vendor folder",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "docker",
        "difficulty": "hard",
    },
    # === Category 4: Framework-specific (Flask, pytest, etc.) (10 queries) ===
    {
        "query_id": 36,
        "query": "Flask app fails with 'FSADatetimeRepresentationWarning: datetime not naive' in logs",
        "expected_problem_class": "type_mismatch",
        "min_relevant_hits": 1,
        "category": "flask",
        "difficulty": "medium",
    },
    {
        "query_id": 37,
        "query": "pytest raises AttributeError: 'NoneType' object has no attribute 'assertEqual' in conftest",
        "expected_problem_class": "null_pointer_chain",
        "min_relevant_hits": 1,
        "category": "pytest",
        "difficulty": "medium",
    },
    {
        "query_id": 38,
        "query": "Flask blueprints: ImportError: cannot import name 'auth_bp' from '__main__'",
        "expected_problem_class": "import_cycle",
        "min_relevant_hits": 1,
        "category": "flask",
        "difficulty": "medium",
    },
    {
        "query_id": 39,
        "query": "pytest fixture 'client' not found — scope conflict with conftest.py",
        "expected_problem_class": "missing_dependency",
        "min_relevant_hits": 1,
        "category": "pytest",
        "difficulty": "easy",
    },
    {
        "query_id": 40,
        "query": "Celery task hangs with TimeoutError: SoftTimeLimitExceeded after 300 seconds",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "celery",
        "difficulty": "hard",
    },
    {
        "query_id": 41,
        "query": "SQLAlchemy: AttributeError: 'NoneType' object has no attribute 'query' on model class",
        "expected_problem_class": "null_pointer_chain",
        "min_relevant_hits": 1,
        "category": "sqlalchemy",
        "difficulty": "medium",
    },
    {
        "query_id": 42,
        "query": "FastAPI startup fails with 'ImproperlyConfigured: instance before app' error",
        "expected_problem_class": "configuration_error",
        "min_relevant_hits": 1,
        "category": "fastapi",
        "difficulty": "medium",
    },
    {
        "query_id": 43,
        "query": "pytest ParametrizeWarning: arguments in fixture 'db' have wrong scope",
        "expected_problem_class": "schema_drift",
        "min_relevant_hits": 1,
        "category": "pytest",
        "difficulty": "hard",
    },
    {
        "query_id": 44,
        "query": "Redis connection refused error during Celery task execution in production",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "celery",
        "difficulty": "medium",
    },
    {
        "query_id": 45,
        "query": "Flask: OperationalError: (psycopg2.OperationalError) could not connect to server",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "flask",
        "difficulty": "easy",
    },
    # === Category 5: Edge cases (5 queries) ===
    {
        "query_id": 46,
        "query": "Race condition: concurrent requests to /api/update cause double-charge in Stripe integration",
        "expected_problem_class": "race_condition",
        "min_relevant_hits": 1,
        "category": "race",
        "difficulty": "hard",
    },
    {
        "query_id": 47,
        "query": "TimeoutError: requests library hanging on API call without timeout parameter",
        "expected_problem_class": "timeout_hang",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "easy",
    },
    {
        "query_id": 48,
        "query": "PermissionError: [Errno 13] Permission denied on /root/.ssh/authorized_keys for SSH key deployment",
        "expected_problem_class": "permission_denied",
        "min_relevant_hits": 1,
        "category": "bash",
        "difficulty": "easy",
    },
    {
        "query_id": 49,
        "query": "Race condition in multiprocessing: manager.list() shows stale data between processes",
        "expected_problem_class": "race_condition",
        "min_relevant_hits": 1,
        "category": "python",
        "difficulty": "hard",
    },
    {
        "query_id": 50,
        "query": "Concurrent database writes fail with deadlock detected in PostgreSQL under high load",
        "expected_problem_class": "race_condition",
        "min_relevant_hits": 1,
        "category": "database",
        "difficulty": "hard",
    },
]


def main() -> None:
    output_path = pathlib.Path(__file__).parent / "error_corpus.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in CORPUS:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Wrote {len(CORPUS)} benchmark queries to {output_path}")
    print(f"  G1 queries (min_relevant_hits=1): {sum(1 for e in CORPUS if e['min_relevant_hits'] == 1)}")
    print(f"  G2 queries (min_relevant_hits=5): {sum(1 for e in CORPUS if e['min_relevant_hits'] == 5)}")
    print(f"  Category breakdown:")
    categories = {}
    for e in CORPUS:
        categories[e["category"]] = categories.get(e["category"], 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"    {cat}: {count}")


if __name__ == "__main__":
    main()
