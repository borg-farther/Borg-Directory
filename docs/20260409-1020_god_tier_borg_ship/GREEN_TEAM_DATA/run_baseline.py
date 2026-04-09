#!/usr/bin/env python3
"""
run_baseline.py — Tests borg search against the 50-query cold-start benchmark corpus.

Run this in a ZERO-STATE environment (fresh HERMES_HOME) to measure cold-start
performance without any pre-existing user packs or traces.

Usage:
    # From the borg source tree:
    cd /root/hermes-workspace/borg
    python docs/20260409-1020_god_tier_borg_ship/GREEN_TEAM_DATA/run_baseline.py

    # Standalone (after pip install agent-borg):
    python run_baseline.py

Environment variables:
    BORG_SEEDS_DATA_DIR  — override path to borg/seeds_data/ for testing
    BORG_DISABLE_SEEDS   — set to 1 to exclude seed packs from search
    HERMES_HOME          — override the borg data directory

Output:
    baseline_results.csv — per-query results with columns:
        query_id, query, category, difficulty, expected_problem_class,
        matches_count, matches_source, relevant_hit_count, g1_pass, g2_pass
"""

import json
import csv
import subprocess
import sys
import os
import pathlib
import tempfile
import shutil

CORPUS_PATH = pathlib.Path(__file__).parent / "error_corpus.jsonl"
RESULTS_PATH = pathlib.Path(__file__).parent / "baseline_results.csv"


