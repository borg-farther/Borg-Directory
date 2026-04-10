# Borg E2E Learning Loop — Product Requirements Document v2
## Version 1.0 | 2026-04-02

---

## 1. Executive Summary

**Current State:** The E2E learning loop is partially implemented but has 8 critical architectural gaps that prevent feedback signals from propagating correctly through the loop. The `BorgV3` integration layer exists (`borg/core/v3_integration.py`), and individual components (`ContextualSelector`, `MutationEngine`, `FeedbackLoop`, `FailureMemory`, `TraceCapture`) are implemented, but the wiring between them is incomplete or absent.

**Target State:** A closed-loop learning system where: (1) pack selection outcomes flow back to Thompson Sampling posteriors, (2) A/B test variant assignments are tracked through the feedback cycle, (3) prior failure context is retrieved and injected at selection time, (4) feedback signals modulate exploration/exploitation balance, (5) unhelpful traces decay over time, (6) concurrent MCP sessions maintain isolated trace state, (7) root causes are captured alongside traces, and (8) agent identity propagates through the entire trace lifecycle.

**Delta:** 8 targeted engineering fixes to close the loop. No new components required — all infrastructure exists.

---

## 2. Background — Current State Analysis

### 2.1 Component Inventory

| Component | File | Implementation Status | Gaps |
|-----------|------|----------------------|------|
| `BorgV3` (integration layer) | `borg/core/v3_integration.py` | Complete | `record_outcome()` skips mutation engine due to missing `test_id`; `run_maintenance()` does not call trace maintenance |
| `ContextualSelector` (Thompson Sampling) | `borg/core/contextual_selector.py` | Complete | Never queries `FeedbackLoop.get_signals()` to weight samples; no `feedback_signal_boost()` method |
| `MutationEngine` (A/B testing) | `borg/core/mutation_engine.py` | Complete | `record_outcome(test_id, variant, success)` exists (L996) but never called by `BorgV3` because `test_id` is not passed |
| `FeedbackLoop` (signal aggregation) | `borg/core/feedback_loop.py` | Complete | `get_signals(pack_id)` exists; never called by `ContextualSelector` |
| `FailureMemory` (failure recall) | `borg/core/failure_memory.py` | Complete | `recall(error_message)` exists; never called by `BorgV3.search()` |
| `TraceCapture` (trace accumulation) | `borg/core/traces.py` | Complete | No decay/maintenance; `helpfulness_score` never decays; no 10k cap enforcement |
| `BorgV3.search()` | `borg/core/v3_integration.py` L212 | Partial | Receives `context_dict` (error_message, error_type, attempts) but does not forward `error_type` to V3 search path |
| `TraceCapture.agent_id` | `borg/core/traces.py` L106 | Broken | Always initialized to `""`; never populated from session context |
| `TraceCapture.root_cause` | `borg/core/traces.py` L140 | Partial | `extract_trace()` accepts `root_cause` param but callers never pass it |

### 2.2 Data Flow Map (Current — Intended But Broken)

```
observe (task arrives with context_dict)
    │
    ▼
borg_observe()
    │  — receives error_message, error_type, attempts
    │  — builds guidance from packs
    │  — FAILS: never calls FailureMemory.recall(context)  [Gap 3.2]
    │  — FAILS: context_dict.error_type not forwarded to v3.search()  [Gap 3.3]
    ▼
BorgV3.search(task_context={error_type, ...})
    │  — calls ContextualSelector.select()
    │  — Thompson samples from Beta posteriors
    │  — FAILS: posteriors not modulated by FeedbackLoop signals  [Gap 3.4]
    ▼
Pack selected + A/B variant assigned
    │  — Variant assignment stored? NO — never persisted to session  [Gap 3.1]
    ▼
Agent executes with pack guidance
    │
    ▼
capture (TraceCapture.on_tool_call())
    │  — Global _trace_capture dict? Actually a single global instance  [Gap 3.6]
    │  — FAILS: concurrent sessions overwrite each other
    ▼
feedback (BorgV3.record_outcome(pack_id, success))
    │  — Feeds ContextualSelector ✓
    │  — Feeds FeedbackLoop ✓
    │  — FAILS: mutation_engine.record_outcome(test_id, variant, success) never called  [Gap 3.1]
    │  — Because: session.selected_variant not set at selection time
    ▼
MutationEngine.check_ab_tests() called? NO — run_maintenance() doesn't call it  [Gap 3.1]
    │
    ▼
run_maintenance()
    │  — Checks A/B tests ✓
    │  — Checks drift ✓
    │  — Suggests mutations ✓
    │  — FAILS: no traces_maintenance() call  [Gap 3.5]
    ▼
MutationEngine → variant winner → promote or revert
```

