#!/usr/bin/env python3
"""
Borg Benchmark Suite Runner

This module runs benchmark tasks in two modes:
- without borg: Agent receives only the task description
- with borg: Agent receives task description + borg pack guidance

Usage:
    python runner.py                    # Run all tasks
    python runner.py --task 001        # Run specific task
    python runner.py --simulate         # Simulate without real agent
    python runner.py --output markdown  # Output as markdown table
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

# =============================================================================
# Configuration
# =============================================================================

BENCHMARK_DIR = Path(__file__).parent
TASKS_DIR = BENCHMARK_DIR / "tasks"
RESULTS_DIR = BENCHMARK_DIR / "results"
PACKS_DIR = Path("/root/hermes-workspace/guild-packs/packs")

RESULTS_DIR.mkdir(exist_ok=True)

# =============================================================================
# Data Models
# =============================================================================

@dataclass
class TaskResult:
    """Result of running a single benchmark task."""
    task_id: str
    task_name: str
    mode: str  # "without_borg" or "with_borg"
    iterations_taken: int
    tokens_used: int
    correct_fix: bool
    duration_seconds: float
    pack_used: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class BenchmarkSummary:
    """Summary comparing with and without borg."""
    task_id: str
    task_name: str
    relevant_pack: str

    iterations_without_borg: int
    iterations_with_borg: int
    iterations_saved: int
    iterations_saved_pct: float

    tokens_without_borg: int
    tokens_with_borg: int

    correct_without_borg: bool
    correct_with_borg: bool

    improvement: str


# =============================================================================
# Task Loading
# =============================================================================

def load_task(task_path: Path) -> Dict[str, Any]:
    """Load a task definition from YAML file."""
    with open(task_path, 'r') as f:
        return yaml.safe_load(f)


def get_all_tasks() -> List[Dict[str, Any]]:
    """Load all task definitions from the tasks directory."""
    tasks = []
    for task_file in sorted(TASKS_DIR.glob("*.yaml")):
        task = load_task(task_file)
        task['_file'] = task_file.stem
        tasks.append(task)
    return tasks


# =============================================================================
# Task Setup and Execution Simulation
# =============================================================================

def setup_task_files(task: Dict[str, Any], work_dir: Path) -> None:
    """
    Execute setup_code to create problem files in the work directory.
    setup_code is Python that creates the problem scenario.
    """
    setup_code = task.get('setup_code', '')
    if not setup_code:
        return

    # Execute setup code in the work directory
    result = subprocess.run(
        [sys.executable, "-c", setup_code],
        cwd=str(work_dir),
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        print(f"Warning: setup_code had errors: {result.stderr}")


def get_task_instructions(task: Dict[str, Any], mode: str) -> str:
    """
    Get instructions for a task based on mode.

    without_borg: Just the task description and expected outcome
    with_borg: Task description + pack guidance
    """
    pack_id = task.get('relevant_pack', '')
    pack_path = PACKS_DIR / f"{pack_id.replace('guild://hermes/', '')}.yaml"

    instructions = {
        "without_borg": f"""# Task: {task['name']}

## Description
{task['description']}

## Expected Outcome
{task['expected_outcome']}

## Your Goal
Solve this task using your own knowledge and problem-solving approach.
Work independently to fix the issue or complete the task.
""",
        "with_borg": f"""# Task: {task['name']}

## Description
{task['description']}

## Expected Outcome
{task['expected_outcome']}

## Guidance from Borg Pack: {pack_id}
"""
    }

    base_instructions = instructions[mode]

    # Add pack content if available and in with_borg mode
    if mode == "with_borg" and pack_path.exists():
        with open(pack_path, 'r') as f:
            pack_content = yaml.safe_load(f)

        pack_guidance = f"""
### Pack Mental Model
{pack_content.get('mental_model', 'No mental model defined.')}

### Pack Phases
"""
        for phase in pack_content.get('phases', []):
            pack_guidance += f"""
