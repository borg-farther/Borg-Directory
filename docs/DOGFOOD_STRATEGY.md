# Dogfood Strategy for Agent-Borg

## Problem Statement

When Hermes (or any agent) is working on a task, borg should **proactively** suggest relevant packs — not just after explicit user request, and not just after consecutive failures. The current `agent_hook` integration is reactive-only (passive nudge after failures).

**Goal:** Make borg the equivalent of an "autocomplete for workflows" — always present in the background, surfacing relevant packs at the right moment without disrupting the agent's flow.

---

## 1. Proactive Prompt Nudge System

### What Exists Today

| Function | Location | Trigger | Blocking? |
|---|---|---|---|
| `borg_on_failure()` | `borg/integrations/agent_hook.py:33` | 2+ consecutive failures OR frustration signals | Sync — blocks agent loop |
| `borg_on_task_start()` | `agent_hook.py:92` | Task start only | Sync — blocks agent loop |
| `_maybe_inject_guild_suggestion()` | Hermes `run_agent.py:5352` | Called after tool execution when `_consecutive_tool_errors >= threshold` | Sync |
| `on_task_start` hook | Hermes plugin hook system | Not wired in `run_agent.py` | Async (fire-and-forget) |

### The Gap

`borg_on_task_start` fires **once** at task start and is called **synchronously**. After that, the agent can work for minutes/hours with no further nudges. The agent can struggle for many turns without borg surfacing anything.

### Proposed Nudge Architecture

```
Conversation Turn
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  NudgeEngine (background, non-blocking)                 │
│                                                         │
│  Per-turn signals collected:                            │
│    - User message keywords  (classify_task)            │
│    - Tool error patterns       (frustration signals)   │
│    - Conversation momentum    (# turns without progress)│
│    - Time elapsed since last suggestion                 │
│                                                         │
│  NudgeEngine.run(context) → nudge or None              │
│      │                                                  │
│      ▼                                                  │
│  If nudge → inject as system message "[Borg 💡 ...]"   │
└─────────────────────────────────────────────────────────┘
```

### Step 1 — Build the NudgeEngine

**File:** `borg/integrations/nudge_engine.py` (new)

