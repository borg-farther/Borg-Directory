# Borg — Cache Layer for Agent Reasoning

**pip install agent-borg | CLI: `borg` | MCP: `borg-mcp`**

Borg is a workflow cache for AI agents. When your agent gets stuck, it can reach into the borg for a proven approach that another agent already worked out — and write back what it learned so the next agent doesn't repeat the same failed attempts.

Think of it as connective brain tissue for agents: not a magic oracle, but a shared cache of approaches that worked.

---

## Installation

```bash
pip install agent-borg                    # core only
pip install agent-borg[embeddings]        # semantic search
pip install agent-borg[crypto]            # Ed25519 pack signing
pip install agent-borg[all]              # everything
pipx install agent-borg                  # recommended — isolated
```

Requires Python 3.10+.

## Quick Start

### CLI

```bash
# Search for a relevant pack
borg search debugging

# Preview without committing
borg try borg://hermes/systematic-debugging

# Pull to local storage
borg pull borg://hermes/systematic-debugging

# Apply it to your task
borg apply systematic-debugging --task "Fix login 401 after OAuth redirect"

# After completing, generate feedback
borg feedback <session_id>
```

### MCP Server

Add to your Claude Code, Cursor, or OpenClaw MCP config:

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp"
    }
  }
}
```

Available tools: `borg_search`, `borg_pull`, `borg_try`, `borg_init`, `borg_apply`, `borg_publish`, `borg_feedback`, `borg_suggest`, `borg_observe`, `borg_convert`.

### Python API

```python
from borg import borg_search, borg_pull, borg_try

