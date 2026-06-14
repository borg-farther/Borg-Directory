#!/usr/bin/env python3
"""Reproducible matcher recall/precision harness (issue #9).

Replaces the prior hand-asserted "recall 0.57" prose number — which had no
script behind it and no test gating it — with a labelled, deterministic,
offline, CI-runnable measurement of the SAME engine the CLI and MCP use
(``borg.core.rescue.rescue`` → ``classify_error`` → seed pack).

    python eval/recall_harness.py            # human summary + exit code
    python eval/recall_harness.py --json     # machine-readable report
    python eval/recall_harness.py --write-snapshot   # refresh the committed baseline

The labelled set (``CASES`` below) pairs LITERAL phrasings (the exact exception
token, e.g. ``ModuleNotFoundError: No module named 'django'``) with
CONVERSATIONAL phrasings of the SAME underlying error (e.g. "my server won't
start, it can't find a module called django"). That pairing is the whole point:
it isolates the conversational/natural-language gap that issue #9 is about and
makes the gap a number that moves when the matcher improves or regresses.

Definitions (standard, computed over the labelled set):
  * a case has ``expected`` = a real problem_class (should match) or None
    (a control that should honestly NOT match).
  * predicted = rescue(input).problem_class when status == "matched", else None.
  * TP  predicted == expected (expected is a real class)
  * FP  predicted is a class but wrong, or expected is None  (a confident-wrong)
  * FN  predicted is None but expected is a real class        (an honest miss)
  * recall    = TP / (TP + FN)   over the should-match cases
  * precision = TP / (TP + FP)   over the predicted-a-class cases

Precision is the safety number ("never confidently wrong"); recall is the
coverage number issue #9 tracks. Both are reported overall AND split by phrasing
so the conversational gap is never hidden inside a blended average.

This harness deliberately does NOT expand coverage — it measures the matcher as
shipped for the pilot. Adding cases here is welcome; "fixing" the number by
deleting hard cases is not (the test gates the case count too).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from borg.core.rescue import rescue  # noqa: E402

SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recall_harness_snapshot.json")

# Conservative synonym families: predicting any member when the label is another
# member counts as a correct match, not a confident-wrong. These are genuine
# taxonomy synonyms (a user with "modules import each other" is helped equally by
# either pack), so scoring them as exact-slug mismatches would understate the
# matcher's real precision. Keep this list tiny and only for true synonyms.
EQUIVALENT_CLASSES: List[set] = [
    {"import_cycle", "circular_dependency"},
]


def _same_class(predicted: Optional[str], expected: Optional[str]) -> bool:
    if predicted == expected:
        return True
    if predicted is None or expected is None:
        return False
    return any(predicted in fam and expected in fam for fam in EQUIVALENT_CLASSES)

# Each case: id, input text, expected problem_class (None = should-not-match
# control), phrasing (literal|conversational), lang. Conversational cases share
# the expected class of their literal twin so the gap is directly visible.
CASES: List[Dict[str, Any]] = [
    # ---- missing_dependency ------------------------------------------------
    {"id": "dep-lit-1", "input": "ModuleNotFoundError: No module named 'django'", "expected": "missing_dependency", "phrasing": "literal", "lang": "en"},
    {"id": "dep-lit-2", "input": "ImportError: No module named requests", "expected": "missing_dependency", "phrasing": "literal", "lang": "en"},
    {"id": "dep-lit-3", "input": "Traceback (most recent call last):\n  File \"app.py\", line 1, in <module>\n    import flask\nModuleNotFoundError: No module named 'flask'", "expected": "missing_dependency", "phrasing": "literal", "lang": "en"},
    {"id": "dep-conv-1", "input": "my server won't start, it says it can't find a module called django", "expected": "missing_dependency", "phrasing": "conversational", "lang": "en"},
    {"id": "dep-conv-2", "input": "I keep getting an error that requests isn't installed when I run my script", "expected": "missing_dependency", "phrasing": "conversational", "lang": "en"},
    {"id": "dep-conv-3", "input": "python can't seem to import flask even though I thought I installed it", "expected": "missing_dependency", "phrasing": "conversational", "lang": "en"},
    # ---- import_cycle ------------------------------------------------------
    {"id": "cyc-lit-1", "input": "ImportError: cannot import name 'models' from partially initialized module (most likely due to a circular import)", "expected": "import_cycle", "phrasing": "literal", "lang": "en"},
    {"id": "cyc-conv-1", "input": "two of my modules import each other and now nothing loads, I think it's a circular thing", "expected": "import_cycle", "phrasing": "conversational", "lang": "en"},
    # ---- migration_state_desync -------------------------------------------
    {"id": "mig-lit-1", "input": "django.db.migrations.exceptions.InconsistentMigrationHistory: Migration admin.0001_initial is applied before its dependency", "expected": "migration_state_desync", "phrasing": "literal", "lang": "en"},
    {"id": "mig-conv-1", "input": "my django migrations are out of order and the database is in a weird state after I reverted one", "expected": "migration_state_desync", "phrasing": "conversational", "lang": "en"},
    # ---- schema_drift ------------------------------------------------------
    {"id": "sch-lit-1", "input": "django.db.utils.ProgrammingError: column users.legacy_flag does not exist", "expected": "schema_drift", "phrasing": "literal", "lang": "en"},
    {"id": "sch-conv-1", "input": "the app crashes because a column it expects in the users table isn't actually there in the db", "expected": "schema_drift", "phrasing": "conversational", "lang": "en"},
    # ---- type_mismatch -----------------------------------------------------
    {"id": "typ-lit-1", "input": "TypeError: unsupported operand type(s) for +: 'int' and 'str'", "expected": "type_mismatch", "phrasing": "literal", "lang": "en"},
    {"id": "typ-conv-1", "input": "I'm trying to add a number and some text together and python is complaining about the types", "expected": "type_mismatch", "phrasing": "conversational", "lang": "en"},
    # ---- null_pointer_chain ------------------------------------------------
    {"id": "null-lit-1", "input": "AttributeError: 'NoneType' object has no attribute 'save'", "expected": "null_pointer_chain", "phrasing": "literal", "lang": "en"},
    {"id": "null-conv-1", "input": "something is None when I didn't expect it and calling a method on it blows up", "expected": "null_pointer_chain", "phrasing": "conversational", "lang": "en"},
    # ---- configuration_error -----------------------------------------------
    {"id": "cfg-lit-1", "input": "django.core.exceptions.ImproperlyConfigured: The SECRET_KEY setting must not be empty", "expected": "configuration_error", "phrasing": "literal", "lang": "en"},
    {"id": "cfg-conv-1", "input": "django keeps telling me something about an improperly configured secret key setting", "expected": "configuration_error", "phrasing": "conversational", "lang": "en"},
    # ---- permission_denied -------------------------------------------------
    {"id": "perm-lit-1", "input": "PermissionError: [Errno 13] Permission denied: '/var/log/app.log'", "expected": "permission_denied", "phrasing": "literal", "lang": "en"},
    {"id": "perm-conv-1", "input": "my app isn't allowed to write to its log file, says permission denied", "expected": "permission_denied", "phrasing": "conversational", "lang": "en"},
    # ---- timeout_hang ------------------------------------------------------
    {"id": "to-lit-1", "input": "TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out", "expected": "timeout_hang", "phrasing": "literal", "lang": "en"},
    {"id": "to-conv-1", "input": "requests to my db just hang forever and eventually time out under load", "expected": "timeout_hang", "phrasing": "conversational", "lang": "en"},
    # ---- non-English (issue #9 documents this stays a gap for the pilot) ----
    {"id": "es-conv-1", "input": "no encuentra el módulo requests al ejecutar mi script de python", "expected": "missing_dependency", "phrasing": "conversational", "lang": "es"},
    {"id": "de-lit-1", "input": "ModuleNotFoundError: Kein Modul namens 'numpy'", "expected": "missing_dependency", "phrasing": "literal", "lang": "de"},
    {"id": "fr-conv-1", "input": "impossible d'importer le module flask dans mon application python", "expected": "missing_dependency", "phrasing": "conversational", "lang": "fr"},
    {"id": "zh-conv-1", "input": "运行 python 时报错 找不到模块 requests 怎么办", "expected": "missing_dependency", "phrasing": "conversational", "lang": "zh"},
    # ---- controls: should honestly NOT match (precision / FP discipline) ----
    {"id": "ctl-1", "input": "it's broken", "expected": None, "phrasing": "conversational", "lang": "en"},
    {"id": "ctl-2", "input": "error", "expected": None, "phrasing": "literal", "lang": "en"},
    {"id": "ctl-3", "input": "my deployment failed again, same as always", "expected": None, "phrasing": "conversational", "lang": "en"},
    {"id": "ctl-4", "input": "how do I get better at python?", "expected": None, "phrasing": "conversational", "lang": "en"},
    {"id": "ctl-5", "input": "can you refactor this function to be cleaner", "expected": None, "phrasing": "conversational", "lang": "en"},
    # ---- non-Python controls: language guard must refuse (no Python answer) -
    {"id": "ctl-docker-1", "input": "ERROR: failed to solve: write /var/lib/docker/tmp: no space left on device", "expected": None, "phrasing": "literal", "lang": "en"},
    {"id": "ctl-js-1", "input": "TypeError: Cannot read properties of undefined (reading 'map')", "expected": None, "phrasing": "literal", "lang": "en"},
]


def _predict(text: str) -> Optional[str]:
    """Predicted problem_class via the real rescue engine, or None on honest miss."""
    result = rescue(text, show_guidance=False)
    if result.status == "matched" and result.problem_class and result.problem_class != "unknown":
        return result.problem_class
    return None


def _bucket() -> Dict[str, int]:
    return {"tp": 0, "fp": 0, "fn": 0, "tn": 0}


def _metrics(b: Dict[str, int]) -> Dict[str, Any]:
    tp, fp, fn = b["tp"], b["fp"], b["fn"]
    recall = round(tp / (tp + fn), 4) if (tp + fn) else None
    precision = round(tp / (tp + fp), 4) if (tp + fp) else None
    return {**b, "recall": recall, "precision": precision}


def run() -> Dict[str, Any]:
    overall = _bucket()
    by_phrasing: Dict[str, Dict[str, int]] = {}
    by_lang: Dict[str, Dict[str, int]] = {}
    details: List[Dict[str, Any]] = []

    for case in CASES:
        expected = case["expected"]
        predicted = _predict(case["input"])
        phrasing = case["phrasing"]
        lang = case["lang"]
        by_phrasing.setdefault(phrasing, _bucket())
        by_lang.setdefault(lang, _bucket())

        if expected is not None:
            outcome = "tp" if _same_class(predicted, expected) else ("fn" if predicted is None else "fp")
        else:
            outcome = "tn" if predicted is None else "fp"

        for b in (overall, by_phrasing[phrasing], by_lang[lang]):
            b[outcome] += 1

        details.append({
            "id": case["id"],
            "phrasing": phrasing,
            "lang": lang,
            "expected": expected,
            "predicted": predicted,
            "outcome": outcome,
        })

    return {
        "schema_version": 1,
        "case_count": len(CASES),
        "should_match_count": sum(1 for c in CASES if c["expected"] is not None),
        "control_count": sum(1 for c in CASES if c["expected"] is None),
        "overall": _metrics(overall),
        "by_phrasing": {k: _metrics(v) for k, v in sorted(by_phrasing.items())},
        "by_lang": {k: _metrics(v) for k, v in sorted(by_lang.items())},
        "details": details,
    }


def _summary_lines(report: Dict[str, Any]) -> List[str]:
    o = report["overall"]
    lines = [
        f"matcher recall harness — {report['case_count']} cases "
        f"({report['should_match_count']} should-match, {report['control_count']} controls)",
        f"  OVERALL   recall={o['recall']}  precision={o['precision']}  "
        f"(tp={o['tp']} fp={o['fp']} fn={o['fn']} tn={o['tn']})",
    ]
    for phrasing, m in report["by_phrasing"].items():
        lines.append(f"  {phrasing:<14} recall={m['recall']}  precision={m['precision']}  "
                     f"(tp={m['tp']} fp={m['fp']} fn={m['fn']} tn={m['tn']})")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    parser.add_argument("--write-snapshot", action="store_true", help="refresh the committed baseline snapshot")
    args = parser.parse_args()

    report = run()

    if args.write_snapshot:
        with open(SNAPSHOT_PATH, "w") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print(f"wrote {SNAPSHOT_PATH}")
        return 0

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("\n".join(_summary_lines(report)))

    # Non-zero exit if any confident-wrong (FP) appears — precision is the
    # safety invariant. Recall is reported, not gated here (the test gates it
    # against the committed baseline so regressions fail CI).
    return 1 if report["overall"]["fp"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
