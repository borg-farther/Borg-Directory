# PRD: Borg Validation — Prove It Works or Kill It

**Status:** ACTIVE
**Date:** 2026-03-30
**Author:** Hermes Agent
**Philosophy:** Stop building. Start measuring. Ship what's proven.

---

## 0. The Tagline

> Domain-specific experience for solving real problems.
> The collective never forgets. We learn from every failure.
> Alpha is found through the hive.
> Assimilate now. Resistance is futile.

---

## 1. The Problem We're Solving

We have 40K LOC and 1,123 tests. We have zero evidence borg helps an agent make a better decision. This PRD fixes that.

**Core question:** Does an agent with borg access outperform an agent without it?

If yes → we have a product. If no → we delete code until we do.

---

## 2. Work Items

### WI-1: Benchmark Suite — Does Borg Help?

**Problem:** We don't know if borg makes agents better. We need to measure.

**Design:**

```
BENCHMARK = 10 realistic tasks an agent would face

For each task:
  1. Run agent WITHOUT borg → measure: time, success, quality
  2. Run agent WITH borg → measure: time, success, quality
  3. Delta = improvement (or regression)

Tasks span:
  - 3 coding/debugging tasks (borg core value prop)
  - 3 DeFi strategy tasks (V2 value prop)
  - 2 configuration/setup tasks
  - 2 edge cases (novel problems with no pack)
```

**The 10 Tasks:**

| # | Task | Domain | What Borg Should Help With |
|---|------|--------|---------------------------|
| 1 | Fix a Python import error in a multi-module project | debugging | systematic-debugging pack |
| 2 | Set up Docker Compose for a 3-service app | devops | docker-networking patterns |
| 3 | Debug a failing pytest with async mocks | testing | test-fix-patterns pack |
| 4 | Choose best yield strategy for 1000 USDC on Base | defi | V2 recommender |
| 5 | Evaluate if a new token is safe to trade | defi | GoPlus + collective warnings |
| 6 | Decide when to exit a yield position | defi | V2 exit guidance from outcomes |
| 7 | Configure nginx reverse proxy with SSL | devops | known pattern |
| 8 | Parse and transform a messy CSV with pandas | data | common approach |
| 9 | Novel: fix a race condition in async websocket code | novel | no pack exists — measure baseline |
| 10 | Novel: optimize a slow SQL query with no indexes | novel | no pack exists — measure baseline |

**Scoring (per task):**

```python
@dataclass
class TaskResult:
    task_id: str
    condition: str          # "baseline" or "with_borg"
    completed: bool         # did the agent finish?
    time_seconds: float     # wall clock time
    quality_score: float    # 0-1 (rubric-based)
    steps_taken: int        # how many tool calls
    errors_made: int        # wrong approaches tried
    borg_consulted: bool    # did agent use borg?
    borg_helpful: bool      # was borg's advice correct?
```

**Quality Rubric (per task, defined in advance):**

```yaml
# Example for Task 1: Fix Python import error
task_id: 1
rubric:
  - criterion: "Correctly identified the import issue"
    weight: 0.3
    pass_condition: "Agent mentions circular import or missing __init__.py"
  - criterion: "Fix actually resolves the error"
    weight: 0.5
    pass_condition: "Running the code after fix produces no ImportError"
  - criterion: "Fix doesn't break other imports"
    weight: 0.2
    pass_condition: "Full test suite passes after fix"
```

**Implementation:**

```
borg/benchmark/
├── __init__.py
├── runner.py           # Orchestrates benchmark runs
├── tasks/              # 10 task definitions
│   ├── task_01_import_error.py
│   ├── task_02_docker_compose.py
│   ├── ...
│   └── task_10_sql_optimize.py
├── rubrics/            # Scoring rubrics (YAML)
│   ├── task_01.yaml
│   └── ...
├── environments/       # Pre-built broken codebases for each task
│   ├── task_01/        # Python project with import error
│   └── ...
├── results/            # Raw results (JSON)
├── analysis.py         # Statistical analysis
└── report.py           # Generate comparison report
```

**Statistical Rigor:**

