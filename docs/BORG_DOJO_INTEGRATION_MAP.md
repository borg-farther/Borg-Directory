# Borg + Dojo Integration Map

**Date:** 2026-03-29  
**Status:** Analysis Complete — Implementation Pending  
**Goal:** Merge dojo's practical session-analysis capabilities into borg's collective intelligence architecture.

---

## Overview

dojo and borg share a common purpose — improving agent performance through structured learning — but they operate at different levels:

| System | Scope | Data Source | Key Capability |
|--------|-------|-------------|----------------|
| **dojo** | Tool/session level | `~/.hermes/state.db` (Hermes聊天日志) | Pattern detection, auto-patching |
| **borg** | Pack/workflow level | `~/.hermes/guild/` (pack executions) | Pack search, trust scoring, collective intelligence |

The integration pipes dojo's fine-grained session analysis into borg's ecosystem-level pack infrastructure.

---

## dojo Module Reference

| Module | File | Core Function |
|--------|------|---------------|
| **monitor** | `hermes-dojo/scripts/monitor.py` | Reads `state.db`, detects tool failures, user corrections, retry loops, skill gaps |
| **analyzer** | `hermes-dojo/scripts/analyzer.py` | Takes monitor output → prioritized patch/create/evolve recommendations |
| **fixer** | `hermes-dojo/scripts/fixer.py` | Applies fixes, runs self-evolution, generates skill patches from FIX_STRATEGIES |
| **reporter** | `hermes-dojo/scripts/reporter.py` | Formats reports for CLI/Telegram, sparkline trend display |
| **tracker** | `hermes-dojo/scripts/tracker.py` | Persists daily snapshots to `metrics.json`, computes learning curves |

---

## 1. `borg/core/aggregator.py` ↔ dojo monitor.py

### What borg/aggregator.py Does (Current)

`PackAggregator` collects execution data for a **single pack** across multiple runs:

- **Ingestion:** Parses JSONL execution logs via `ingest_execution()`. Looks for `execution_started`, `checkpoint_pass`, `checkpoint_fail`, `execution_completed` event types.
- **Metrics:** Computes `success_rate`, `avg_iterations` (mean duration), per-phase pass/fail counts, `common_failures` (phases with ≥2 failures AND <70% success rate).
- **Suggestions:** Generic suggestions like "add common failure handling to phase X".
- **Confidence promotion:** Tier upgrades `inferred → tested` after 10+ executions at ≥70% success.
- **Improvement generation:** Adds hardcoded anti-pattern strings to failing phases.

### What dojo monitor.py Does Differently

- Reads **raw Hermes聊天数据库 (`state.db`)** — tool-level failures, not pack-level phases.
- Detects **retry patterns** (same tool called multiple times in <30s).
- Detects **user corrections** (user says "no, I meant..." patterns).
- Identifies **skill gaps** (user requests for capabilities with no matching skill).
- Computes **per-tool success rates** (not per-phase within a pack).

### Integration Points

```
dojo monitor.py                          borg aggregator.py
────────────────                         ─────────────────

analyze_sessions(days=7)
  → weakest_tools[]       ──────────────►  phase_metrics (per-phase success rates)
  → overall_success_rate ──────────────►  compute_metrics().success_rate
  → retry_patterns[]     ──────────────►  track in aggregator for retry-aware suggestions
  → skill_gaps[]         ──────────────►  new: gap-aware improvement suggestions
  → user_corrections[]   ──────────────►  feed into suggest_improvements()
```

**Specific wiring:**

1. **`PackAggregator.ingest_session_data(session_data: dict)`** — new method that accepts the full `analyze_sessions()` output and extracts per-pack signals:
   - Map tool errors to phase-level failures (via checkpoint names or session metadata).
   - Pull `overall_success_rate` into `compute_metrics()` as a baseline/floor.
   - Store `retry_patterns` and `user_corrections` for context-aware suggestion generation.

2. **`suggest_improvements()` enrichment** — when `common_failures` is empty, consult `skill_gaps` from dojo for gap-driven suggestions (e.g., "no skill exists for X — consider creating a pack").

3. **`compute_metrics()` enhancement** — add `tool_error_rate` and `user_correction_count` fields pulled from dojo session data.