```python
"""
NudgeEngine — non-blocking proactive suggestion engine.

Design principles:
  - Runs in a background thread; never blocks the main agent loop.
  - Aggregates signals across the conversation turn window.
  - Fires a nudge only when confidence exceeds a threshold, not on every turn.
  - Respects suppression: don't nudge the same pack twice in a row.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from borg.core.search import classify_task, borg_search, check_for_suggestion
from borg.integrations.agent_hook import borg_on_failure, borg_on_task_start
from borg.db.store import GuildStore

logger = logging.getLogger(__name__)

# Suppress a pack from nudges for this many seconds
_NUDGE_COOLDOWN_SECONDS = 120  # 2 minutes

# Minimum turns between nudges for the same search term
_MIN_TURNS_BETWEEN_NUDGES = 3


@dataclass
class NudgeSignal:
    """A single signal extracted from the conversation."""
    signal_type: str          # "keyword" | "frustration" | "error" | "progress"
    value: str                # e.g. the keyword or error text
    turn_index: int           # conversation turn number
    timestamp: str            # ISO8601


@dataclass
class NudgeDecision:
    """A nudge to be injected."""
    message: str              # formatted suggestion text
    pack_names: List[str]      # packs suggested (for suppression)
    confidence: float         # 0.0–1.0
    trigger_signals: List[str] # what triggered this
    turn_index: int


class NudgeEngine:
    """
    Background nudge engine.

    Usage:
        engine = NudgeEngine()
        engine.start()

        # After each agent turn:
        engine.submit_turn(turn_index=5, user_message="the build keeps failing",
                           agent_messages=["...error output..."], tool_errors=[])

        # Check for pending nudge (non-blocking):
        nudge = engine.poll_nudge()
        if nudge:
            inject_as_system_message(nudge.message)

        # On agent idle (every few seconds):
        idle_nudge = engine.poll_idle_nudge()
        if idle_nudge:
            inject_as_system_message(idle_nudge.message)

        engine.stop()
    """

    def __init__(
        self,
        cooldown_seconds: float = _NUDGE_COOLDOWN_SECONDS,
        min_turns_between: int = _MIN_TURNS_BETWEEN_NUDGES,
    ):
        self._cooldown = cooldown_seconds
        self._min_turns = min_turns_between

        # Conversation state
        self._turn_index = 0
        self._signals: List[NudgeSignal] = []
        self._last_nudge_turn = -999
        self._last_nudge_time = 0.0
        self._suppressed_packs: set = set()  # pack names to suppress

        # Background thread
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pending_nudge: Optional[NudgeDecision] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API — called from main agent loop (all non-blocking)
    # ------------------------------------------------------------------

    def start(self):
        """Start the background nudge thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("NudgeEngine started")

    def stop(self):
        """Stop the background thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("NudgeEngine stopped")

    def submit_turn(
        self,
        turn_index: int,
        user_message: str,
        agent_messages: List[str],
        tool_errors: List[str],
        tried_packs: Optional[List[str]] = None,
    ):
        """
        Submit signals from a conversation turn to the nudge engine.

        This method is non-blocking and returns immediately.
        The actual nudge computation happens in the background thread.

        Args:
            turn_index: Monotonic turn number in the conversation.
            user_message: The user's message this turn.
            agent_messages: List of agent response texts this turn.
            tool_errors: List of error strings from tool executions this turn.
            tried_packs: Pack names already tried (exclude from suggestions).
        """
        combined = " ".join([user_message] + agent_messages)
        with self._lock:
            self._turn_index = turn_index

            # Extract keyword signals
            keywords = classify_task(user_message)
            for kw in keywords:
                self._signals.append(NudgeSignal(
                    signal_type="keyword",
                    value=kw,
                    turn_index=turn_index,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))

            # Extract frustration signals from agent + user messages
            frustration_keywords = [
                "still failing", "tried everything", "not working",
                "keeps failing", "same error", "stuck", "can't figure",
                "nothing works", "give up", "going in circles",
            ]
            for frag in frustration_keywords:
                if frag.lower() in combined.lower():
                    self._signals.append(NudgeSignal(
                        signal_type="frustration",
                        value=frag,
                        turn_index=turn_index,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ))
                    break  # only one frustration signal per turn

            # Extract tool error signals
            for err in tool_errors:
                self._signals.append(NudgeSignal(
                    signal_type="error",
                    value=err[:200],  # truncate
                    turn_index=turn_index,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))

            # Track tried packs for suppression
            if tried_packs:
                self._suppressed_packs.update(tried_packs)

    def poll_nudge(self) -> Optional[NudgeDecision]:
        """
        Poll for a computed nudge. Non-blocking.

        Call this after submit_turn() to check if a nudge is ready.
        Returns a NudgeDecision or None.
        """
        with self._lock:
            nudge = self._pending_nudge
            self._pending_nudge = None
            return nudge

    def poll_idle_nudge(self) -> Optional[NudgeDecision]:
        """
        Poll for a nudge during agent idle time (no recent activity).

        This is called periodically (e.g., every 30s) to surface
        nudges when the agent appears to be making slow progress.
        """
        # Prune old signals
        with self._lock:
            cutoff = self._turn_index - 10
            self._signals = [s for s in self._signals if s.turn_index >= cutoff]
            return self._poll_unlocked()

    def suppress_pack(self, pack_name: str, seconds: Optional[float] = None):
        """Suppress a pack from nudges for the cooldown period."""
        with self._lock:
            self._suppressed_packs.add(pack_name)
            # Also set a time-based expiry checked in _run_loop
            expiry = time.time() + (seconds or self._cooldown)
            self._pack_suppress_until: dict[str, float][pack_name] = expiry

    # ------------------------------------------------------------------
    # Internal background loop
    # ------------------------------------------------------------------

    def _run_loop(self):
        """Background thread: waits for turns, computes nudges."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=1.0)  # wake every second

            if self._stop_event.is_set():
                break

            # Check for idle nudges (slow path)
            with self._lock:
                if self._signals and (self._turn_index - self._last_nudge_turn) >= self._min_turns:
                    nudge = self._compute_nudge_unlocked()
                    if nudge:
                        self._pending_nudge = nudge

    def _poll_unlocked(self) -> Optional[NudgeDecision]:
        """Internal poll — must be called with lock held."""
        if self._signals and (self._turn_index - self._last_nudge_turn) >= self._min_turns:
            return self._compute_nudge_unlocked()
        return None

    def _compute_nudge_unlocked(self) -> Optional[NudgeDecision]:
        """
        Compute a nudge from accumulated signals.

        Strategy:
          1. If any frustration signals → use borg_on_failure path (high confidence).
          2. If keyword signals exist → use borg_on_task_start path.
          3. If only tool errors → use borg_on_failure with error context.
          4. Otherwise → skip (not enough signal).
        """
        now = time.time()

        # Check pack suppressions (time-based expiry)
        if hasattr(self, "_pack_suppress_until"):
            expired = [p for p, t in self._pack_suppress_until.items() if now >= t]
            for p in expired:
                self._suppressed_packs.discard(p)
                del self._pack_suppress_until[p]

        # Categorize signals
        has_frustration = any(s.signal_type == "frustration" for s in self._signals)
        has_error = any(s.signal_type == "error" for s in self._signals)
        keywords = {s.value for s in self._signals if s.signal_type == "keyword"}

        # Build context string from recent signals
        recent_signals = [s for s in self._signals if s.turn_index >= self._turn_index - 5]
        context = " ".join([s.value for s in recent_signals])

        # Decide nudge strategy
        if has_frustration or (has_error and len(keywords) == 0):
            # High urgency — delegate to borg_on_failure
            result = borg_on_failure(
                context=context,
                failure_count=2,  # treat as worthy of failure path
                tried_packs=list(self._suppressed_packs),
            )
            if result:
                pack_names = self._extract_pack_names_from_suggestion(result)
                return NudgeDecision(
                    message=result,
                    pack_names=pack_names,
                    confidence=0.85 if has_frustration else 0.7,
                    trigger_signals=["frustration" if has_frustration else "tool_error"],
                    turn_index=self._turn_index,
                )

        elif keywords:
            # Keyword-based proactive nudge — use borg_on_task_start
            # Combine keywords into a search query
            combined_query = " ".join(sorted(keywords))
            result = borg_on_task_start(combined_query)
            if result:
                pack_names = self._extract_pack_names_from_suggestion(result)
                # Suppress these packs so we don't nudge again immediately
                for p in pack_names:
                    self._suppressed_packs.add(p)
                    if not hasattr(self, "_pack_suppress_until"):
                        self._pack_suppress_until = {}
                    self._pack_suppress_until[p] = now + self._cooldown
                return NudgeDecision(
                    message=result,
                    pack_names=pack_names,
                    confidence=0.6,  # proactive nudges are lower confidence
                    trigger_signals=list(keywords),
                    turn_index=self._turn_index,
                )

        return None

    def _extract_pack_names_from_suggestion(self, text: str) -> List[str]:
        """Extract pack names from a formatted suggestion string."""
        import re
        # Pattern: "pack-name [tested] (Description)" or "guild://hermes/pack-name"
        names = []
        # guild://hermes/pack-name URIs
        names.extend(re.findall(r"guild://hermes/([a-zA-Z0-9_-]+)", text))
        # Pack names before parentheses or brackets
        names.extend(re.findall(r"\b([a-z][a-z0-9-]{2,30})\s*\(", text))
        return list(set(names))
```

