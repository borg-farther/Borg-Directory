"""
Tests for the borg_observe short-form wrapper.

Target: the monkey-patch wrapper at ~L3087 of borg/integrations/mcp_server.py
that redefines borg_observe to add short-form output and deterministic
hard-stop injection over the original at ~L1679.

Covers confirmed issues 1-5 from the 2026-04-24 audit, plus two
additional findings (L3113 empty separator, L3089 double rebuild).

Uses unittest.mock.patch.object to stub _borg_observe_orig so the wrapper's
own logic is exercised without invoking the heavy DB/embedding stack.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.integrations import mcp_server


# ============================================================================
# Helpers
# ============================================================================


def _call_wrapper(orig_return, task, short=True, context=""):
    """Call the wrapper with _borg_observe_orig stubbed to return orig_return.

    The stub does not touch _maybe_rebuild_index — that side-effect is
    exercised by the dedicated rebuild-count tests below.
    """
    def stub(**kwargs):
        return orig_return
    with patch.object(mcp_server, "_borg_observe_orig", stub):
        return mcp_server.borg_observe(task=task, context=context, short=short)


# ============================================================================
# Issue 1 + Issue 2: hard-stop loop reachability and all-patterns coverage
# ============================================================================


class TestHardStopReachability:
    """Issue 1: _HARD_STOPS loop was unreachable whenever result had an
    ACTION: line (the common case). Fix must make the loop reachable in
    the relevant path.

    Issue 2: `return result[:200]` indented inside the for loop meant
    only the first pattern was checked. Fix must iterate every pattern.
    """

    def test_sudo_npm_first_pattern_injects_stop(self):
        # First key in _HARD_STOPS — passes even with Issue 2 present,
        # fails under Issue 1 if ACTION line blocks loop entry.
        result = _call_wrapper(
            "no action header here", task="please run sudo npm install foo"
        )
        assert "STOP" in result
        assert "npm" in result.lower()

    def test_chmod_777_last_pattern_injects_stop(self):
        # Last key in _HARD_STOPS dict. Under Issue 2, only the first key
        # gets checked, so this pattern never matches. Must fail pre-fix.
        result = _call_wrapper(
            "no action header here", task="chmod 777 /app please"
        )
        assert "STOP" in result
        assert "777" in result or "security risk" in result.lower()

    def test_cast_any_middle_pattern_injects_stop(self):
        # Middle key — also dead under Issue 2.
        result = _call_wrapper(
            "no action header here", task="let me cast it as any"
        )
        assert "STOP" in result
        assert "any" in result.lower()

    def test_hard_stop_reachable_when_result_has_action_line(self):
        # Issue 1 scenario: orig returned an ACTION line, so the wrapper
        # used to early-return at the `if action:` branch and never
        # reached the hard-stop block. After fix, a matching task should
        # still trigger the STOP injection regardless of whether the
        # stub response contains ACTION: / CONFIDENCE: lines.
        result = _call_wrapper(
            "ACTION: install foo\nCONFIDENCE: 0.8",
            task="sudo pip install requests",
        )
        assert "STOP" in result, (
            "hard-stop unreachable when result contains ACTION: line"
        )


# ============================================================================
# L3113 additional finding: empty-string separator
# ============================================================================


class TestSeparatorIsVisible:
    """L3113 `''*50` evaluates to ''. The STOP banner and the original
    result have no visible separation. Fix must produce a non-empty
    separator (e.g., '-'*50)."""

    def test_visible_separator_between_stop_and_result(self):
        # Use short=False so the body survives; short-form deliberately
        # collapses to the STOP line alone.
        result = _call_wrapper(
            "no action header\nbody of original response",
            task="sudo pip install x",
            short=False,
        )
        lines = result.split("\n")
        stop_idx = next(
            (i for i, l in enumerate(lines) if "STOP" in l), None
        )
        body_idx = next(
            (i for i, l in enumerate(lines)
             if "body of original response" in l), None
        )
        assert stop_idx is not None, "STOP banner not injected"
        assert body_idx is not None, "original body missing"
        assert body_idx > stop_idx
        between = lines[stop_idx + 1:body_idx]
        assert any(
            l.strip() for l in between
        ), f"no visible separator between STOP and result; lines={between!r}"


# ============================================================================
# Issue 3: short parameter propagation
# ============================================================================


class TestShortParamPropagation:
    """Issue 3: wrapper hardcoded short=False when calling _borg_observe_orig,
    discarding caller intent. Fix must forward the caller's `short` value."""

    def test_short_true_propagates_to_orig(self):
        captured = {}

        def stub(**kwargs):
            captured["short"] = kwargs.get("short")
            return "ACTION: x\nCONFIDENCE: 0.9"

        with patch.object(mcp_server, "_borg_observe_orig", stub):
            mcp_server.borg_observe(task="t", short=True)
        assert captured.get("short") is True, (
            f"wrapper dropped short=True; orig got {captured.get('short')!r}"
        )

    def test_short_false_propagates_to_orig(self):
        captured = {}

        def stub(**kwargs):
            captured["short"] = kwargs.get("short")
            return "long content"

        with patch.object(mcp_server, "_borg_observe_orig", stub):
            mcp_server.borg_observe(task="t", short=False)
        assert captured.get("short") is False


# ============================================================================
# L3089 additional finding: double _maybe_rebuild_index call
# ============================================================================


class TestNoDoubleRebuild:
    """Wrapper calls _maybe_rebuild_index() at L3089 and the delegation to
    the original at L1680 calls it again. Fix: wrapper should not call it
    directly — the original will."""

    def test_wrapper_does_not_call_rebuild_itself(self):
        call_count = {"n": 0}

        def counting_rebuild():
            call_count["n"] += 1

        # Stub orig to NOT touch _maybe_rebuild_index so we isolate the
        # wrapper's own call.
        def stub(**kwargs):
            return "ACTION: x"

        with patch.object(mcp_server, "_maybe_rebuild_index", counting_rebuild), \
                patch.object(mcp_server, "_borg_observe_orig", stub):
            mcp_server.borg_observe(task="t", short=True)
        assert call_count["n"] == 0, (
            f"wrapper called _maybe_rebuild_index {call_count['n']} time(s); "
            "the delegation to orig already calls it."
        )


# ============================================================================
# Issue 4: wrapper has import-time test coverage
# ============================================================================


class TestWrapperSurface:
    """Issue 4: no prior test coverage for the wrapper. This file is the
    remediation. Smoke-check the wrapper is importable and keeps its
    advertised signature."""

    def test_wrapper_is_callable(self):
        import inspect
        assert callable(mcp_server.borg_observe)
        sig = inspect.signature(mcp_server.borg_observe)
        assert "short" in sig.parameters
        assert sig.parameters["short"].default is False

    def test_wrapper_delegates_to_orig_module_attr(self):
        # _borg_observe_orig must still be bound to the original function
        # object, not accidentally shadowed.
        assert hasattr(mcp_server, "_borg_observe_orig")
        assert callable(mcp_server._borg_observe_orig)


# ============================================================================
# Issue 5: stale build/lib copy removed
# ============================================================================


class TestNoStaleBuildArtifact:
    """Issue 5: build/lib/borg/integrations/mcp_server.py is a setuptools
    build artifact that had drifted to carry the same buggy wrapper. It
    should not live in the source tree."""

    def test_no_stale_build_lib_mcp_server(self):
        stale = (
            Path(__file__).parent.parent.parent
            / "build" / "lib" / "borg" / "integrations" / "mcp_server.py"
        )
        assert not stale.exists(), (
            f"Stale build artifact at {stale} — remove build/ directory"
        )