### 2.3 Gap Analysis

| Gap | Severity | Root Cause | Impact |
|-----|----------|------------|--------|
| A/B outcome recording never fires | P0 — Critical | `BorgV3.record_outcome()` cannot pass `test_id` to `MutationEngine.record_outcome(test_id, variant, success)` because `selected_variant` is never stored in session at selection time | A/B tests never resolve; mutation engine cannot close the loop |
| Thompson Sampling ignores feedback signals | P1 — High | `ContextualSelector.select()` never calls `FeedbackLoop.get_signals(pack_id)`; no `feedback_signal_boost()` method | Selector uses pure historical success rates; cannot exploit real-time quality signals |
| `FailureMemory.recall()` never called | P1 — High | `borg_observe()` / `BorgV3.search()` never calls `FailureMemory.recall(error_message)` | Prior failure context (wrong approaches, correct approaches) never injected into guidance |
| `context_dict` not forwarded to V3 search | P1 — High | `BorgV3.search()` receives `task_context` but `error_type` from `context_dict` is not included in the `task_context` passed to `ContextualSelector.select()` | Task classification degrades; wrong category posteriors updated |
| Trace helpfulness never decays | P1 — High | `run_maintenance()` in `BorgV3` has no `traces_maintenance()` call; `helpfulness_score` is permanent | Unhelpful traces persist forever; search quality degrades over time |
| Global `_trace_capture` not thread-safe | P1 — High | `TraceCapture` is a single global instance in MCP server; no `session_id` keying | Concurrent MCP sessions overwrite each other's trace state |
| Root cause never captured | P2 — Medium | `extract_trace(root_cause=...)` param exists but callers never pass it; `root_cause` field exists in DB schema but is always empty | Traces show dead ends but not what fixed the problem; learning value is halved |
| `agent_id` always empty string | P2 — Medium | `TraceCapture.__init__(agent_id="")` hardcoded; MCP server never passes `agent_id` from session context | Cannot track per-agent contribution; reputation system cannot function |

---

## 3. Proposed Improvements

---

### 3.1 A/B Outcome Recording — Architectural Fix

**Problem:** `MutationEngine.record_outcome(test_id, variant, success)` (defined at `mutation_engine.py:996`) is never called because `BorgV3.record_outcome()` has no `test_id` to pass. The `selected_variant` (which A/B arm was chosen) is not stored at selection time, so at feedback time the system cannot attribute the outcome to the correct variant. This means A/B tests never resolve — the mutation engine cannot determine winners, and pack evolution stalls.

**Approach:** Store `test_id + variant` in the MCP session when `BorgV3.select()` returns an A/B variant. At feedback time, look up `selected_variant` from session and call `mutation_engine.record_outcome()` correctly.

Specifically:

1. **Add `selected_variant` field to session** (schema at `session.py:75`):
   ```python
   "selected_variant": {           # new field
       "test_id": str,             # A/B test UUID
       "variant": "original"|"mutant",
       "pack_id": str,             # the pack_id that was actually selected
       "timestamp": str             # ISO-8601
   }
   ```

2. **In `BorgV3.select()`** (`v3_integration.py:254`), when the result includes an A/B variant (detected by checking if `result.pack_id` is a mutant pack from an active A/B test), record the `test_id + variant` in the session via a new `set_selected_variant(session_id, test_id, variant, pack_id)` call.

3. **In `BorgV3.record_outcome()`** (`v3_integration.py:324`), look up `selected_variant` from session and call:
   ```python
   self._mutation.record_outcome(test_id, variant, success)
   ```

4. **Fallback:** If no `selected_variant` in session, fall back to current behavior (record to selector + feedback loop only, skip mutation engine).