### Step 2 — Integrate NudgeEngine into Hermes Plugin

**File:** `hermes-plugin/__init__.py` — extend `register()`

```python
# In register(), after existing patch/tool registration:

# Step 4: Start the NudgeEngine (background, non-blocking)
try:
    from borg.integrations.nudge_engine import NudgeEngine
    _nudge_engine = NudgeEngine()
    _nudge_engine.start()

    # Patch run_agent.py's turn loop to call submit_turn
    # (We do this by registering a turn-level hook if available,
    #  or by patching the specific method.)
    def _make_turn_submitter(turn_index_ref):
        def submit_turn(
            user_message: str,
            agent_messages: List[str],
            tool_errors: List[str],
            tried_packs: Optional[List[str]] = None,
        ):
            _nudge_engine.submit_turn(
                turn_index=turn_index_ref[0],
                user_message=user_message,
                agent_messages=agent_messages,
                tool_errors=tool_errors,
                tried_packs=tried_packs,
            )
            turn_index_ref[0] += 1
        return submit_turn

    # Expose the submit function via a module-level callable
    import sys
    sys.modules["borg_nudge_submitter"] = type(sys)("borg_nudge_submitter")
    turn_ref = [0]  # mutable ref to track turn index
    sys.modules["borg_nudge_submitter"].submit = _make_turn_submitter(turn_ref)
    sys.modules["borg_nudge_submitter"].poll = _nudge_engine.poll_nudge

    logger.info("NudgeEngine started and registered as borg_nudge_submitter")
except Exception as exc:
    logger.warning("Could not start NudgeEngine: %s", exc)
```