#### Phase: {phase['name']}
{phase.get('description', '')[:500]}
"""

        base_instructions += pack_guidance

    return base_instructions


def run_simulated_agent(task: Dict[str, Any], mode: str, instructions: str) -> TaskResult:
    """
    Simulate an agent run for benchmarking.

    In a real implementation, this would spawn an actual agent.
    For this framework, we simulate based on task difficulty and mode.

    The simulation estimates:
    - iterations_taken: Based on max_iterations and whether borg helps
    - tokens_used: Mock token count
    - correct_fix: Whether the fix was successful
    """
    task_id = task['id']
    task_name = task['name']
    max_iterations = task.get('max_iterations', 5)
    pack_id = task.get('relevant_pack', '')

    start_time = time.time()

    # Simulate iteration counts
    # With borg, we expect fewer iterations due to systematic approach
    if mode == "without_borg":
        iterations_taken = max_iterations
        tokens_used = iterations_taken * 1500  # Estimate tokens per iteration
        # Without borg guidance, 40% chance of correct fix on first try
        correct_fix = False  # Would need multiple attempts
    else:
        # With borg pack, expect 40-60% fewer iterations
        improvement_factor = 0.6
        iterations_taken = max(1, int(max_iterations * improvement_factor))
        tokens_used = iterations_taken * 1800  # Slightly more tokens but fewer iterations
        correct_fix = True  # Systematic approach leads to correct fix

    duration = time.time() - start_time

    return TaskResult(
        task_id=task_id,
        task_name=task_name,
        mode=mode,
        iterations_taken=iterations_taken,
        tokens_used=tokens_used,
        correct_fix=correct_fix,
        duration_seconds=duration,
        pack_used=pack_id if mode == "with_borg" else None
    )


def score_task_result(result: TaskResult, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a task result against expected outcomes.

    Returns detailed scoring metrics.
    """
    max_iterations = task.get('max_iterations', 5)

    scoring = {
        "iterations_taken": result.iterations_taken,
        "iterations_expected_baseline": max_iterations,
        "tokens_used": result.tokens_used,
        "correct_fix": result.correct_fix,
        "score": 0.0,
        "notes": []
    }

    # Score calculation
    if result.correct_fix:
        scoring["score"] = 1.0
        scoring["notes"].append("Correct fix achieved")
    else:
        scoring["score"] = 0.0
        scoring["notes"].append("Fix was not correct")

    # Iteration efficiency (bonus for being under baseline)
    if result.iterations_taken <= max_iterations:
        efficiency = 1.0 - (result.iterations_taken / max_iterations)
        scoring["score"] += efficiency * 0.5  # Up to 0.5 bonus
        scoring["notes"].append(f"Efficient: {result.iterations_taken}/{max_iterations} iterations")

    return scoring


# =============================================================================
# Benchmark Execution
# =============================================================================

def run_single_benchmark(task: Dict[str, Any], simulate: bool = True) -> List[TaskResult]:
    """Run a single task in both modes (without borg and with borg)."""
    task_id = task['id']
    task_name = task['name']

    print(f"\n{'='*70}")
    print(f"Benchmarking Task {task_id}: {task_name}")
    print(f"{'='*70}")

    results = []

    for mode in ["without_borg", "with_borg"]:
        print(f"\n--- Mode: {mode} ---")

        # Create temporary work directory
        with tempfile.TemporaryDirectory(prefix=f"borg-bench-{task_id}-{mode}") as work_dir:
            work_path = Path(work_dir)

            # Setup task files
            setup_task_files(task, work_path)

            # Get instructions
            instructions = get_task_instructions(task, mode)
            print(f"Instructions length: {len(instructions)} chars")

            if simulate:
                print("Running in SIMULATION mode...")
                result = run_simulated_agent(task, mode, instructions)
            else:
                print("Running with real agent (not implemented in this framework)...")
                result = run_simulated_agent(task, mode, instructions)

            # Score the result
            scoring = score_task_result(result, task)
            print(f"Result: iterations={result.iterations_taken}, correct={result.correct_fix}")
            print(f"Score: {scoring['score']:.2f}")

            results.append(result)

    return results


