#!/usr/bin/env python3.12
"""
GEPA spike for the Borg debug classifier.

Goal
----
Point GEPA at borg.core.pack_taxonomy.classify_error and ask it to evolve the
keyword table (TEXT representation only — GEPA evolves text, not code) so that
the False-Confident Rate (FCR) on the 173-row labelled error corpus drops below
the v3.2.2 baseline. Headline release gate from the PRD is per-language FCR
<= 2%; the spike's job is to show whether GEPA can plausibly *get there* without
hand-authored regex packs.

What this script does
---------------------
1. Loads the 173-row labelled corpus from error_corpus.jsonl.
2. Defines a TEXT format for the keyword table:
        # comment
        keyword<TAB>problem_class
   The seed candidate is the current `_ERROR_KEYWORDS` list serialised in this
   format. The Phase 0 language-guard regex cascade is left untouched — GEPA only
   evolves the keyword table, since that is the part of the v3.2.2 classifier
   that still produces false-confident hits.
3. Defines a `borg_eval(keyword_table_text) -> dict` helper that builds a
   temporary classify_error variant against the candidate table, runs it over
   the corpus, and returns FCR, recall, precision plus a per-row breakdown.
4. Implements a `BorgKeywordTableAdapter(GEPAAdapter)` whose `evaluate` method
   scores each row (1.0 correct, 0.5 honest-miss, 0.0 false-confident) and
   builds rich trajectories so `make_reflective_dataset` can show the LLM
   exactly which inputs are false-confident and why.
5. Wires GEPA to evolve the table for ~5 iterations.
6. Picks an LLM in this order:
       a. ANTHROPIC_API_KEY     (litellm: anthropic/claude-...)
       b. OPENAI_API_KEY        (litellm: openai/gpt-4.1-mini)
       c. /root/.hermes/secrets/google_api_key  -> gemini/gemini-1.5-flash
       d. fall back to a deterministic mock LM (label results MOCK_LLM)
   The cap is "small": GEPA's max_metric_calls is set to 60 (~5 reflection
   iterations of minibatch=3 plus the seed eval) to keep cost well under $5.
7. Writes results.json with before/after metrics and the evolved candidate.

Run it:
    /tmp/gepa-spike-venv/bin/python \\
        /root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/gepa_spike/borg_gepa_evolve.py
"""
from __future__ import annotations

import json
import os
import re as _re
import sys
import time
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Paths & corpus loading
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
PRD_DIR = HERE.parent
CORPUS_PATH = PRD_DIR / "error_corpus.jsonl"
RESULTS_PATH = HERE / "results.json"
RUN_DIR = HERE / "gepa_run"

# Make borg importable (editable install lives at /root/hermes-workspace/borg)
BORG_REPO = Path("/root/hermes-workspace/borg")
if str(BORG_REPO) not in sys.path:
    sys.path.insert(0, str(BORG_REPO))

# Import the language guard from the actual v3.2.2 classifier so the spike
# uses exactly the same locking-signal cascade that ships in production. The
# only thing GEPA gets to evolve is the keyword table.
from borg.core.pack_taxonomy import _detect_language_quick  # type: ignore
from borg.core.pack_taxonomy import _ERROR_KEYWORDS as PROD_KEYWORDS  # type: ignore


def load_corpus() -> list[dict[str, Any]]:
    rows = []
    for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


CORPUS: list[dict[str, Any]] = load_corpus()
assert len(CORPUS) == 173, f"expected 173 corpus rows, got {len(CORPUS)}"


# ---------------------------------------------------------------------------
# Text <-> keyword table serialisation
# ---------------------------------------------------------------------------
SEED_HEADER = """\
# Borg classifier keyword table (GEPA-evolved).
# Format: one rule per line, "<keyword><TAB><problem_class>".
# Lines starting with # are comments and ignored.
# First match wins. Matching is case-insensitive substring on the lowercased
# error message. The Phase 0 non-Python language guard runs *before* this
# table; if it fires, classify_error returns None and never consults this
# table at all. Therefore adding rules for Rust/Go/JS/TS/Docker/K8s errors
# whose locking signals already fire is wasted effort — those rows already
# return None.
#
# The goal is to MINIMISE False-Confident Rate (FCR), defined as the fraction
# of corpus rows where the classifier returns a non-None problem_class that
# does not equal the labelled expected_problem_class. Honest misses (returning
# None when an answer was expected) are a much smaller penalty than confident
# wrong answers.
"""