### Step 3 — Wire NudgeEngine into Hermes `run_agent.py`

**Add to `run_agent.py`** (no changes to existing autosuggest logic — additive only):

```python
# Near the top of run_agent.py or in the __init__ of the agent class:
try:
    from borg_nudge_submitter import submit as borg_submit_turn, poll as borg_poll_nudge
    _BORG_NUDGE_AVAILABLE = True
except ImportError:
    _BORG_NUDGE_AVAILABLE = False

# In run_conversation (or the turn loop), after each turn completes:
if _BORG_NUDGE_AVAILABLE:
    borg_submit_turn(
        user_message=user_message,
        agent_messages=[last_agent_response],
        tool_errors=_get_recent_tool_errors(),  # extract from last turn
        tried_packs=self._tried_packs,         # track what was tried
    )

    # Also check for nudges right after submitting (non-blocking)
    nudge = borg_poll_nudge()
    if nudge:
        self._inject_borg_nudge(nudge)  # inject as system message

# New method on the agent class:
def _inject_borg_nudge(self, nudge):
    """Inject a proactive Borg nudge as a system message."""
    msg = f"\n[Borg 💡] {nudge.message}\n"
    self._messages.append({
        "role": "system",
        "content": msg,
        # Prevent this from being shown to the operator again
        "_borg_nudge": True,
        "_nudge_turn": self._turn_count,
    })
```

---

## 2. Async Patterns for Pack Observation/Publish

### What Exists vs. What Needs Building

The current `borg_on_failure` and `borg_on_task_start` are **synchronous**. Each call:
1. Calls `classify_task()` (fast regex, ~0ms)
2. Calls `borg_search()` which fetches the index and does text matching (~10–100ms network)
3. Formats the result

For proactive nudging (Step 1), we need this to be **non-blocking**. The `NudgeEngine` above handles this via a background thread. But we also need async patterns for two other operations:

1. **Pack usage observation** — tracking when a pack is pulled/started/completed without blocking the agent
2. **Pack result publishing** — sending feedback/results back to the guild without blocking

### Pattern A: Background Observation Thread

```
Agent calls borg_pull / borg_apply
      │
      │ immediate response returned to agent
      ▼
Observation event queued (non-blocking)
      │
      ▼
Background Observer thread processes queue:
  - Logs to GuildStore (SQLite) for analytics
  - Updates reputation scores (async, non-blocking)
  - Pre-fetches related pack metadata (opportunistic)
```

**Implementation:** `borg/integrations/observer.py` (new)