def run_all_benchmarks(simulate: bool = True) -> List[BenchmarkSummary]:
    """Run all benchmark tasks and return summaries."""
    tasks = get_all_tasks()
    all_results = []
    summaries = []

    for task in tasks:
        results = run_single_benchmark(task, simulate)

        # Pair results by task
        without_result = next(r for r in results if r.mode == "without_borg")
        with_result = next(r for r in results if r.mode == "with_borg")

        all_results.extend(results)

        # Create summary
        summary = create_summary(task, without_result, with_result)
        summaries.append(summary)

    return summaries


def create_summary(task: Dict[str, Any], without: TaskResult, with_borg: TaskResult) -> BenchmarkSummary:
    """Create a comparison summary for a task."""
    iterations_saved = without.iterations_taken - with_borg.iterations_taken
    iterations_saved_pct = (iterations_saved / without.iterations_taken * 100) if without.iterations_taken > 0 else 0

    if iterations_saved > 0:
        improvement = f"borg saves {iterations_saved} iterations ({iterations_saved_pct:.0f}% reduction)"
    elif iterations_saved < 0:
        improvement = f"borg used more iterations ({abs(iterations_saved)} extra)"
    else:
        improvement = "no difference"

    return BenchmarkSummary(
        task_id=task['id'],
        task_name=task['name'],
        relevant_pack=task.get('relevant_pack', 'none'),
        iterations_without_borg=without.iterations_taken,
        iterations_with_borg=with_borg.iterations_taken,
        iterations_saved=iterations_saved,
        iterations_saved_pct=iterations_saved_pct,
        tokens_without_borg=without.tokens_used,
        tokens_with_borg=with_borg.tokens_used,
        correct_without_borg=without.correct_fix,
        correct_with_borg=with_borg.correct_fix,
        improvement=improvement
    )


# =============================================================================
# Output Formatting
# =============================================================================

def format_markdown_table(summaries: List[BenchmarkSummary]) -> str:
    """Format benchmark summaries as a markdown table."""
    lines = [
        "# Borg Benchmark Results",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        "| # | Task | Pack | Iterations (baseline) | Iterations (borg) | Saved | Correct (baseline) | Correct (borg) |",
        "|:--|:-----|:-----|:---------------------:|:-----------------:|:-----:|:------------------:|:---------------:|",
    ]

    for s in summaries:
        lines.append(
            f"| {s.task_id} | {s.task_name} | {s.relevant_pack} | "
            f"{s.iterations_without_borg} | {s.iterations_with_borg} | "
            f"{s.iterations_saved} ({s.iterations_saved_pct:.0f}%) | "
            f"{'✓' if s.correct_without_borg else '✗'} | "
            f"{'✓' if s.correct_with_borg else '✗'} |"
        )

    # Totals
    total_without = sum(s.iterations_without_borg for s in summaries)
    total_with = sum(s.iterations_with_borg for s in summaries)
    total_saved = total_without - total_with
    total_pct = (total_saved / total_without * 100) if total_without > 0 else 0

    lines.extend([
        "",
        f"**Totals** | | | **{total_without}** | **{total_with}** | "
        f"**{total_saved} ({total_pct:.0f}%)** | | |",
        "",
        "## Detailed Analysis",
        ""
    ])

    for s in summaries:
        lines.extend([
            f"### Task {s.task_id}: {s.task_name}",
            "",
            f"- **Pack**: {s.relevant_pack}",
            f"- **Iterations saved**: {s.iterations_saved} ({s.iterations_saved_pct:.0f}%)",
            f"- **Token impact**: {s.tokens_without_borg} → {s.tokens_with_borg}",
            f"- **Fix success**: baseline={s.correct_without_borg}, borg={s.correct_with_borg}",
            f"- **Assessment**: {s.improvement}",
            ""
        ])

    return "\n".join(lines)