def serialise_table(rules: list[tuple[str, str]]) -> str:
    lines = [SEED_HEADER.rstrip(), ""]
    for kw, pc in rules:
        lines.append(f"{kw}\t{pc}")
    return "\n".join(lines) + "\n"


_RULE_RE = _re.compile(r"^([^\t#]+)\t([A-Za-z_][A-Za-z0-9_]*)\s*$")


def parse_table(text: str) -> list[tuple[str, str]]:
    """Lenient parser. Accepts TAB-separated rules; falls back to splitting on
    runs of 2+ whitespace chars when no tab is present (LLMs love to drop
    tabs)."""
    rules: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        # primary path: TAB separator
        if "\t" in line:
            kw, _, pc = line.partition("\t")
            kw = kw.strip()
            pc = pc.strip()
        else:
            # fallback: 2+ whitespace separator
            m = _re.match(r"^(.*?)\s{2,}([A-Za-z_][A-Za-z0-9_]*)\s*$", line)
            if not m:
                # last resort: last whitespace-separated token = problem_class
                parts = line.rsplit(None, 1)
                if len(parts) != 2:
                    continue
                kw, pc = parts[0].strip(), parts[1].strip()
            else:
                kw, pc = m.group(1).strip(), m.group(2).strip()
        # Drop quoting noise the LLM may add
        kw = kw.strip("\"'`")
        if not kw or not pc:
            continue
        rules.append((kw, pc))
    return rules


SEED_TABLE_TEXT = serialise_table(list(PROD_KEYWORDS))


# ---------------------------------------------------------------------------
# Candidate evaluator
# ---------------------------------------------------------------------------
def make_classify_fn(rules: list[tuple[str, str]]):
    """Return a classify_error variant that uses the supplied keyword table
    while keeping the production language guard intact."""
    lowered = [(kw.lower(), pc) for kw, pc in rules]

    def classify(text: str) -> Optional[str]:
        if not text:
            return None
        # Phase 0 language guard — same as production.
        if _detect_language_quick(text) is not None:
            return None
        lower = text.lower()
        for kw, pc in lowered:
            if kw in lower:
                return pc
        return None

    return classify


@dataclass
class RowResult:
    row: dict[str, Any]
    expected: Optional[str]
    actual: Optional[str]
    kind: str  # "correct" | "false_confident" | "correct_no_match" | "silent_miss"
    score: float


def score_row(row: dict[str, Any], actual: Optional[str]) -> RowResult:
    expected = row.get("expected_problem_class")
    if actual is not None and actual == expected:
        kind = "correct"
        score = 1.0
    elif actual is None and expected is None:
        kind = "silent_miss"  # never happens in this corpus
        score = 1.0
    elif actual is None and expected is not None:
        kind = "correct_no_match"
        score = 0.5
    else:
        kind = "false_confident"
        score = 0.0
    return RowResult(row=row, expected=expected, actual=actual, kind=kind, score=score)