```python
"""
Observer — async pack usage observation without blocking the agent.

The agent calls borg_pull() / borg_apply() and gets an immediate response.
Simultaneously, an observation event is queued for the background thread
which updates the store, reputation, and pre-fetches related packs.
"""

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Literal

logger = logging.getLogger(__name__)

# Queue of pending observation events
_OBSERVATION_QUEUE: queue.Queue = queue.Queue()

# Max events to process per batch
_BATCH_SIZE = 10
_SHUTDOWN_TIMEOUT = 5.0


@dataclass
class ObservationEvent:
    """A pack usage event to be recorded asynchronously."""
    event_type: Literal["pull", "try", "apply_start", "apply_complete", "apply_fail", "feedback"]
    pack_id: str
    pack_name: str
    timestamp: str
    agent_id: Optional[str] = None
    task_context: Optional[str] = None  # first 200 chars of task
    outcome: Optional[str] = None        # "success", "failure", None
    phases_completed: Optional[int] = None
    execution_time_seconds: Optional[float] = None


def observe(event: ObservationEvent):
    """
    Queue a pack usage event for async processing.

    This function returns immediately (non-blocking).
    The actual store update happens in the background thread.
    """
    try:
        _OBSERVATION_QUEUE.put_nowait(event)
    except queue.Full:
        logger.warning("Observation queue full (%d events dropped)", _OBSERVATION_QUEUE.qsize())


def start_observer():
    """Start the background observer thread."""
    t = threading.Thread(target=_observer_loop, daemon=True, name="borg-observer")
    t.start()
    logger.info("Observer thread started")


def stop_observer():
    """Signal the observer thread to shut down."""
    _OBSERVATION_QUEUE.put(None)  # sentinel
    logger.info("Observer thread stopping")


def _observer_loop():
    """Background loop: process observation events in batches."""
    while True:
        events = []
        try:
            # Block for up to 5 seconds waiting for events
            event = _OBSERVATION_QUEUE.get(timeout=5.0)
            if event is None:  # shutdown sentinel
                break
            events.append(event)

            # Drain up to BATCH_SIZE more events
            while len(events) < _BATCH_SIZE:
                try:
                    e = _OBSERVATION_QUEUE.get_nowait()
                    if e is None:
                        break
                    events.append(e)
                except queue.Empty:
                    break
        except queue.Empty:
            continue

        _process_batch(events)


def _process_batch(events):
    """Process a batch of observation events."""
    try:
        from borg.db.store import GuildStore
        from borg.db.analytics import GuildAnalytics
    except ImportError:
        logger.debug("borg.db not available — observation events skipped")
        return

    try:
        store = GuildStore()
        analytics = GuildAnalytics(store)

        for event in events:
            try:
                if event.event_type == "pull":
                    store.record_pack_pull(event.pack_id, event.timestamp)
                elif event.event_type == "apply_complete":
                    store.record_pack_execution(
                        pack_id=event.pack_id,
                        outcome=event.outcome or "unknown",
                        phases_completed=event.phases_completed,
                        execution_time=event.execution_time_seconds,
                    )
                    # Update analytics
                    analytics.record_outcome(event.pack_id, event.outcome)
                elif event.event_type == "feedback":
                    # Store feedback for the reputation engine
                    store.store_feedback(
                        pack_id=event.pack_id,
                        feedback_data=event.task_context or "",
                        outcome=event.outcome,
                    )
                    # Reputation update is async — doesn't block
                    _async_update_reputation(event.pack_id)

            except Exception as exc:
                logger.debug("Failed to process observation event: %s", exc)

        store.close()
    except Exception as exc:
        logger.warning("Observer batch processing failed: %s", exc)


def _async_update_reputation(pack_id: str):
    """Update reputation scores asynchronously (fire-and-forget)."""
    def _update():
        try:
            from borg.db.reputation import ReputationEngine
            store = GuildStore()
            rep = ReputationEngine(store)
            rep.update_pack_reputation(pack_id)
            store.close()
        except Exception:
            pass  # Reputation is best-effort

    t = threading.Thread(target=_update, daemon=True)
    t.start()
```

**Wiring into MCP server** (`borg/integrations/mcp_server.py`):

In each tool handler (`borg_pull_handler`, `borg_apply_handler`), add:

```python
# After the main operation succeeds:
from borg.integrations.observer import observe, ObservationEvent
observe(ObservationEvent(
    event_type="pull" if "pull" in tool_name else "apply_complete",
    pack_id=result.get("id", result.get("pack_id", "")),
    pack_name=result.get("name", ""),
    timestamp=datetime.now(timezone.utc).isoformat(),
    outcome=result.get("verdict") or "success",
))
```

### Pattern B: Non-blocking Feedback Publish

Currently `borg_publish` (via `publish.py`) makes synchronous GitHub API calls. For async publish:

```python
def borg_feedback_async(
    pack_id: str,
    execution_log_hash: str,
    feedback_data: dict,
) -> str:
    """
    Queue feedback for async publishing to GitHub.

    Returns immediately with a ticket ID.
    The actual GitHub publish happens in the background.
    """
    import queue, threading, uuid, json

    ticket_id = str(uuid.uuid4())[:8]

    def _publish():
        try:
            # Call the existing synchronous publish logic
            from borg.core.publish import create_github_pr
            # ... build PR content from feedback_data ...
            create_github_pr(...)
            # Update ticket status in store
            store.update_feedback_ticket(ticket_id, status="published")
        except Exception as exc:
            store.update_feedback_ticket(ticket_id, status="failed", error=str(exc))

    threading.Thread(target=_publish, daemon=True).start()

    return json.dumps({
        "success": True,
        "ticket_id": ticket_id,
        "status": "queued",
        "message": f"Feedback queued for async publish (ticket: {ticket_id})",
    })
```

---

## 3. Feedback Loops — Pack Usage Improves Future Recommendations

### What Exists

- `GuildStore.record_pack_execution()` — logs outcomes to SQLite
- `GuildAnalytics.record_outcome()` — computes adoption metrics
- `ReputationEngine` — exists but is **never called** (GAP_ANALYSIS.md finding)
- `check_confidence_decay()` — computed but advisory only

