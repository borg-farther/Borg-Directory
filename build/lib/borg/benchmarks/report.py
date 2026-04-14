"""
Generate markdown reports from benchmark results.
"""

from borg.benchmarks.runner import BenchmarkReport, TaskResult


def generate_markdown_report(report: BenchmarkReport) -> str:
    """
    Generate a markdown report from a BenchmarkReport.

    Args:
        report: The benchmark comparison report

    Returns:
        Markdown formatted string
    """
    lines = []

    # Header
    lines.append("# Borg Benchmark Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")

    # Aggregate stats
    delta_emoji = "▲" if report.success_rate_delta > 0 else "▼" if report.success_rate_delta < 0 else "●"
    quality_emoji = "▲" if report.avg_quality_delta > 0 else "▼" if report.avg_quality_delta < 0 else "●"
    time_emoji = "▲" if report.avg_time_delta > 0 else "▼" if report.avg_time_delta < 0 else "●"

    lines.append(
        f"| Metric | Baseline | Borg | Delta |"
    )
    lines.append(
        f"|--------|----------|------|-------|"
    )
    lines.append(
        f"| Success Rate | {report.baseline_success_rate:.0%} | {report.borg_success_rate:.0%} | {delta_emoji} {report.success_rate_delta:+.0%} |"
    )
    lines.append(
        f"| Avg Quality | {report.baseline_avg_quality:.1f}/10 | {report.borg_avg_quality:.1f}/10 | {quality_emoji} {report.avg_quality_delta:+.1f} |"
    )
    lines.append(
        f"| Avg Time (s) | {report.baseline_avg_time:.0f}s | {report.borg_avg_time:.0f}s | {time_emoji} {report.avg_time_delta:+.0f}s |"
    )
    lines.append("")

    # Key findings
    lines.append("### Key Findings")
    lines.append("")

    if report.success_rate_delta > 0.2:
        lines.append("- **Borg significantly improves task success rate** (+{:.0%})".format(report.success_rate_delta))
    elif report.success_rate_delta > 0:
        lines.append("- Borg slightly improves task success rate (+{:.0%})".format(report.success_rate_delta))
    elif report.success_rate_delta < -0.1:
        lines.append("- **WARNING: Borg success rate is lower than baseline** ({:.0%})".format(report.success_rate_delta))
    else:
        lines.append("- No significant difference in task success rate")

    if report.avg_quality_delta > 1:
        lines.append("- **Borg substantially improves solution quality** (+{:.1f} points)".format(report.avg_quality_delta))
    elif report.avg_quality_delta > 0:
        lines.append("- Borg modestly improves solution quality (+{:.1f} points)".format(report.avg_quality_delta))
    elif report.avg_quality_delta < -1:
        lines.append("- **WARNING: Borg solution quality is lower** ({:.1f} points)".format(report.avg_quality_delta))

    if report.avg_time_delta > 30:
        lines.append("- Borg-assisted solutions take longer (+{:.0f}s avg) - more thorough approach".format(report.avg_time_delta))
    elif report.avg_time_delta < -30:
        lines.append("- Borg-assisted solutions are faster ({:.0f}s avg) - more efficient".format(report.avg_time_delta))

    lines.append("")

    # Per-task breakdown
    lines.append("## Per-Task Results")
    lines.append("")

    for result in report.task_results:
        status_icon = "✅" if result["borg_solved"] else "❌"
        quality_icon = "▲" if result["quality_delta"] > 0 else "▼" if result["quality_delta"] < 0 else "●"

        lines.append(f"### {status_icon} {result['task_id']} ({result['category']})")
        lines.append("")
        lines.append(f"| | Baseline | Borg | Delta |")
        lines.append(f"|---|----------|------|-------|")
        lines.append(f"| Solved | {'Yes' if result['baseline_solved'] else 'No'} | {'Yes' if result['borg_solved'] else 'No'} | {'+' if result['quality_delta'] >= 0 else ''}{result['quality_delta']} |")
        lines.append(f"| Quality | {result['baseline_quality']}/10 | {result['borg_quality']}/10 | {quality_icon} {result['quality_delta']:+d} |")
        lines.append(f"| Time | {result['baseline_time']:.0f}s | {result['borg_time']:.0f}s | {result['time_delta']:+.0f}s |")
        lines.append(f"| Best Practice | {'Yes' if result['baseline_used_best_practice'] else 'No'} | {'Yes' if result['borg_used_best_practice'] else 'No'} | - |")
        lines.append(f"| Anti-Pattern | {'Yes' if result['baseline_hit_anti_pattern'] else 'No'} | {'Yes' if result['borg_hit_anti_pattern'] else 'No'} | - |")
        lines.append("")

        # Reasoning snippets
        lines.append(f"**Baseline reasoning**: {result['baseline_reasoning'][:100]}...")
        lines.append(f"**Borg reasoning**: {result['borg_reasoning'][:100]}...")
        lines.append("")

    # Honest assessment
    lines.append("## Honest Assessment")
    lines.append("")
    lines.append("This benchmark measures whether having access to borg packs improves agent decision-making.")
    lines.append("")

    # Calculate what borg helped with
    helped_tasks = [r for r in report.task_results if r["quality_delta"] > 0]
    hurt_tasks = [r for r in report.task_results if r["quality_delta"] < 0]
    neutral_tasks = [r for r in report.task_results if r["quality_delta"] == 0]

    lines.append(f"- Tasks where borg **helped**: {len(helped_tasks)}/{report.total_tasks}")
    lines.append(f"- Tasks where borg **hurt**: {len(hurt_tasks)}/{report.total_tasks}")
    lines.append(f"- Tasks where borg had **no effect**: {len(neutral_tasks)}/{report.total_tasks}")
    lines.append("")

    if len(hurt_tasks) > len(helped_tasks):
        lines.append("⚠️ **WARNING**: Borg hurt more tasks than it helped. Review the benchmark design.")
    elif report.avg_quality_delta < 0.5 and report.success_rate_delta < 0.1:
        lines.append("⚠️ **NOTE**: Marginal improvement from borg. The packs may need refinement or the baseline may be too weak.")
    else:
        lines.append("✅ Borg shows positive impact on agent decision-making.")

    lines.append("")
    lines.append("*Report generated from borg benchmark suite*")

    return "\n".join(lines)


def print_summary(report: BenchmarkReport) -> None:
    """Print a brief text summary to stdout."""
    print("=" * 60)
    print("BORG BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Tasks tested: {report.total_tasks}")
    print(f"Baseline success rate: {report.baseline_success_rate:.0%}")
    print(f"Borg success rate: {report.borg_success_rate:.0%}")
    print(f"Success rate delta: {report.success_rate_delta:+.0%}")
    print(f"Baseline avg quality: {report.baseline_avg_quality:.1f}/10")
    print(f"Borg avg quality: {report.borg_avg_quality:.1f}/10")
    print(f"Quality delta: {report.avg_quality_delta:+.1f}")
    print(f"Baseline avg time: {report.baseline_avg_time:.0f}s")
    print(f"Borg avg time: {report.borg_avg_time:.0f}s")
    print(f"Time delta: {report.avg_time_delta:+.0f}s")
    print("=" * 60)