**Verification:** Write integration test `test_ab_outcome_recording_flow`:
```
1. Create A/B test via MutationEngine.apply_mutation()
2. Call BorgV3.select() for a task → verify selected_variant written to session
3. Call BorgV3.record_outcome() with the session's selected_variant
4. Call mutation_engine.check_ab_tests()
5. Verify winner is computed (not "insufficient_data") after n=20+ samples per arm
```

**Success Criteria:**
- After 25 original + 25 mutant samples, `check_ab_tests()` returns winner ≠ "insufficient_data" with p < 0.05
- Measurable: Unit test `test_ab_outcome_recording_integration` passes

---

### 3.2 `failure_memory.recall()` in `borg_observe`

**Problem:** `borg_observe` never calls `FailureMemory.recall(context)` to get prior failure context. The `FailureMemory` module (`failure_memory.py:153`) has a fully implemented `recall(error_message)` method that returns `wrong_approaches`, `correct_approaches`, and `total_sessions` — but this intelligence is never used. Agents repeat the same failed approaches because the system knows what doesn't work but never shares that knowledge.

**Approach:** In `BorgV3.search()` (the `borg_observe` equivalent in the V3 path), after building guidance from packs, call `failure_memory.recall(error_pattern)` and include the prior failures and successes in the returned guidance structure.

Specifically, modify `BorgV3.search()` at `v3_integration.py:212`:
```python
# After building guidance from packs (existing code around L233-L275)
# Add:
if task_context and task_context.get("error_message"):
    prior = self._failure_memory.recall(task_context["error_message"])
    if prior:
        guidance["prior_failures"] = prior.get("wrong_approaches", [])
        guidance["prior_successes"] = prior.get("correct_approaches", [])
```

Note: `BorgV3.__init__()` already instantiates `FailureMemory` at `v3_integration.py:178` as `self._fm`. The instance is created but `recall()` is never called.

**Verification:** Test `test_failure_memory_recall_in_search`:
```
1. Pre-populate failure memory with an error pattern + wrong approach
2. Call BorgV3.search() with that error pattern in task_context
3. Verify the returned guidance includes prior_failures
```

**Success Criteria:**
- `BorgV3.search()` returns `prior_failures` list when `FailureMemory` has a matching error pattern
- `prior_failures` is empty list when no match exists (no regression)

---

### 3.3 `context_dict` Forwarding to V3 Search

**Problem:** `borg_observe` receives a `context_dict` containing `error_message`, `error_type`, and `attempts` (from the MCP tool call), but `BorgV3.search()` does not forward these to the V3 search path. Specifically, `error_type` is critical for task classification (`contextual_selector.py:126-135`) — without it, the classifier relies on weaker signals and often misclassifies tasks. The `context_dict` is passed as `task_context` to `search()` but only `task_type`, `language`, `keywords`, and `file_path` are forwarded to `classify_task()` (`v3_integration.py:243-249`).

**Approach:** In `BorgV3.search()` at `v3_integration.py:241-249`, add `error_type` and `attempts` to the `task_context` passed to `classify_task()`:

```python
category = classify_task(
    task_type=task_context.get("task_type"),
    error_type=task_context.get("error_type"),   # ADD THIS LINE
    language=task_context.get("language"),
    keywords=task_context.get("keywords"),
    file_path=task_context.get("file_path"),
    # ADD: attempts=task_context.get("attempts"),  # for future classification models
)
```

This requires that the caller of `BorgV3.search()` — the MCP server handler — actually passes `error_type` from `context_dict` into `task_context`. The `context_dict` should be unpacked into `task_context` at the MCP tool handler level.

**Verification:** Test `test_context_dict_error_type_forwarding`:
```
1. Call BorgV3.search() with task_context containing error_type="NullPointerException"
2. Verify that the internal classify_task call receives error_type="NullPointerException"
3. Verify the classified category is "debug"
```

**Success Criteria:**
- `classify_task(error_type="NullPointerException")` returns `"debug"`
- End-to-end: `BorgV3.search()` with `task_context={"error_type": "IndexError"}` classifies as `"debug"`

---

### 3.4 Thompson Sampling + Feedback Signal Integration