- Run each task 3 times per condition (account for LLM variance)
- Paired t-test for time/quality differences
- Effect size (Cohen's d) to measure practical significance
- Report confidence intervals, not just means

**Success Criteria:**

- [ ] 10 tasks defined with rubrics
- [ ] 10 environments built (reproducible broken codebases)
- [ ] Baseline run complete (30 runs: 10 tasks × 3 repetitions)
- [ ] Treatment run complete (30 runs with borg)
- [ ] Statistical analysis shows p < 0.05 on at least 3 metrics
- [ ] Report generated with honest results

**Verification:**

- Formal: paired t-test p-values for time, quality, success rate
- Formal: Cohen's d effect sizes with interpretation
- Informal: read 5 task transcripts and verify scoring matches rubric

---

### WI-2: Lean Skill Format — What Agents Actually Read

**Problem:** Current packs are 200-line YAML. Claude reads the first line. Agents need: trigger → principles → example → edge case. Nothing more.

**The Lean Format:**

```yaml
---
name: fix-python-imports
trigger: "Agent encounters ImportError, ModuleNotFoundError, or circular import"
---

# Fix Python Import Errors

## Principles (WHY, not just WHAT)
1. Python resolves imports depth-first. Circular imports fail at the SECOND import, not the first.
2. Missing `__init__.py` makes a directory invisible to Python's import system.
3. Relative imports (from . import X) only work inside packages, not scripts.
4. sys.path order matters — the FIRST match wins, even if it's wrong.

## Output Format
Return a diagnosis with:
- Root cause (one sentence)
- Fix (exact code change)
- Verification command (one command that proves it's fixed)

## Edge Cases
- CIRCULAR: A imports B imports A → fix by moving shared code to C
- SHADOW: local file named same as stdlib module → rename local file
- MESSY: import works in pytest but not in script → check sys.path differences

## Example

INPUT: `ModuleNotFoundError: No module named 'utils'`

OUTPUT:
```
Root cause: utils/ directory missing __init__.py
Fix: touch utils/__init__.py
Verify: python -c "from utils import helper; print('ok')"
```
```

**5 Skills to Rewrite:**

| # | Skill | Current State | Lean Rewrite |
|---|-------|--------------|-------------|
| 1 | systematic-debugging | 80 lines, 5 phases | trigger + 4 principles + example |
| 2 | test-driven-development | 60 lines, steps | trigger + 3 principles + example |
| 3 | code-review | 90 lines, checklist | trigger + 5 principles + example |
| 4 | docker-networking (new) | doesn't exist | trigger + 3 principles + example |
| 5 | defi-yield-strategy (new) | V2 recommender | trigger + 4 principles + example |

**Key Constraints:**

- Total skill length: ≤30 lines (excluding frontmatter)
- First line after `#` heading: one sentence explaining WHEN to use
- Principles: WHY reasoning, not WHAT steps. "Python resolves imports depth-first" not "Step 1: check imports"
- Example: complete input → output pair
- Edge cases: max 3, one line each
- Recovery: what to do if the approach fails (one line)

**Testing Each Skill:**

```python
def test_skill_effectiveness(skill_name, test_cases):
    """
    For each test case:
    1. Agent reads the skill
    2. Agent attempts the task
    3. Score against rubric
    
    Compare: agent with skill vs agent with full verbose pack vs agent with nothing
    """
    results = {
        "no_skill": [],
        "lean_skill": [],
        "verbose_pack": [],
    }
    
    for case in test_cases:
        for condition in results:
            score = run_agent(case, skill=condition)
            results[condition].append(score)
    
    return compare_conditions(results)
```

**Success Criteria:**

- [ ] 5 skills rewritten in lean format
- [ ] Each skill ≤30 lines
- [ ] Each has: trigger, principles (with reasoning), output format, edge cases, example
- [ ] A/B test: lean skill vs verbose pack vs no skill
- [ ] Lean skill outperforms verbose pack on ≥3 of 5 tasks

---

### WI-3: Circuit Breaker — Stop Bad Recommendations

**Problem:** If borg recommends a strategy that loses money, there's no automatic stop. The first 3 users are sacrificial canaries.

**Design:**

```python
class CircuitBreaker:
    """
    Monitors recommendation outcomes and disables packs that are hurting users.
    
    States:
      CLOSED  → recommendations flowing normally
      OPEN    → pack disabled, no recommendations
      HALF    → limited recommendations with warnings
    """
    
    # Thresholds
    MAX_CONSECUTIVE_LOSSES = 2      # 2 losses in a row → OPEN
    MAX_LOSS_RATE = 0.6             # >60% loss rate with ≥3 samples → OPEN  
    MAX_SINGLE_LOSS_PCT = 20.0      # any single loss >20% → HALF + alert
    RECOVERY_PERIOD_HOURS = 72      # stay OPEN for 72h before retrying
    
    def check_outcome(self, pack_id: str, outcome: ExecutionOutcome):
        """Called after every outcome. May trip the breaker."""
        
        state = self.get_state(pack_id)
        
        if not outcome.profitable:
            state.consecutive_losses += 1
            state.total_losses += 1
            
            # Single catastrophic loss
            if abs(outcome.return_pct) > self.MAX_SINGLE_LOSS_PCT:
                self.trip(pack_id, "HALF", 
                    f"Single loss of {outcome.return_pct}% exceeds threshold")
                self.alert_human(pack_id, outcome)
            
            # Consecutive losses
            if state.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
                self.trip(pack_id, "OPEN",
                    f"{state.consecutive_losses} consecutive losses")
                self.alert_human(pack_id, outcome)
            
            # Loss rate
            if state.total_outcomes >= 3:
                loss_rate = state.total_losses / state.total_outcomes
                if loss_rate > self.MAX_LOSS_RATE:
                    self.trip(pack_id, "OPEN",
                        f"Loss rate {loss_rate:.0%} exceeds {self.MAX_LOSS_RATE:.0%}")
        else:
            state.consecutive_losses = 0  # reset on win
        
        state.total_outcomes += 1
    
    def can_recommend(self, pack_id: str) -> tuple[bool, str]:
        """Check if a pack can be recommended."""
        state = self.get_state(pack_id)
        
        if state.status == "OPEN":
            if hours_since(state.tripped_at) > self.RECOVERY_PERIOD_HOURS:
                state.status = "HALF"  # auto-recover to half
            else:
                return False, f"Circuit OPEN: {state.reason}"
        
        if state.status == "HALF":
            return True, f"⚠️ WARNING: {state.reason}. Recommend smaller position."
        
        return True, ""
```

**Integration with V2 Recommender:**

```python
def recommend(self, query, limit=5):
    candidates = self.load_matching_packs(query)
    
    scored = []
    for pack in candidates:
        # Circuit breaker check
        can_rec, warning = self.circuit_breaker.can_recommend(pack.id)
        if not can_rec:
            continue  # skip this pack entirely
        
        score = self.calculate_score(pack)
        rec = self.to_recommendation(pack, score)
        
        if warning:
            rec.rug_warnings.append(warning)
            rec.confidence *= 0.5  # halve confidence for warned packs
        
        scored.append(rec)
    
    return sorted(scored, key=lambda x: x.confidence, reverse=True)[:limit]
```

**Human Alert:**

When circuit breaker trips, send to Telegram:

```
🚨 BORG CIRCUIT BREAKER TRIPPED

Pack: yield/kamino-usdc-sol
Status: OPEN (disabled)
Reason: 2 consecutive losses (-8.2%, -12.1%)

The collective has paused this recommendation.
It will auto-retry in 72 hours in HALF mode.

To manually override: borg pack enable yield/kamino-usdc-sol
```

**Success Criteria:**

- [ ] CircuitBreaker class with CLOSED/OPEN/HALF states
- [ ] Trips on: 2 consecutive losses, >60% loss rate, >20% single loss
- [ ] Auto-recovery after 72h to HALF mode
- [ ] Integrated into V2 recommender
- [ ] Human alert on trip
- [ ] Tests: trip on losses, don't trip on wins, recovery, half-mode behavior
- [ ] Edge: new pack with 1 loss doesn't trip (needs minimum samples)

---

### WI-4: Deterministic Execution Layer for DeFi

**Problem:** Borg says "exit at 7 days" but the agent might forget. High-stakes DeFi actions need deterministic execution, not advisory suggestions.

**Design:**

```python
@dataclass
class DeFiCommitment:
    """A binding action the system WILL execute, not a suggestion."""
    commitment_id: str
    pack_id: str
    action: str              # "exit_position" | "enter_position" | "rebalance"
    trigger: str             # "time_based" | "condition" | "circuit_breaker"
    
    # Time-based
    execute_at: Optional[datetime] = None  # when to fire
    
    # Condition-based
    condition: Optional[str] = None  # "health_factor < 1.3" | "il_pct > yield_pct"
    check_interval_minutes: int = 30
    
    # Safety
    max_loss_pct: float = 10.0     # hard stop — exit if loss exceeds this
    human_approval_required: bool = False  # for amounts > threshold
    
    # State
    status: str = "pending"  # pending | executing | completed | failed | cancelled
    created_at: datetime = field(default_factory=datetime.now)


class CommitmentEngine:
    """Executes DeFi commitments deterministically."""
    
    def create_commitment(self, rec: StrategyRecommendation, 
                          entry_amount_usd: float) -> DeFiCommitment:
        """Create a binding commitment from a recommendation."""
        
        commitment = DeFiCommitment(
            commitment_id=generate_id(),
            pack_id=rec.pack_id,
            action="exit_position",
            trigger="time_based",
            execute_at=datetime.now() + timedelta(days=rec.avg_duration_days),
            max_loss_pct=10.0,
        )
        
        # Also create a monitoring commitment
        monitor = DeFiCommitment(
            commitment_id=generate_id(),
            pack_id=rec.pack_id,
            action="check_position",
            trigger="condition",
            condition="loss_pct > max_loss_pct",
            check_interval_minutes=30,
        )
        
        self.save(commitment)
        self.save(monitor)
        
        # Create actual cron job for the exit
        self.schedule_cron(commitment)
        
        return commitment
    
    def execute(self, commitment: DeFiCommitment) -> bool:
        """Execute a commitment. Returns True if successful."""
        
        if commitment.human_approval_required:
            approved = self.request_human_approval(commitment)
            if not approved:
                commitment.status = "cancelled"
                self.save(commitment)
                return False
        
        # Execute the action
        try:
            if commitment.action == "exit_position":
                result = self.swap_executor.exit_position(commitment)
            elif commitment.action == "check_position":
                result = self.check_and_alert(commitment)
            
            commitment.status = "completed"
            
            # Record outcome for V2 learning loop
            outcome = self.create_outcome_from_commitment(commitment, result)
            self.recommender.record_outcome(outcome)
            
        except Exception as e:
            commitment.status = "failed"
            self.alert_human(commitment, error=str(e))
        
        self.save(commitment)
        return commitment.status == "completed"
```

**Cron Integration:**

```python
# When agent accepts a recommendation:
rec = recommender.recommend(query)[0]

# Create deterministic commitments
commitment = engine.create_commitment(rec, entry_amount_usd=1000)

# This creates:
# 1. Cron job: "exit position in 7 days"
# 2. Monitor: "check every 30 min, alert if loss > 10%"
# 3. Hard stop: "exit immediately if loss > 20%"

# Agent doesn't need to remember. The system enforces.
```

**Success Criteria:**

- [ ] DeFiCommitment dataclass with time/condition triggers
- [ ] CommitmentEngine creates cron jobs for exits
- [ ] Position monitor checks every 30 min
- [ ] Hard stop at configurable loss threshold
- [ ] Human approval for amounts > $1000
- [ ] Outcome auto-recorded on commitment completion
- [ ] Tests: commitment lifecycle, cron creation, hard stop trigger

---

### WI-5: Honest Documentation + Risk Disclosure

**What to write:**

```markdown
# Borg — Honest Status

## What Works (Proven)
- Skill search and retrieval
- CLI and MCP tool interface
- DeFi yield/token/TVL scanning (live API data)
- Lean skill format fires reliably with Claude/GPT agents

## What's Unproven
- Collective learning (V2): seed packs contain synthetic data
- Strategy recommendations: no real agent outcomes yet
- Thompson Sampling: mathematically sound, practically untested
- Warning propagation: needs 2+ agents to lose before it fires

## What Could Go Wrong
- Borg recommends a yield pool that rugs → first 2 users lose money before warning fires
- Seed pack data is fictional → early recommendations are educated guesses, not collective intelligence
- Alpha decay: if many agents follow the same recommendation, returns degrade (crowding)
- Stale data: strategies that worked last month may not work now

## Risk Mitigations
- Circuit breaker: 2 consecutive losses → pack disabled
- Hard stops: >20% loss on any position → auto-exit
- Human alerts: every circuit breaker trip notifies via Telegram
- Honest seed packs: clearly marked as synthetic until real outcomes replace them

## How to Interpret Recommendations
- <3 outcomes: "We're guessing. Treat as experimental."
- 3-9 outcomes: "Some evidence. Smaller position recommended."
- 10+ outcomes: "Real collective data. Higher confidence."
- Any warning flag: "Agents have lost money here. Proceed with extreme caution."

## First User Experience
You are building the collective from scratch. Your outcomes become the first real data.
This is valuable — you're the foundation. But it also means early recommendations
are based on synthetic data, not battle-tested collective intelligence.

We'd rather tell you this than pretend the system is mature.
```

**Success Criteria:**

- [ ] Honest status doc in README or standalone
- [ ] Risk disclosure for DeFi module
- [ ] Seed pack data clearly marked as synthetic
- [ ] Confidence levels explained for end users
- [ ] "What could go wrong" section with mitigations

---

## 3. Implementation Plan

**Batch 1 (parallel, no dependencies):**
- WI-2: Lean skill rewrites (5 skills)
- WI-3: Circuit breaker
- WI-5: Honest docs

**Batch 2 (depends on WI-2):**
- WI-1: Benchmark suite (needs lean skills to test)

**Batch 3 (depends on WI-3):**
- WI-4: Deterministic execution layer

**Batch 4:**
- WI-1: Run benchmarks, analyze results, report

---

## 4. Definition of Done

- [ ] 5 lean skills, each ≤30 lines, with trigger/principles/example/edge
- [ ] Benchmark suite: 10 tasks, rubrics, environments
- [ ] Benchmark results: statistical comparison with/without borg
- [ ] Circuit breaker: trips on losses, recovers, alerts humans
- [ ] Deterministic layer: cron-backed exits and hard stops
- [ ] Honest docs: risk disclosure, confidence levels, synthetic data flagged
- [ ] All existing 1,123 tests still pass
- [ ] New tests for circuit breaker, commitments, benchmark runner