def load_corpus(path: pathlib.Path) -> list[dict]:
    """Load the benchmark corpus from JSONL."""
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def run_borg_search(query: str, *, hermes_home: pathlib.Path) -> dict:
    """
    Run `borg search <query>` in a zero-state environment.

    Returns dict with keys:
        success: bool
        matches_count: int
        matches: list of dicts with name, confidence, tier, source
        stderr: str
        returncode: int
    """
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env["HOME"] = str(hermes_home)  # fallback for things that read $HOME
    # Prevent any contamination from existing borg data
    env.pop("BORG_REMOTE_INDEX", None)
    env.pop("BORG_INDEX_URL", None)

    try:
        result = subprocess.run(
            ["python", "-m", "borg.cli", "search", query],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(pathlib.Path(__file__).parent.parent.parent / "borg"),
            env=env,
        )
    except FileNotFoundError:
        # Fallback: try `borg` directly if running from PATH
        try:
            result = subprocess.run(
                ["borg", "search", query],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
        except FileNotFoundError:
            return {
                "success": False,
                "matches_count": 0,
                "matches": [],
                "stderr": "borg not found in PATH or as python module",
                "returncode": -1,
            }

    # Parse stdout looking for structured output or fallback to text parsing
    stdout = result.stdout
    stderr = result.stderr

    # Try JSON output first
    try:
        data = json.loads(stdout)
        return {
            "success": data.get("success", False),
            "matches_count": data.get("total", 0),
            "matches": data.get("matches", []),
            "stderr": stderr,
            "returncode": result.returncode,
        }
    except json.JSONDecodeError:
        # Fallback: text parsing
        lines = stdout.splitlines()
        matches = []
        in_results = False
        for line in lines:
            if "No packs found" in line:
                return {
                    "success": True,
                    "matches_count": 0,
                    "matches": [],
                    "stderr": stderr,
                    "returncode": result.returncode,
                }
            if "Name" in line and "Confidence" in line:
                in_results = True
                continue
            if in_results and line.strip() and not line.startswith("-"):
                # Parse result line: "name   confidence   tier     source"
                parts = line.split()
                if parts:
                    matches.append({
                        "name": parts[0],
                        "confidence": parts[1] if len(parts) > 1 else "unknown",
                        "tier": parts[2] if len(parts) > 2 else "unknown",
                        "source": parts[3] if len(parts) > 3 else "unknown",
                    })

        return {
            "success": result.returncode == 0,
            "matches_count": len(matches),
            "matches": matches,
            "stderr": stderr,
            "returncode": result.returncode,
        }


def evaluate_relevance(
    matches: list[dict],
    expected_problem_class: str,
) -> tuple[int, list[dict]]:
    """
    Count how many matches are relevant to the expected problem class.

    A match is relevant if its name or problem_class overlaps with the
    expected_problem_class token-wise (simple token intersection).

    Returns (relevant_count, relevant_matches).
    """
    expected_tokens = set(expected_problem_class.lower().replace("_", " ").split())
    relevant = []
    for m in matches:
        name_tokens = set(m.get("name", "").lower().replace("_", " ").replace("-", " ").split())
        # Also check problem_class field if present
        pc_tokens = set()
        if "problem_class" in m:
            pc_tokens = set(m["problem_class"].lower().replace("_", " ").split())
        overlap = expected_tokens & (name_tokens | pc_tokens)
        if overlap:
            relevant.append(m)
    return len(relevant), relevant


def main() -> None:
    if not CORPUS_PATH.exists():
        print(f"ERROR: corpus not found at {CORPUS_PATH}", file=sys.stderr)
        print("Run build_corpus.py first to generate the corpus.", file=sys.stderr)
        sys.exit(1)

    corpus = load_corpus(CORPUS_PATH)
    print(f"Loaded {len(corpus)} benchmark queries from {CORPUS_PATH}")

    # Create a fresh temp directory for zero-state testing
    zero_home = pathlib.Path(tempfile.mkdtemp(prefix="borg_baseline_"))
    try:
        print(f"Zero-state HOME: {zero_home}")
        print(f"Running borg search for each query...")

        rows = []
        g1_pass = 0
        g2_pass = 0

        for entry in corpus:
            qid = entry["query_id"]
            query = entry["query"]
            expected = entry["expected_problem_class"]
            min_hits = entry["min_relevant_hits"]
            category = entry["category"]
            difficulty = entry["difficulty"]

            result = run_borg_search(query, hermes_home=zero_home)

            relevant_count, relevant_matches = evaluate_relevance(
                result["matches"], expected
            )

            g1 = 1 if result["matches_count"] >= 1 else 0
            g2 = 1 if result["matches_count"] >= 5 else 0
            g1_pass += g1
            g2_pass += g2

            # Determine sources of hits
            sources = list(set(m.get("source", "unknown") for m in result["matches"]))

            row = {
                "query_id": qid,
                "query": query,
                "category": category,
                "difficulty": difficulty,
                "expected_problem_class": expected,
                "matches_count": result["matches_count"],
                "matches_source": "|".join(sources) if sources else "none",
                "relevant_hit_count": relevant_count,
                "g1_pass": g1,
                "g2_pass": g2,
            }
            rows.append(row)

            print(
                f"  Q{qid:3d} | {category:8s} | hits={result['matches_count']:2d} "
                f"rel={relevant_count} | G1={'PASS' if g1 else 'FAIL':4s} | {query[:60]}"
            )
    finally:
        # Cleanup
        shutil.rmtree(zero_home, ignore_errors=True)

    # Write results CSV
    fieldnames = [
        "query_id", "query", "category", "difficulty",
        "expected_problem_class", "matches_count", "matches_source",
        "relevant_hit_count", "g1_pass", "g2_pass",
    ]
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n=== BASELINE RESULTS ===")
    print(f"Total queries:  {len(corpus)}")
    print(f"G1 pass (>=1 hit):  {g1_pass}/{len(corpus)} = {100*g1_pass/len(corpus):.1f}%  (target: >=80%)")
    print(f"G2 pass (>=5 hits): {g2_pass}/{len(corpus)} = {100*g2_pass/len(corpus):.1f}%  (target: >=95%)")
    print(f"Results written to: {RESULTS_PATH}")

    # Exit code: 0 if G1 >= 40/50 (80%), 1 otherwise
    if g1_pass < 40:
        print(f"\nWARNING: G1 pass rate {g1_pass}/{len(corpus)} is below 40/50 threshold.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