results = borg_search("debugging")
borg_try("borg://hermes/systematic-debugging")
borg_pull("borg://hermes/systematic-debugging")
```

### Growth Execution System

If you're working adoption and distribution in production, use:
- `docs/WORLD_CLASS_GROWTH_EXECUTION_SYSTEM.md` (human runbook)
- `docs/DISTRIBUTION_CHANNEL_EXECUTION_BOARD.md` (ranked channel board + kill/scale rules)
- `eval/growth_execution_plan.json` (machine-readable operating spec)
- `eval/distribution_channel_execution_board.json` (machine-readable distribution board)
- `eval/growth_plan_lint.py` (quality gates)
- `eval/tests/test_growth_execution_plan.py` (test enforcement)
- `eval/tests/test_distribution_channel_execution_board.py` (distribution-board test enforcement)

### Security Hardening Baseline (Pre-Distribution)

Security-first controls that must stay green before channel expansion:
- `docs/SECURITY_HARDENING_BASELINE.md` (human baseline + operating policy)
- `eval/security_hardening_baseline.json` (machine-readable baseline spec)
- `scripts/security_gate_check.py` (policy linter used by CI)
- `.github/workflows/security-gates.yml` (secret/dependency/static/policy security gates)
- `eval/tests/test_security_hardening_baseline.py` (test enforcement)

### Public Launch Master Plan (Brand + Org + Trust)

World-class launch architecture for moving from test-branding to production-grade public trust:
- `docs/PUBLIC_LAUNCH_MASTER_PLAN.md` (human runbook)
- `docs/PUBLIC_LAUNCH_NEXT_ACTIONS.md` (simple operator checklist: done vs you)
- `docs/DISCREET_PILOT_CHECKLIST.md` (private pre-launch pilot gate + feedback criteria)
- `eval/public_launch_master_plan.json` (machine-readable launch specification)
- `scripts/public_launch_plan_lint.py` (launch-plan quality + consistency linter)
- `eval/tests/test_public_launch_master_plan.py` (test enforcement)
- `eval/tests/test_public_branding_cutover_runtime.py` (old-org regression prevention)

### Value + Economics Communication Dashboard

Human-readable and machine-readable value framing (API/token/time/economic savings):
- `docs/VALUE_COMMUNICATION_DASHBOARD.md` (plain-English narrative)
- `docs/VALUE_COMMUNICATION_DASHBOARD.html` (public-facing visual dashboard)
- `docs/public/value-dashboard/index.html` (stable alias URL that does not change)
- `docs/PUBLIC_DASHBOARD_URLS.md` (current public URL + refresh workflow)
- `eval/value_communication_dashboard.json` (machine-readable dashboard)
- `scripts/value_dashboard_lint.py` (quality guard)
- `eval/tests/test_value_communication_dashboard.py` (test enforcement)

### 100-User Performance Hardening Plan

Execution plan to move `ready_for_100=false` to sustained pass:
- `docs/PERFORMANCE_100_USER_HARDENING_PLAN.md` (human runbook)
- `eval/performance_100_user_hardening_plan.json` (machine plan)
- `scripts/performance_hardening_plan_lint.py` (quality guard)
- `eval/tests/test_value_communication_dashboard.py` (includes hardening plan tests)

### Illumi Stack Operating System Integration

Systematic adoption of Illumi architecture into Hermes + Borg with safety gates:
- `docs/ILLUMI_STACK_SYSTEM_SPEC.md` (human operating spec)
- `eval/illumi_stack_system_baseline.json` (machine baseline)
- `scripts/illumi_stack_lint.py` (baseline/schema/no-placeholder lint)
- `eval/tests/test_illumi_stack_operating_system.py` (test enforcement)
- `docs/ILLUMI_STACK_OPTIMIZATION_SCORECARD.md` (optimal-use score and gap)
- `eval/illumi_stack_optimization_scorecard.json` (machine scorecard)
- `docs/ILLUMI_EMBODIED_LAYER_HARDENING.md` (embodied-layer security model)
- `eval/illumi_embodied_layer_policy.json` (machine policy for embodied actions)
- `scripts/illumi_embodied_abuse_checks.py` (abuse simulation checks)
- `eval/tests/test_illumi_embodied_layer_hardening.py` (embodied-layer test enforcement)
- `docs/ILLUMI_10_USER_READINESS_SCORECARD.md` (latest 10-user readiness verdict)
- `eval/illumi_10_user_readiness_scorecard.json` (machine readiness scorecard)
- `scripts/illumi_10_user_readiness_report.py` (readiness scorecard generator)
- `docs/ILLUMI_100_USER_BLOCKER_FIXES.md` (documented permanent fixes for 100-user tail-latency blockers)
- `docs/ILLUMI_10_USER_PILOT_PACKET.md` (pilot operating packet)
- `eval/illumi_10_user_pilot_packet.json` (machine pilot packet)
- `eval/illumi_10_user_pilot_status.json` (live pilot state)
- `scripts/illumi_final_sweep.sh` (one-command operator pack)
- `borg/core/canonical_truth.py` (canonical conflict resolver)
- `borg/core/outcome_ledger.py` (durable outcome ledger + metrics)
- `borg/core/action_policy.py` (high-risk action gating)
- `borg/core/provider_router.py` (task-to-provider routing)

### External Communications + Public Status (Canonical)

- `docs/EXTERNAL_COMMUNICATION_STANDARD.md` (claim policy + canonical truth rules)
- `scripts/sync_public_status.py` (generates canonical public artifacts)
- `docs/public/index.html` (public status landing)
- `docs/public/status.json` (machine-readable readiness truth)
- `docs/public/value.json` (machine-readable value + readiness payload)
- `eval/tests/test_external_comms_alignment.py` (no-contradiction enforcement)
- `docs/BORG_HUMAN_IMPACT_UTILITY_SYSTEM.md` (human-first impact/utility explanation)
- `eval/borg_human_impact_os.json` (machine-readable impact utility scorecard)
- `scripts/borg_human_impact_lint.py` (impact artifact quality checks)
- `scripts/generate_human_impact_case_studies.py` (builds role-based proof narratives from live trace sessions)
- `eval/human_impact_trace_registry.json` (canonical trace inputs for operator/builder/executive stories)
- `eval/tests/test_human_impact_utility_system.py` (impact-system test enforcement)
- `eval/tests/test_human_impact_case_studies.py` (case-study pipeline enforcement)
- `eval/tests/test_first_user_external_readiness.py` (PyPI/GitHub first-user install + metadata consistency checks)
- `docs/public/impact/index.html` + `docs/public/impact/impact.json` + `docs/public/impact/case-studies.json` (public impact endpoint + machine case studies)
- `docs/public/proof/index.html` + `docs/public/proof/case-studies.json` (public proof surface for role-specific evidence)

---

## What It Actually Does

Borg manages **workflow packs** — YAML files that encode how to approach a problem class. A pack contains:

- **Problem class**: what kind of task this pack addresses
- **Mental model**: how to think about it (e.g., "slow-thinker" vs "fast-thinker")
- **Phases**: ordered steps with descriptions, checkpoints, and anti-patterns
- **Provenance**: confidence level (guessed → inferred → tested → validated)
- **Safety scan results**: injection and privacy pattern checks

The core loop:

```
Agent hits a problem
  → borg_search finds relevant packs
    → borg_try previews phases and safety scan
      → borg_pull downloads to ~/.hermes/borg/
        → borg_apply executes phase by phase
          → borg_feedback generates a structured artifact
            → next agent gets a better starting point
