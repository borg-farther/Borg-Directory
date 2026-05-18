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
    _ANTI_SIGNATURES,
    _anti_signature_blocks,
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


# ----------------------------------------------------------------------
# v3.2.3 anti_signatures — kill the 8 residual false-confident rows
# ----------------------------------------------------------------------
#
# Each ANTI_SIGNATURE_TARGETS row is pulled from
#   docs/20260408-0623_classifier_prd/baseline_results.csv
# where is_false_confident=1 on the v3.2.2 wheel. After the v3.2.3 patch
# the classifier must NOT return the old wrong answer — either the right
# answer (e0009 flips to import_cycle) or None (all the others, since the
# correct class does not have a pack yet).
#
# e0005 (ImportError: cannot import name 'soft_unicode' from 'markupsafe')
# is intentionally NOT in this list because its text is textually
# indistinguishable from the existing Python PYTHON_REGRESSION_FIXTURES
# row ("ImportError: cannot import name 'foo' from 'bar'" → import_cycle).
# See v323_fc_analysis.md §e0005 residual for the explanation. Phase 2
# confidence scoring + unique_to_class signals will fix it.

ANTI_SIGNATURE_TARGETS = [
    # (id, text, v3.2.2_wrong_prediction, v3.2.3_expected)
    (
        "e0009",
        "ImportError: cannot import name 'User' from partially initialized module "
        "'app.models' (most likely due to a circular import)",
        "circular_dependency",
        "import_cycle",
    ),
    (
        "e0036",
        "TypeError: Cannot read property 'length' of null",
        "type_mismatch",
        None,
    ),
    (
        "e0042",
        "TypeError: foo.map is not a function",
        "type_mismatch",
        None,
    ),
    (
        "e0043",
        "TypeError: Assignment to constant variable.",
        "type_mismatch",
        None,
    ),
    (
        "e0044",
        "TypeError: Converting circular structure to JSON",
        "circular_dependency",
        None,
    ),
    (
        "e0122",
        "import cycle not allowed\npackage foo imports bar imports foo",
        "import_cycle",
        None,
    ),
    (
        "e0157",
        'Readiness probe failed: Get "http://10.0.0.5:8080/health": '
        "dial tcp 10.0.0.5:8080: connect: connection refused",
        "timeout_hang",
        None,
    ),
]


@pytest.mark.parametrize(
    "corpus_id,text,v322_wrong,v323_expected",
    ANTI_SIGNATURE_TARGETS,
    ids=[row[0] for row in ANTI_SIGNATURE_TARGETS],
)
def test_anti_signature_blocks_corpus_row(
    corpus_id, text, v322_wrong, v323_expected
):
    """Each residual false-confident row is killed by the v3.2.3 patch."""
    result = classify_error(text)
    assert result != v322_wrong, (
        f"{corpus_id}: v3.2.3 regression — still returns the v3.2.2 wrong "
        f"answer {v322_wrong!r}. Check _ANTI_SIGNATURES in pack_taxonomy.py."
    )
    assert result == v323_expected, (
        f"{corpus_id}: got {result!r}, expected {v323_expected!r}"
    )


@pytest.mark.parametrize("err,expected", PYTHON_REGRESSION_FIXTURES)
def test_anti_signatures_do_not_break_python_fixtures(err, expected):
    """v3.2.3 belt+suspenders: none of the 10 Python fixtures match ANY
    anti_signature. This is orthogonal to test_python_django_recall_unchanged
    above — that test checks the end-to-end classify_error() result; this
    test walks the anti_signature dict directly to prove the regexes are
    disjoint from every Python positive."""
    for problem_class, patterns in _ANTI_SIGNATURES.items():
        for pat in patterns:
            assert not pat.search(err), (
                f"Python fixture {err!r} matches v3.2.3 anti_signature "
                f"{pat.pattern!r} for class {problem_class!r} — this would "
                f"suppress a Python positive."
            )
    # Sanity: classify_error still returns the expected Python class.
    assert classify_error(err) == expected


def test_anti_signature_blocks_helper_direct():
    """Unit test for _anti_signature_blocks() — covers the Dict.get fallback,
    empty-string input, None input, and a positive hit."""
    # None / empty input → always False
    assert _anti_signature_blocks("", "type_mismatch") is False
    assert _anti_signature_blocks(None, "type_mismatch") is False  # type: ignore[arg-type]
    # Unknown class → False (Dict.get fallback)
    assert (
        _anti_signature_blocks("TypeError: something", "nonexistent_class") is False
    )
    # Positive hits
    assert _anti_signature_blocks(
        "TypeError: foo.map is not a function", "type_mismatch"
    ) is True
    assert _anti_signature_blocks(
        "import cycle not allowed\npackage foo", "import_cycle"
    ) is True
    assert _anti_signature_blocks(
        "Readiness probe failed: Get http://x", "timeout_hang"
    ) is True
    # Negative on correct class (no cross-talk)
    assert _anti_signature_blocks(
        "TimeoutError: Connection timed out", "timeout_hang"
    ) is False


def test_corpus_false_confident_count_under_budget():
    """Integration test: the full 173-row corpus runs through classify_error
    and the residual false-confident count must be <= 2 after v3.2.3. The
    PRD budget is 'target 0–2 residual' because some labels are ambiguous
    (see v323_fc_analysis.md §e0005)."""
    import json
    from pathlib import Path

    corpus_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "20260408-0623_classifier_prd"
        / "error_corpus.jsonl"
    )
    if not corpus_path.exists():
        pytest.skip(f"corpus file not shipped with wheel: {corpus_path}")

    rows = [json.loads(line) for line in corpus_path.read_text().splitlines() if line.strip()]
    assert len(rows) == 173, f"Expected 173 corpus rows, got {len(rows)}"

    n_fc = 0
    fc_ids: list[str] = []
    for r in rows:
        expected = r["expected_problem_class"]
        actual = classify_error(r["text"])
        if actual is not None and actual != expected:
            n_fc += 1
            fc_ids.append(r["id"])

    assert n_fc <= 2, (
        f"v3.2.3 regression: {n_fc} false-confident rows on the 173-row "
        f"corpus (budget is <= 2). IDs: {fc_ids}"
    )


def test_anti_signature_no_catastrophic_backtracking():
    """Adversarial: a 10K-char input must not hang the regex engine.
    Phase-4 review gate from the v3.2.3 adversarial checklist."""
    import time

    adversarial_strings = [
        "TypeError: " + "Cannot read property " * 500,
        "a" * 10000,
        "cannot import name " * 500 + "partially initialized module",
        "Readiness probe failed" + " " * 5000 + "end",
    ]
    for s in adversarial_strings:
        start = time.monotonic()
        classify_error(s)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, (
            f"classify_error took {elapsed:.2f}s on a {len(s)}-char input — "
            f"possible catastrophic backtracking in _ANTI_SIGNATURES"
        )
