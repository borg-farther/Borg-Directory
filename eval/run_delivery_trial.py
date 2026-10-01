#!/usr/bin/env python3
"""Run the preregistered Borg tool-turn versus pre-LLM prefetch study."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from eval.run_value_trial import (
    ROOT,
    bootstrap_median_ci,
    create_workspace,
    file_hash,
    root_task_path_state,
    run_hidden,
    run_one,
    run_public,
    seed_database,
    tracked_diff_hash,
    tree_hash,
    utc_now,
    write_json,
)
from eval.value_trial_borg_tool import lookup

ARMS = {
    "T0_tool_empty": ("C1_borg_empty", "tool"),
    "T1_tool_seeded": ("C2_borg_seeded", "tool"),
    "P0_prefetch_empty": ("C1_borg_empty", "prefetch"),
    "P1_prefetch_seeded": ("C2_borg_seeded", "prefetch"),
}
METRICS = (
    "api_calls",
    "non_cache_tokens",
    "wall_seconds",
    "total_tokens",
    "cache_read_tokens",
    "retrieval_seconds",
    "estimated_cost_usd",
)


def _paired_metrics(rows: list[dict], left: str, right: str) -> dict:
    by_task: dict[str, dict[str, dict]] = {}
    for row in rows:
        by_task.setdefault(row["task_id"], {})[row["condition"]] = row
    complete = [values for values in by_task.values() if left in values and right in values]
    both_solved = [values for values in complete if values[left]["success"] and values[right]["success"]]
    metrics = {}
    for key in METRICS:
        pairs = [
            (float(values[left][key]), float(values[right][key]))
            for values in both_solved
            if isinstance(values[left].get(key), (int, float))
            and isinstance(values[right].get(key), (int, float))
        ]
        deltas = [right_value - left_value for left_value, right_value in pairs]
        percentages = [
            100.0 * (right_value - left_value) / left_value
            for left_value, right_value in pairs
            if left_value != 0
        ]
        ci = bootstrap_median_ci(deltas)
        metrics[key] = {
            "n_pairs": len(pairs),
            "median_paired_delta": statistics.median(deltas) if deltas else None,
            "median_paired_delta_ci95": list(ci) if deltas else None,
            "median_paired_percent_change": statistics.median(percentages) if percentages else None,
            "prefetch_lower": sum(delta < 0 for delta in deltas),
            "tie": sum(delta == 0 for delta in deltas),
            "tool_lower": sum(delta > 0 for delta in deltas),
        }
    negative_transfer = [
        task_id
        for task_id, values in by_task.items()
        if values.get(left, {}).get("success") and not values.get(right, {}).get("success")
    ]
    return {
        "left": left,
        "right": right,
        "delta_definition": "right minus left; negative favors prefetch",
        "n_complete_pairs": len(complete),
        "n_both_solved_pairs": len(both_solved),
        "negative_transfer_tasks": negative_transfer,
        "metrics": metrics,
    }


def _median(rows: list[dict], key: str):
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    return statistics.median(values) if values else None


def summarize(rows: list[dict], prereg: dict, fingerprints: dict) -> dict:
    per_condition = {}
    for arm in ARMS:
        group = [row for row in rows if row["condition"] == arm]
        per_condition[arm] = {
            "n": len(group),
            "valid": sum(bool(row["valid"]) for row in group),
            "solved": sum(bool(row["success"]) for row in group),
            "solve_rate": sum(bool(row["success"]) for row in group) / len(group) if group else None,
            **{f"median_{key}": _median(group, key) for key in METRICS},
            "total_borg_invocations": sum(int(row["borg_invocations"]) for row in group),
        }
    primary = _paired_metrics(rows, "T1_tool_seeded", "P1_prefetch_seeded")
    empty = _paired_metrics(rows, "T0_tool_empty", "P0_prefetch_empty")
    api_delta = primary["metrics"]["api_calls"]["median_paired_delta"]
    token_delta = primary["metrics"]["non_cache_tokens"]["median_paired_delta"]
    all_valid = len(rows) == len(prereg["task_ids"]) * len(ARMS) and all(row["valid"] for row in rows)
    improved = bool(
        all_valid
        and not primary["negative_transfer_tasks"]
        and isinstance(api_delta, (int, float)) and api_delta < 0
        and isinstance(token_delta, (int, float)) and token_delta < 0
    )
    status = "completed" if len(rows) == len(prereg["task_ids"]) * len(ARMS) else "incomplete"
    verdict = (
        "DIRECTIONAL_MECHANISM_IMPROVEMENT"
        if improved
        else "MECHANISM_NOT_IMPROVED_UNDER_PREREGISTERED_RULE"
    ) if status == "completed" else "INCOMPLETE"
    return {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "trial_status": status,
        "verdict": verdict,
        "all_runs_valid": all_valid,
        "n_tasks": len(prereg["task_ids"]),
        "n_runs_expected": len(prereg["task_ids"]) * len(ARMS),
        "n_runs_observed": len(rows),
        "per_condition": per_condition,
        "primary_seeded_prefetch_minus_tool": primary,
        "secondary_empty_prefetch_minus_tool": empty,
        "fingerprints": fingerprints,
        "token_accounting": (
            "total_tokens includes provider-reported cache reads; non_cache_tokens is input_tokens + output_tokens. "
            "Reasoning tokens are not added separately because provider usage counts them inside output tokens."
        ),
        "claim_boundary": prereg["decision_rule"]["claim_boundary"],
    }


def render_report(summary: dict) -> str:
    lines = [
        "# Borg delivery mechanism trial", "",
        f"**Verdict:** `{summary['verdict']}`", "",
        "This compares mandatory agent tool lookup with pre-first-call retrieval. It reuses the frozen v2 tasks and is not independent evidence of general solve-rate lift.", "",
        "## Per condition", "",
        "| condition | solved | valid | median calls | median non-cache tokens | median cache reads | median seconds |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        value = summary["per_condition"][arm]
        lines.append(
            f"| {arm} | {value['solved']}/{value['n']} | {value['valid']}/{value['n']} | "
            f"{value['median_api_calls']} | {value['median_non_cache_tokens']} | "
            f"{value['median_cache_read_tokens']} | {value['median_wall_seconds']} |"
        )
    lines += ["", "## Primary paired contrast", ""]
    primary = summary["primary_seeded_prefetch_minus_tool"]
    lines.append("Negative deltas favor prefetch. Only pairs solved by both conditions are included for efficiency metrics.")
    lines += ["", "| metric | pairs | median delta | 95% bootstrap CI | prefetch lower | tie | tool lower |", "|---|---:|---:|---:|---:|---:|---:|"]
    for metric, value in primary["metrics"].items():
        lines.append(
            f"| {metric} | {value['n_pairs']} | {value['median_paired_delta']} | "
            f"{value['median_paired_delta_ci95']} | {value['prefetch_lower']} | {value['tie']} | {value['tool_lower']} |"
        )
    lines += [
        "", f"Negative-transfer tasks: `{primary['negative_transfer_tasks']}`", "",
        "## Token accounting", "", summary["token_accounting"], "",
        "## Claim boundary", "", summary["claim_boundary"], "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, default=ROOT / "eval" / "delivery_trial_preregistration.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval" / "delivery_trial_20260918")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=480)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    prereg = json.loads(args.preregistration.read_text(encoding="utf-8"))
    taskset_path = ROOT / prereg["source_taskset"]
    if file_hash(taskset_path) != prereg["source_taskset_sha256"]:
        raise SystemExit("source taskset hash differs from preregistration")
    taskset = json.loads(taskset_path.read_text(encoding="utf-8"))
    by_id = {task["id"]: task for task in taskset["tasks"]}
    tasks = [by_id[task_id] for task_id in prereg["task_ids"]]

    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output dir: {out}")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.preregistration, out / "preregistration.json")

    trial_root = Path(tempfile.mkdtemp(prefix="borg-delivery-trial-"))
    snapshot_root = trial_root / "immutable_source"
    shutil.copytree(ROOT / "borg", snapshot_root / "borg")
    (snapshot_root / "eval").mkdir(parents=True)
    shutil.copy2(ROOT / "eval" / "value_trial_borg_tool.py", snapshot_root / "eval" / "value_trial_borg_tool.py")
    seeded_db = trial_root / uuid.uuid4().hex / "traces.db"
    seed_database(tasks, seeded_db)
    empty_db = trial_root / uuid.uuid4().hex / "traces.db"

    preflight = []
    for task in tasks:
        work, _ = create_workspace(task, trial_root / "preflight")
        row = {
            "task_id": task["id"],
            "public_baseline_pass": run_public(work).returncode == 0,
            "hidden_baseline_fail": run_hidden(work, task["hidden_test"]).returncode != 0,
            "empty_status": lookup(task["prompt"], str(empty_db))["status"],
            "seeded_status": lookup(task["prompt"], str(seeded_db))["status"],
        }
        preflight.append(row)
        if not all((
            row["public_baseline_pass"],
            row["hidden_baseline_fail"],
            row["empty_status"] == "no_confident_match",
            row["seeded_status"] == "matched_verified_memory",
        )):
            write_json(out / "preflight.json", preflight)
            raise SystemExit(f"preflight failed: {row}")
    write_json(out / "preflight.json", preflight)

    fingerprints = {
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty_diff_sha256": tracked_diff_hash(),
        "preregistration_sha256": file_hash(args.preregistration),
        "taskset_sha256": file_hash(taskset_path),
        "immutable_runtime_snapshot_sha256": tree_hash(snapshot_root),
        "model": prereg["model"],
    }
    write_json(out / "fingerprints.json", fingerprints)
    if args.preflight_only:
        print(json.dumps({"status": "preflight_passed", "tasks": len(tasks), "fingerprints": fingerprints}, indent=2))
        return 0

    rows: list[dict] = []
    results_path = out / "results.jsonl"
    parent_diff_before = tracked_diff_hash()
    parent_paths_before = root_task_path_state(tasks)
    arm_names = list(ARMS)
    for index, task in enumerate(tasks):
        order = arm_names[index % len(arm_names):] + arm_names[:index % len(arm_names)]
        print(f"TASK {index + 1}/{len(tasks)} {task['id']} order={order}", flush=True)
        with ThreadPoolExecutor(max_workers=min(args.workers, len(ARMS))) as pool:
            futures = {}
            for arm in order:
                base_condition, delivery_mode = ARMS[arm]
                future = pool.submit(
                    run_one,
                    task,
                    base_condition,
                    trial_root,
                    seeded_db,
                    snapshot_root,
                    args.timeout,
                    int(prereg["model"]["max_turns"]),
                    delivery_mode,
                )
                futures[future] = arm
            wave = []
            for future in as_completed(futures):
                arm = futures[future]
                row = future.result()
                row["base_condition"] = row["condition"]
                row["condition"] = arm
                wave.append(row)
                print(
                    f"  {arm}: success={row['success']} valid={row['valid']} calls={row['api_calls']} "
                    f"noncache={row['non_cache_tokens']} sec={row['wall_seconds']}",
                    flush=True,
                )
            wave.sort(key=lambda row: arm_names.index(row["condition"]))
            with results_path.open("a", encoding="utf-8") as handle:
                for row in wave:
                    rows.append(row)
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        if tracked_diff_hash() != parent_diff_before or root_task_path_state(tasks) != parent_paths_before:
            write_json(out / "INVALID.json", {"status": "invalid_parent_workspace_contamination", "task_id": task["id"]})
            raise SystemExit(f"parent workspace contamination detected after {task['id']}")

    summary = summarize(rows, prereg, fingerprints)
    write_json(out / "summary.json", summary)
    (out / "REPORT.md").write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0 if summary["trial_status"] == "completed" and summary["all_runs_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
