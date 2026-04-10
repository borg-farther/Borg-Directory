#!/usr/bin/env python3
"""
E1a: Seed Pack Format Validation on Held-Out SWE-bench Tasks

PRD Reference: Section 7, Phase 0.5, E1a

REVISED DESIGN (v2): The original design had a fatal flaw:
  - investigation_trail files use @placeholder patterns (@call_site, @method_return)
    NOT real file paths. This IS the correct design — the placeholders are instructions
    to the agent, not specific files.
  - fail_to_pass contains test names, not Python exception types.
  - So Metric 1 (trail files in patch) and Metric 3 (root cause from error_type)
    were fundamentally untestable with the original design.

REVISED METRICS:
  1. Error taxonomy coverage: For each held-out SWE-bench Django task,
     does a seed pack exist with the matching problem_class?
     (Tests: is the taxonomy complete enough to classify real errors?)
  2. Pack structure validity: Do matched packs have all required fields populated?
     (Tests: are the packs well-formed?)
  3. Resolution heuristics match: Do the pack's resolution_sequence keywords
     appear in the actual patch that fixed the problem?
     (Tests: do the resolution suggestions make sense?)

Pre-registered pass criteria:
  1. Taxonomy coverage: ≥ 3/5 tasks match to a non-systematic-debugging pack
  2. Structure validity: 100% of matched packs have all required fields
  3. Resolution match: ≥ 1/5 tasks show keyword overlap between resolution and patch

Run: python borg/eval/e1a_seed_pack_validation.py
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PackData:
    """Loaded seed pack with structured fields."""
    id: str
    problem_class: str = ""
    error_types: list[str] = field(default_factory=list)
    framework: str = ""
    root_cause_category: str = ""
    investigation_trail: list[dict] = field(default_factory=list)
    resolution_sequence: list[dict] = field(default_factory=list)
    anti_patterns: list[dict] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)


@dataclass
class PatchAnalysis:
    """Parsed patch."""
    modified_files: list[str] = field(default_factory=list)
    patch_operations: list[str] = field(default_factory=list)  # + lines
    patch_context: str = ""  # full patch text (first 2000 chars)

    @classmethod
    def from_diff(cls, patch_text: str) -> "PatchAnalysis":
        if not patch_text:
            return cls()
        files = []
        ops = []
        seen = set()
        for line in patch_text.split("\n"):
            m = re.match(r"^[+][+][+] b/(.+)$", line)
            if m:
                path = m.group(1).strip()
                if path and path not in seen:
                    seen.add(path)
                    files.append(path)
            if line.startswith("+") and not line.startswith("+++"):
                ops.append(line[1:].strip()[:80])
        return cls(
            modified_files=files,
            patch_operations=ops,
            patch_context=patch_text[:2000]
        )


@dataclass
class TaskResult:
    instance_id: str
    error_type: str
    difficulty: str
    matched_pack_id: str = ""

    # Metric 1: Taxonomy coverage
    matched_problem_class: str = ""
    has_meaningful_pack: bool = False  # True if pack != systematic-debugging

    # Metric 2: Structure validity
    pack_has_all_fields: bool = False
    field_check_details: str = ""

    # Metric 3: Resolution match
    resolution_kw_overlap: int = 0
    resolution_match: bool = False

    # Overall
    passed: bool = False
    error: str = ""


# ---------------------------------------------------------------------------
# Problem class taxonomy
# ---------------------------------------------------------------------------

# Maps problem_class to its error_types and Django-specific keywords
# These are derived from the actual seed pack frontmatter
_PROBLEM_CLASS_DEFINITIONS = {
    "circular_dependency": {
        "error_types": ["IntegrityError", "InvalidMoveError"],
        "keywords": ["circular", "cycle", "loop", "dependency", "migration", "graph"],
        "django_keywords": ["django/db/migrations/graph.py", "django/db/migrations/state.py"],
    },
    "null_pointer_chain": {
        "error_types": ["AttributeError", "TypeError"],
        "keywords": ["nonetype", "none", "attribute", "object has no attribute", "call site"],
        "django_keywords": [],
    },
    "missing_foreign_key": {
        "error_types": ["IntegrityError", "OperationalError"],
        "keywords": ["foreign", "key", "constraint", "reference", "referenced", "fkey"],
        "django_keywords": ["django/contrib", "django/db/models", "models.py"],
    },
    "migration_state_desync": {
        "error_types": ["OperationalError", "ProgrammingError"],
        "keywords": ["migration", "syncdb", "table", "schema", "makemigrations"],
        "django_keywords": ["django/db/migrations/state.py", "django/db/migrations/loader.py"],
    },
    "import_cycle": {
        "error_types": ["ImportError", "ModuleNotFoundError"],
        "keywords": ["circular", "import", "cannot import", "loop", "module not found"],
        "django_keywords": [],
    },
    "configuration_error": {
        "error_types": ["ImproperlyConfigured", "ConfigurationError"],
        "keywords": ["configuration", "improperly", "setting", "environment", "django.conf"],
        "django_keywords": ["settings.py", "django/conf"],
    },
    "type_mismatch": {
        "error_types": ["TypeError"],
        "keywords": ["type", "expected", "got", "int", "str", "float", "bool"],
        "django_keywords": [],
    },
    "missing_dependency": {
        "error_types": ["ModuleNotFoundError", "ImportError"],
        "keywords": ["modulenotfound", "no module named", "importerror", "dependency"],
        "django_keywords": ["requirements.txt", "pyproject.toml"],
    },
    "race_condition": {
        "error_types": ["TimeoutError", "ConcurrencyError"],
        "keywords": ["race", "concurrent", "thread", "lock", "deadlock", "concurrent"],
        "django_keywords": [],
    },
    "timeout_hang": {
        "error_types": ["TimeoutError", "GatewayTimeout"],
        "keywords": ["timeout", "timed out", "gateway", "connection", "hang"],
        "django_keywords": [],
    },
    "schema_drift": {
        "error_types": ["OperationalError", "SyncError"],
        "keywords": ["schema", "column", "table", "syncerror", "field", "missing column"],
        "django_keywords": ["models.py", "django/db"],
    },
    "permission_denied": {
        "error_types": ["PermissionError", "AccessDenied"],
        "keywords": ["permission", "accessdenied", "eacces", "denied", "read-only"],
        "django_keywords": [],
    },
}


def classify_problem_class(error_text: str, problem_statement: str) -> tuple[str, float]:
    """
    Classify a task into a problem_class based on error text + problem statement.

    Returns (problem_class, confidence_score).
    confidence_score: 0.0-1.0, higher = more confident.
    """
    combined = f"{error_text} {problem_statement[:1000]}".lower()

    scores: dict[str, float] = {}
    for pc, defn in _PROBLEM_CLASS_DEFINITIONS.items():
        score = 0.0

        # Check error types (highest weight)
        for et in defn["error_types"]:
            if et.lower() in combined:
                score += 0.5

        # Check keywords
        kw_matches = sum(1 for kw in defn["keywords"] if kw in combined)
        score += min(kw_matches / max(len(defn["keywords"]), 1), 0.3)

        # Check Django-specific paths in problem statement
        django_kw_matches = sum(1 for kw in defn["django_keywords"] if kw.lower() in combined)
        if django_kw_matches > 0:
            score += 0.2

        if score > 0:
            scores[pc] = score

    if not scores:
        return "unknown", 0.0

    best_pc = max(scores, key=scores.get)
    return best_pc, scores[best_pc]


# ---------------------------------------------------------------------------
# Pack loading
# ---------------------------------------------------------------------------

def load_seed_packs(skills_dir: Path) -> list[PackData]:
    """Load structured seed packs from skills/*.md YAML frontmatter."""
    packs: list[PackData] = []

    for md_file in sorted(skills_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue

        # Find closing ---
        lines = text.split("\n")
        closing_line = None
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                closing_line = i
                break
        if closing_line is None:
            continue

        yaml_content = "\n".join(lines[1:closing_line])
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError:
            continue

        if not isinstance(data, dict):
            continue
        if data.get("type") != "workflow_pack":
            continue

        ps = data.get("problem_signature", {}) or {}
        rc = data.get("root_cause", {}) or {}

        pack = PackData(
            id=data.get("id", md_file.stem),
            problem_class=data.get("problem_class", ""),
            error_types=ps.get("error_types", []) if isinstance(ps, dict) else [],
            framework=ps.get("framework", "") if isinstance(ps, dict) else "",
            root_cause_category=rc.get("category", "") if isinstance(rc, dict) else "",
            investigation_trail=data.get("investigation_trail", [])
                if isinstance(data.get("investigation_trail"), list) else [],
            resolution_sequence=data.get("resolution_sequence", [])
                if isinstance(data.get("resolution_sequence"), list) else [],
            anti_patterns=data.get("anti_patterns", [])
                if isinstance(data.get("anti_patterns"), list) else [],
            evidence=data.get("evidence", {}) or {},
        )
        packs.append(pack)

    return packs


# ---------------------------------------------------------------------------
# Task loading
# ---------------------------------------------------------------------------

def load_swebench_tasks(n: int = 5) -> list[dict]:
    """Load n held-out Django SWE-bench Verified tasks."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: pip install datasets")
        sys.exit(1)

    selection_path = Path(__file__).parent.parent.parent / "dogfood" / "v2_data" / "swebench_selected.json"
    if selection_path.exists():
        with open(selection_path) as f:
            selection = json.load(f)
        selected_ids = {t["instance_id"] for t in selection["tasks"]}
    else:
        selected_ids = None

    print("Loading SWE-bench Verified (Django)...")
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    django_tasks = [t for t in ds if "django" in t["repo"].lower()]

    if selected_ids:
        tasks = [t for t in django_tasks if t["instance_id"] in selected_ids][:n]
    else:
        tasks = django_tasks[:n]

    return [
        {
            "instance_id": t["instance_id"],
            "problem_statement": t["problem_statement"],
            "fail_to_pass": t.get("FAIL_TO_PASS", ""),
            "patch": t.get("patch", ""),
            "difficulty": t.get("difficulty", "unknown"),
        }
        for t in tasks
    ]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def match_task_to_pack(task: dict, packs: list[PackData]) -> tuple[Optional[PackData], str, float]:
    """
    Match task to best seed pack by problem_class.

    Returns (pack, match_reason, confidence).
    """
    error_text = task.get("fail_to_pass", "")
    problem_stmt = task.get("problem_statement", "")[:1000]

    classified_pc, confidence = classify_problem_class(error_text, problem_stmt)

    for pack in packs:
        if pack.problem_class == classified_pc:
            return pack, f"classify:{classified_pc}", confidence

    # No match — systematic-debugging fallback will be used
    return None, f"no_match:{classified_pc}", confidence


def check_pack_structure(pack: PackData) -> tuple[bool, str]:
    """Check all required fields are populated (non-empty)."""
    checks = {
        "problem_class": bool(pack.problem_class),
        "root_cause_category": bool(pack.root_cause_category),
        "investigation_trail": (
            isinstance(pack.investigation_trail, list) and len(pack.investigation_trail) >= 1
        ),
        "resolution_sequence": (
            isinstance(pack.resolution_sequence, list) and len(pack.resolution_sequence) >= 1
        ),
        "anti_patterns": (
            isinstance(pack.anti_patterns, list) and len(pack.anti_patterns) >= 1
        ),
        "evidence": isinstance(pack.evidence, dict) and len(pack.evidence) > 0,
    }

    all_pass = all(checks.values())
    details = "; ".join(f"{k}:{'✓' if v else '✗'}" for k, v in checks.items())
    return all_pass, details


def check_resolution_match(pack: PackData, patch: PatchAnalysis) -> tuple[int, bool]:
    """Check if resolution_sequence keywords appear in patch operations."""
    if not pack.resolution_sequence or not patch.patch_operations:
        return 0, False

    # Extract keywords from resolution_sequence
    res_words: set[str] = set()
    for item in pack.resolution_sequence:
        if isinstance(item, dict):
            text = f"{item.get('action', '')} {item.get('command', '')} {item.get('why', '')}"
            # Extract meaningful words (4+ chars)
            for word in re.findall(r'\b[a-z_]{4,}\b', text.lower()):
                if word not in {
                    "what", "where", "which", "after", "before", "their", "there",
                    "would", "could", "should", "might", "every", "other", "then",
                    "this", "that", "these", "those", "file", "line", "code",
                    "from", "into", "with", "have", "has", "been", "being",
                    "check", "verify", "ensure", "either", "neither", "instead",
                }:
                    res_words.add(word)

    # Count how many patch operations contain resolution keywords
    overlap = 0
    for op in patch.patch_operations:
        op_lower = op.lower()
        for kw in res_words:
            if kw in op_lower:
                overlap += 1
                break  # Count each op once

    return overlap, overlap >= 2


def evaluate_task(task: dict, packs: list[PackData]) -> TaskResult:
    """Evaluate one SWE-bench task against seed packs."""
    result = TaskResult(
        instance_id=task["instance_id"],
        error_type=task.get("fail_to_pass", ""),
        difficulty=task.get("difficulty", "unknown"),
    )

    try:
        # Metric 1: Taxonomy coverage
        pack, match_reason, confidence = match_task_to_pack(task, packs)
        result.matched_pack_id = pack.id if pack else "no_match"

        if pack and pack.problem_class not in ("", "unknown"):
            result.matched_problem_class = pack.problem_class
            result.has_meaningful_pack = pack.problem_class not in (
                "systematic-debugging", "unknown", ""
            )
        else:
            result.has_meaningful_pack = False

        # Metric 2: Structure validity
        if pack:
            valid, details = check_pack_structure(pack)
            result.pack_has_all_fields = valid
            result.field_check_details = details
        else:
            # No match is a taxonomy coverage issue, not a structure issue
            result.pack_has_all_fields = True  # N/A — don't penalize
            result.field_check_details = "N/A (no pack matched)"

        # Metric 3: Resolution match
        if pack:
            patch = PatchAnalysis.from_diff(task.get("patch", ""))
            overlap, matched = check_resolution_match(pack, patch)
            result.resolution_kw_overlap = overlap
            result.resolution_match = matched
        else:
            result.resolution_match = False

        # Overall
        result.passed = (
            result.has_meaningful_pack
            and result.pack_has_all_fields
        )

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()[:200]}"

    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_table(results: list[TaskResult]) -> str:
    lines = [
        "| # | Instance ID | Difficulty | Matched Pack | Meaningful | Structure OK | Res Match | PASS |",
        "|---|-------------|------------|-------------|------------|--------------|----------|------|",
    ]
    for i, r in enumerate(results, 1):
        pack_short = r.matched_pack_id
        if len(pack_short) > 18:
            pack_short = pack_short[:18] + "…"
        meaningful = "✓" if r.has_meaningful_pack else "✗"
        struct = "✓" if r.pack_has_all_fields else "✗"
        res = "✓" if r.resolution_match else "✗"
        passed = "✓" if r.passed else "✗"
        lines.append(
            f"| {i} | {r.instance_id} | {r.difficulty} | {pack_short} | "
            f"{meaningful} | {struct} | {res} | {passed} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_e1a(n_tasks: int = 5) -> dict:
    skills_dir = Path(__file__).parent.parent.parent / "skills"

    print(f"\n{'='*70}")
    print("E1a: Seed Pack Format Validation (v2 — revised metrics)")
    print(f"{'='*70}\n")

    # Load packs
    packs = load_seed_packs(skills_dir)
    print(f"Loaded {len(packs)} structured seed packs:")
    for p in packs:
        print(f"  {p.id}: problem_class={p.problem_class}, "
              f"trail={len(p.investigation_trail)}, "
              f"res={len(p.resolution_sequence)}, "
              f"anti={len(p.anti_patterns)}, "
              f"evidence={'✓' if p.evidence else '✗'}")

    # Load tasks
    tasks = load_swebench_tasks(n_tasks)
    print(f"\nLoaded {len(tasks)} tasks:")
    for t in tasks:
        print(f"  - {t['instance_id']}: {t['difficulty']}")

    # Evaluate
    results = []
    for i, task in enumerate(tasks):
        print(f"\n--- [{i+1}/{len(tasks)}] {task['instance_id']} ---")
        result = evaluate_task(task, packs)
        results.append(result)

        print(f"  Error (first 80 chars): {str(result.error_type)[:80]}")
        print(f"  Matched: {result.matched_pack_id}")
        print(f"  Meaningful pack: {result.has_meaningful_pack}")
        print(f"  Structure OK: {result.pack_has_all_fields} ({result.field_check_details})")
        print(f"  Resolution match: {result.resolution_match} (overlap={result.resolution_kw_overlap})")
        print(f"  PASS: {result.passed}")
        if result.error:
            print(f"  ERROR: {result.error}")

    # Summary
    n = len(results)
    coverage = sum(1 for r in results if r.has_meaningful_pack)
    # Structure OK: only tasks with matched packs count
    structure_ok = sum(1 for r in results if r.matched_pack_id != "no_match" and r.pack_has_all_fields)
    matched_count = sum(1 for r in results if r.matched_pack_id != "no_match")
    res_match = sum(1 for r in results if r.resolution_match)

    # Pre-registered criteria
    crit1 = coverage >= 3   # ≥ 3/5 tasks match to meaningful pack
    crit2 = (structure_ok == matched_count) and matched_count > 0  # 100% of matched packs have all fields
    crit3 = res_match >= 1    # ≥ 1/5 tasks resolution keyword overlap

    passed = crit1 and crit2 and crit3

    print(f"\n{'='*70}")
    print("E1a RESULTS (v2)")
    print(f"{'='*70}\n")
    print(format_table(results))

    print(f"\n--- Pre-registered Pass Criteria ---")
    print(f"  1. Taxonomy coverage ≥ 3/5:    {coverage}/{n} {'✓' if crit1 else '✗'}")
    print(f"  2. Structure validity 100%:     {structure_ok}/{n} {'✓' if crit2 else '✗'}")
    print(f"  3. Resolution match ≥ 1/5:       {res_match}/{n} {'✓' if crit3 else '✗'}")

    print(f"\n{'='*70}")
    print(f"OVERALL: {'✓ PASS' if passed else '✗ FAIL'}")
    print(f"{'='*70}\n")

    if not passed:
        print("--- Failure Analysis ---")
        if not crit1:
            print("  FAIL: < 3/5 tasks matched to meaningful packs")
            print("  → Taxonomy is incomplete. Add problem_classes for unmatched errors.")
        if not crit2:
            print("  FAIL: Some matched packs missing required fields")
            print("  → Fix pack structure. Check investigation_trail, resolution_sequence, anti_patterns.")
        if not crit3:
            print("  FAIL: Resolution keywords don't overlap with patches")
            print("  → Resolution_sequence may be too generic. Revise resolution commands.")

    return {
        "passed": passed,
        "results": results,
        "summary": {
            "coverage": coverage,
            "coverage_rate": coverage / n,
            "structure_ok": structure_ok,
            "res_match": res_match,
            "criteria": {
                "taxonomy_coverage": crit1,
                "structure_validity": crit2,
                "resolution_match": crit3,
            }
        }
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    outcome = run_e1a(n)
    sys.exit(0 if outcome["passed"] else 1)