```

This is a cache, not a magic box. Packs encode what worked before. They get better as feedback accumulates. No packs have been externally validated yet — that's the gap between what's built and what's useful at scale.

---

## Architecture

```
borg/
├── core/                    # Engine — zero external deps beyond PyYAML
│   ├── search.py            # borg_search, borg_pull, borg_try, borg_init
│   ├── apply.py             # Phase-by-phase pack execution
│   ├── publish.py           # GitHub PR creation via gh CLI
│   ├── safety.py            # 13 injection + 11 privacy pattern scanner
│   ├── proof_gates.py       # Confidence tier validation
│   ├── schema.py            # YAML parsing and pack validation
│   ├── privacy.py           # PII detection and redaction
│   ├── session.py           # Execution state and JSONL logging
│   ├── uri.py               # borg:// URI resolution and fetch
│   ├── semantic_search.py   # Vector similarity (optional, requires embeddings)
│   └── convert.py           # SKILL.md / CLAUDE.md / .cursorrules converter
├── db/
│   ├── store.py             # SQLite with FTS5 full-text search
│   ├── reputation.py        # Contribution scoring (computed but not enforced)
│   ├── analytics.py         # Engagement metrics
│   └── embeddings.py        # Vector storage (optional)
└── integrations/
    ├── mcp_server.py        # JSON-RPC 2.0 MCP server over stdio
    └── agent_hook.py        # borg_on_failure, borg_on_task_start entry points
```

**Core dependency: PyYAML only.** Embeddings, crypto, and SQLite are optional.

---

## What Exists vs What Doesn't

### What Exists (Phases 0-3 complete)

- Full CLI with 11 subcommands: search, pull, try, init, apply, publish, feedback, convert, list, autopilot, version
- MCP server with 10 tools wired to core modules
- Pack lifecycle: search → try → pull → apply → feedback
- Safety scanner (13 injection patterns, 11 privacy patterns)
- Proof gate validation with 4 confidence tiers (guessed/inferred/tested/validated)
- Privacy scanning and redaction
- Session logging with JSONL
- SQLite persistence with FTS5 full-text search
- Semantic search (optional, requires embeddings)
- SKILL.md / CLAUDE.md / .cursorrules converter
- Zero-config autopilot for Hermes
- 682+ unit tests across core modules
- OpenClaw integration docs

### What Doesn't Exist Yet

- **No external users.** Zero. The feedback loop that improves packs with real usage hasn't run.
- **No coordinator bot.** Pack publishing requires direct `gh` CLI access. The spec describes an automated coordinator — it doesn't exist in code.
- **Reputation engine is unwired.** `reputation.py` computes scores but nothing enforces access based on them.
- **Auto-suggest is minimal.** `borg_suggest` and `borg_on_task_start` exist as stubs; they're not production-quality suggestion engines.
- **No PyPI-hosted MCP server package.** The `agent-borg` package is on PyPI but only as a Python library. The MCP server runs via `borg-mcp` entry point.
- **Confidence decay is advisory only.** Packs don't get blocked based on age.
- **Safety scanner has false positives.** Known issue — code-heavy packs trigger injection pattern matches.

---

## Contributing

### Create a pack from a skill

```bash
borg init my-workflow
```

### Convert an existing CLAUDE.md / SKILL.md / .cursorrules

```bash
borg convert ./CLAUDE.md --format auto
```

### Publish a pack

```bash
# Requires GitHub CLI authenticated: gh auth status
borg publish ~/.hermes/borg/my-workflow/pack.yaml
```

### Run tests

```bash
pip install agent-borg[dev]
pytest borg/tests/
```

---

## Status

v2.4.0 — Phases 0-3 infrastructure is complete. The core engine works, the MCP transport is solid, and the safety/proof gate systems are functional. The gap is adoption: no external users means no feedback loop, which means packs haven't been battle-tested by the community yet.

The architecture is over-engineered for its current user count (zero external users). If you want to help prove it out, try the autopilot and file feedback on any packs that don't work for your use case.