**Problem:** Thompson Sampling posteriors (`ContextualSelector.select()` at `contextual_selector.py:491`) are never influenced by `FeedbackLoop` signals. The selector samples purely from historical Beta posterior distributions. Meanwhile, `FeedbackLoop.get_signals(pack_id)` returns signal data including `quality_score` and `success_rate_trend` — but this information is never used to modulate sampling probabilities. A pack with rapidly degrading quality (negative drift) is sampled at the same rate as a pack with improving quality.

**Approach:** In `ContextualSelector`, add a `feedback_signal_boost(pack_id) → float` method that queries `FeedbackLoop.get_signals(pack_id)` and computes a multiplicative boost factor. Multiply Thompson samples by this boost factor during selection.

Specifically, in `ContextualSelector.select()` (`contextual_selector.py:536-569`):
```python
# After computing sampled value (around L559):
# Get feedback signal boost
boost = self.feedback_signal_boost(pack.pack_id)  # new method
sampled *= boost

# The boost formula:
# If FeedbackLoop reports negative drift (quality declining): boost < 1.0
# If positive drift: boost > 1.0
# Neutral: boost = 1.0
```

New method in `ContextualSelector`:
```python
def feedback_signal_boost(self, pack_id: str) -> float:
    """Compute multiplicative boost from FeedbackLoop signals.
    
    Returns float in [0.0, 2.0]. Values < 1.0 reduce sampling probability
    (negative drift); values > 1.0 increase it (positive drift).
    """
    if not hasattr(self, "_feedback_loop") or self._feedback_loop is None:
        return 1.0  # neutral
    
    signals = self._feedback_loop.get_signals(pack_id)
    if not signals:
        return 1.0  # neutral
    
    # Compute boost from signal quality and trend
    # quality_score ∈ [0, 1], success_rate_trend ∈ [-1, 1]
    quality = sum(s.quality_score for s in signals) / len(signals)
    trend = sum(s.success_rate_trend for s in signals) / len(signals)
    
    # Boost = quality * (1 + trend/2), clamped to [0.0, 2.0]
    boost = quality * (1.0 + trend / 2.0)
    return max(0.0, min(2.0, boost))
```

The `ContextualSelector` is initialized with a reference to `FeedbackLoop`:
```python
def __init__(self, ..., feedback_loop=None):
    ...
    self._feedback_loop = feedback_loop  # injected, not hard-coded
```

**Verification:** Test `test_thompson_sampling_feedback_boost`:
```
1. Create ContextualSelector with a mock FeedbackLoop
2. Mock FeedbackLoop.get_signals() returns [Signal(quality=0.3, trend=-0.5)] (negative drift)
3. Mock FeedbackLoop.get_signals() for another pack returns [Signal(quality=0.9, trend=0.5)] (positive drift)
4. Run 1000 Thompson samples for each pack
5. Verify the negative-drift pack is sampled significantly less frequently (boost < 1.0)
```

**Success Criteria:**
- Pack with `quality=0.3, trend=-0.5` has boost ≈ `0.3 * (1 - 0.25)` = 0.225 (sampled ~4.4x less)
- Pack with `quality=0.9, trend=0.5` has boost ≈ `0.9 * (1 + 0.25)` = 1.125 (sampled ~1.1x more)
- The sampling ratio between the two packs reflects the boost ratio

---

### 3.5 Trace Helpfulness Decay

**Problem:** Traces persist forever in `traces.db` (`traces.py:23`). The `helpfulness_score` field (default 0.5) and `times_shown` counter are never used for decay or cleanup. Unhelpful traces shown 5+ times with low helpfulness scores continue to be returned by search, cluttering results and reducing effective recall.

**Approach:** Add a `traces_maintenance()` function in `traces.py` and call it from `BorgV3.run_maintenance()` (`v3_integration.py:571`).

