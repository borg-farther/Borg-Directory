"""Human-language layer for firing visibility (E-014).

Every place Borg fires must produce ONE deterministic, honest line a human can
understand in the moment — the ``human_summary``. The live-session audit
(evidence E-014) showed that without a line *designed to survive relay*, the
agent decides whether the human ever learns Borg fired; with borg_suggest the
human never learned Borg caught their stuck agent at all.

Formula (binding design spec):
    "🛟 Borg: " + [event in human words] + [trust basis]
                + [counterfactual when trigger=after_n_failures]
    ≤ 140 characters. Deterministic. No savings claims. No internal vocabulary.

Vocabulary translation is mandatory for every human-facing line:
    matched            -> "found a known fix"
    no_confident_match -> "nothing reliable known — won't guess"
    seed_corpus        -> "Borg's starter library"
    your_traces        -> "your own past errors"
    tested             -> "tested"
    observed           -> "reported working"

Push/pull rule: hits and stuck-catches may be pushed into live channels;
misses are PULL-only (status / direct CLI) and must never be pushed into an
agent transcript.
"""

from __future__ import annotations

MAX_HUMAN_SUMMARY_CHARS = 140

_PROVENANCE_HUMAN = {
    # receipt vocabulary
    "seed_corpus": "Borg's starter library",
    "your_traces": "your own past errors",
    "collective": "the shared fix library",
    "pack_suggestion": "Borg's workflow library",
    # raw evidence-source vocabulary (rescue packets)
    "seed_pack": "Borg's starter library",
    "trace": "your own past errors",
    "local_trace": "your own past errors",
    "local_trace_db": "your own past errors",
    "atom": "the shared fix library",
    "federated": "the shared fix library",
}

_CONFIDENCE_HUMAN = {
    "tested": "tested",
    "observed": "reported working",
    "inferred": "unverified",
    "suggested": "reported working",
}


def humanize_problem_class(problem_class: str) -> str:
    """missing_dependency -> 'missing dependency' (never show slugs to humans)."""
    text = (problem_class or "").strip().replace("_", " ").replace("-", " ")
    return text or "this kind of"


def humanize_confidence(confidence: str) -> str:
    return _CONFIDENCE_HUMAN.get((confidence or "").strip().lower(), "unverified")


def humanize_provenance(provenance: str) -> str:
    return _PROVENANCE_HUMAN.get((provenance or "").strip().lower(), "")


def _clamp(line: str) -> str:
    if len(line) <= MAX_HUMAN_SUMMARY_CHARS:
        return line
    return line[: MAX_HUMAN_SUMMARY_CHARS - 1].rstrip() + "…"


def rescue_human_summary(
    status: str,
    problem_class: str = "",
    confidence: str = "",
    provenance: str = "",
    *,
    failure_count: int = 0,
) -> str:
    """The one line a human must see when a rescue fires."""
    if status == "matched":
        klass = humanize_problem_class(problem_class)
        trust = humanize_confidence(confidence)
        if failure_count >= 2:
            line = (
                f"🛟 Borg: your agent was stuck ({failure_count} failed attempts) — "
                f"found a known, {trust} fix for this {klass} error."
            )
        else:
            source = humanize_provenance(provenance)
            suffix = f", from {source}." if source else "."
            line = f"🛟 Borg: found a known fix for this {klass} error — {trust}{suffix}"
        return _clamp(line)
    # Miss: honest, PULL-only — callers must never push this into a transcript.
    return _clamp("🛟 Borg: nothing reliable known for this error — won't guess.")


def suggestion_human_summary(pack_name: str, failure_count: int) -> str:
    """The caught-after-stuck line for the suggest path (only after the
    relevance gate passed — a gated-out suggestion produces NO summary)."""
    n = max(2, int(failure_count or 0))
    pack = (pack_name or "a known workflow").replace("-", " ").replace("_", " ")
    return _clamp(
        f"🛟 Borg: your agent was stuck ({n} failed attempts) — "
        f"a relevant known workflow may help: {pack}."
    )


RELAY_INSTRUCTION = (
    "Relay human_summary to the user VERBATIM as the first line of your reply — "
    "it is the only way they learn Borg fired."
)
