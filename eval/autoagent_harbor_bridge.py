#!/usr/bin/env python3
"""Bridge AutoAgent/Harbor trial outputs into Borg eval instrumentation.

Borg-first design goals:
1) Deterministic Harbor -> BorgTaskRecord mapping
2) Optional strict schema validation (for production-gate use)
3) Optional provenance manifest generation/verification
4) Arm auto-detection fallback when not explicitly provided
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    # Package-style imports (pytest, module execution)
    from eval.instrumentation_schema import BorgTaskRecord, evaluate, record_task
except ModuleNotFoundError:
    # Script-style imports (python eval/autoagent_harbor_bridge.py)
    from instrumentation_schema import BorgTaskRecord, evaluate, record_task

REQUIRED_TRIAL_KEYS = {
    "trial_name",
    "task_name",
    "task_id",
    "started_at",
    "finished_at",
    "agent_result",
    "verifier_result",
}


@dataclass
class ConvertedTrial:
    trial_name: str
    record: BorgTaskRecord


@dataclass
class ValidationResult:
    valid: bool
    warnings: list[str]


class TrialValidationError(ValueError):
    pass


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _latency_seconds(result: dict[str, Any]) -> float:
    start = _parse_ts(result.get("started_at"))
    end = _parse_ts(result.get("finished_at"))
    if not start or not end:
        return 0.0
    return max((end - start).total_seconds(), 0.0)


def _completion_status_from_reward(reward: Optional[float]) -> int:
    if reward is None:
        return 0
    if reward >= 0.99:
        return 2
    if reward > 0.0:
        return 1
    return 0


def _extract_reward(result: dict[str, Any]) -> Optional[float]:
    vr = result.get("verifier_result") or {}
    rewards = vr.get("rewards") or {}
    reward = rewards.get("reward")
    if reward is None:
        return None
    try:
        return float(reward)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _trial_result_paths(job_dir: Path) -> Iterable[Path]:
    for path in job_dir.glob("*/result.json"):
        if path.is_file():
            yield path


def _infer_task_bucket(task_name: str, task_id_path: str, default_bucket: str = "B") -> str:
    text = f"{task_name} {task_id_path}".lower()
    if any(k in text for k in ("hard", "complex", "swebench")):
        return "C"
    if any(k in text for k in ("easy", "smoke", "sanity")):
        return "A"
    return default_bucket


def _infer_arm(explicit_arm: Optional[str], trial_result: dict[str, Any]) -> str:
    if explicit_arm and explicit_arm in {"control", "treatment"}:
        return explicit_arm
    metadata = ((trial_result.get("agent_result") or {}).get("metadata") or {})
    pack_name = metadata.get("pack_name")
    return "treatment" if pack_name else "control"


def _load_trajectory_metrics(trial_dir: Path) -> tuple[int, int, int]:
    traj = trial_dir / "agent" / "trajectory.json"
    if not traj.exists():
        return 0, 0, 0

    try:
        data = _load_json(traj)
    except Exception:
        return 0, 0, 0

    steps = data.get("steps", [])
    tool_call_count = sum(len((step.get("tool_calls") or [])) for step in steps)

    final_metrics = data.get("final_metrics") or {}
    prompt_tokens = final_metrics.get("total_prompt_tokens")
    guidance_token_count = max(int(prompt_tokens * 0.05), 0) if isinstance(prompt_tokens, int) else 0

    # Harbor trajectories do not expose trace retrieval counts directly.
    return tool_call_count, 0, guidance_token_count


def validate_trial_result(trial_result: dict[str, Any], *, strict: bool = False) -> ValidationResult:
    warnings: list[str] = []

    missing = [k for k in REQUIRED_TRIAL_KEYS if k not in trial_result]
    if missing:
        msg = f"missing required keys: {sorted(missing)}"
        if strict:
            raise TrialValidationError(msg)
        warnings.append(msg)

    task_id = trial_result.get("task_id")
    if task_id is not None and not isinstance(task_id, dict):
        msg = "task_id should be an object"
        if strict:
            raise TrialValidationError(msg)
        warnings.append(msg)

    reward = _extract_reward(trial_result)
    if reward is None:
        msg = "reward missing or non-numeric"
        if strict:
            raise TrialValidationError(msg)
        warnings.append(msg)

    latency = _latency_seconds(trial_result)
    if latency <= 0.0:
        warnings.append("non-positive latency derived from timestamps")

    return ValidationResult(valid=len(missing) == 0 and reward is not None, warnings=warnings)


def build_provenance_manifest(job_dir: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for result_path in sorted(_trial_result_paths(job_dir)):
        trial_dir = result_path.parent
        trajectory_path = trial_dir / "agent" / "trajectory.json"
        verifier_reward_path = trial_dir / "verifier" / "reward.txt"

        entry: dict[str, Any] = {
            "trial_dir": str(trial_dir),
            "result_json": {
                "path": str(result_path),
                "sha256": _sha256(result_path),
            },
        }

        if trajectory_path.exists():
            entry["trajectory_json"] = {
                "path": str(trajectory_path),
                "sha256": _sha256(trajectory_path),
            }
        if verifier_reward_path.exists():
            entry["verifier_reward_txt"] = {
                "path": str(verifier_reward_path),
                "sha256": _sha256(verifier_reward_path),
            }

        entries.append(entry)

    return {
        "schema_version": "borg.autoagent.provenance.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "job_dir": str(job_dir),
        "trial_count": len(entries),
        "entries": entries,
    }


def verify_provenance_manifest(job_dir: Path, manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    current = build_provenance_manifest(job_dir)

    expected_entries = manifest.get("entries") or []
    current_entries = current.get("entries") or []

    by_result = {
        (e.get("result_json") or {}).get("path"): e
        for e in expected_entries
    }
    current_by_result = {
        (e.get("result_json") or {}).get("path"): e
        for e in current_entries
    }

    for result_path, expected in by_result.items():
        actual = current_by_result.get(result_path)
        if not actual:
            errors.append(f"missing trial in current job: {result_path}")
            continue

        for key in ("result_json", "trajectory_json", "verifier_reward_txt"):
            e_node = expected.get(key)
            if not e_node:
                continue
            a_node = actual.get(key)
            if not a_node:
                errors.append(f"missing {key} for {result_path}")
                continue
            if e_node.get("sha256") != a_node.get("sha256"):
                errors.append(f"sha mismatch for {key} in {result_path}")

    return len(errors) == 0, errors


def convert_trial_result(
    trial_result: dict[str, Any],
    trial_dir: Path,
    *,
    experiment_id: str,
    arm: str,
    borg_version: str,
    default_bucket: str = "B",
) -> ConvertedTrial:
    trial_name = trial_result.get("trial_name") or trial_dir.name
    task_name = trial_result.get("task_name") or ""
    task_id_path = ((trial_result.get("task_id") or {}).get("path") or "")

    reward = _extract_reward(trial_result)
    completion_status = _completion_status_from_reward(reward)
    latency_seconds = _latency_seconds(trial_result)

    agent_result = trial_result.get("agent_result") or {}
    metadata = agent_result.get("metadata") or {}
    pack_name = metadata.get("pack_name")
    model_name = ((trial_result.get("config") or {}).get("agent") or {}).get("model_name") or ""

    input_tokens = agent_result.get("n_input_tokens") or 0
    output_tokens = agent_result.get("n_output_tokens") or 0
    tokens_total = int(input_tokens) + int(output_tokens)

    tool_call_count, trace_count_injected, guidance_token_count = _load_trajectory_metrics(trial_dir)

    severe_failure = trial_result.get("exception_info") is not None
    bucket = _infer_task_bucket(task_name, task_id_path, default_bucket=default_bucket)

    record = BorgTaskRecord(
        experiment_id=experiment_id,
        experiment_arm=arm,
        borg_version=borg_version,
        model_version=model_name,
        task_id=task_id_path or task_name or trial_name,
        task_bucket=bucket,
        task_type="harbor",
        task_title=task_name,
        complexity_band="medium",
        tool_heavy=tool_call_count >= 5,
        trace_retrieved=bool(pack_name),
        trace_ids_used=[pack_name] if pack_name else [],
        trace_count_injected=trace_count_injected,
        trace_relevance_scores=[],
        guidance_token_count=guidance_token_count,
        guidance_followed=True if pack_name else None,
        completion_status=completion_status,
        tokens_total=tokens_total,
        latency_seconds=latency_seconds,
        tools_called=["shell"] if tool_call_count > 0 else [],
        tool_call_count=tool_call_count,
        errors_encountered=[str(trial_result.get("exception_info"))] if severe_failure else [],
        severe_failure=severe_failure,
        human_intervention=False,
        cost_usd=float(agent_result.get("cost_usd") or 0.0),
    )

    return ConvertedTrial(trial_name=trial_name, record=record)


def ingest_job_dir(
    job_dir: Path,
    *,
    experiment_id: str,
    arm: Optional[str],
    borg_version: str,
    dry_run: bool = False,
    strict: bool = False,
) -> tuple[list[ConvertedTrial], list[str]]:
    converted: list[ConvertedTrial] = []
    warnings: list[str] = []

    for result_path in sorted(_trial_result_paths(job_dir)):
        trial_dir = result_path.parent
        trial_result = _load_json(result_path)

        if "trial_name" not in trial_result:
            continue

        validation = validate_trial_result(trial_result, strict=strict)
        if validation.warnings:
            warnings.extend([f"{trial_dir.name}: {w}" for w in validation.warnings])

        resolved_arm = _infer_arm(arm, trial_result)
        trial = convert_trial_result(
            trial_result,
            trial_dir,
            experiment_id=experiment_id,
            arm=resolved_arm,
            borg_version=borg_version,
        )
        converted.append(trial)
        if not dry_run:
            record_task(trial.record)

    return converted, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest AutoAgent/Harbor results into Borg eval DB")
    parser.add_argument("--job-dir", required=True, help="Path to Harbor job directory (contains trial subdirs)")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--arm", default="auto", choices=["auto", "control", "treatment"])
    parser.add_argument("--borg-version", default="3.3.1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail on missing required trial fields")
    parser.add_argument("--write-manifest", help="Write provenance manifest JSON to this path")
    parser.add_argument("--verify-manifest", help="Verify job artifacts against an existing manifest JSON")
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    job_dir = Path(args.job_dir)
    if not job_dir.exists() or not job_dir.is_dir():
        raise SystemExit(f"job directory not found: {job_dir}")

    if args.verify_manifest:
        manifest_path = Path(args.verify_manifest)
        if not manifest_path.exists():
            raise SystemExit(f"manifest not found: {manifest_path}")
        manifest = _load_json(manifest_path)
        ok, errors = verify_provenance_manifest(job_dir, manifest)
        if not ok:
            print("manifest_verification=FAIL")
            for e in errors:
                print(f"  - {e}")
            return 2
        print("manifest_verification=PASS")

    manifest = build_provenance_manifest(job_dir)
    if args.write_manifest:
        out = Path(args.write_manifest)
        out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"manifest_written={out}")

    resolved_arm = None if args.arm == "auto" else args.arm
    trials, warnings = ingest_job_dir(
        job_dir,
        experiment_id=args.experiment_id,
        arm=resolved_arm,
        borg_version=args.borg_version,
        dry_run=args.dry_run,
        strict=args.strict,
    )

    print(f"converted_trials={len(trials)} dry_run={args.dry_run} strict={args.strict}")
    if warnings:
        print(f"warnings={len(warnings)}")
        for w in warnings:
            print(f"  - {w}")

    if trials:
        passed = sum(1 for t in trials if t.record.completion_status == 2)
        partial = sum(1 for t in trials if t.record.completion_status == 1)
        failed = sum(1 for t in trials if t.record.completion_status == 0)
        ctrl = sum(1 for t in trials if t.record.experiment_arm == "control")
        treat = sum(1 for t in trials if t.record.experiment_arm == "treatment")
        print(f"pass={passed} partial={partial} fail={failed} control={ctrl} treatment={treat}")

    if args.print_summary and not args.dry_run:
        print(evaluate(args.experiment_id))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