In `traces.py`, add:
```python
def traces_maintenance(db_path: str = None, decay_factor: float = 0.95,
                       decay_days: int = 30,
                       max_traces: int = 10000) -> Dict[str, int]:
    """
    Run trace maintenance: decay scores, delete low-value traces, enforce cap.
    
    Returns: {"decayed": n, "deleted": m, "total": t}
    """
    db = _get_db(db_path)
    now = time.time()
    cutoff = now - (decay_days * 86400)
    
    decayed = 0
    deleted = 0
    
    # 1. Decay helpfulness_score by decay_factor for traces not shown in decay_days
    cur = db.execute("""
        UPDATE traces 
        SET helpfulness_score = helpfulness_score * ?
        WHERE times_shown = 0 
          AND created_at < datetime('now', '-' || ? || ' days')
          AND helpfulness_score > 0
    """, (decay_factor, decay_days))
    decayed = cur.rowcount
    
    # 2. Delete traces with times_shown > 5 AND helpfulness_score < 0.1
    cur = db.execute("""
        DELETE FROM traces 
        WHERE times_shown > 5 AND helpfulness_score < 0.1
    """)
    deleted = cur.rowcount
    
    # 3. Enforce 10,000 trace cap (FIFO — delete oldest by created_at)
    cur = db.execute("SELECT COUNT(*) FROM traces")
    total = cur.fetchone()[0]
    if total > max_traces:
        excess = total - max_traces
        db.execute(f"""
            DELETE FROM traces WHERE id IN (
                SELECT id FROM traces ORDER BY created_at ASC LIMIT ?
            )
        """, (excess,))
    
    db.commit()
    db.close()
    
    return {"decayed": decayed, "deleted": deleted, "total": total}
```

In `BorgV3.run_maintenance()` at `v3_integration.py:571`, add:
```python
# 4. Trace maintenance
try:
    from borg.core.traces import traces_maintenance
    trace_stats = traces_maintenance()
    results["trace_maintenance"] = trace_stats
except Exception as e:
    logger.warning("Trace maintenance failed: %s", e)
```

**Verification:** Test `test_trace_helpfulness_decay`:
```
1. Insert 100 traces into traces.db
2. Mark 10 traces with times_shown=6, helpfulness_score=0.05 (should be deleted)
3. Mark 20 traces with times_shown=0, created_at=now-45 days (should decay)
4. Insert 9,990 more traces to hit 10,000 cap (oldest should be FIFO'd)
5. Call traces_maintenance()
6. Verify: 10 deleted, 20 decayed, oldest traces pruned to reach 10k
```

**Success Criteria:**
- Traces with `times_shown > 5 AND helpfulness_score < 0.1` are deleted
- Traces not shown in 30+ days have `helpfulness_score` multiplied by 0.95
- DB never exceeds 10,000 traces (oldest deleted when over cap)

---

### 3.6 Thread Safety for `_trace_capture`

**Problem:** The MCP server (`guild-mcp-package/src/guild_mcp/server.py`) uses a single global `TraceCapture` instance (`_trace_capture: TraceCapture`). When multiple concurrent MCP sessions exist (different agents or different tasks), each session's tool calls overwrite the same global instance, mixing traces. This makes per-session trace analysis impossible.

**Approach:** Replace the global `_trace_capture` with a `session_id`-keyed dict:

```python
# OLD (guild_mcp/server.py):
_trace_capture = TraceCapture()

# NEW:
_trace_captures: Dict[str, TraceCapture] = {}  # keyed by session_id
```

Update all trace capture functions to accept and use `session_id`:
```python
def init_trace_capture(session_id: str, task: str = "", agent_id: str = "") -> None:
    """Initialize a trace capture for a session."""
    _trace_captures[session_id] = TraceCapture(task=task, agent_id=agent_id)

def get_trace_capture(session_id: str) -> Optional[TraceCapture]:
    return _trace_captures.get(session_id)

def close_trace_capture(session_id: str) -> Optional[TraceCapture]:
    return _trace_captures.pop(session_id, None)
```

In the MCP server's JSON-RPC `initialize` handler, extract `session_id` from the request and call `init_trace_capture(session_id, ...)`. The MCP protocol's `initialize` request includes `session_id` as part of the request metadata.

**Verification:** Test `test_concurrent_trace_capture_isolation`:
```
1. Spawn 10 threads, each with a unique session_id
2. Each thread calls init_trace_capture(session_id, task=f"task-{i}")
3. Each thread accumulates different tool calls into its own TraceCapture
4. After accumulation, verify each session's TraceCapture has only its own calls
5. Verify cross-contamination: session_1's TraceCapture has 0 calls from session_2
```