### What Needs Building

The feedback loop has three components that need to be wired together:

```
Pack Used
    │
    ├──► Observer records outcome  (done in Step 2, Pattern A)
    │         │
    │         ▼
    │    GuildStore updated
    │         │
    │         ├──► ReputationEngine recomputes score (async, fire-and-forget)
    │         │         │
    │         │         ▼
    │         │    Reputation affects search ranking and suggestion confidence
    │         │
    │         └──► Analytics aggregates patterns
    │                   │
    │                   ▼
    │              What patterns of task → pack success exist?
    │                   │
    │                   ▼
    │              Adjusted relevance scores returned by suggest/search
    │
    └──► Pack outcome (success/failure) fed back to NudgeEngine
              │
              ▼
         Future nudge confidence adjusted for this pack
```

### Step 4 — Wire Reputation into Suggestion Ranking

**File:** `borg/core/search.py` — modify `check_for_suggestion()`

```python
# In check_for_suggestion(), after getting unique_matches but before returning:

# Boost packs that have good reputation (async lookup, non-blocking cache)
try:
    from borg.db.store import GuildStore
    from borg.db.reputation import ReputationEngine

    store = GuildStore()
    rep = ReputationEngine(store)

    # Get reputation scores for top matches (batched, non-blocking)
    for pack in unique_matches:
        pack_id = pack.get("id", "") or pack.get("name", "")
        try:
            score = rep.get_pack_reputation(pack_id)
            # Boost confidence if reputation is high
            if score and score.get("tier") in ("trusted", "core"):
                pack["_reputation_boost"] = 0.1  # subtle boost
        except Exception:
            pass

    store.close()
except Exception:
    pass  # Reputation lookup is best-effort — never block suggestions

# Re-sort matches with reputation boost applied
unique_matches.sort(
    key=lambda p: (
        p.get("confidence") in ("tested", "validated"),  # tested first
        p.get("_reputation_boost", 0.0),                   # then reputation
        p.get("match_count", 0),                           # then popularity
    ),
    reverse=True,
)
```

### Step 5 — Outcome-Aware Nudge Confidence

**File:** `borg/integrations/nudge_engine.py` — extend `_compute_nudge_unlocked()`

```python
def _get_pack_outcome_history(self, pack_name: str) -> dict:
    """Query GuildStore for this pack's recent outcome history."""
    try:
        from borg.db.store import GuildStore
        from borg.db.analytics import GuildAnalytics
        store = GuildStore()
        stats = store.get_pack_usage_stats(pack_name)
        store.close()
        return stats or {}
    except Exception:
        return {}

# In _compute_nudge_unlocked(), after getting result from borg_on_task_start:
if result:
    # Check outcome history for suggested pack
    for pack_name in pack_names:
        history = self._get_pack_outcome_history(pack_name)
        completion_rate = history.get("completion_rate", 0.5)
        apply_count = history.get("apply_count", 0)

        # If pack has poor outcomes, downgrade confidence
        if apply_count >= 3 and completion_rate < 0.3:
            confidence *= 0.5  # reduce nudge confidence
            result = result.replace(
                f"guild://hermes/{pack_name}",
                f"[low-success] guild://hermes/{pack_name}",
            )
```

### Step 6 — Feedback Signal from Pack Execution Back to NudgeEngine

**File:** `hermes-plugin/__init__.py` — extend the turn submit to include outcome

```python
# When a pack is applied and completes, call:
_nudge_engine.record_pack_outcome(
    pack_name="systematic-debugging",
    outcome="success",  # or "failure"
    turn_index=self._turn_index,
)
```

Then in `NudgeEngine`, track per-pack success rates and adjust future nudge confidence:

```python
# In NudgeEngine, add:
self._pack_outcomes: dict[str, list] = {}  # pack_name -> [True/False, ...]

def record_pack_outcome(self, pack_name: str, outcome: str, turn_index: int):
    with self._lock:
        if pack_name not in self._pack_outcomes:
            self._pack_outcomes[pack_name] = []
        self._pack_outcomes[pack_name].append(outcome == "success")

def _pack_confidence(self, pack_name: str) -> float:
    """Return a 0.0–1.0 confidence score for a pack based on history."""
    outcomes = self._pack_outcomes.get(pack_name, [])
    if not outcomes:
        return 0.5  # unknown — neutral
    recent = outcomes[-5:]  # last 5 only
    return sum(recent) / len(recent)
```

