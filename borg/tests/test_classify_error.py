"""
Tests for borg.core.pack_taxonomy.classify_error / debug_error.

Phase 0 of the multi-language classifier (v3.2.2):
  - Bare ("Error", "schema_drift") fallback removed.
  - Non-Python locking signals refuse to answer with a Python pack.
  - Python/Django coverage is unchanged.

Reference:
  /root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/SYNTHESIS_AND_ACTION_PLAN.md
  /root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/RED_TEAM_REVIEW.md (CRITICAL-1..6, HIGH-1..11)
"""
from __future__ import annotations

import pytest

from borg.core.pack_taxonomy import (
    PROBLEM_CLASSES,
    _detect_language_quick,
    classify_error,
    debug_error,
)


# ----------------------------------------------------------------------
# CRITICAL: the four canonical dogfood reproductions
# ----------------------------------------------------------------------

DOGFOOD_REPRODUCTIONS = [
    # (input, expected_classify_error_result, expected_detected_language)
    ("error[E0382]: borrow of moved value: `x`", None, "rust"),
    ("Error: ENOSPC: no space left on device", None, "docker"),
    ("TS2322: Type 'string' is not assignable to type 'number'", None, "typescript"),
    ("Hydration failed because the initial UI does not match what was rendered on the server", None, "react"),
]


@pytest.mark.parametrize("error,expected_class,expected_lang", DOGFOOD_REPRODUCTIONS)
def test_dogfood_reproductions_no_python_answer(error, expected_class, expected_lang):
    """The 4 canonical reproductions from CONTEXT_DOSSIER must NOT return a Python pack."""
    assert classify_error(error) == expected_class
    assert _detect_language_quick(error) == expected_lang


@pytest.mark.parametrize("error,expected_class,expected_lang", DOGFOOD_REPRODUCTIONS)
def test_dogfood_reproductions_debug_error_unknown(error, expected_class, expected_lang):
    """debug_error() must return the UnknownMatch block, not Django migration advice."""
    output = debug_error(error)
    assert "[unknown]" in output
    assert "schema_drift" not in output or "Known Python/Django problem classes" in output
    assert "manage.py makemigrations" not in output
    assert expected_lang in output


# ----------------------------------------------------------------------
# CRITICAL-1: bare "Error" no longer routes to schema_drift
# ----------------------------------------------------------------------

GENERIC_NON_PYTHON_ERRORS = [
    'panic: runtime error: invalid memory address or nil pointer dereference',
    'goroutine 17 [running]:',
    'CrashLoopBackOff',
    'ImagePullBackOff',
    'OOMKilled',
    'Cannot read properties of undefined (reading "map")',
    "Cannot read properties of null (reading 'id')",
    'failed to solve: rpc error: code = Unknown',
    'COPY failed: file not found',
    'manifest unknown',
]


@pytest.mark.parametrize("err", GENERIC_NON_PYTHON_ERRORS)
def test_generic_error_substring_no_longer_poisons(err):
    """Inputs containing the substring 'error' but not Python should NOT match schema_drift."""
    result = classify_error(err)
    # In v3.2.1 these all returned 'schema_drift' via the bare ("Error",...) fallback.
    assert result != "schema_drift", (
        f"Regression: {err!r} → schema_drift. "
        "The bare ('Error', 'schema_drift') fallback at pack_taxonomy.py:83 must stay deleted."
    )


# ----------------------------------------------------------------------
# Python/Django backwards compat — recall must NOT regress
# ----------------------------------------------------------------------

PYTHON_REGRESSION_FIXTURES = [
    # (input, expected_problem_class)
    ("ModuleNotFoundError: No module named 'cv2'", "missing_dependency"),
    ("ImportError: cannot import name 'foo' from 'bar'", "import_cycle"),
    ("django.db.utils.OperationalError: no such column: app_user.email", "schema_drift"),
    ("django.db.utils.IntegrityError: FOREIGN KEY constraint failed", "missing_foreign_key"),
    ("ImproperlyConfigured: SECRET_KEY must not be empty", "configuration_error"),
    ("PermissionError: [Errno 13] Permission denied: '/etc/passwd'", "permission_denied"),
    ("TimeoutError: [Errno 110] Connection timed out", "timeout_hang"),
    ("AttributeError: 'NoneType' object has no attribute 'get'", "null_pointer_chain"),
    ("django.db.migrations.exceptions.InconsistentMigrationHistory: applied migrations", "migration_state_desync"),
    ("RuntimeError: dictionary changed size during iteration", "race_condition"),
]


@pytest.mark.parametrize("err,expected", PYTHON_REGRESSION_FIXTURES)
def test_python_django_recall_unchanged(err, expected):
    """Python/Django recall must not regress — Phase 0 is additive-deletion only."""
    assert classify_error(err) == expected, (
        f"Python/Django regression on {err!r}: got {classify_error(err)!r}, expected {expected!r}"
    )


# ----------------------------------------------------------------------
# Edge cases that previously hit the bare-Error trap
# ----------------------------------------------------------------------

@pytest.mark.parametrize("err", [
    "",
    None,
    "   ",
    "no errors at all",
])
def test_empty_and_trivial_inputs(err):
    """Empty / whitespace / null inputs return None instead of any class."""
    assert classify_error(err) is None


def test_detect_language_quick_python_lock_wins():
    """Polyglot logs that contain Python locking signals stay on the Python path."""
    polyglot = (
        "Traceback (most recent call last):\n"
        '  File "manage.py", line 22, in <module>\n'
        "    main()\n"
        "subprocess.CalledProcessError: cargo build failed with error[E0382]"
    )
    # Even though E0382 fires the rust signal, the Traceback line keeps it Python.
    assert _detect_language_quick(polyglot) is None


def test_detect_language_quick_returns_known_languages_only():
    """Detector should only return language strings from the known set."""
    known = {"rust", "go", "javascript", "typescript", "react", "docker", "kubernetes"}
    samples = [
        "error[E0277]: the trait bound `T: Foo` is not satisfied",
        "panic: runtime error: index out of range [3] with length 2",
        'TypeError: Cannot read properties of undefined (reading "map")',
        "TS2532: Object is possibly 'undefined'.",
        "Hydration failed because the initial UI does not match",
        "ENOSPC: no space left on device",
        "Pod foo has CrashLoopBackOff status",
    ]
    for s in samples:
        lang = _detect_language_quick(s)
        assert lang in known, f"{s!r} → {lang!r}"


def test_problem_classes_unchanged():
    """The 12 Python/Django problem_classes must stay stable across the v3.2.2 patch."""
    expected = {
        "circular_dependency",
        "null_pointer_chain",
        "missing_foreign_key",
        "migration_state_desync",
        "import_cycle",
        "race_condition",
        "configuration_error",
        "type_mismatch",
        "missing_dependency",
        "timeout_hang",
        "schema_drift",
        "permission_denied",
    }
    assert set(PROBLEM_CLASSES) == expected
