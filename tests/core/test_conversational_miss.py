"""Conversational-miss detection (issue #9 mitigation).

A user who *describes* an error in prose ("can't find a module called django")
must not get a SILENT zero. The rescue stays honest (no_confident_match — never
fabricates a match) but now tells the user how to get a hit, and when a module
is named in the prose, hands them the exact literal command that will match.
"""

from __future__ import annotations

from borg.core.rescue import (
    rescue,
    _looks_conversational,
    _module_from_prose,
    _has_error_signature,
)


def _has_conv_state(result) -> bool:
    return any(s.get("code") == "CONVERSATIONAL_INPUT_LIKELY" for s in result.fallback_states)


# --- the detector ----------------------------------------------------------

def test_prose_describing_an_error_is_conversational():
    assert _looks_conversational("my server won't start, it can't find a module called django")
    assert _looks_conversational("python can't seem to import flask even though I installed it")


def test_literal_error_text_is_not_conversational():
    assert not _looks_conversational("ModuleNotFoundError: No module named 'django'")
    assert not _looks_conversational("TypeError: unsupported operand type(s) for +: 'int' and 'str'")
    assert not _looks_conversational("Traceback (most recent call last): File x.py, line 3")


def test_bare_tokens_are_not_misread_as_conversational():
    # No conversational marker -> not flagged, even with no error signature.
    assert not _looks_conversational("ECONNREFUSED 127.0.0.1:5432")
    assert not _looks_conversational("segfault")


def test_error_signature_detection():
    assert _has_error_signature("ModuleNotFoundError: x")
    assert _has_error_signature("see app.py line 42")
    assert not _has_error_signature("my app is broken somehow")


def test_module_extraction_from_prose():
    assert _module_from_prose("can't find a module called django") == "django"
    assert _module_from_prose("python can't import flask") == "flask"
    assert _module_from_prose("the build is just slow") is None


# --- the rescue behavior ---------------------------------------------------

def test_conversational_module_miss_suggests_the_literal_form_that_matches():
    r = rescue("my server won't start, it can't find a module called django", show_guidance=False)
    assert r.status == "no_confident_match"          # still honest
    assert _has_conv_state(r)
    assert r.next_command == 'borg rescue "ModuleNotFoundError: No module named \'django\'"'
    # and that suggested command actually produces a match (no dead-end advice)
    followup = rescue("ModuleNotFoundError: No module named 'django'", show_guidance=False)
    assert followup.status == "matched"
    assert followup.problem_class == "missing_dependency"


def test_conversational_nonmodule_miss_asks_for_the_literal_error():
    r = rescue("my django migrations are out of order and the db is in a weird state", show_guidance=False)
    assert r.status == "no_confident_match"
    assert _has_conv_state(r)
    assert "paste the exact error" in r.next_command.lower() or "traceback" in r.next_command.lower()


def test_conversational_miss_never_fabricates_and_stays_pull_only():
    r = rescue("python can't seem to import flask even though I installed it", show_guidance=False)
    assert r.success is False
    assert r.status == "no_confident_match"
    # The pushed human moment-line stays the honest miss line (push/pull rule):
    # the conversational hint lives in action/fallback_states/next_command (pull),
    # never in a fabricated "found a fix" summary.
    assert "found a known fix" not in r.human_summary
    assert "won't guess" in r.human_summary


def test_literal_miss_outside_coverage_is_not_flagged_conversational():
    # A genuine literal error with no pack is a coverage gap, not a phrasing gap.
    r = rescue("ECONNREFUSED 127.0.0.1:6379 redis", show_guidance=False)
    assert not _has_conv_state(r)