**Success Criteria:**
- 10 concurrent sessions, each accumulating 100 tool calls, result in 10 isolated `TraceCapture` objects with exactly 100 calls each
- No cross-session contamination

---

### 3.7 Root Cause Extraction

**Problem:** `TraceCapture.extract_trace()` accepts a `root_cause` parameter (`traces.py:140`) and the `traces` table has a `root_cause TEXT` column (`traces.py:47`), but this field is always empty. `save_trace()` never receives a `root_cause` because the caller (`borg_feedback` in the MCP server) never extracts or passes it. Traces capture what files were read and what errors occurred (dead ends), but not what actually fixed the problem.

**Approach:** In `borg_feedback` (the MCP server's feedback handler), after extracting the trace, also extract `root_cause` from one of:
1. The agent's final message (look for patterns like "The fix was...", "Root cause:...", "I fixed it by...")
2. The feedback's `what_changed` field if provided

Pass the extracted `root_cause` to `save_trace()`:
```python
trace = capture.extract_trace(outcome="success", root_cause=extracted_root_cause, ...)
save_trace(trace)
```

**Verification:** Test `test_root_cause_save_and_retrieve`:
```
1. Create a TraceCapture, accumulate some activity
2. Call extract_trace() with root_cause="Missing null check in auth validator"
3. Call save_trace() and retrieve the saved trace
4. Verify root_cause field is persisted and returned correctly
5. Verify search by root_cause keyword works (FTS5 query)
```

**Success Criteria:**
- `save_trace()` with `root_cause="Null pointer dereference in getUser()"` persists it
- `get_trace(id)` returns `root_cause == "Null pointer dereference in getUser()"`
- FTS5 search over `root_cause` column returns the trace

---

### 3.8 `agent_id` Population

**Problem:** `TraceCapture.__init__(agent_id="")` (`traces.py:106`) is always initialized with an empty string. The MCP server's JSON-RPC `initialize` handler receives `client_info` containing `agent_id` (from the connecting agent's handshake), but this is never passed to `init_trace_capture()`. Without `agent_id`, the reputation system cannot track per-agent contribution rates, and per-agent statistics in the dashboard are meaningless.

**Approach:** In the MCP server's JSON-RPC `initialize` handler (or the session setup code), extract `agent_id` from the client's `initialize` request:

```python
# In guild_mcp/server.py — JSON-RPC initialize handler:
async def handle_initialize(self, request: dict) -> dict:
    client_info = request.get("client_info", {})
    agent_id = client_info.get("agent_id", "unknown")
    
    # Store agent_id in session context
    session_id = request.get("session_id", "default")
    init_trace_capture(session_id=session_id, task="", agent_id=agent_id)
```

Update `init_trace_capture()` to accept `agent_id`:
```python
def init_trace_capture(session_id: str, task: str = "", agent_id: str = "") -> None:
    _trace_captures[session_id] = TraceCapture(task=task, agent_id=agent_id)
```

**Verification:** Test `test_agent_id_persists_in_trace`:
```
1. Call init_trace_capture(session_id="s1", agent_id="agent-alice-001")
2. Accumulate some tool calls
3. Extract and save the trace
4. Retrieve from DB
5. Verify trace["agent_id"] == "agent-alice-001"
```

**Success Criteria:**
- `init_trace_capture(agent_id="agent-alice-001")` → saved trace has `agent_id="agent-alice-001"`
- `agent_id` appears correctly in `BorgV3.get_dashboard()` per-agent breakdown

---

## 4. Implementation Order

### Phase 1: Fix the A/B Loop Closure (Critical Path — Must Be First)
**Dependencies: None**

1. **Implement 3.1** — A/B Outcome Recording Fix
   - Add `selected_variant` to session schema
   - Modify `BorgV3.select()` to store variant in session
   - Modify `BorgV3.record_outcome()` to look up and pass `test_id + variant`
   - Write `test_ab_outcome_recording_flow`

### Phase 2: Close the Thompson Sampling Feedback Path
**Dependencies: Phase 1**