---

## 4. Hermes Plugin Updates — Full Implementation

Putting it all together, the `hermes-plugin/__init__.py` register() function grows by ~80 lines:

```python
def register(ctx) -> None:
    # ... existing Steps 1–3 (patch, tool, lifecycle hooks) ...

    # Step 4: Start NudgeEngine
    try:
        from borg.integrations.nudge_engine import NudgeEngine
        from borg.integrations.observer import start_observer, observe, ObservationEvent

        # Start observer thread
        start_observer()

        # Create and start nudge engine
        _nudge_engine = NudgeEngine()
        _nudge_engine.start()

        # Create a turn submitter function bound to the engine
        _turn_index_ref = [0]

        def submit_turn(
            user_message: str,
            agent_messages: List[str],
            tool_errors: List[str],
            tried_packs: Optional[List[str]] = None,
        ):
            _nudge_engine.submit_turn(
                turn_index=_turn_index_ref[0],
                user_message=user_message,
                agent_messages=agent_messages,
                tool_errors=tool_errors,
                tried_packs=tried_packs,
            )
            _turn_index_ref[0] += 1

        # Expose via the ctx manager so run_agent.py can import it
        ctx._borg_nudge_engine = _nudge_engine
        ctx._borg_submit_turn = submit_turn
        ctx._borg_observe = observe

        logger.info("NudgeEngine and Observer started successfully")
    except Exception as exc:
        logger.warning("Could not start NudgeEngine/Observer: %s", exc)
```

---

## 5. Configuration

**File:** `~/.hermes/config.yaml`

```yaml
agent:
  borg:
    autosuggest_enabled: true       # master switch
    error_threshold: 3             # consecutive failures before triggering

    nudge:
      enabled: true                 # proactive nudges during conversation
      min_turns_between: 3         # don't nudge more than once per N turns
      cooldown_seconds: 120        # suppress same pack for N seconds
      idle_check_seconds: 30       # check for idle nudges every N seconds
      min_confidence: 0.5          # don't nudge below this confidence

    feedback:
      async_publish: true          # queue feedback publish instead of blocking
      record_outcomes: true        # log pack outcomes to store
      update_reputation: true      # async reputation update
```

---

## 6. Implementation Order

| Phase | Step | File | Description |
|---|---|---|---|
| 1 | 4.1 | `borg/integrations/nudge_engine.py` | Build NudgeEngine class |
| 1 | 4.2 | `hermes-plugin/__init__.py` | Wire NudgeEngine into plugin |
| 1 | 4.3 | Hermes `run_agent.py` | Call `submit_turn()` and `poll_nudge()` each turn |
| 2 | 5.1 | `borg/integrations/observer.py` | Build Observer background thread |
| 2 | 5.2 | MCP server handlers | Call `observe()` after pull/apply |
| 2 | 5.3 | `borg/core/search.py` | Wire reputation into suggestion ranking |
| 3 | 6.1 | `nudge_engine.py` | Add `record_pack_outcome()` and confidence adjustment |
| 3 | 6.2 | `nudge_engine.py` | Add outcome-aware nudge confidence |

---

## 7. Key Design Decisions

1. **Background thread, not asyncio.** The nudge engine uses a simple `threading.Thread` with a queue. This avoids introducing asyncio into the MCP server and Hermes synchronous code paths. If the agent already uses asyncio, consider a `asyncio.create_task()` equivalent instead.

2. **Non-blocking everywhere.** The main agent loop must never wait for borg. All network I/O (search, GitHub) happens in background threads. The agent gets the fastest possible path.

3. **Suppression prevents spam.** `_suppressed_packs` and `_pack_suppress_until` ensure we don't nudge the agent with the same pack repeatedly. The cooldown is configurable.

4. **Reputation is fire-and-forget.** `ReputationEngine.update_pack_reputation()` is called in a daemon thread. If it fails or is slow, the agent is unaffected.

5. **Outcome feedback closes the loop.** `record_pack_outcome()` feeds execution results back into the nudge engine, allowing it to gradually learn which packs work well for which task patterns — without any explicit training step.

6. **Opt-in.** All nudge behavior is controlled by config flags. If `nudge.enabled: false`, the plugin behaves exactly as it does today (reactive-only on failure).
