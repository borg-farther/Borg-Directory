"""
Benchmark runner for simulating agent task execution.
Simulates both baseline (without borg) and borg-assisted (with borg) runs.
"""

from dataclasses import dataclass, field
from typing import Optional
import time

from borg.benchmarks.tasks import Task, TASKS


@dataclass
class TaskResult:
    """Result of running a single task."""

    task_id: str
    solution: str  # The simulated solution text
    time_seconds: float  # How long it took (simulated)
    pack_used: Optional[str] = None  # Which borg pack was used (if any)


@dataclass
class BenchmarkReport:
    """Comparison report between baseline and borg-assisted runs."""

    task_results: list[dict] = field(default_factory=list)
    total_tasks: int = 0
    baseline_success_rate: float = 0.0
    borg_success_rate: float = 0.0
    success_rate_delta: float = 0.0
    baseline_avg_quality: float = 0.0
    borg_avg_quality: float = 0.0
    avg_quality_delta: float = 0.0
    baseline_avg_time: float = 0.0
    borg_avg_time: float = 0.0
    avg_time_delta: float = 0.0


class BenchmarkRunner:
    """
    Runs benchmarks comparing baseline vs borg-assisted task completion.

    Simulation approach:
    - Baseline: Agent uses "obvious first approach" - may be wrong or suboptimal
    - Borg-assisted: Agent follows pack guidance - should be better when pack is relevant
    """

    # Simulated responses for baseline (naive/obvious approach)
    BASELINE_RESPONSES = {
        "docker-dns": {
            "solution": (
                "I'll fix the DNS issue by using localhost instead of the container name. "
                "Let me change the host from 'postgres' to '127.0.0.1' and expose the port. "
                "Actually, I'll just use the host network mode to simplify things. "
                "This way everything can talk to each other easily."
            ),
            "time_seconds": 45.0,
        },
        "oauth-401": {
            "solution": (
                "The error says redirect_uri_mismatch. I'll disable URI validation in the OAuth "
                "provider SDK to bypass this check. Let me also log the tokens for debugging. "
                "For now I'll skip SSL verification to make it work faster."
            ),
            "time_seconds": 30.0,
        },
        "db-migration": {
            "solution": (
                "I'll run a simple ALTER TABLE to rename the column. "
                "It should be fast since PostgreSQL handles this efficiently. "
                "Let me do it in a single transaction during off-peak hours. "
                "I'll just block reads during the migration."
            ),
            "time_seconds": 120.0,
        },
        "yield-selection": {
            "solution": (
                "Option C has the highest APY at 25%! That's 8x better than option A. "
                "I'll put all $3K into the unaudited protocol since the APY is amazing. "
                "High APY means the protocol is successful and can pay out. "
                "The 40% IL exposure isn't a big deal since crypto always goes up."
            ),
            "time_seconds": 20.0,
        },
        "rug-detection": {
            "solution": (
                "18% APY is pretty good for staked ETH. The team being anonymous is fine - "
                "many DeFi protocols have anonymous teams. Not having audits is a yellow flag "
                "but the $50M TVL shows people trust it. I'll mark it as 'proceed with caution' "
                "and allocate a small portion to test."
            ),
            "time_seconds": 25.0,
        },
        "portfolio-rebalance": {
            "solution": (
                "ETH is up 40% which is great! I should hold and wait for it to go higher. "
                "Timing the market is better than mechanical rebalancing. "
                "I'll sell when ETH hits a new all-time high. "
                "No need to rebalance since the portfolio is performing well."
            ),
            "time_seconds": 15.0,
        },
        "deploy-config": {
            "solution": (
                "I'll use the 'latest' tag for simplicity - it's always up to date. "
                "Rolling updates take too long, let me use Recreate strategy for speed. "
                "No need for health probes since the container starts quickly. "
                "Resource limits are for big companies - we'll monitor manually."
            ),
            "time_seconds": 35.0,
        },
        "monitoring-setup": {
            "solution": (
                "I'll set up alerts for every metric so we don't miss anything. "
                "No 'for' clause needed - we want to know immediately. "
                "I'll use email alerts since everyone checks email. "
                "All alerts go to #general channel so the whole company sees."
            ),
            "time_seconds": 40.0,
        },
        "api-comparison": {
            "solution": (
                "Option C has the lowest fees at 0.5%! That's 5x cheaper than Stripe. "
                "I'll recommend building on Raw TCP for maximum cost savings. "
                "The $50k setup cost is an investment that will pay off. "
                "DIY infrastructure gives us full control."
            ),
            "time_seconds": 30.0,
        },
        "arch-decision": {
            "solution": (
                "Microservices are the modern architecture. I'll suggest decomposing everything "
                "into services: users-service, orders-service, payments-service, etc. "
                "We should extract all services now to be future-proof. "
                "One database per service - this is the correct pattern."
            ),
            "time_seconds": 45.0,
        },
    }

    # Simulated responses for borg-assisted (pack-guided approach)
    BORG_RESPONSES = {
        "docker-dns": {
            "solution": (
                "Following docker-networking pack guidance: containers communicate by container name, "
                "not localhost. Both containers need to be on the same docker-compose network. "
                "Diagnosis: containers are on different networks or DNS not resolved. "
                "Fix: Ensure both services have 'networks: [app-network]' in docker-compose. "
                "Use 'docker exec container ping postgres' to verify DNS. "
                "Restart containers to pick up network changes."
            ),
            "time_seconds": 60.0,
        },
        "oauth-401": {
            "solution": (
                "Following auth pack: redirect_uri must match exactly what is registered. "
                "The registered URI is '/auth/callback' but code uses '/oauth/callback'. "
                "Fix: Update the code to use the correct callback path. "
                "Store client_secret in environment variables, never in code. "
                "Verify redirect_uri matches provider console exactly including trailing slash."
            ),
            "time_seconds": 45.0,
        },
        "db-migration": {
            "solution": (
                "Following database-migration pack: use expand-contract pattern for zero downtime. "
                "Step 1 (expand): Add new column with default NULL. "
                "Step 2 (dual-write): Update app to write both columns. "
                "Step 3 (backfill): Update existing rows in batches of 1000. "
                "Step 4 (migrate reads): Switch reads to new column behind feature flag. "
                "Step 5 (contract): Drop old column after verification. "
                "Use pg_repack for zero-downtime index changes."
            ),
            "time_seconds": 180.0,
        },
        "yield-selection": {
            "solution": (
                "Following defi-yield-strategy pack: yield = reward for risk taken. "
                "Analysis: Option C is unaudited with 25% APY - binary smart contract risk. "
                "Option B has 40% impermanent loss exposure - IL rarely covered by APR. "
                "Option A (Aave): 3.2% APY, blue-chip, no IL, fully liquid. "
                "Decision: Aave USDC - overcollateralized, audited, no IL risk. "
                "Consider Morpho Blue for 4.2% with same safety profile. "
                "Exit conditions: APY drops 50%+ or risk-off signal."
            ),
            "time_seconds": 35.0,
        },
        "rug-detection": {
            "solution": (
                "Following defi-yield-strategy pack: evaluate smart contract risk first. "
                "Red flags identified: anonymous team, no audits, LP tokens not locked, "
                "40% transfer tax, small $2M liquidity, unsustainable 18% APY. "
                "Assessment: HIGH RUG PROBABILITY. "
                "Tax token + unlocked LP = rug mechanism. "
                "Anonymous + unaudited = no accountability. "
                "Recommendation: DO NOT INVEST. Walk away."
            ),
            "time_seconds": 30.0,
        },
        "portfolio-rebalance": {
            "solution": (
                "Following defi-yield-strategy pack: portfolio drift requires rebalancing. "
                "Current: ETH 60%, BTC 25%, USDC 15%. Target: ETH 40%, BTC 30%, USDC 30%. "
                "Action: Sell 20% ETH, buy 5% BTC and 15% USDC. "
                "Use dex aggregators (1inch, Paraswap) for best execution. "
                "Consider limit orders to minimize slippage. "
                "Spread transactions over 2-3 batches to average gas costs. "
                "This is rebalancing, not market timing - execute systematically."
            ),
            "time_seconds": 25.0,
        },
        "deploy-config": {
            "solution": (
                "Following kubernetes-deployment pack: configure rolling update properly. "
                "Strategy: RollingUpdate with maxSurge=1, maxUnavailable=0. "
                "Resource limits: set requests and limits for CPU/memory. "
                "Health probes: readinessProbe (is traffic ready?) + livenessProbe (needs restart?). "
                "Image: use specific tag (e.g., v1.2.3), never 'latest'. "
                "Rollback: kubectl rollout undo deployment/app - enables quick revert. "
                "PreStop: sleep 5 for graceful shutdown before SIGTERM."
            ),
            "time_seconds": 55.0,
        },
        "monitoring-setup": {
            "solution": (
                "Following monitoring-setup pack: define SLI/SLO first. "
                "PromQL rules with 'for: 5m' to avoid flapping alerts. "
                "Error rate: rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m]) > 0.01 "
                "Latency P99: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 0.5 "
                "Severity levels: critical (page), warning (Slack #alerts), info (dashboard). "
                "Alertmanager routing: route by severity to appropriate channel. "
                "Grafana dashboard with Red Method for API, USE Method for resources."
            ),
            "time_seconds": 65.0,
        },
        "api-comparison": {
            "solution": (
                "Following api-selection pack: evaluate integration complexity vs cost. "
                "Stripe: 2.5% + 30¢, handles PCI DSS compliance, excellent docs, $0 setup. "
                "Adyen: 2.0% + 25¢ but $500/mo minimum + complex docs + 3-month integration. "
                "Raw TCP: 0.5% + 5¢ but DIY PCI compliance ($50k+), 6-month build, high OpEx. "
                "For small business (500 txns/mo, 2 engineers): Stripe is optimal. "
                "Adyen breaks even only at 50k+ txns/month. "
                "PCI compliance self-hosting costs exceed savings for our volume."
            ),
            "time_seconds": 40.0,
        },
        "arch-decision": {
            "solution": (
                "Following architecture-decision pack: microservices require prerequisites. "
                "Current team (4 engineers) lacks microservices experience. "
                "Premature decomposition adds: network latency, distributed tracing, "
                "data consistency, 2x operational burden. "
                "Recommendation: Modular Monolith with clear boundaries. "
                "Extract services ONLY when: explicit scale pressure, team > 10, "
                "clear domain boundaries identified. "
                "Ship in 3 months = monolith. Be suspicious of 'modern architecture' advice."
            ),
            "time_seconds": 50.0,
        },
    }

    def __init__(self):
        self.scorer = None  # Set by run method to avoid circular import issues

    def run_baseline(self, task: Task) -> TaskResult:
        """
        Simulate an agent solving a task WITHOUT borg assistance.

        Uses a naive/obvious first approach that may include anti-patterns.
        """
        response = self.BASELINE_RESPONSES.get(task.id)
        if not response:
            # Fallback for unknown tasks - generic naive response
            return TaskResult(
                task_id=task.id,
                solution=f"I need to solve: {task.description}. I'll use the most obvious approach.",
                time_seconds=60.0,
                pack_used=None,
            )

        return TaskResult(
            task_id=task.id,
            solution=response["solution"],
            time_seconds=response["time_seconds"],
            pack_used=None,
        )

    def run_with_borg(self, task: Task) -> TaskResult:
        """
        Simulate an agent solving a task WITH borg pack assistance.

        Uses the pack's recommended approach when available.
        """
        response = self.BORG_RESPONSES.get(task.id)
        if not response:
            # Fallback: use baseline if no pack exists
            return TaskResult(
                task_id=task.id,
                solution=f"Following pack guidance for: {task.description}",
                time_seconds=60.0,
                pack_used=task.borg_pack_id,
            )

        return TaskResult(
            task_id=task.id,
            solution=response["solution"],
            time_seconds=response["time_seconds"],
            pack_used=task.borg_pack_id,
        )

    def compare(self, baseline_results: list[TaskResult], borg_results: list[TaskResult]) -> BenchmarkReport:
        """
        Compare baseline vs borg-assisted results and generate a report.
        """
        from borg.benchmarks.scorer import TaskScorer

        scorer = TaskScorer()

        # Score all results
        baseline_scores = []
        borg_scores = []
        task_comparisons = []

        for baseline, borg in zip(baseline_results, borg_results):
            # Get the task
            task = None
            for t in TASKS:
                if t.id == baseline.task_id:
                    task = t
                    break

            if task is None:
                continue

            # Score both
            baseline_score = scorer.score(task, baseline)
            borg_score = scorer.score(task, borg)

            baseline_scores.append(baseline_score)
            borg_scores.append(borg_score)

            # Per-task comparison
            task_comparisons.append(
                {
                    "task_id": task.id,
                    "category": task.category,
                    "baseline_solved": baseline_score.solved,
                    "borg_solved": borg_score.solved,
                    "baseline_quality": baseline_score.quality,
                    "borg_quality": borg_score.quality,
                    "quality_delta": borg_score.quality - baseline_score.quality,
                    "baseline_time": baseline_score.time_seconds,
                    "borg_time": borg_score.time_seconds,
                    "time_delta": borg_score.time_seconds - baseline_score.time_seconds,
                    "baseline_used_best_practice": baseline_score.used_best_practice,
                    "borg_used_best_practice": borg_score.used_best_practice,
                    "baseline_hit_anti_pattern": baseline_score.hit_anti_pattern,
                    "borg_hit_anti_pattern": borg_score.hit_anti_pattern,
                    "baseline_reasoning": baseline_score.reasoning,
                    "borg_reasoning": borg_score.reasoning,
                }
            )

        # Calculate aggregates
        total = len(baseline_scores)
        baseline_success_rate = sum(1 for s in baseline_scores if s.solved) / total if total > 0 else 0
        borg_success_rate = sum(1 for s in borg_scores if s.solved) / total if total > 0 else 0

        baseline_avg_quality = sum(s.quality for s in baseline_scores) / total if total > 0 else 0
        borg_avg_quality = sum(s.quality for s in borg_scores) / total if total > 0 else 0

        baseline_avg_time = sum(s.time_seconds for s in baseline_scores) / total if total > 0 else 0
        borg_avg_time = sum(s.time_seconds for s in borg_scores) / total if total > 0 else 0

        return BenchmarkReport(
            task_results=task_comparisons,
            total_tasks=total,
            baseline_success_rate=baseline_success_rate,
            borg_success_rate=borg_success_rate,
            success_rate_delta=borg_success_rate - baseline_success_rate,
            baseline_avg_quality=baseline_avg_quality,
            borg_avg_quality=borg_avg_quality,
            avg_quality_delta=borg_avg_quality - baseline_avg_quality,
            baseline_avg_time=baseline_avg_time,
            borg_avg_time=borg_avg_time,
            avg_time_delta=borg_avg_time - baseline_avg_time,
        )

    def run_all(self) -> tuple[list[TaskResult], list[TaskResult], BenchmarkReport]:
        """
        Run the full benchmark suite on all tasks.

        Returns:
            Tuple of (baseline_results, borg_results, report)
        """
        baseline_results = []
        borg_results = []

        for task in TASKS:
            baseline_result = self.run_baseline(task)
            borg_result = self.run_with_borg(task)
            baseline_results.append(baseline_result)
            borg_results.append(borg_result)

        report = self.compare(baseline_results, borg_results)
        return baseline_results, borg_results, report