2. **Implement 3.4** — Thompson Sampling + Feedback Signal Integration
   - Add `feedback_signal_boost()` to `ContextualSelector`
   - Inject `FeedbackLoop` reference into `ContextualSelector`
   - Write `test_thompson_sampling_feedback_boost`
   
3. **Implement 3.3** — `context_dict` Forwarding to V3 Search
   - Forward `error_type` from `context_dict` to `classify_task()`
   - Write `test_context_dict_error_type_forwarding`

### Phase 3: Failure Memory Wiring
**Dependencies: Phase 2 (uses same BorgV3.search() entry point)**

4. **Implement 3.2** — `failure_memory.recall()` in `borg_observe`
   - Call `FailureMemory.recall()` in `BorgV3.search()` after building guidance
   - Include `prior_failures` and `prior_successes` in guidance response
   - Write `test_failure_memory_recall_in_search`

### Phase 4: Trace Quality Maintenance
**Dependencies: Phase 1**

5. **Implement 3.5** — Trace Helpfulness Decay
   - Add `traces_maintenance()` to `traces.py`
   - Call from `BorgV3.run_maintenance()`
   - Write `test_trace_helpfulness_decay`

6. **Implement 3.7** — Root Cause Extraction
   - Extract `root_cause` in `borg_feedback` from final agent message / `what_changed`
   - Pass to `extract_trace(root_cause=...)`
   - Write `test_root_cause_save_and_retrieve`

### Phase 5: MCP Server Hardening
**Dependencies: Phase 4 (uses same trace capture infrastructure)**

7. **Implement 3.6** — Thread Safety for `_trace_capture`
   - Replace global `_trace_capture` with `_trace_captures: Dict[str, TraceCapture]`
   - Add `session_id` parameter to all trace functions
   - Write `test_concurrent_trace_capture_isolation`

8. **Implement 3.8** — `agent_id` Population
   - Extract `agent_id` from MCP `initialize` request `client_info`
   - Pass to `init_trace_capture(agent_id=...)`
   - Write `test_agent_id_persists_in_trace`

### Phase 6: Integration and Validation
**Dependencies: All above**

9. Write `test_e2e_learning_loop_integration` — full end-to-end test from observe → capture → feedback → mutation → trace maintenance

---

## 5. Success Criteria — Formal Verification

| Improvement | Metric | Target | Measurement Method |
|-------------|--------|--------|---------------------|
| 3.1 A/B Outcome Recording | `MutationEngine.record_outcome()` called with correct `test_id` and `variant` | 100% of pack executions with active A/B test call `record_outcome(test_id, variant, success)` | Integration test: 25+ outcomes per arm → `check_ab_tests()` returns winner (not `insufficient_data`) |
| 3.1 A/B Outcome Recording | A/B test resolution rate | ≥ 90% of A/B tests reach significance within 100 outcomes | `test_ab_outcome_recording_flow` with mocked outcomes |
| 3.2 Failure Memory Recall | `prior_failures` returned when matching error exists | 100% of `BorgV3.search()` calls with matching error return `prior_failures` | Unit test: pre-populate FM → search → assert `prior_failures` is non-empty |
| 3.3 Context Dict Forwarding | `error_type` included in `classify_task()` call | 100% of `BorgV3.search()` calls forward `error_type` from `task_context` | Mock/spy test verifying `classify_task` receives `error_type` argument |
| 3.4 Thompson + Feedback | Sampling ratio between negative-drift and positive-drift pack | Negative-drift pack sampled ≤ 0.5x frequency of positive-drift pack | 1000-sample Monte Carlo test measuring actual sampling frequency |
| 3.5 Trace Decay | `helpfulness_score` decay factor applied correctly | All traces not shown in 30+ days have score × 0.95 | Direct DB query after `traces_maintenance()` |
| 3.5 Trace Decay | Overflow traces deleted (FIFO) | DB count ≤ 10,000 after maintenance with 10,500 pre-existing | Direct row count in `traces` table |
| 3.5 Trace Decay | Low-quality traces deleted | 100% of traces with `times_shown > 5 AND helpfulness_score < 0.1` are deleted | Direct DB query |
| 3.6 Thread Safety | Session isolation (cross-contamination) | 0 calls from session A found in session B's `TraceCapture` | Concurrent thread test with 10 sessions × 100 calls |
| 3.7 Root Cause | `root_cause` field populated | `root_cause` is non-empty string in ≥ 80% of "success" traces | DB query on `traces` table after E2E run |
| 3.8 Agent ID | `agent_id` field in traces | 100% of traces from known agents have non-empty `agent_id` | DB query: `SELECT COUNT(*) WHERE agent_id != ''` / `SELECT COUNT(*)` |

