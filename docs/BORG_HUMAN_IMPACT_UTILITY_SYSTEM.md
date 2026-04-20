# Borg Human Impact + Utility Operating System

Date: 2026-04-20  
Machine source: `eval/borg_human_impact_os.json`

## Executive TL;DR
- Borg should be explained to humans through five questions only: finish rate, cost, speed, reliability, trust.
- Current evidence is strong on utility and reliability, weak on external adoption.
- Best next move: ship a public impact endpoint and proof-linked narratives by audience.

## The 5-question human model
Humans evaluating agent infra almost always ask:
1. Is my agent finishing more work?
2. Is it cheaper?
3. Is it faster?
4. Is it reliable at my scale?
5. Why should I trust the claims?

Borg already has machine evidence for each.

## Current measured impact (from live artifacts)
- Completion lift: **+65 percentage points** (35% -> 100%)
- Pass-rate lift: **+100 percentage points** (0% -> 100%)
- Tokens saved per task: **1,275**
- Time saved per task: **25.5s**
- Readiness: **ready_for_10=true, ready_for_100=true**

## Utility scorecard
- Utility: **8.8 / 10**
- Trustability of evidence: **8.6 / 10**
- Adoption: **3.5 / 10**
- Overall: **7.3 / 10**

Interpretation: product value is real; distribution is the bottleneck.

## Audience-specific framing

### For operators
"Your agent now shows measured completion, cost, and speed gains with passing 100-user readiness gates."

### For builders
"Use machine endpoints (`status.json`, `value.json`) to embed proof in your own UI without manual reporting."

### For executives
"Value and reliability are now proven in current gates; growth outcome depends on distribution and onboarding conversion."

## Trust rules (non-negotiable)
- Never present readiness from stale docs.
- Always tie claims to `eval/gate_run_snapshot.json` timestamp.
- Separate real vs synthetic telemetry sources in all public reports.

## What to publish at web URL
- `/status` -> readiness truth (`docs/public/status.json`)
- `/value` -> utility/value truth (`docs/public/value.json`)
- `/impact` -> human narrative + scorecard (`docs/public/impact/index.html`)
- `/proof` -> role-specific case studies with live trace linkage (`docs/public/proof/index.html`)
- machine case-study feed: `docs/public/proof/case-studies.json` (mirrored at `docs/public/impact/case-studies.json`)

## Next 7-day execution
1. Publish impact page and JSON feed.
2. Add 3 role-based case studies (operator, builder, exec).
3. Instrument funnel: docs view -> install -> first passing run.
4. Add weekly trend deltas (up/down/flat) for utility and adoption.