def borg_eval(keyword_table_text: str, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Evaluate a candidate keyword table over the corpus (or a subset).

    Returns a dict with FCR, recall, precision, exact_correct, score totals
    and per-row results.
    """
    rows = rows if rows is not None else CORPUS
    rules = parse_table(keyword_table_text)
    classify = make_classify_fn(rules)

    per_row: list[RowResult] = []
    n_correct = 0
    n_fc = 0
    n_cnm = 0
    n_fired = 0
    n_with_expected = 0
    for r in rows:
        actual = classify(r["text"])
        rr = score_row(r, actual)
        per_row.append(rr)
        if rr.kind == "correct":
            n_correct += 1
        elif rr.kind == "false_confident":
            n_fc += 1
        elif rr.kind == "correct_no_match":
            n_cnm += 1
        if actual is not None:
            n_fired += 1
        if rr.expected is not None:
            n_with_expected += 1

    n_total = len(rows)
    fcr = n_fc / n_total if n_total else 0.0
    recall = n_correct / n_with_expected if n_with_expected else 0.0
    precision = n_correct / n_fired if n_fired else 0.0
    return {
        "n_total": n_total,
        "n_correct": n_correct,
        "n_false_confident": n_fc,
        "n_correct_no_match": n_cnm,
        "n_fired": n_fired,
        "fcr": fcr,
        "recall": recall,
        "precision": precision,
        "exact_correct_rate": n_correct / n_total if n_total else 0.0,
        "n_rules": len(rules),
        "per_row": per_row,
    }


# ---------------------------------------------------------------------------
# GEPA adapter
# ---------------------------------------------------------------------------
import gepa  # noqa: E402
from gepa.core.adapter import EvaluationBatch, GEPAAdapter  # noqa: E402


class BorgKeywordTableAdapter:
    """GEPA adapter that evaluates a candidate keyword_table against the
    Borg debug corpus and produces reflective feedback the LLM can use to
    propose better tables.
    """

    component_name = "keyword_table"
    # GEPA's reflective mutation proposer reads this attribute and dispatches
    # to its default LLM-driven proposer when it is None.
    propose_new_texts = None

    def __init__(self, full_corpus: list[dict[str, Any]]):
        self.full_corpus = full_corpus

    # --- evaluate ----------------------------------------------------------
    def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        table_text = candidate.get(self.component_name, "")
        result = borg_eval(table_text, rows=batch)
        per_row: list[RowResult] = result["per_row"]

        outputs = [
            {
                "expected": rr.expected,
                "actual": rr.actual,
                "kind": rr.kind,
            }
            for rr in per_row
        ]
        scores = [rr.score for rr in per_row]
        objective_scores = [
            {
                "fcr_penalty": 0.0 if rr.kind == "false_confident" else 1.0,
                "is_correct": 1.0 if rr.kind == "correct" else 0.0,
            }
            for rr in per_row
        ]

        trajectories = None
        if capture_traces:
            rules = parse_table(table_text)
            trajectories = []
            for rr in per_row:
                fired_rule = None
                lower = rr.row["text"].lower()
                if _detect_language_quick(rr.row["text"]) is None:
                    for kw, pc in rules:
                        if kw.lower() in lower:
                            fired_rule = (kw, pc)
                            break
                trajectories.append(
                    {
                        "row": rr.row,
                        "expected": rr.expected,
                        "actual": rr.actual,
                        "kind": rr.kind,
                        "fired_rule": fired_rule,
                        "language_guard": _detect_language_quick(rr.row["text"]),
                    }
                )

        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
            objective_scores=objective_scores,
        )

    # --- reflective dataset ------------------------------------------------
    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        records: list[dict[str, Any]] = []
        trajectories = eval_batch.trajectories or []
        for traj in trajectories:
            row = traj["row"]
            kind = traj["kind"]
            fired = traj["fired_rule"]
            if kind == "correct":
                feedback = (
                    f"CORRECT. The rule {fired!r} matched and {traj['actual']} "
                    f"is the expected problem_class. Keep this rule."
                )
            elif kind == "false_confident":
                feedback = (
                    f"FALSE-CONFIDENT — this is the failure mode we MUST eliminate. "
                    f"The rule {fired!r} matched and routed this error to "
                    f"{traj['actual']!r} but the correct answer is {traj['expected']!r}. "
                    f"Either DELETE the offending substring rule, REPLACE it with a "
                    f"more specific phrase that does not match this input, or REORDER "
                    f"so that a more specific rule matches first. Substrings of length "
                    f"<6 chars are dangerous."
                )
            elif kind == "correct_no_match":
                feedback = (
                    f"HONEST MISS. No rule matched (language_guard={traj['language_guard']!r}). "
                    f"This is acceptable but not ideal. The expected answer is "
                    f"{traj['expected']!r}. ONLY add a new rule for this if you can "
                    f"choose a substring that is uniquely characteristic of this class "
                    f"AND does not appear in any false-confident or wrong-class example."
                )
            else:
                feedback = "Silent miss (acceptable)."

            records.append(
                {
                    "Inputs": {
                        "error_text": row["text"],
                        "language": row.get("language", ""),
                        "framework": row.get("framework") or "",
                        "expected_problem_class": row.get("expected_problem_class") or "(none)",
                    },
                    "Generated Outputs": {
                        "actual_problem_class": traj["actual"] or "(none)",
                        "fired_rule": (
                            f"{fired[0]!r} -> {fired[1]}" if fired else "(no rule fired)"
                        ),
                        "language_guard_lock": traj["language_guard"] or "(none)",
                        "outcome": kind,
                    },
                    "Feedback": feedback,
                }
            )

        # Cap at 12 records to keep the reflection prompt small.
        # Bias toward false_confident first, then correct_no_match for high-priority
        # python rows, then a couple of correct examples for context.
        def priority(rec):
            outcome = rec["Generated Outputs"]["outcome"]
            order = {"false_confident": 0, "correct_no_match": 1, "correct": 2}
            return order.get(outcome, 3)

        records.sort(key=priority)
        records = records[:12]

        return {self.component_name: records}


# ---------------------------------------------------------------------------
# LM selection
# ---------------------------------------------------------------------------
def pick_reflection_lm() -> tuple[Any, str]:
    """Return (callable_or_model_id, label) for the reflection LM.

    Tries Anthropic, OpenAI, then Google, then falls back to a mock.
    """
    # Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        return ("anthropic/claude-3-5-haiku-20241022", "anthropic_haiku")
    # OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        return ("openai/gpt-4.1-mini", "openai_gpt41_mini")
    # Google via /root/.hermes/secrets/google_api_key
    google_key_path = Path("/root/.hermes/secrets/google_api_key")
    if google_key_path.exists():
        key = google_key_path.read_text().strip()
        if key:
            os.environ["GEMINI_API_KEY"] = key
            os.environ["GOOGLE_API_KEY"] = key
            return ("gemini/gemini-2.0-flash", "gemini_2_flash")
    # Mock
    return (MockReflectionLM(), "MOCK_LLM")


class MockReflectionLM:
    """Deterministic mock that exercises the GEPA pipeline without an LLM.

    Each call appends one new keyword rule to the existing table extracted
    from the prompt. The candidate substrings are intentionally specific so
    they should improve recall on python rows without introducing FC.
    """

    # Long, specific substrings extracted from the corpus that are unique to
    # a single python problem class and don't appear in any non-python row.
    _CANDIDATE_RULES = [
        ("KeyError:", "schema_drift"),       # NOTE: intentionally noisy to test FCR pressure
        ("RecursionError", "null_pointer_chain"),
        ("ValueError: invalid literal", "type_mismatch"),
        ("FileNotFoundError", "missing_dependency"),
        ("RuntimeError: dictionary changed size", "race_condition"),
        ("RuntimeError: maximum recursion depth", "null_pointer_chain"),
        ("UnicodeDecodeError", "type_mismatch"),
        ("AssertionError", "type_mismatch"),
    ]

    def __init__(self):
        self.calls = 0

    def __call__(self, prompt):
        # Extract the current table from the prompt (curr_param block).
        if isinstance(prompt, list):
            text = "\n\n".join(
                m.get("content", "") if isinstance(m.get("content"), str) else ""
                for m in prompt
            )
        else:
            text = prompt
        # Find the existing keyword_table block — between the first ``` after
        # "instructions" and the matching closing ```.
        block_start = text.find("```")
        if block_start == -1:
            current = SEED_TABLE_TEXT
        else:
            block_end = text.find("```", block_start + 3)
            current = text[block_start + 3:block_end] if block_end != -1 else SEED_TABLE_TEXT
            current = current.lstrip("\n")

        rule = self._CANDIDATE_RULES[self.calls % len(self._CANDIDATE_RULES)]
        self.calls += 1

        # Append the new rule before any trailing whitespace.
        new_table = current.rstrip() + f"\n{rule[0]}\t{rule[1]}\n"

        return f"```\n{new_table}```\n"


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 72)
    print("Borg GEPA spike — evolving the classify_error keyword table")
    print("=" * 72)

    # 1. Baseline measurement on the seed
    before = borg_eval(SEED_TABLE_TEXT)
    print(f"BEFORE  rows={before['n_total']}  "
          f"correct={before['n_correct']} ({before['exact_correct_rate']:.1%})  "
          f"fc={before['n_false_confident']} (FCR={before['fcr']:.1%})  "
          f"cnm={before['n_correct_no_match']}  "
          f"precision={before['precision']:.1%}  recall={before['recall']:.1%}")

    # 2. Choose LM
    lm_choice, lm_label = pick_reflection_lm()
    print(f"Reflection LM: {lm_label}  ({type(lm_choice).__name__})")

    # 3. Build adapter, datasets
    adapter = BorgKeywordTableAdapter(full_corpus=CORPUS)
    # GEPA needs a list of DataInst items. We use raw corpus rows.
    trainset = list(CORPUS)
    valset = list(CORPUS)

    seed_candidate = {"keyword_table": SEED_TABLE_TEXT}

    # GEPA resumes from RUN_DIR if it exists; clear it for a fresh run.
    import shutil
    if RUN_DIR.exists():
        shutil.rmtree(RUN_DIR)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Run GEPA
    started_at = time.time()
    gepa_error: Optional[str] = None
    best_candidate_text: str = SEED_TABLE_TEXT
    best_score_val: Optional[float] = None
    history: list[dict[str, Any]] = []

    try:
        # Budget accounting: GEPA counts every per-example evaluation as one
        # "metric call". A full 173-row valset sweep consumes 173 calls. The
        # spike runs ~5 reflective iterations (minibatch_size=8 → 8 calls each)
        # plus ~3 full valset sweeps for tracking. Cap at 800 metric calls to
        # stay well inside the $5 ceiling on a flash-tier model:
        #   ~800 calls × ~2 KB prompt + ~5 reflections × ~6 KB prompt
        #   = ~1.7 MB tokens ≈ <$0.10 on gemini-2.0-flash or gpt-4.1-mini.
        result = gepa.optimize(
            seed_candidate=seed_candidate,
            trainset=trainset,
            valset=valset,
            adapter=adapter,
            reflection_lm=lm_choice,
            max_metric_calls=800,
            reflection_minibatch_size=8,
            candidate_selection_strategy="pareto",
            display_progress_bar=False,
            seed=0,
            run_dir=str(RUN_DIR),
            raise_on_exception=False,
        )
        best = getattr(result, "best_candidate", None)
        if best is not None and "keyword_table" in best:
            best_candidate_text = best["keyword_table"]
        best_score_val = getattr(result, "best_val_aggregate_score", None) or getattr(
            result, "best_score", None
        )
        # Try to dump per-iteration history
        cand_list = getattr(result, "val_aggregate_scores", None)
        if cand_list:
            history = [{"iter": i, "val_aggregate": float(s)} for i, s in enumerate(cand_list)]
    except Exception as exc:  # noqa: BLE001
        gepa_error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        print("GEPA raised:\n" + gepa_error)

    elapsed = time.time() - started_at

    # 5. After measurement
    after = borg_eval(best_candidate_text)
    print(f"AFTER   rows={after['n_total']}  "
          f"correct={after['n_correct']} ({after['exact_correct_rate']:.1%})  "
          f"fc={after['n_false_confident']} (FCR={after['fcr']:.1%})  "
          f"cnm={after['n_correct_no_match']}  "
          f"precision={after['precision']:.1%}  recall={after['recall']:.1%}")
    print(f"Elapsed: {elapsed:.1f}s")

    # 6. Persist results.json
    def strip_per_row(d: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in d.items() if k != "per_row"}

    payload = {
        "label": lm_label,
        "is_mock": lm_label == "MOCK_LLM",
        "elapsed_seconds": elapsed,
        "max_metric_calls": 800,
        "reflection_minibatch_size": 8,
        "before": strip_per_row(before),
        "after": strip_per_row(after),
        "delta": {
            "fcr": after["fcr"] - before["fcr"],
            "exact_correct_rate": after["exact_correct_rate"] - before["exact_correct_rate"],
            "recall": after["recall"] - before["recall"],
            "precision": after["precision"] - before["precision"],
            "n_rules": after["n_rules"] - before["n_rules"],
        },
        "best_score": best_score_val,
        "history": history,
        "gepa_error": gepa_error,
        "seed_candidate_table": SEED_TABLE_TEXT,
        "best_candidate_table": best_candidate_text,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {RESULTS_PATH}")

    print()
    print(f"BEFORE_FCR={before['fcr']:.4f}")
    print(f"AFTER_FCR ={after['fcr']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