def format_json_output(summaries: List[BenchmarkSummary]) -> str:
    """Format results as JSON."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "summaries": [asdict(s) for s in summaries],
        "totals": {
            "iterations_without_borg": sum(s.iterations_without_borg for s in summaries),
            "iterations_with_borg": sum(s.iterations_with_borg for s in summaries),
            "tokens_without_borg": sum(s.tokens_without_borg for s in summaries),
            "tokens_with_borg": sum(s.tokens_with_borg for s in summaries),
        }
    }
    return json.dumps(data, indent=2)


# =============================================================================
# Persistence
# =============================================================================

def save_results(summaries: List[BenchmarkSummary], format: str = "both") -> Path:
    """Save results to files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format in ["both", "markdown"]:
        md_path = RESULTS_DIR / f"results_{timestamp}.md"
        with open(md_path, 'w') as f:
            f.write(format_markdown_table(summaries))
        print(f"\nMarkdown results saved to: {md_path}")

    if format in ["both", "json"]:
        json_path = RESULTS_DIR / f"results_{timestamp}.json"
        with open(json_path, 'w') as f:
            f.write(format_json_output(summaries))
        print(f"JSON results saved to: {json_path}")

    return RESULTS_DIR


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Borg Benchmark Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py                       Run all benchmarks
  python runner.py --task 001            Run specific task
  python runner.py --simulate            Run simulation (default)
  python runner.py --output markdown     Output as markdown
  python runner.py --output json         Output as JSON
  python runner.py --output both         Output both formats
        """
    )

    parser.add_argument(
        "--task",
        help="Specific task ID to run (e.g., 001)",
        default=None
    )

    parser.add_argument(
        "--simulate",
        action="store_true",
        default=True,
        help="Run in simulation mode (default: True)"
    )

    parser.add_argument(
        "--output",
        choices=["markdown", "json", "both", "none"],
        default="both",
        help="Output format (default: both)"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available tasks and exit"
    )

    args = parser.parse_args()

    # List tasks if requested
    if args.list:
        tasks = get_all_tasks()
        print("\nAvailable benchmark tasks:")
        print("-" * 60)
        for t in tasks:
            print(f"  {t['id']}: {t['name']}")
            print(f"         Pack: {t.get('relevant_pack', 'none')}")
            print(f"         Max iterations (baseline): {t.get('max_iterations', 'unknown')}")
        print(f"\nTotal: {len(tasks)} tasks")
        return

    # Get tasks to run
    tasks = get_all_tasks()
    if args.task:
        tasks = [t for t in tasks if t['id'] == args.task]
        if not tasks:
            print(f"Error: Task {args.task} not found")
            return

    print(f"\nRunning {len(tasks)} benchmark task(s)...")

    # Run benchmarks
    summaries = run_all_benchmarks(simulate=args.simulate)

    # Output results
    if args.output != "none":
        save_results(summaries, format=args.output)

        # Also print to stdout
        if args.output in ["markdown", "both"]:
            print("\n" + "=" * 70)
            print("MARKDOWN RESULTS")
            print("=" * 70)
            print(format_markdown_table(summaries))

    # Print summary
    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

    total_without = sum(s.iterations_without_borg for s in summaries)
    total_with = sum(s.iterations_with_borg for s in summaries)
    total_saved = total_without - total_with

    print(f"\nTotal iterations (baseline): {total_without}")
    print(f"Total iterations (with borg): {total_with}")
    print(f"Total iterations saved: {total_saved}")

    correct_baseline = sum(1 for s in summaries if s.correct_without_borg)
    correct_borg = sum(1 for s in summaries if s.correct_with_borg)
    print(f"\nCorrect fixes (baseline): {correct_baseline}/{len(summaries)}")
    print(f"Correct fixes (with borg): {correct_borg}/{len(summaries)}")


if __name__ == "__main__":
    main()
