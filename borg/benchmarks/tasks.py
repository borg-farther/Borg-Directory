"""
Benchmark tasks for evaluating borg effectiveness.
Each task simulates a real-world problem where borg packs may or may not help.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """A benchmark task representing a real-world problem."""

    id: str
    category: str  # coding, defi, ops, research
    description: str
    context: str  # The problem scenario
    expected_approach: str  # Ideal solution approach
    rubric: list[str]  # Keywords indicating correct solution
    anti_patterns: list[str]  # Keywords indicating wrong approach
    borg_pack_id: str  # Which borg pack should help

    def __post_init__(self):
        # Normalize lists
        if isinstance(self.rubric, str):
            self.rubric = [self.rubric]
        if isinstance(self.anti_patterns, str):
            self.anti_patterns = [self.anti_patterns]


# =============================================================================
# CODING TASKS
# =============================================================================

DOCKER_DNS = Task(
    id="docker-dns",
    category="coding",
    description="Fix container DNS resolution failure",
    context=(
        "Two Docker containers on the same docker-compose network cannot communicate. "
        "Container A (Python app) tries to reach container B (Postgres) at 'postgres:5432' "
        "but gets 'Name or service not known'. The docker-compose.yml shows both services "
        "on the same 'app-network' network. pinging 'postgres' from container A fails."
    ),
    expected_approach=(
        "Use container names as hostnames, ensure both on same network, "
        "check /etc/hosts inside container, restart containers to pick up DNS changes, "
        "use 'network_mode' appropriately, verify network driver is bridge not host"
    ),
    rubric=[
        "container name as hostname",
        "network membership",
        "bridge network",
        "dns resolution",
        "same network",
        "restart containers",
        "network driver",
    ],
    anti_patterns=[
        "use localhost",
        "use 127.0.0.1",
        "use host network",
        "hardcode IP",
        "port exposure only",
    ],
    borg_pack_id="docker-networking",
)

OAUTH_401 = Task(
    id="oauth-401",
    category="coding",
    description="Fix OAuth 2.0 redirect URI mismatch",
    context=(
        "Your OAuth flow returns 401 'redirect_uri_mismatch' from the provider. "
        "The registered URI in the provider console is 'https://app.example.com/auth/callback'. "
        "Your code redirects to 'https://app.example.com/oauth/callback'. "
        "You're trying to fix the integration and don't want to re-register the app."
    ),
    expected_approach=(
        "Change redirect URI in code to match registered URI, "
        "or update provider registration to match your code's URI. "
        "Never hardcode credentials. Use environment variables for OAuth secrets."
    ),
    rubric=[
        "redirect_uri",
        "uri match",
        "provider console",
        "registration",
        "callback path",
        "environment variables",
    ],
    anti_patterns=[
        "ignore error",
        "disable validation",
        "use GET for tokens",
        "log secrets",
        "skip SSL verification",
    ],
    borg_pack_id="github-auth",  # OAuth is generic here
)

DB_MIGRATION = Task(
    id="db-migration",
    category="coding",
    description="Run database migration with zero production downtime",
    context=(
        "Need to rename a column in a high-traffic PostgreSQL table (10M rows). "
        "A simple ALTER TABLE ... RENAME COLUMN would take a lock blocking reads/writes. "
        "The application is running on Kubernetes with rolling deployments. "
        "You need zero downtime migration."
    ),
    expected_approach=(
        "Use expand-contract pattern: add new column (online), dual-write both columns, "
        "backfill old column data, switch reads to new column, stop writing to old, "
        "drop old column. Or use pg_repack for zero-downtime rename. "
        "Use feature flags to toggle column usage."
    ),
    rubric=[
        "expand-contract",
        "dual write",
        "backfill",
        "feature flag",
        "online migration",
        "pg_repack",
        "no lock",
        "gradual rollout",
    ],
    anti_patterns=[
        "direct alter",
        "lock table",
        "batch migration",
        "single transaction",
        "immediate cutover",
        "blocking operation",
    ],
    borg_pack_id="database-migration",  # Would be a real pack
)


# =============================================================================
# DEFI TASKS
# =============================================================================

YIELD_SELECTION = Task(
    id="yield-selection",
    category="defi",
    description="Select best yield for $3,000 USDC with appropriate risk",
    context=(
        "You have $3,000 USDC sitting idle. Three options:\n"
        "A) Aave USDC: 3.2% APY, blue-chip, fully liquid\n"
        "B) Curve TriCrypto pool: 12% APY but 40% impermanent loss exposure to BTC\n"
        "C) Unaudited protocol: 25% APY, $50M TVL, no audits\n"
        "Risk appetite: low-medium. Time horizon: 3 months."
    ),
    expected_approach=(
        "Choose Aave (blue-chip, no IL, reasonable APY). "
        "Reject Curve due to impermanent loss risk on 3-month horizon. "
        "Reject unaudited protocol entirely (binary smart contract risk). "
        "Consider Morpho Blue for slightly better rates with same safety."
    ),
    rubric=[
        "aave",
        "morpho",
        "blue-chip",
        "no impermanent loss",
        "overcollateralized",
        "audit status",
        "smart contract risk",
        "impermanent loss",
        "IL risk",
    ],
    anti_patterns=[
        "highest APY",
        "highest yield",
        "15%+ APY",
        "20%+ APY",
        "unaudited",
        "no audits",
        "volatility exposure",
        "crypto volatile pair",
    ],
    borg_pack_id="defi-yield-strategy",
)

RUG_DETECTION = Task(
    id="rug-detection",
    category="defi",
    description="Evaluate if a DeFi protocol is likely a rug pull",
    context=(
        "Found a new yield aggregator protocol: 'MegaYield' offering 18% APY on staked ETH. "
        "Token launched 2 weeks ago. Team is anonymous. "
        "Contract not audited. Liquidity pool is $2M (small). "
        "Token has 40% tax on transfer. LP tokens are not locked."
    ),
    expected_approach=(
        "This is HIGH RISK of rug: anonymous team + no audit + high APY + tax token "
        "+ unlocked LP + small liquidity. Use 'rugged' assessment. "
        "Red flags: no audits, LP not locked, tax token, anonymous team, APY unsustainable."
    ),
    rubric=[
        "anonymous team",
        "no audit",
        "lp not locked",
        "high tax",
        "small liquidity",
        "unsustainable APY",
        "rugged",
        "high risk",
        "red flag",
    ],
    anti_patterns=[
        "invest",
        "deposit",
        "high APY acceptable",
        "low risk",
        "safe",
        "audit not needed",
        "trust team",
    ],
    borg_pack_id="defi-yield-strategy",
)

PORTFOLIO_REBALANCE = Task(
    id="portfolio-rebalance",
    category="defi",
    description="Rebalance an overweight DeFi portfolio",
    context=(
        "Your DeFi portfolio is 60% ETH (up 40% this month), 25% BTC, 15% USDC. "
        "Target allocation is 40% ETH, 30% BTC, 30% stablecoin. "
        "Gas is currently $15 (moderate). You want to rebalance to target."
    ),
    expected_approach=(
        "Sell some ETH to buy BTC and USDC. Use limit orders to avoid slippage. "
        "Consider rebalancing over several transactions to average gas costs. "
        "UseDEX aggregators for best execution. Don't panic sell - this is rebalancing not timing."
    ),
    rubric=[
        "rebalance",
        "sell ETH",
        "buy BTC",
        "buy USDC",
        "target allocation",
        "gradual",
        "limit order",
        "dex aggregator",
        "dollar cost average",
        "gas efficient",
    ],
    anti_patterns=[
        "wait for higher ETH",
        "time market",
        "all at once",
        "market order high gas",
        "panic sell",
        "no rebalance needed",
    ],
    borg_pack_id="defi-yield-strategy",
)


# =============================================================================
# OPS TASKS
# =============================================================================

DEPLOY_CONFIG = Task(
    id="deploy-config",
    category="ops",
    description="Configure Kubernetes deployment with rollback strategy",
    context=(
        "Deploying a new version of a payment service to Kubernetes. "
        "The service processes 1000 req/min. You need: rolling update strategy, "
        "resource limits, health checks, and the ability to rollback quickly if needed. "
        "Current deployment uses 'latest' tag - you need to fix this."
    ),
    expected_approach=(
        "Use RollingUpdate strategy with maxSurge=1, maxUnavailable=0 for zero downtime. "
        "Set resource requests/limits (CPU/memory). Configure readiness/liveness probes. "
        "Use specific image tags, not 'latest'. Enable rollback with 'kubectl rollout undo'. "
        "Set preStop hook for graceful shutdown."
    ),
    rubric=[
        "rolling update",
        "maxsurge",
        "maxunavailable",
        "resource limits",
        "readiness probe",
        "liveness probe",
        "image tag",
        "specific tag",
        "rollback",
        "rollout undo",
        "graceful shutdown",
        "prestop",
    ],
    anti_patterns=[
        "latest tag",
        "recreate strategy",
        "no probes",
        "no resource limits",
        "all at once",
        "blocking rollout",
    ],
    borg_pack_id="kubernetes-deployment",  # Would be a real pack
)

MONITORING_SETUP = Task(
    id="monitoring-setup",
    category="ops",
    description="Set up alerting for a production API service",
    context=(
        "Running an API service on 3 Kubernetes pods. Need to set up alerting for:\n"
        "- High error rate (5xx > 1% for 5 min)\n"
        "- Latency P99 > 500ms\n"
        "- Pods crashing repeatedly\n"
        "- Disk/memory pressure\n"
        "Alerting system: Prometheus + Alertmanager + Slack."
    ),
    expected_approach=(
        "Define PromQL alerting rules with 'for' clause for persistence. "
        "Use SLI/SLO format: error budget. Configure Alertmanager with severity labels. "
        "Route to Slack channel based on severity. Set up dashboard in Grafana. "
        "Use RedMethod or USE method for resource metrics."
    ),
    rubric=[
        "promql",
        "alerting rules",
        "for clause",
        "severity",
        "routing",
        "slack",
        "dashboard",
        "grafana",
        "sli",
        "slo",
        "error budget",
        "red method",
        "use method",
    ],
    anti_patterns=[
        "no for clause",
        "instant alerts",
        "no severity",
        "email only",
        "alert fatigue",
        "every metric",
        "no routing",
    ],
    borg_pack_id="monitoring-setup",  # Would be a real pack
)


# =============================================================================
# RESEARCH TASKS
# =============================================================================

API_COMPARISON = Task(
    id="api-comparison",
    category="research",
    description="Choose between 3 API providers for payment processing",
    context=(
        "Need to integrate payment processing. Three options:\n"
        "1) Stripe: $2.5% + 30¢ per transaction, 99.99% uptime, great docs, $0 setup\n"
        "2) Adyen: 2.0% + 25¢, 99.95% uptime, complex docs, $500 setup + monthly fee\n"
        "3) Raw TCP (simulated): 0.5% + 5¢, 99.9% uptime, DIY infrastructure, $50k setup\n\n"
        "Small business, 500 txns/month, 2 engineers, need PCI compliance."
    ),
    expected_approach=(
        "Choose Stripe: best docs, no upfront cost, handles PCI compliance, "
        "acceptable rates for volume. Avoid Raw TCP (overkill, PCI burden). "
        "Adyen only if volume justifies ($500/month minimum + complexity)."
    ),
    rubric=[
        "stripe",
        "documentation",
        "ease of integration",
        "no upfront cost",
        "pci compliance",
        "handled",
        "small business",
        "acceptable rate",
    ],
    anti_patterns=[
        "raw tcp",
        "diy infrastructure",
        "cheapest rate",
        "0.5%",
        "adyen",
        "complex setup",
        "high upfront",
        "build your own",
    ],
    borg_pack_id="api-selection",  # Would be a real pack
)

ARCH_DECISION = Task(
    id="arch-decision",
    category="research",
    description="Decide between monolith and microservices for a startup",
    context=(
        "Startup with 4 engineers building a B2B SaaS (50k users, 500 concurrent). "
        "Currently monolith (Django). Considering microservices. "
        "Team is senior but no microservices experience. "
        "Need to ship in 3 months for seed round demo."
    ),
    expected_approach=(
        "Stay with monolith. Microservices add complexity (network calls, distributed systems, "
        "observability). Use modular monolith: separate concerns within single deploy. "
        "Extract services only when you have clear boundaries AND scale pressure. "
        "Premature microservices is an anti-pattern for small teams."
    ),
    rubric=[
        "monolith",
        "modular monolith",
        "stay",
        "don't migrate",
        "premature",
        "complexity",
        "extract later",
        "clear boundaries",
        "scale pressure",
        "team size",
    ],
    anti_patterns=[
        "microservices now",
        "extract services early",
        "future proof",
        "modern architecture",
        "decouple everything",
        "one service per table",
        "jump to microservices",
    ],
    borg_pack_id="architecture-decision",  # Would be a real pack
)


# =============================================================================
# TASK REGISTRY
# =============================================================================

TASKS = [
    # Coding
    DOCKER_DNS,
    OAUTH_401,
    DB_MIGRATION,
    # DeFi
    YIELD_SELECTION,
    RUG_DETECTION,
    PORTFOLIO_REBALANCE,
    # Ops
    DEPLOY_CONFIG,
    MONITORING_SETUP,
    # Research
    API_COMPARISON,
    ARCH_DECISION,
]


def get_tasks_by_category(category: str) -> list[Task]:
    """Get all tasks in a specific category."""
    return [t for t in TASKS if t.category == category]


def get_task_by_id(task_id: str) -> Optional[Task]:
    """Get a specific task by its ID."""
    for task in TASKS:
        if task.id == task_id:
            return task
    return None