**Code sketch:**
```python
def ingest_session_data(self, session_data: dict) -> None:
    """Ingest dojo monitor session analysis data."""
    for tool in session_data.get("weakest_tools", []):
        # Map tool name to phase name if possible
        phase_name = self._tool_to_phase.get(tool["tool"], "unknown")
        self._tool_errors[phase_name].append(tool)

    self._user_corrections = session_data.get("user_corrections", 0)
    self._skill_gaps = session_data.get("skill_gaps", [])
```

---

## 2. `borg/integrations/nudge.py` ↔ dojo monitor.py

### What borg nudge.py Does (Current)

`NudgeEngine` runs in a background thread, monitors conversation turns, and fires proactive suggestions:

- **Signal types:** `keyword` (from `classify_task`), `frustration` (hardcoded phrases), `error` (tool errors).
- **Decision paths:** frustration → `borg_on_failure`; keywords → `borg_on_task_start`; tool errors only → `borg_on_failure` with error context.
- **Confidence:** Base 0.85 (frustration) or 0.6 (proactive), multiplied by pack outcome history.
- **Suppression:** `_suppressed_packs` set, per-pack cooldown.

### What dojo monitor.py Does That nudge.py Can't

- **Pattern-based tool failure classification** — does regex matching against error text (30+ patterns like `timeout`, `permission denied`, `rate limit`, `ENOENT`).
- **User correction detection** — detects "no I meant", "wrong", "that's not what I" patterns.
- **Skill gap detection** — maps user requests to capability names (csv-parsing, docker-management, etc.).
- **Retry loop detection** — flags same tool called 2+ times in quick succession.

### Integration Points

```
dojo monitor.py               borg nudge.py
───────────────               ──────────────

analyze_sessions()
  → weakest_tools[]           → submit_turn() enriches error signals
  → user_corrections[]        → new signal_type: "correction"  
  → skill_gaps[]              → new signal_type: "skill_gap"
  → retry_patterns[]         → suppress repeated pack nudges proactively
```

**Specific wiring:**

1. **New signal type: `"correction"`** — `NudgeSignal` dataclass already has `signal_type: str`, no schema change needed. In `submit_turn()`, detect correction patterns and append `NudgeSignal(signal_type="correction", ...)`. In `_compute_nudge_unlocked()`, handle `"correction"` signals by boosting confidence of failure-path nudges.

2. **Skill gap signals** — add a `skill_gap` signal type. When a skill gap is detected, instead of (or in addition to) keyword-based nudging, trigger a proactive pack suggestion for the gap capability. Wire into `_call_borg_on_task_start()` with the gap capability as the search term.

3. **Retry-aware suppression** — dojo's `retry_patterns` data tells us which tools are in retry loops. If a user has already retried the same tool 3x, suppress generic nudges for that tool's domain and instead suggest a pack targeting that specific failure mode.

