"""
NudgeEngine — non-blocking proactive suggestion engine.

Design principles:
  - Runs in a background thread; never blocks the main agent loop.
  - Aggregates signals across the conversation turn window.
  - Fires a nudge only when confidence exceeds a threshold, not on every turn.
  - Respects suppression: don't nudge the same pack twice in a row.

File: borg/integrations/nudge.py (as per DOGFOOD_STRATEGY.md spec)
"""

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Suppress a pack from nudges for this many seconds
_NUDGE_COOLDOWN_SECONDS = 120  # 2 minutes

# Minimum turns between nudges for the same search term
_MIN_TURNS_BETWEEN_NUDGES = 3


@dataclass
class NudgeSignal:
    """A single signal extracted from the conversation."""
    signal_type: str   # "keyword" | "frustration" | "error" | "progress"
    value: str         # e.g. the keyword or error text
    turn_index: int     # conversation turn number
    timestamp: str      # ISO8601


@dataclass
class NudgeDecision:
    """A nudge to be injected."""
    message: str              # formatted suggestion text
    pack_names: List[str]     # packs suggested (for suppression)
    confidence: float        # 0.0–1.0
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
        self._suppressed_packs: Set[str] = set()

        # Background thread
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pending_nudge: Optional[NudgeDecision] = None
        self._lock = threading.Lock()

        # Pack suppression expiry times
        self._pack_suppress_until: Dict[str, float] = {}

        # Per-pack outcome history for confidence adjustment
        self._pack_outcomes: Dict[str, List[bool]] = {}

    # ------------------------------------------------------------------
    # Public API — called from main agent loop (all non-blocking)
    # ------------------------------------------------------------------

    def start(self):
        """Start the background nudge thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="borg-nudge")
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

            # Extract keyword signals via classify_task
            try:
                from borg.core.search import classify_task
                keywords = classify_task(user_message)
                for kw in keywords:
                    self._signals.append(NudgeSignal(
                        signal_type="keyword",
                        value=kw,
                        turn_index=turn_index,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ))
            except Exception as exc:
                logger.debug("classify_task failed: %s", exc)

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

            # Add dojo correction detection
            try:
                from borg.dojo.failure_classifier import detect_corrections
                corrections = detect_corrections([(user_message, time.time())])
                for c in corrections:
                    self._signals.append(NudgeSignal(
                        signal_type="correction",
                        value=c.pattern,
                        turn_index=turn_index,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ))
            except ImportError:
                pass  # Dojo not installed — skip gracefully

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
            if nudge:
                self._last_nudge_turn = nudge.turn_index
            return nudge

    def poll_idle_nudge(self) -> Optional[NudgeDecision]:
        """
        Poll for a nudge during agent idle time (no recent activity).

        This is called periodically (e.g., every 30s) to surface
        nudges when the agent appears to be making slow progress.
        """
        with self._lock:
            # Prune old signals
            cutoff = self._turn_index - 10
            self._signals = [s for s in self._signals if s.turn_index >= cutoff]
            return self._poll_unlocked()

    def suppress_pack(self, pack_name: str, seconds: Optional[float] = None):
        """Suppress a pack from nudges for the cooldown period."""
        with self._lock:
            self._suppressed_packs.add(pack_name)
            expiry = time.time() + (seconds or self._cooldown)
            self._pack_suppress_until[pack_name] = expiry

    def record_pack_outcome(
        self,
        pack_name: str,
        outcome: str,
        turn_index: int,
    ):
        """
        Record the outcome of a pack that was applied.

        This feeds execution results back into the nudge engine,
        allowing future nudge confidence to be adjusted based on
        whether the pack succeeded or failed.
        """
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

    # ------------------------------------------------------------------
    # Internal background loop
    # ------------------------------------------------------------------

    def _run_loop(self):
        """Background thread: waits for turns, computes nudges."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=1.0)

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

        # Expire old pack suppressions
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
        if has_frustration or (has_error and not keywords):
            # High urgency — delegate to borg_on_failure
            result = self._call_borg_on_failure(
                context=context,
                failure_count=2,
                tried_packs=list(self._suppressed_packs),
            )
            if result:
                pack_names = self._extract_pack_names_from_suggestion(result)
                confidence = 0.85 if has_frustration else 0.7
                # Adjust confidence based on pack outcome history
                for p in pack_names:
                    confidence *= self._pack_confidence(p)
                confidence = max(confidence, 0.3)  # floor
                return NudgeDecision(
                    message=result,
                    pack_names=pack_names,
                    confidence=confidence,
                    trigger_signals=["frustration"] if has_frustration else ["tool_error"],
                    turn_index=self._turn_index,
                )

        elif keywords:
            # Keyword-based proactive nudge — use borg_on_task_start
            combined_query = " ".join(sorted(keywords))
            result = self._call_borg_on_task_start(combined_query)
            if result:
                pack_names = self._extract_pack_names_from_suggestion(result)
                # Suppress these packs so we don't nudge again immediately
                for p in pack_names:
                    self._suppressed_packs.add(p)
                    self._pack_suppress_until[p] = now + self._cooldown

                confidence = 0.6  # proactive nudges are lower confidence
                # Adjust confidence based on pack outcome history
                for p in pack_names:
                    confidence *= self._pack_confidence(p)
                confidence = max(confidence, 0.25)  # floor

                return NudgeDecision(
                    message=result,
                    pack_names=pack_names,
                    confidence=confidence,
                    trigger_signals=list(keywords),
                    turn_index=self._turn_index,
                )

        return None

    def _call_borg_on_failure(
        self,
        context: str,
        failure_count: int,
        tried_packs: List[str],
    ) -> Optional[str]:
        """Call borg_on_failure safely, returning the suggestion string or None."""
        try:
            from borg.integrations.agent_hook import borg_on_failure
            return borg_on_failure(
                context=context,
                failure_count=failure_count,
                tried_packs=tried_packs,
            )
        except Exception as exc:
            logger.debug("borg_on_failure failed: %s", exc)
            return None

    def _call_borg_on_task_start(self, task_description: str) -> Optional[str]:
        """Call borg_on_task_start safely, returning the suggestion string or None."""
        try:
            from borg.integrations.agent_hook import borg_on_task_start
            return borg_on_task_start(task_description)
        except Exception as exc:
            logger.debug("borg_on_task_start failed: %s", exc)
            return None

    def _extract_pack_names_from_suggestion(self, text: str) -> List[str]:
        """Extract pack names from a formatted suggestion string."""
        if not text:
            return []
        # Pattern: guild://hermes/pack-name URIs
        names = re.findall(r"guild://hermes/([a-zA-Z0-9_-]+)", text)
        # Pattern: "pack-name (Description)" or "pack-name [tested]"
        names.extend(re.findall(r"\b([a-z][a-z0-9-]{2,30})\s*\(", text))
        # Pattern: "pack-name [tested]" standalone
        names.extend(re.findall(r"\b([a-z][a-z0-9-]{2,30})\s*\[", text))
        return list(set(names))
