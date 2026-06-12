"""Firing-visibility human-language contract (E-014): one deterministic,
honest, <=140-char line in human vocabulary every time Borg fires."""

from __future__ import annotations

import json
import sys

import pytest

from borg.core.human_language import (
    MAX_HUMAN_SUMMARY_CHARS,
    RELAY_INSTRUCTION,
    rescue_human_summary,
    suggestion_human_summary,
)

_INTERNAL_TERMS = (
    "seed_corpus", "seed_pack", "your_traces", "no_confident_match",
    "problem_class", "missing_dependency", "_",
)


def test_matched_summary_spec_example_shape():
    line = rescue_human_summary(
        "matched", "missing_dependency", "tested", "seed_pack", failure_count=2
    )
    assert line == (
        "🛟 Borg: your agent was stuck (2 failed attempts) — "
        "found a known, tested fix for this missing dependency error."
    )
    assert len(line) <= MAX_HUMAN_SUMMARY_CHARS


def test_matched_summary_without_stuck_names_source():
    line = rescue_human_summary("matched", "missing_dependency", "tested", "seed_pack")
    assert line == (
        "🛟 Borg: found a known fix for this missing dependency error — "
        "tested, from Borg's starter library."
    )


def test_vocabulary_translation_is_mandatory():
    for status, args in [
        ("matched", ("type_mismatch", "observed", "trace")),
        ("matched", ("schema_drift", "tested", "seed_pack")),
        ("no_confident_match", ("", "", "")),
    ]:
        line = rescue_human_summary(status, *args)
        for term in _INTERNAL_TERMS:
            assert term not in line, f"internal term {term!r} leaked into: {line}"


def test_miss_summary_is_honest_and_never_guessy():
    line = rescue_human_summary("no_confident_match")
    assert "nothing reliable known" in line
    assert "won't guess" in line


def test_observed_tier_translates_to_reported_working():
    line = rescue_human_summary("matched", "type_mismatch", "observed", "trace")
    assert "reported working" in line
    assert "your own past errors" in line


def test_suggestion_summary_leads_with_caught_after_stuck():
    line = suggestion_human_summary("django-migration-state", 3)
    assert line.startswith("🛟 Borg: your agent was stuck (3 failed attempts)")
    assert "django migration state" in line
    assert len(line) <= MAX_HUMAN_SUMMARY_CHARS


def test_summaries_deterministic_and_clamped():
    a = rescue_human_summary("matched", "x" * 300, "tested", "seed_pack")
    b = rescue_human_summary("matched", "x" * 300, "tested", "seed_pack")
    assert a == b
    assert len(a) <= MAX_HUMAN_SUMMARY_CHARS


def test_no_savings_claims_anywhere():
    for line in [
        rescue_human_summary("matched", "missing_dependency", "tested", "seed_pack", failure_count=4),
        suggestion_human_summary("pack", 2),
        rescue_human_summary("no_confident_match"),
    ]:
        for banned in ("saved", "minutes", "tokens", "%", "faster"):
            assert banned not in line.lower()


# ------------------------------------------------------ packet/CLI integration

def test_rescue_packet_carries_human_summary_and_relay_instruction():
    from borg.core.rescue import rescue

    result = rescue("ModuleNotFoundError: No module named flask", source="test", show_guidance=False)
    assert result.human_summary.startswith("🛟 Borg: found a known fix")
    assert RELAY_INSTRUCTION in result.agent_instruction
    assert result.human_summary in result.agent_instruction  # relayable in-band
    # The defeating instruction from the E-014 audit must be gone.
    assert "only surface Borg when" not in result.agent_instruction


def test_miss_packet_has_pull_only_summary():
    from borg.core.rescue import rescue

    result = rescue("how do I get better at python?", source="test", show_guidance=False)
    assert "won't guess" in result.human_summary


def test_cli_rescue_prints_moment_line_first(tmp_path, monkeypatch, capsys):
    from borg.cli import main

    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["borg", "rescue", "ModuleNotFoundError: No module named flask", "--short"])
    main()
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("🛟 Borg: found a known fix")


def test_status_reads_as_receipt(tmp_path, monkeypatch, capsys):
    from borg.cli import main
    from borg.core.value_receipts import record_rescue_receipt

    record_rescue_receipt(
        {"status": "matched", "problem_class": "missing_dependency", "confidence": "tested",
         "evidence": {"source": "seed_pack"}},
        trigger="after_n_failures", trigger_n=2, error_text="x", borg_home=tmp_path,
    )
    record_rescue_receipt(
        {"status": "no_confident_match", "problem_class": "unknown", "confidence": "unknown",
         "evidence": {"source": "none"}},
        borg_home=tmp_path,
    )
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["borg", "status"])
    main()
    out = capsys.readouterr().out
    lines = [l.strip() for l in out.splitlines()]
    start = lines.index("Value on this machine (local rescue tally):")
    assert lines[start + 1] == "🛟 Caught your agent stuck: 1"
    assert lines[start + 2] == "Found known fixes: 1 of 2 errors"
    assert any("Borg's starter library=1" in l for l in lines)
    assert any("not claimed" in l for l in lines)  # honesty note stays


