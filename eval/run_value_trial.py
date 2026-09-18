#!/usr/bin/env python3
"""Run the preregistered no-Borg / empty-Borg / seeded-Borg GPT trial."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shlex
import shutil
import statistics
import subprocess
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from borg.core.traces import save_trace
from eval.value_trial_borg_tool import lookup

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKSET = ROOT / "eval" / "value_trial_taskset.json"
DEFAULT_OUT = ROOT / "eval" / "value_trial_20260918"
CONDITIONS = ["C0_no_borg", "C1_borg_empty", "C2_borg_seeded"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(item.relative_to(path)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def tracked_diff_hash() -> str:
    diff = subprocess.run(
        ["git", "diff", "--binary"], cwd=ROOT, capture_output=True, check=True,
    ).stdout
    return sha256_bytes(diff)


def root_task_path_state(tasks: list[dict]) -> dict[str, str | None]:
    state: dict[str, str | None] = {}
    for task in tasks:
        for rel in task["files"]:
            candidate = ROOT / rel
            state[rel] = file_hash(candidate) if candidate.is_file() else None
    return state


def build_hermes_environment(work: Path) -> dict[str, str]:
    env = dict(os.environ)
    # Hermes' terminal backend gives TERMINAL_CWD precedence over subprocess
    # cwd. Pin both carriers or parallel trials can edit the parent repository.
    env["TERMINAL_CWD"] = str(work)
    env["HERMES_CWD"] = str(work)
    env["HERMES_SAFE_MODE"] = "1"
    env["HERMES_IGNORE_USER_CONFIG"] = "1"
    env["HERMES_IGNORE_RULES"] = "1"
    env["HERMES_SESSION_SOURCE"] = "tool"
    return env


def build_hermes_command(prompt: str, usage_path: Path, max_turns: int | None) -> list[str]:
    hermes_executable = shutil.which("hermes")
    if not hermes_executable:
        raise RuntimeError("hermes executable not found")
    hermes_python = Path(hermes_executable).resolve().with_name("python3")
    if not hermes_python.is_file():
        raise RuntimeError(f"Hermes interpreter not found beside executable: {hermes_python}")
    turn_budget = 90 if max_turns is None else max_turns
    driver = (
        "import os, sys\n"
        "cwd = os.path.realpath(os.getcwd())\n"
        "sys.path[:] = [p for p in sys.path if p and os.path.realpath(p) != cwd]\n"
        "import cli\n"
        f"cli.CLI_CONFIG.setdefault('agent', {{}})['max_turns'] = {turn_budget!r}\n"
        "from hermes_cli.oneshot import run_oneshot\n"
        "raise SystemExit(run_oneshot("
        "sys.argv[1], model='gpt-5.6-sol', provider='openai-codex', "
        "toolsets='terminal,file', usage_file=sys.argv[2]))\n"
    )
    return [str(hermes_python), "-c", driver, prompt, str(usage_path)]


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_workspace(task: dict, base: Path) -> tuple[Path, dict[str, str]]:
    work = base / uuid.uuid4().hex
    work.mkdir(parents=True)
    hashes: dict[str, str] = {}
    for rel, content in task["files"].items():
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if rel.startswith("tests/"):
            hashes[rel] = file_hash(path)
    subprocess.run(["git", "init", "-q"], cwd=work, check=True)
    return work, hashes


def run_public(work: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3.12", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=work, capture_output=True, text=True, timeout=120,
    )


def run_hidden(work: Path, source: str) -> subprocess.CompletedProcess[str]:
    hidden = work / f".hidden_{uuid.uuid4().hex}.py"
    hidden.write_text(source, encoding="utf-8")
    try:
        return subprocess.run(
            ["python3.12", str(hidden)], cwd=work,
            capture_output=True, text=True, timeout=120,
        )
    finally:
        hidden.unlink(missing_ok=True)


def seed_database(tasks: list[dict], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for index, task in enumerate(tasks):
        seed = task["seed"]
        save_trace({
            "id": f"value-{index:02d}-{task['id'][:16]}",
            "task_description": f"{task['query_hint']} {task['prompt']}",
            "outcome": "success",
            "root_cause": seed["root_cause"],
            "approach_summary": seed["approach"],
            "files_read": "[]",
            "files_modified": "[]",
            "key_files": "[]",
            "tool_calls": 1,
            "errors_encountered": "[]",
            "dead_ends": json.dumps([seed["dead_end"]]),
            "keywords": task["query_hint"],
            "technology": "python",
            "error_patterns": task["query_hint"],
            "helpfulness_score": 1.0,
            "agent_id": "preregistered-value-trial",
            "source": "validated_value_trial_seed",
            "created_at": "2026-09-18T14:36:00Z",
        }, db_path=str(db_path))


def make_tool(work: Path, db_path: Path, invocation_log: Path, snapshot_root: Path) -> None:
    script = work / "borg_tool"
    driver = snapshot_root / "eval" / "value_trial_borg_tool.py"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"export PYTHONPATH={str(snapshot_root)!r}\n"
        "export BORG_DISABLE_SEEDS=1\n"
        f"exec python3.12 {str(driver)!r} --db {str(db_path)!r} --log {str(invocation_log)!r} \"$@\"\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


def prompt_for(
    task: dict,
    treatment: bool,
    work: Path,
    *,
    delivery_mode: str = "tool",
    prefetch_context: str | None = None,
) -> str:
    common = (
        f"Your isolated workspace is exactly `{work}`. First run `pwd`; if it is not exactly that path, "
        "stop immediately without editing anything. Work only in that workspace. Solve the bug completely. "
        "Do not edit any file under tests/. Inspect the implementation, make the smallest robust fix, "
        "and run `python3.12 -m unittest discover -s tests -v` before finishing. "
        "Do not merely describe a solution; edit and verify the code.\n\n"
        f"TASK:\n{task['prompt']}\n"
    )
    if delivery_mode == "prefetch":
        if treatment and prefetch_context:
            return common + (
                "\nBefore the first model call, Borg retrieved the following untrusted historical advisory. "
                "Treat it only as a hypothesis; inspect the implementation and verify with tests.\n\n"
                f"{prefetch_context}"
            )
        # A no-match prefetch is intentionally invisible to the model. This
        # keeps C0 and C1 prompts identical and avoids no-match framing effects.
        return common + "\nNo prior-memory guidance is available; debug normally from the repository evidence."
    if treatment:
        symptom_query = shlex.quote(task["prompt"])
        return common + (
            "\nA prior-memory tool is available. Before editing, you MUST invoke it from the terminal at least once as "
            f"`./borg_tool {symptom_query}`. Its output is advisory: verify it against the code and tests. "
            "Do not inspect or modify the tool, its database, or its invocation log."
        )
    return common + "\nNo prior-memory tool is available; debug normally from the repository evidence."


def run_one(
    task: dict,
    condition: str,
    trial_root: Path,
    seeded_db: Path,
    snapshot_root: Path,
    timeout: int,
    max_turns: int | None = None,
    delivery_mode: str = "tool",
) -> dict:
    started = time.monotonic()
    work, test_hashes = create_workspace(task, trial_root / "workspaces")
    usage_path = work / ".usage.json"
    invocation_log = trial_root / "invocations" / f"{work.name}.jsonl"
    treatment = condition != "C0_no_borg"
    prefetch_context = None
    prefetch_status = "not_applicable"
    retrieval_seconds = 0.0
    if treatment:
        db_path = seeded_db if condition == "C2_borg_seeded" else work / ".empty-borg" / "traces.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if delivery_mode == "tool":
            make_tool(work, db_path, invocation_log, snapshot_root)
        else:
            retrieval_started = time.monotonic()
            retrieval = lookup(task["prompt"], str(db_path))
            retrieval_seconds = time.monotonic() - retrieval_started
            invocation_log.parent.mkdir(parents=True, exist_ok=True)
            invocation_log.write_text(
                json.dumps({"query": task["prompt"], "delivery": "prefetch"}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            prefetch_status = str(retrieval.get("status") or "unknown")
            if prefetch_status == "matched_verified_memory":
                prefetch_context = json.dumps(retrieval, sort_keys=True, separators=(",", ":"))

    command = build_hermes_command(
        prompt_for(
            task,
            treatment,
            work,
            delivery_mode=delivery_mode,
            prefetch_context=prefetch_context,
        ),
        usage_path,
        max_turns,
    )
    model_error = None
    timed_out = False
    try:
        proc = subprocess.run(
            command,
            cwd=work,
            env=build_hermes_environment(work),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        model_rc = proc.returncode
        model_stdout = proc.stdout[-8000:]
        model_stderr = proc.stderr[-4000:]
    except subprocess.TimeoutExpired as exc:
        model_rc = 124
        timed_out = True
        model_error = f"timeout after {timeout}s"
        model_stdout = (exc.stdout or "")[-8000:] if isinstance(exc.stdout, str) else ""
        model_stderr = (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else ""

    public = run_public(work)
    hidden = run_hidden(work, task["hidden_test"])
    unchanged = all((work / rel).exists() and file_hash(work / rel) == digest for rel, digest in test_hashes.items())
    invocations = 0
    if invocation_log.exists():
        invocations = len([line for line in invocation_log.read_text(encoding="utf-8").splitlines() if line.strip()])
    if isinstance(model_stdout, bytes):
        model_stdout = model_stdout.decode("utf-8", errors="replace")
    if isinstance(model_stderr, bytes):
        model_stderr = model_stderr.decode("utf-8", errors="replace")
    command_accepted = timed_out or usage_path.exists()
    treatment_valid = (not treatment) or invocations >= 1
    if delivery_mode == "prefetch" and condition == "C1_borg_empty":
        treatment_valid = treatment_valid and prefetch_status == "no_confident_match"
    if delivery_mode == "prefetch" and condition == "C2_borg_seeded":
        treatment_valid = treatment_valid and prefetch_status == "matched_verified_memory"
    valid = command_accepted and treatment_valid
    usage = {}
    if usage_path.exists():
        try:
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            usage = {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    non_cache_tokens = (
        input_tokens + output_tokens
        if isinstance(input_tokens, (int, float)) and isinstance(output_tokens, (int, float))
        else None
    )
    success = bool(
        model_rc == 0 and valid and unchanged
        and public.returncode == 0 and hidden.returncode == 0
    )
    record = {
        "task_id": task["id"],
        "condition": condition,
        "success": success,
        "valid": valid,
        "harness_command_accepted": command_accepted,
        "timed_out": timed_out,
        "model_returncode": model_rc,
        "model_error": model_error,
        "public_tests_pass": public.returncode == 0,
        "hidden_grader_pass": hidden.returncode == 0,
        "test_files_unchanged": unchanged,
        "borg_invocations": invocations,
        "borg_delivery": delivery_mode,
        "prefetch_status": prefetch_status,
        "prefetch_context_chars": len(prefetch_context or ""),
        "retrieval_seconds": round(retrieval_seconds, 6),
        "wall_seconds": round(time.monotonic() - started, 3),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "non_cache_tokens": non_cache_tokens,
        "cache_read_tokens": usage.get("cache_read_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "estimated_cost_usd": usage.get("estimated_cost_usd"),
        "cost_status": usage.get("cost_status"),
        "api_calls": usage.get("api_calls"),
        "usage_completed": usage.get("completed"),
        "usage_failed": usage.get("failed"),
        "model": usage.get("model", "gpt-5.6-sol"),
        "provider": usage.get("provider", "openai-codex"),
        "model_stdout_tail": model_stdout,
        "model_stderr_tail": model_stderr,
        "public_test_tail": (public.stdout + public.stderr)[-2500:],
        "hidden_test_tail": (hidden.stdout + hidden.stderr)[-2500:],
        "workspace": str(work),
    }
    return record


def exact_mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    lower = min(b, c)
    tail = sum(math.comb(n, k) for k in range(lower + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def bootstrap_rd(rows: list[dict], a: str, b: str, iterations: int = 10000) -> tuple[float, float]:
    by_task = {}
    for row in rows:
        by_task.setdefault(row["task_id"], {})[row["condition"]] = int(bool(row["success"]))
    pairs = [(v[a], v[b]) for v in by_task.values() if a in v and b in v]
    if not pairs:
        return (float("nan"), float("nan"))
    rng = random.Random(20260918)
    diffs = []
    for _ in range(iterations):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        diffs.append(sum(y - x for x, y in sample) / len(sample))
    diffs.sort()
    return diffs[int(0.025 * iterations)], diffs[min(iterations - 1, int(0.975 * iterations))]


def bootstrap_median_ci(values: list[float], iterations: int = 10000) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(20260918)
    estimates = []
    for _ in range(iterations):
        sample = [values[rng.randrange(len(values))] for _ in values]
        estimates.append(statistics.median(sample))
    estimates.sort()
    return estimates[int(0.025 * iterations)], estimates[min(iterations - 1, int(0.975 * iterations))]


def paired_efficiency(rows: list[dict], left: str, right: str) -> dict:
    by_task: dict[str, dict[str, dict]] = {}
    for row in rows:
        by_task.setdefault(row["task_id"], {})[row["condition"]] = row
    complete = [
        values for values in by_task.values()
        if left in values and right in values
    ]
    solved = [values for values in complete if values[left]["success"] and values[right]["success"]]
    metrics = {}
    for key in (
        "wall_seconds", "retrieval_seconds", "total_tokens", "non_cache_tokens",
        "cache_read_tokens", "estimated_cost_usd", "api_calls",
    ):
        pairs = [
            (float(values[left][key]), float(values[right][key]))
            for values in solved
            if isinstance(values[left].get(key), (int, float))
            and isinstance(values[right].get(key), (int, float))
        ]
        deltas = [float(right_value - left_value) for left_value, right_value in pairs]
        percentages = [
            100.0 * (right_value - left_value) / left_value
            for left_value, right_value in pairs
            if left_value != 0
        ]
        ci = bootstrap_median_ci(deltas)
        metrics[key] = {
            "n_pairs": len(pairs),
            "median_paired_delta": statistics.median(deltas) if deltas else None,
            "median_paired_delta_ci95": [ci[0], ci[1]] if deltas else None,
            "median_paired_percent_change": statistics.median(percentages) if percentages else None,
            "right_lower_better": sum(delta < 0 for delta in deltas),
            "tie": sum(delta == 0 for delta in deltas),
            "left_lower_better": sum(delta > 0 for delta in deltas),
        }
    return {
        "n_complete_pairs": len(complete),
        "n_both_solved_pairs": len(solved),
        "eligibility": "metric comparisons include only task pairs solved by both conditions",
        "metrics": metrics,
    }


def summarize(
    rows: list[dict],
    taskset: dict,
    fingerprints: dict,
    preregistration: str | None = None,
) -> dict:
    per_condition = {}
    for condition in CONDITIONS:
        group = [row for row in rows if row["condition"] == condition]
        solved = sum(bool(row["success"]) for row in group)
        valid = sum(bool(row["valid"]) for row in group)
        def med(key: str):
            vals = [row[key] for row in group if isinstance(row.get(key), (int, float))]
            return statistics.median(vals) if vals else None
        per_condition[condition] = {
            "n": len(group), "valid": valid, "solved": solved,
            "solve_rate": solved / len(group) if group else None,
            "median_wall_seconds": med("wall_seconds"),
            "median_retrieval_seconds": med("retrieval_seconds"),
            "median_total_tokens": med("total_tokens"),
            "median_non_cache_tokens": med("non_cache_tokens"),
            "median_cache_read_tokens": med("cache_read_tokens"),
            "median_estimated_cost_usd": med("estimated_cost_usd"),
            "median_api_calls": med("api_calls"),
            "total_borg_invocations": sum(row["borg_invocations"] for row in group),
        }
    paired = {}
    efficiency = {}
    for left, right in [("C0_no_borg", "C1_borg_empty"), ("C1_borg_empty", "C2_borg_seeded"), ("C0_no_borg", "C2_borg_seeded")]:
        task_rows = {}
        for row in rows:
            task_rows.setdefault(row["task_id"], {})[row["condition"]] = bool(row["success"])
        pairs = [(v[left], v[right]) for v in task_rows.values() if left in v and right in v]
        b = sum((not x) and y for x, y in pairs)
        c = sum(x and (not y) for x, y in pairs)
        rd = (sum(y for _, y in pairs) - sum(x for x, _ in pairs)) / len(pairs) if pairs else None
        ci = bootstrap_rd(rows, left, right)
        paired[f"{right}_minus_{left}"] = {
            "n_pairs": len(pairs), "risk_difference": rd,
            "bootstrap_ci95": [ci[0], ci[1]],
            "discordant_left_fail_right_pass": b,
            "discordant_left_pass_right_fail": c,
            "mcnemar_exact_two_sided_p": exact_mcnemar_p(b, c),
        }
        efficiency[f"{right}_minus_{left}"] = paired_efficiency(rows, left, right)
    negative_transfer = []
    by_task = {}
    for row in rows:
        by_task.setdefault(row["task_id"], {})[row["condition"]] = bool(row["success"])
    for task_id, values in by_task.items():
        if values.get("C0_no_borg") and values.get("C1_borg_empty") and not values.get("C2_borg_seeded"):
            negative_transfer.append(task_id)
    command_rejections = sum(row.get("harness_command_accepted") is False for row in rows)
    if command_rejections:
        trial_status = "invalid_harness_command"
    elif len(rows) == len(taskset["tasks"]) * 3:
        trial_status = "completed"
    else:
        trial_status = "incomplete"
    return {
        "schema_version": 3,
        "generated_at_utc": utc_now(),
        "trial_status": trial_status,
        "delivery_modes": sorted({str(row.get("borg_delivery", "tool")) for row in rows}),
        "token_accounting": (
            "total_tokens includes provider-reported cache reads; non_cache_tokens is input_tokens + output_tokens. "
            "Reasoning tokens, when separately reported, are a subset of output tokens and are not added again."
        ),
        "harness_command_rejections": command_rejections,
        "preregistration": preregistration or taskset.get("artifact") or str(DEFAULT_TASKSET.relative_to(ROOT)),
        "model": taskset["model"],
        "n_tasks": len(taskset["tasks"]),
        "n_runs_expected": len(taskset["tasks"]) * 3,
        "n_runs_observed": len(rows),
        "per_condition": per_condition,
        "paired_contrasts": paired,
        "paired_efficiency": efficiency,
        "negative_transfer_tasks": negative_transfer,
        "primary_contrast": paired.get("C2_borg_seeded_minus_C1_borg_empty"),
        "fingerprints": fingerprints,
        "claim_boundary": (
            "This pilot has a solve-rate ceiling: every arm solved every task, so it provides no evidence of solve-rate lift. "
            "Efficiency findings are directional secondary metrics only. Proven value requires a harder powered preregistered "
            "replication whose primary C2-C1 confidence interval excludes zero."
            if rows and all(bool(row["success"]) for row in rows)
            else "Directional pilot only. Proven lift requires a powered preregistered replication with the C2-C1 confidence interval excluding zero."
        ),
    }


def render_report(summary: dict) -> str:
    lines = [
        "# Borg C0/C1/C2 GPT value trial", "",
        f"Generated: `{summary['generated_at_utc']}`", "",
        "## Verdict", "",
    ]
    primary = summary["primary_contrast"] or {}
    rd = primary.get("risk_difference")
    ci = primary.get("bootstrap_ci95")
    p = primary.get("mcnemar_exact_two_sided_p")
    if summary["trial_status"].startswith("invalid"):
        verdict = "INVALID — the harness command was rejected before agent execution; no value claim is permitted."
    elif rd is None:
        verdict = "INCOMPLETE — the primary contrast could not be computed."
    elif rd > 0 and ci and ci[0] > 0 and not summary["negative_transfer_tasks"]:
        verdict = "POSITIVE IN THIS TRIAL — seeded Borg beat empty Borg with a CI above zero; replication is still required."
    elif rd > 0:
        verdict = "DIRECTIONAL ONLY — seeded Borg beat empty Borg descriptively, but uncertainty includes no effect."
    elif rd == 0:
        verdict = "NULL — seeded Borg did not improve solve rate over empty Borg in this trial."
    else:
        verdict = "NEGATIVE — seeded Borg underperformed empty Borg in this trial."
    lines += [verdict, "", f"Primary C2-C1 risk difference: `{rd}`; paired bootstrap 95% CI: `{ci}`; exact McNemar p: `{p}`.", ""]
    lines += [
        "## Per condition", "",
        "| condition | solved / n | rate | median seconds | median non-cache tokens | median cache-read tokens | median total tokens | median API calls | Borg calls |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        value = summary["per_condition"][condition]
        lines.append(
            f"| {condition} | {value['solved']} / {value['n']} | {value['solve_rate']:.3f} | "
            f"{value['median_wall_seconds']} | {value['median_non_cache_tokens']} | "
            f"{value['median_cache_read_tokens']} | {value['median_total_tokens']} | "
            f"{value['median_api_calls']} | {value['total_borg_invocations']} |"
        )
    lines += [
        "", "Token accounting", "",
        summary["token_accounting"], "",
        "## Claim boundary", "", summary["claim_boundary"], "",
    ]
    efficiency = summary.get("paired_efficiency", {}).get("C2_borg_seeded_minus_C1_borg_empty", {})
    if efficiency:
        lines += [
            "## Paired efficiency: seeded Borg versus empty Borg", "",
            "Only task pairs solved by both conditions are included; negative deltas favor seeded Borg.", "",
            "| metric | pairs | median paired delta | bootstrap 95% CI | median % change | seeded lower | tie | empty lower |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for metric, value in efficiency["metrics"].items():
            lines.append(
                f"| {metric} | {value['n_pairs']} | {value['median_paired_delta']} | "
                f"{value['median_paired_delta_ci95']} | {value['median_paired_percent_change']} | "
                f"{value['right_lower_better']} | {value['tie']} | {value['left_lower_better']} |"
            )
        lines.append("")
    if summary["negative_transfer_tasks"]:
        lines += ["## Negative transfer", "", ", ".join(summary["negative_transfer_tasks"]), ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taskset", type=Path, default=DEFAULT_TASKSET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=480)
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--delivery-mode", choices=("tool", "prefetch"), default="tool")
    parser.add_argument("--task", action="append", dest="task_ids")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.max_turns is not None and args.max_turns < 1:
        parser.error("--max-turns must be >= 1")

    taskset = json.loads(args.taskset.read_text(encoding="utf-8"))
    tasks = taskset["tasks"]
    max_turns = args.max_turns or taskset.get("model", {}).get("max_turns")
    if max_turns is not None and (not isinstance(max_turns, int) or max_turns < 1):
        parser.error("taskset model.max_turns must be a positive integer")
    if args.task_ids:
        wanted = set(args.task_ids)
        tasks = [task for task in tasks if task["id"] in wanted]
        taskset = dict(taskset, tasks=tasks)
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output dir: {out}")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.taskset, out / "preregistration.json")

    trial_root = Path(tempfile.mkdtemp(prefix="borg-value-trial-"))
    snapshot_root = trial_root / "immutable_source"
    shutil.copytree(ROOT / "borg", snapshot_root / "borg")
    (snapshot_root / "eval").mkdir(parents=True)
    shutil.copy2(ROOT / "eval" / "value_trial_borg_tool.py", snapshot_root / "eval" / "value_trial_borg_tool.py")
    seeded_db = trial_root / uuid.uuid4().hex / "traces.db"
    seed_database(tasks, seeded_db)
    empty_probe = trial_root / uuid.uuid4().hex / "traces.db"

    # Preflight task and treatment separation before spending model calls.
    preflight = []
    for task in tasks:
        work, _ = create_workspace(task, trial_root / "preflight")
        public = run_public(work)
        hidden = run_hidden(work, task["hidden_test"])
        empty = lookup(task["prompt"], str(empty_probe))
        seeded = lookup(task["prompt"], str(seeded_db))
        row = {
            "task_id": task["id"],
            "public_baseline_pass": public.returncode == 0,
            "hidden_baseline_fail": hidden.returncode != 0,
            "empty_status": empty["status"],
            "seeded_status": seeded["status"],
        }
        preflight.append(row)
        if not all([
            row["public_baseline_pass"], row["hidden_baseline_fail"],
            row["empty_status"] == "no_confident_match",
            row["seeded_status"] == "matched_verified_memory",
        ]):
            write_json(out / "preflight.json", preflight)
            raise SystemExit(f"preflight failed for {task['id']}: {row}")
    write_json(out / "preflight.json", preflight)

    wheel = ROOT / "dist" / "agent_borg-3.3.21-py3-none-any.whl"
    fingerprints = {
        "source_version": "3.3.21",
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty_diff_sha256": tracked_diff_hash(),
        "immutable_runtime_snapshot_sha256": tree_hash(snapshot_root),
        "wheel_sha256": file_hash(wheel) if wheel.exists() else None,
        "taskset_sha256": file_hash(args.taskset),
        "delivery_mode": args.delivery_mode,
    }
    write_json(out / "fingerprints.json", fingerprints)

    if args.preflight_only:
        print(json.dumps({"status": "preflight_passed", "tasks": len(tasks), "fingerprints": fingerprints}, indent=2))
        return 0

    rows: list[dict] = []
    jsonl = out / "results.jsonl"
    parent_diff_before = tracked_diff_hash()
    parent_paths_before = root_task_path_state(tasks)
    for index, task in enumerate(tasks):
        order = CONDITIONS[index % 3:] + CONDITIONS[:index % 3]
        print(f"TASK {index + 1}/{len(tasks)} {task['id']} order={order}", flush=True)
        with ThreadPoolExecutor(max_workers=min(args.workers, 3)) as pool:
            futures = {
                pool.submit(
                    run_one,
                    task,
                    condition,
                    trial_root,
                    seeded_db,
                    snapshot_root,
                    args.timeout,
                    max_turns,
                    args.delivery_mode,
                ): condition
                for condition in order
            }
            wave = []
            for future in as_completed(futures):
                row = future.result()
                wave.append(row)
                print(
                    f"  {row['condition']}: success={row['success']} valid={row['valid']} "
                    f"borg={row['borg_invocations']} tokens={row['total_tokens']} sec={row['wall_seconds']}",
                    flush=True,
                )
            wave.sort(key=lambda row: CONDITIONS.index(row["condition"]))
            for row in wave:
                rows.append(row)
                with jsonl.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
        if tracked_diff_hash() != parent_diff_before or root_task_path_state(tasks) != parent_paths_before:
            failure = {
                "status": "invalid_parent_workspace_contamination",
                "task_id": task["id"],
                "generated_at_utc": utc_now(),
            }
            write_json(out / "INVALID.json", failure)
            raise SystemExit(f"parent workspace contamination detected after {task['id']}")

    try:
        preregistration = str(args.taskset.resolve().relative_to(ROOT))
    except ValueError:
        preregistration = str(args.taskset.resolve())
    summary = summarize(rows, taskset, fingerprints, preregistration)
    write_json(out / "summary.json", summary)
    (out / "REPORT.md").write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0 if summary["trial_status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