4. **`_compute_nudge_unlocked()` enhancement** — pass `session_data` (dojo's `analyze_sessions()` output) to give the nudge engine cross-session context:
   ```python
   def _compute_nudge_unlocked(self, session_context: dict = None) -> Optional[NudgeDecision]:
       # Use session_context["weakest_tools"] to weight nudge confidence
       # Use session_context["skill_gaps"] to pre-populate proactive suggestions
   ```

---

## 3. `borg/core/search.py` ↔ dojo analyzer.py (skill gap detection)

### What borg search.py Does (Current)

- **`borg_search()`** — text search over pack index. Searches `name`, `problem_class`, `id`, `phase_names`. Supports `text`/`semantic`/`hybrid` modes. Reranks by author reputation (CORE/GOVERNANCE authors get boosted).
- **`check_for_suggestion()`** — triggered when `failure_count >= 2` or frustration signals. Uses `classify_task()` (keyword map: 40+ entries) to extract search terms. Returns top 3 pack matches.
- **`classify_task()`** — hardcoded keyword map. Returns search terms like `"debug"`, `"test"`, `"github"`, `"deploy"`, `"refactor"`.

### What dojo analyzer.py Does That search.py Can't

- **Data-driven gap detection** — `analyzer.generate_recommendations()` actually analyzes real session failures and user requests. It produces `skill_gaps` that are **proven gaps** (user requested, no skill exists), not just keyword guesses.
- **Tool-to-skill mapping** — `map_tool_to_skill()` fuzzy-matches tool names to existing skills. Gaps that can't be mapped indicate missing capabilities.
- **Priority scoring** — gaps ranked by `requests * 10` priority, so frequently-requested missing skills surface first.

### Integration Points

```
dojo analyzer.py              borg search.py
───────────────               ──────────────

generate_recommendations()
  → skill_gaps[]               → classify_task() + check_for_suggestion()
  → action="create"           → trigger borg_init() for new pack from gap
  → priority scores           → influence search result ranking
```

**Specific wiring:**

1. **`classify_task()` enrichment** — replace or extend the hardcoded `_KEYWORD_MAP` with dynamically-loaded skill gaps from dojo:
   ```python
   def classify_task(context: str, skill_gaps: list = None) -> List[str]:
       # First use dojo skill gaps if available
       if skill_gaps:
           gaps_as_keywords = [g["capability"] for g in skill_gaps if g.get("capability")]
           # Match gaps against context
           ...
       # Fall back to hardcoded keyword map
       return terms
   ```

2. **`check_for_suggestion()` gap-aware path** — add a gap-first code path:
   ```python
   def check_for_suggestion(..., skill_gaps: list = None):
       # If skill_gaps exist and match context, prefer gap-driven pack creation
       # over pack search (the pack may not exist yet)
       gap_match = find_gap_match(context, skill_gaps)
       if gap_match and gap_match["requests"] >= 2:
           # Return a suggestion to CREATE a pack for this gap
           return suggest_pack_creation(gap_match)
   ```

3. **New function: `suggest_pack_for_gap(gap: dict)`** — when dojo detects a skill gap with no existing pack, this function generates a new pack stub via `borg_init()` targeting that specific capability. This closes the loop from detection → creation.

---

## 4. `borg/core/apply.py` ↔ dojo fixer.py

### What borg apply.py Does (Current)

- **`action_start()`** — loads pack YAML, safety scans, creates session, returns approval summary. Does NOT log `execution_started` until `__approval__` checkpoint passes.
- **`action_checkpoint()`** — logs phase results. Each phase gets 1 retry. On retry exhaustion, phase is marked "failed" and execution continues to next phase.
- **`action_complete()`** — generates feedback draft, writes to disk, logs execution to store. Feedback includes `why_it_worked`, `what_changed`, `suggestions` (phase-level, generic).
- **`_generate_feedback()`** — inline feedback generation. Suggestions are phase-specific but generic ("consider breaking it into smaller steps").

### What dojo fixer.py Does That apply.py Can't

- **Error classification** — `fixer.classify_error()` maps error text to 8 categories: `path_not_found`, `timeout`, `permission_denied`, `command_not_found`, `rate_limit`, `wrong_context`, `missing_dependency`, `generic`.
- **FIX_STRATEGIES** — a dict of 8 concrete fix strategies, each with a `patch` description and `skill_addition` markdown content.
- **Skill patch generation** — `generate_skill_patch()` produces structured `tool_instruction` dicts ready for the `skill_manage` tool.
- **Self-evolution** — `run_evolution()` invokes the hermes-agent-self-evolution pipeline for skills with ≥90% calls but <90% success.

### Integration Points

```
dojo fixer.py                 borg apply.py
───────────────               ──────────────

FIX_STRATEGIES                → use in action_checkpoint() on failure
classify_error()              → pass phase evidence through classify_error()
generate_skill_patch()        → feed into feedback_draft["suggestions"]
run_evolution()               → called from action_complete() for weak packs
```

**Specific wiring:**

1. **`action_checkpoint()` on failure** — when a phase fails after retry, pipe the `evidence` text through `fixer.classify_error()`:
   ```python
   def action_checkpoint(...):
       ...
       elif status == "failed":
           error_type = classify_error(evidence)  # from fixer
           strategy = FIX_STRATEGIES.get(error_type, FIX_STRATEGIES["generic"])
           guidance = (
               f"Phase '{phase_name}' failed ({error_type}). "
               f"Fixer suggestion: {strategy['patch']}"
           )
   ```
   This gives operators actionable, specific guidance rather than "consider breaking it into smaller steps."

2. **`action_complete()` feedback enrichment** — instead of generic phase suggestions, use `generate_skill_patch()` to produce concrete patch instructions:
   ```python
   def _build_phase_suggestion(phase_result: dict, skill_path: str = None) -> str:
       error_type = classify_error(phase_result.get("evidence", ""))
       strategy = FIX_STRATEGIES.get(error_type, FIX_STRATEGIES["generic"])
       return f"Fix: {strategy['patch']} — Add: {strategy['skill_addition']}"
   ```

3. **Self-evolution trigger** — in `action_complete()`, after generating feedback, check if the pack's success rate (from aggregator metrics) qualifies for `run_evolution()`:
   ```python
   if phases_failed > 0 and success_rate < 0.7 and total_phases >= 5:
       evolution_result = run_evolution(skill_name=pack_name, iterations=5, dry_run=True)
       feedback_draft["evolution_candidate"] = evolution_result
   ```

---

## 5. `borg/db/reputation.py` ↔ dojo monitor.py (success rate tracking)

### What borg reputation.py Does (Current)

`ReputationEngine` computes trust scores for agents based on pack contributions:

- **`contribution_score()`** — weighted sum of `ACTION_WEIGHTS` (pack_publication=10, quality_review=3, bug_report=2, etc.) with recency decay (`lambda=0.95` per 30-day epoch).
- **`delta_pack_published()`** — rep deltas by confidence: `guessed=1`, `inferred=3`, `tested=7`, `validated=15`.
- **`delta_pack_failure()`** — fixed `-2` penalty.
- **`free_rider_score()`** — `packs_consumed / max(1, packs_contributed + quality_reviews)`.
- **`apply_pack_failure()`** — records failure, updates agent stats.
- **`build_profile()`** — aggregates all data into a `ReputationProfile`.

### What dojo monitor.py Tracks That reputation.py Doesn't

- **Per-tool success rates** — which specific tools an agent uses successfully vs. fails with.
- **User correction rate** — how often an agent needs correction, which maps to a quality signal.
- **Retry loop count** — agents caught in retry loops may have lower effectiveness scores.

### Integration Points

```
dojo monitor.py               borg reputation.py
───────────────               ───────────────────

overall_success_rate          → factor into agent contribution_score
user_corrections              → new signal in ReputationEngine
weakest_tools[]               → per-tool quality scores per agent
skill_gaps[]                  → flag agents who frequently hit skill gaps
```

**Specific wiring:**

1. **`ContributionAction` enrichment** — add a `quality` field based on session-level success rate:
   ```python
   def contribution_score(self, agent_id: str, actions: list[ContributionAction],
                          session_data: dict = None) -> float:
       base_score = super().contribution_score(agent_id, actions)
       if session_data:
           # Adjust based on tool-level success rate
           tool_success = session_data.get("overall_success_rate", 100)
           base_score *= (tool_success / 100.0)
       return base_score
   ```

2. **New `apply_session_feedback()` method** — record user corrections and tool errors into the agent's reputation profile:
   ```python
   def apply_session_feedback(self, agent_id: str, session_data: dict) -> ReputationProfile:
       corrections = session_data.get("user_corrections", 0)
       if corrections > 0:
           # Negative quality signal from corrections
           delta = -corrections  # small penalty per correction
           self.store.update_agent_stats(agent_id, contribution_score_delta=delta)
   ```

3. **`delta_pack_failure()` enhancement** — look at the actual tool that failed to provide more granular failure tracking. Instead of a flat `-2`, weight by error severity (timeout=-1, permission=-2, path_not_found=-3).

---

## 6. `borg/db/analytics.py` ↔ dojo tracker.py (learning curve)

### What borg analytics.py Does (Current)

`AnalyticsEngine` computes ecosystem-level metrics:

- **`pack_usage_stats()`** — `pull_count`, `apply_count`, `success_count`, `failure_count`, `completion_rate` per pack.
- **`adoption_metrics()`** — unique agents and operators per pack.
- **`ecosystem_health()`** — total agents, active contributors/consumers, contributor ratio, avg quality score, tier distribution, domain coverage.
- **Time series:** `timeseries_pack_publishes()`, `timeseries_executions()`, `timeseries_quality_scores()`, `timeseries_active_agents()`.
- **`_daily_buckets()`, `_weekly_buckets()`, `_monthly_buckets()`** — time bucketing helpers.

### What dojo tracker.py Does That analytics.py Doesn't

- **Daily snapshots** — saves a daily JSON snapshot to `~/.hermes/skills/hermes-dojo/data/metrics.json` with per-tool success rates, correction counts, skill gap counts, retry pattern counts.
- **Learning curve display** — sparkline visualization, trend direction (first→last success rate).
- **Before/after tracking** — `improvements_made` field tracks what changed between snapshots.

### Integration Points

```
dojo tracker.py               borg analytics.py
───────────────               ─────────────────

save_snapshot()               → new: timeseries_dojo_metrics()
load_metrics()                → new: ecosystem_health() enrichment
metrics.json                  → new: cross-reference with pack_usage_stats
learning curve                → new: adoption_metrics() uses for trend
```

**Specific wiring:**

1. **`timeseries_dojo_metrics()`** — new method in `AnalyticsEngine`:
   ```python
   def timeseries_dojo_metrics(self, period: str = "daily", days: int = 30) -> TimeSeriesResult:
       """Time series of dojo session success rates (learning curve)."""
       from dojo_tracker import load_metrics  # lazy import
       history = load_metrics()
       # Convert to TimeSeriesResult using period bucketing
       ...
   ```
   This gives borg the same learning curve visualization as dojo's CLI.

2. **`ecosystem_health()` enrichment** — add dojo session data to the health report:
   ```python
   def ecosystem_health(self, now: Optional[datetime] = None) -> EcosystemHealth:
       base = super().ecosystem_health(now)
       # Add dojo metrics
       dojo_data = load_metrics()  # from tracker
       if dojo_data:
           base.avg_tool_success_rate = avg(d["overall_success_rate"] for d in dojo_data)
           base.total_corrections = sum(d.get("user_corrections", 0) for d in dojo_data)
       return base
   ```

3. **`pack_usage_stats()` cross-reference** — when computing `completion_rate`, also check dojo's `weakest_tools` to see if failures are concentrated in specific tools used by the pack. This adds tool-level failure context to pack-level metrics.

4. **`AdoptionMetrics` enhancement** — if a pack's users frequently hit skill gaps (from dojo), flag it as a `gap_indicator` — the pack may be addressing a gap area but not fully closing it.

---

## 7. `hermes-plugin/__init__.py` ↔ dojo monitor.py (session reading)

### What the Plugin Does (Current)

`register(ctx)` sets up the guild-v2 plugin in Hermes:

1. **`_patch_guild_autosuggest()`** — monkey-patches `tools.guild_autosuggest.check_for_suggestion` to delegate to `borg.integrations.agent_hook.guild_on_failure`.
2. **`_make_guild_v2_autosuggest_tool()`** — registers `guild_v2_autosuggest` tool for direct LLM use.
3. **`_register_lifecycle_hooks()`** — registers `on_consecutive_failure` and `on_task_start` hooks (informational only — not yet called by `run_agent.py`).
4. **`NudgeEngine` startup** — starts `NudgeEngine` in background thread, exposes `_borg_submit_turn`, `_borg_poll_nudge` on `ctx`.

### What dojo monitor.py Does That the Plugin Doesn't

- **Reads `~/.hermes/state.db`** directly for session analysis. The plugin currently only hooks into the agent loop via `submit_turn()` — it doesn't directly query the Hermes聊天数据库.
- **Provides a complete picture** of what happened in a session, not just what was said in the current conversation window.

### Integration Points

```
dojo monitor.py               hermes-plugin __init__.py
───────────────               ─────────────────────────

analyze_sessions()            → call from _borg_submit_turn() periodically
weakest_tools[]               → feed into NudgeEngine confidence calculation
skill_gaps[]                  → pre-populate proactive nudges
state.db reads                → new: read Hermes session DB directly
```

**Specific wiring:**

1. **`_borg_submit_turn()` periodic analysis** — every N turns (e.g., every 10), trigger a lightweight dojo `analyze_sessions(days=1)` and cache the result:
   ```python
   def _submit_turn(...):
       ...
       _nudge_turn_index[0] += 1
       # Every 10 turns, refresh dojo session analysis
       if _nudge_turn_index[0] % 10 == 0:
           _dojo_cache = analyze_sessions(days=1)  # lightweight
   ```
   Pass `_dojo_cache` to `_compute_nudge_unlocked()`.

2. **Direct `state.db` access for session context** — add a helper that reads dojo's `analyze_sessions()` output and exposes `weakest_tools` and `skill_gaps` to the nudge engine:
   ```python
   def _get_dojo_context() -> dict:
       try:
           from hermes_dojo.scripts.monitor import analyze_sessions
           return analyze_sessions(days=7)
       except Exception:
           return {}
   ```
   This is called once on plugin load and cached.

3. **`ctx._dojo_context`** — expose dojo session context on the plugin context so `borg_on_failure` and `borg_on_task_start` hooks can consult it:
   ```python
   ctx._dojo_context = _get_dojo_context()
   ```

4. **`_register_lifecycle_hooks()` full implementation** — currently informational only. Wire `on_consecutive_failure` to actually call `borg_on_failure` with dojo `weakest_tools` context:
   ```python
   def on_consecutive_failure_hook(task_description: str = "", ...):
       dojo_ctx = getattr(ctx, '_dojo_context', {}) or {}
       weakest = dojo_ctx.get("weakest_tools", [])
       suggestion = agent_hook.guild_on_failure(
           context=error_context or task_description,
           failure_count=failure_count,
           tried_packs=None,
           weakest_tools=weakest,  # NEW: pass dojo weakest tools
       )
   ```

---

## Summary of Integration Points

| # | Borg File | dojo Module | Integration Type | Priority |
|---|----------|------------|-----------------|----------|
| 1 | `aggregator.py` | `monitor.py` | Session data ingestion into pack metrics | **High** |
| 2 | `nudge.py` | `monitor.py` | Signal enrichment (correction, skill_gap, retry-aware) | **High** |
| 3 | `search.py` | `analyzer.py` | Gap-aware pack search + gap-driven pack creation | **High** |
| 4 | `apply.py` | `fixer.py` | Error-classified phase guidance + self-evolution trigger | **Medium** |
| 5 | `reputation.py` | `monitor.py` | Per-agent tool success rates, correction signals | **Medium** |
| 6 | `analytics.py` | `tracker.py` | Learning curve time series, ecosystem health cross-reference | **Medium** |
| 7 | `hermes-plugin/__init__.py` | `monitor.py` | Periodic session analysis, state.db direct reads | **High** |

---

## Key Shared Data Structures

### Session Context (from dojo monitor)

```python
{
    "overall_success_rate": float,       # 0-100
    "weakest_tools": [
        {"tool": str, "total": int, "errors": int,
         "success_rate": float, "top_error": str},
        ...
    ],
    "user_corrections": int,
    "correction_samples": [...],
    "retry_patterns": [
        {"tool": str, "count": int, "session_id": str},
        ...
    ],
    "skill_gaps": [
        {"capability": str, "requests": int},
        ...
    ],
}
```

### dojo Recommendation (from analyzer)

```python
{
    "action": "patch" | "create" | "evolve" | "investigate",
    "priority": float,
    "target": str,          # skill or tool name
    "skill_path": str,       # path to skill (for patch/evolve)
    "reason": str,
    "top_error": str,
    "suggested_fix": str,
}
```

### Fix Strategy (from fixer)

```python
FIX_STRATEGIES = {
    "path_not_found": {
        "patch": "Add path validation...",
        "skill_addition": "## Pre-flight Checks\n..."
    },
    "timeout": { ... },
    "permission_denied": { ... },
    "command_not_found": { ... },
    "rate_limit": { ... },
    "wrong_context": { ... },
    "missing_dependency": { ... },
    "generic": { ... },
}
```

---

## Implementation Notes

1. **Graceful degradation** — all dojo imports are optional. If dojo is not installed, borg operates on its existing data sources only. Use `try/except ImportError` around all dojo references.

2. **Database path compatibility** — dojo reads `~/.hermes/state.db`. Borg uses `~/.hermes/guild/`. These are separate filesystems — no conflicts.

3. **Performance** — dojo `analyze_sessions()` reads the full `state.db`. Cache results for at least 5 minutes to avoid repeated DB reads. The nudge engine's 1-second polling loop must not trigger dojo analysis on every poll.

4. **Bidirectional** — this integration is not one-way. Borg's pack ecosystem can also feed dojo: when a new pack is published via borg, that information should be visible in dojo's skill gap analysis (the gap is now filled).