# --------------------------------------------------------------- MCP behavior

def test_mcp_rescue_packet_stuck_override(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    from borg.integrations import mcp_server

    payload = json.loads(mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask", show_guidance=False, failure_count=3,
    ))
    assert payload["human_summary"].startswith("🛟 Borg: your agent was stuck (3 failed attempts)")


def test_mcp_suggest_gates_irrelevant_pack_d019(tmp_path, monkeypatch):
    # The exact live failure from E-014: docker-no-space @0.993 for a Django
    # migration error must be REFUSED, not suggested, and record NO receipt.
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    from borg.integrations import mcp_server
    from borg.core.value_receipts import value_summary

    class _WrongV3:
        def search(self, context, task_context=None):
            return [{"name": "docker-no-space", "description": "Docker ran out of disk space",
                     "score": 0.993}]

    monkeypatch.setattr(mcp_server, "_get_borg_v3", lambda: _WrongV3())
    payload = json.loads(mcp_server.borg_suggest(
        context=("django.db.migrations.exceptions.InconsistentMigrationHistory: "
                 "Migration admin.0001_initial is applied before its dependency accounts.0001_initial"),
        failure_count=2,
    ))
    assert payload["has_suggestion"] is False
    assert payload["reason"] == "no_confident_suggestion"
    assert "human_summary" not in payload  # misses are pull-only, nothing to relay
    assert value_summary(borg_home=tmp_path)["rescues_fired"] == 0  # no fake receipt


def test_mcp_suggest_relevant_pack_leads_with_stuck_framing(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    from borg.integrations import mcp_server

    class _RightV3:
        def search(self, context, task_context=None):
            return [{"name": "django-migration-state",
                     "description": "Django migrations out of sync with database state",
                     "score": 0.9}]

    monkeypatch.setattr(mcp_server, "_get_borg_v3", lambda: _RightV3())
    payload = json.loads(mcp_server.borg_suggest(
        context=("django migration failing: InconsistentMigrationHistory admin.0001_initial "
                 "applied before its dependency"),
        failure_count=2,
    ))
    assert payload["has_suggestion"] is True
    assert payload["caught_after_stuck"] is True
    assert payload["human_summary"].startswith("🛟 Borg: your agent was stuck (2 failed attempts)")
    assert list(payload.keys())[1] == "human_summary"  # leads the packet
    assert "VERBATIM" in payload["agent_instruction"]


def test_tool_descriptions_direct_verbatim_relay():
    from borg.integrations import mcp_server

    for tool_name in ("borg_rescue", "error_lookup", "borg_suggest"):
        [descriptor] = [t for t in mcp_server.TOOLS if t["name"] == tool_name]
        assert "VERBATIM" in descriptor["description"], tool_name


# ----------------------------------------------------------------- notify push

def test_notify_unconfigured_is_silent_noop(monkeypatch):
    from borg.integrations import notify

    monkeypatch.delenv("BORG_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("BORG_TELEGRAM_CHAT_ID", raising=False)
    assert notify.push_human_summary("🛟 Borg: found a known fix …") is False


def test_notify_pushes_hits_and_refuses_misses(monkeypatch):
    from borg.integrations import notify

    sent = []

    class _Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(request, timeout):
        sent.append(json.loads(request.data.decode()))
        return _Resp()

    monkeypatch.setenv("BORG_TELEGRAM_BOT_TOKEN", "t0k")
    monkeypatch.setenv("BORG_TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(notify.urllib.request, "urlopen", fake_urlopen)

    assert notify.push_human_summary("🛟 Borg: your agent was stuck (2 failed attempts) — found a known, tested fix.") is True
    assert sent[0]["chat_id"] == "42"
    # Push/pull rule: a miss line is REFUSED even when configured.
    assert notify.push_human_summary("🛟 Borg: nothing reliable known for this error — won't guess.") is False
    assert len(sent) == 1


def test_hook_pushes_summary_on_hit(monkeypatch):
    from borg.integrations import agent_hook, notify

    pushed = []
    monkeypatch.setattr(
        "borg.integrations.notify.push_human_summary", lambda text: pushed.append(text) or True
    )
    monkeypatch.setattr(
        agent_hook, "check_for_suggestion",
        lambda **kw: json.dumps({
            "has_suggestion": True,
            "suggestion": "Borg pack available: systematic-debugging",
            "suggestions": [{"pack_name": "systematic-debugging"}],
        }),
    )
    out = agent_hook.borg_on_failure("stuck on flaky test", failure_count=2)
    assert out
    assert pushed and pushed[0].startswith("🛟 Borg: your agent was stuck (2 failed attempts)")


def test_hook_no_push_on_miss(monkeypatch):
    from borg.integrations import agent_hook

    pushed = []
    monkeypatch.setattr(
        "borg.integrations.notify.push_human_summary", lambda text: pushed.append(text) or True
    )
    monkeypatch.setattr(
        agent_hook, "check_for_suggestion", lambda **kw: json.dumps({"has_suggestion": False}),
    )
    assert agent_hook.borg_on_failure("nothing relevant", failure_count=2) is None
    assert pushed == []