---

## 6. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| A/B test variant stored in memory session but session is lost on crash | Medium | A/B test outcomes silently lost; test never resolves | Persist `selected_variant` to disk (session JSON file); on restart, replay active sessions |
| `feedback_signal_boost()` creates a feedback loop that amplifies noise | Low | Pack sampling becomes unstable if feedback signals are noisy | Clamp boost to `[0.2, 2.0]`; require minimum 3 signals before applying boost; use exponential moving average for trend |
| Decay/maintenance running during active trace capture corrupts state | Low | In-flight traces may have `helpfulness_score` updated mid-capture | Use DB transactions; decay queries filter by `times_shown = 0` to exclude active traces |
| `session_id` keying breaks existing code that relies on global `_trace_capture` | High | Existing callers of `on_tool_call()` without `session_id` cause KeyError | Add `_trace_captures.get("default", None)` fallback; deprecation warning; update all callers in same PR |
| `agent_id` not available in all MCP session types | Medium | Some traces have `agent_id=""` | Fall back to `client_info.host` or `client_info.name` from initialize handshake; log warning when agent_id missing |
| `FailureMemory.recall()` is slow on cold start (scans all YAML files) | Low | `BorgV3.search()` latency increases | Cache recall results in-memory with TTL; only scan pack dirs matching the current task's pack set |
| Introducing `test_id` into `BorgV3.record_outcome()` breaks existing callers | Medium | Existing code calling `record_outcome(pack_id, task_context, success)` may break | Maintain backwards-compatible signature; add `test_id` as optional keyword arg with default `None` |
| Trace cap of 10,000 causes FIFO to delete high-value traces under FIFO ordering | Low | Oldest traces are not necessarily least valuable | Add LRU eviction option: track last_accessed timestamp; evict by `last_accessed` ASC instead of `created_at` ASC |

---

## Appendix A: File Locations Reference

| Component | File | Key Lines |
|-----------|------|-----------|
| `BorgV3` integration | `borg/core/v3_integration.py` | 157–661 |
| `ContextualSelector` | `borg/core/contextual_selector.py` | 383–613 |
| `MutationEngine` | `borg/core/mutation_engine.py` | 860–1100 |
| `FeedbackLoop` | `borg/core/feedback_loop.py` | 466–564 |
| `FailureMemory` | `borg/core/failure_memory.py` | 47–283 |
| `TraceCapture` | `borg/core/traces.py` | 103–182 |
| `save_trace()` | `borg/core/traces.py` | 184–241 |
| `Session` management | `borg/core/session.py` | 47–323 |
| `classify_task()` | `borg/core/contextual_selector.py` | 93–185 |

## Appendix B: Test Inventory

| Test Name | File | Improvement Tested |
|-----------|------|-------------------|
| `test_ab_outcome_recording_flow` | `tests/test_v3_integration.py` (new) | 3.1 |
| `test_failure_memory_recall_in_search` | `tests/test_v3_integration.py` (new) | 3.2 |
| `test_context_dict_error_type_forwarding` | `tests/test_v3_integration.py` (new) | 3.3 |
| `test_thompson_sampling_feedback_boost` | `tests/test_contextual_selector.py` (new) | 3.4 |
| `test_trace_helpfulness_decay` | `tests/test_traces.py` (new) | 3.5 |
| `test_concurrent_trace_capture_isolation` | `tests/test_traces.py` (new) | 3.6 |
| `test_root_cause_save_and_retrieve` | `tests/test_traces.py` (new) | 3.7 |
| `test_agent_id_persists_in_trace` | `tests/test_traces.py` (new) | 3.8 |
| `test_e2e_learning_loop_integration` | `tests/test_e2e.py` (new) | All |
