"""
Borg V3 Integration Layer — single entry point for V3 contextual selector,
mutation engine, and feedback loop.

BorgV3 class owns:
  - ContextualSelector (contextual Thompson Sampling)
  - MutationEngine    (A/B tests, drift detection, pack mutation suggestions)
  - FeedbackLoop     (records outcomes, feeds selector + mutation engine)

SQLite DB: ~/.borg/borg_v3.db (separate from V2 ~/.borg/borg.db)
Schema:
  - outcomes:     id, pack_id, agent_id, task_category, success, tokens_used, time_taken, timestamp
  - feedback_signals: id, agent_id, pack_id, signal_type, value, timestamp
  - ab_tests:     id, original_pack_id, mutant_pack_id, mutation_type, status, created_at
  - pack_versions: id, pack_id, version, content_hash, created_at
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try importing V3 components (may not exist yet — use stubs)
# ---------------------------------------------------------------------------

try:
    from borg.core.contextual_selector import (
        ContextualSelector,
        classify_task,
        PackDescriptor,
    )
except ImportError:
    ContextualSelector = None
    classify_task = None
    PackDescriptor = None

try:
    from borg.core.mutation_engine import MutationEngine
except ImportError:
    MutationEngine = None

try:
    from borg.core.feedback_loop import FeedbackLoop
except ImportError:
    FeedbackLoop = None

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

V3_SCHEMA = """
CREATE TABLE IF NOT EXISTS outcomes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id      TEXT    NOT NULL,
    agent_id     TEXT,
    task_category TEXT   NOT NULL,
    success      INTEGER NOT NULL,
    tokens_used  INTEGER DEFAULT 0,
    time_taken   REAL    DEFAULT 0.0,
    timestamp    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_signals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id     TEXT,
    pack_id      TEXT,
    signal_type  TEXT    NOT NULL,
    value        REAL,
    timestamp    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS ab_tests (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    original_pack_id TEXT    NOT NULL,
    mutant_pack_id   TEXT    NOT NULL,
    mutation_type    TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'running',
    created_at       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS pack_versions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id      TEXT    NOT NULL,
    version      TEXT    NOT NULL,
    content_hash TEXT    NOT NULL,
    created_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS maintenance_state (
    key         TEXT PRIMARY KEY,
    value       INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_outcomes_pack_id    ON outcomes(pack_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_agent_id   ON outcomes(agent_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_category   ON outcomes(task_category);
CREATE INDEX IF NOT EXISTS idx_feedback_signals_pack ON feedback_signals(pack_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_original   ON ab_tests(original_pack_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_status     ON ab_tests(status);
CREATE INDEX IF NOT EXISTS idx_pack_versions_pack   ON pack_versions(pack_id);
"""

# ---------------------------------------------------------------------------
# Stub classes used when real modules are not available
# ---------------------------------------------------------------------------

class _StubContextualSelector:
    """No-op selector used when borg.core.contextual_selector is unavailable."""

    def __init__(self):
        self.outcomes = []

    def record_outcome(self, pack_id, category, successful):
        self.outcomes.append((pack_id, category, successful))

    def record_outcomes(self, outcomes):
        pass

    def select(self, task_context, candidates, limit=1, seed=None):
        return []


class _StubMutationEngine:
    """No-op mutation engine used when borg.core.mutation_engine is unavailable."""

    def record_outcome(self, pack_id, task_category, success, tokens_used=0, time_taken=0):
        pass

    def check_ab_tests(self):
        return []

    def check_drift(self):
        return []

    def suggest_mutations(self):
        return []


class _StubFeedbackLoop:
    """No-op feedback loop used when borg.core.feedback_loop is unavailable."""

    def record(self, pack_id, task_context, success, tokens_used=0, time_taken=0, agent_id=None):
        pass

    def get_signals(self, pack_id=None):
        return []


# ---------------------------------------------------------------------------
# BorgV3 — main entry point
# ---------------------------------------------------------------------------

class BorgV3:
    """Single entry point for V3 contextual selector, mutation engine, and feedback loop.

    DB path: ~/.borg/borg_v3.db (configurable via db_path).
    """

    def __init__(self, db_path: str = "~/.borg/borg_v3.db"):
        self._db_path = os.path.expanduser(db_path)
        self._ensure_db()

        # Feedback loop — try real FeedbackLoop first, fall back to stub
        self._feedback: Any = _StubFeedbackLoop()
        try:
            from borg.core.feedback_loop import FeedbackLoop as RealFL
            from borg.db.analytics import AnalyticsEngine
            if AnalyticsEngine is not None:
                self._feedback = RealFL()
        except Exception as e:
            logger.debug("FeedbackLoop not available, using stub: %s", e)

        # Contextual selector (needs _feedback to be initialized first)
        if ContextualSelector is not None:
            self._selector = ContextualSelector(feedback_loop=self._feedback)
        else:
            self._selector = _StubContextualSelector()

        # Failure memory — shared with search for prior failure context
        self._failure_memory: Any = None
        try:
            from borg.core.failure_memory import FailureMemory as RealFM
            self._failure_memory = RealFM()
        except Exception as e:
            logger.debug("FailureMemory not available: %s", e)

        # Mutation engine — try real MutationEngine first, fall back to stub
        self._mutation: Any = _StubMutationEngine()
        try:
            from borg.core.mutation_engine import MutationEngine as RealME
            from borg.db.store import AgentStore
            if AgentStore is not None and self._failure_memory is not None:
                store = AgentStore()
                self._mutation = RealME(pack_store=store, failure_memory=self._failure_memory)
        except Exception as e:
            logger.debug("MutationEngine not available, using stub: %s", e)

        # A/B test context — set at search() time, retrieved at record_outcome() time.
        # This bridges the gap when callers don't provide session_id.
        # The in-memory context is scoped to this BorgV3 instance.
        self._last_ab_context: Optional[Dict[str, str]] = None

    # -------------------------------------------------------------------------
    # DB helpers
    # -------------------------------------------------------------------------

    def _ensure_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(V3_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    # -------------------------------------------------------------------------
    # search — contextual or fallback to V2 keyword
    # -------------------------------------------------------------------------

    def search(self, query: str, task_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for packs.

        If task_context is provided, uses the V3 contextual selector (Thompson
        Sampling with task classification). Otherwise falls back to V2 keyword
        search via borg.core.search.borg_search.

        Args:
            query:      Keyword query string.
            task_context: Optional dict with keys:
                          - task_type (str)
                          - error_type (str)
                          - language (str)
                          - keywords (List[str])
                          - file_path (str)
                          - frustration (bool)
                          - agent_id (str)

        Returns:
            List of pack dicts with keys: pack_id, name, score, category, ...
        """
        if not task_context:
            return self._v2_search(query)

        # V3 contextual search path
        candidates = self._get_candidates()
        if not candidates:
            return self._v2_search(query)

        # Phase 1 Day 8-10: Filter by problem_class BEFORE Thompson Sampling.
        # If error_type is in task_context, derive problem_class and use the
        # matching seed pack directly. Seed packs (from borg/skills/) are not in
        # the V3 candidate pool — they are loaded via pack_taxonomy. When a
        # problem_class match exists, return it as the top result and let
        # Thompson Sampling rank it above other candidates.
        problem_class_match = None
        if task_context and task_context.get("error_type"):
            from borg.core.pack_taxonomy import classify_error, load_pack_by_problem_class
            error_msg = task_context.get("error_message", "") or ""
            derived_pc = classify_error(error_msg) if error_msg else None
            if derived_pc:
                matched = load_pack_by_problem_class(derived_pc)
                if matched:
                    # Return the seed pack as a high-priority result
                    evidence = matched.get("evidence", {})
                    return [{
                        "pack_id": matched.get("id", ""),
                        "name": matched.get("id", ""),
                        "category": matched.get("problem_class", ""),
                        "score": 1.0,
                        "match_type": "problem_class_match",
                        "confidence": "tested",
                        "problem_class": derived_pc,
                        "investigation_trail": matched.get("investigation_trail", []),
                        "resolution_sequence": matched.get("resolution_sequence", []),
                        "anti_patterns": matched.get("anti_patterns", []),
                        "evidence": evidence,
                        "is_exploration": False,
                        "reputation": 1.0,
                        "sampled_value": 1.0,
                        "uncertainty": 0.0,
                    }]

        # Classify the task
        if classify_task is not None:
            category = classify_task(
                task_type=task_context.get("task_type"),
                error_type=task_context.get("error_type"),
                language=task_context.get("language"),
                keywords=task_context.get("keywords"),
                file_path=task_context.get("file_path"),
            )
        else:
            category = task_context.get("task_type", "other") or "other"

        # Thompson-sample from the selector
        results = self._selector.select(
            task_context=task_context,
            candidates=candidates,
            limit=10,
            seed=task_context.get("seed"),
        )

        out = []
        for r in results:
            item = {
                "pack_id": r.pack_id,
                "name": r.pack_id,
                "category": r.category,
                "score": r.score,
                "sampled_value": r.sampled_value,
                "uncertainty": r.uncertainty,
                "is_exploration": r.is_exploration,
                "reputation": r.reputation,
                "match_type": "contextual",
            }
            # Annotate A/B test info if pack is part of an active A/B test
            if hasattr(self._mutation, 'ab_tests'):
                for test_id, test in self._mutation.ab_tests.items():
                    if test.variant.mutant_pack_id == r.pack_id:
                        item["ab_test"] = {"test_id": test_id, "variant": "mutant"}
                        break
                    elif test.variant.original_pack_id == r.pack_id:
                        item["ab_test"] = {"test_id": test_id, "variant": "original"}
                        break
                if "ab_test" not in item:
                    item["ab_test"] = None
            out.append(item)

        # ITEM 3.2: Inject prior failure context from FailureMemory
        if self._failure_memory is not None and task_context and task_context.get("error_message"):
            prior = self._failure_memory.recall(task_context["error_message"])
            if prior:
                for item in out:
                    item["prior_failures"] = prior.get("wrong_approaches", [])[:3]
                    item["prior_successes"] = prior.get("correct_approaches", [])[:2]

        # Capture A/B test context from the top result so record_outcome() can
        # attribute the outcome to the correct A/B test variant — even when
        # no session_id is provided. This bridges the A/B wiring gap.
        self._last_ab_context = None
        if out and out[0].get("ab_test"):
            ab_info = out[0]["ab_test"]
            self._last_ab_context = {
                "test_id": ab_info.get("test_id", ""),
                "variant": ab_info.get("variant", ""),
            }

        return out

    def _v2_search(self, query: str) -> List[Dict[str, Any]]:
        """Fallback V2 keyword search via borg.core.search.borg_search."""
        try:
            from borg.core.search import borg_search as _v2_search
            result_json = _v2_search(query, mode="text")
            parsed = json.loads(result_json)
            if parsed.get("success") and parsed.get("matches"):
                out = []
                for p in parsed["matches"]:
                    out.append({
                        "pack_id": p.get("id", p.get("name", "")),
                        "name":    p.get("name", ""),
                        "category": p.get("problem_class", ""),
                        "score":   1.0,
                        "match_type": "keyword",
                        "tier":    p.get("tier", "unknown"),
                        "confidence": p.get("confidence", "unknown"),
                    })
                return out
        except Exception as e:
            logger.warning("V2 search failed: %s", e)
        return []

    def _get_candidates(self) -> List["PackDescriptor"]:
        """Build a list of PackDescriptor candidates from V2 pack index."""
        if PackDescriptor is None:
            return []
        try:
            from borg.core.uri import get_available_pack_names
            names = get_available_pack_names()
        except Exception:
            names = []

        descriptors = []
        for name in names:
            descriptors.append(PackDescriptor(
                pack_id=name,
                name=name,
                keywords=[],
                supported_tasks=[],
            ))
        return descriptors

    # -------------------------------------------------------------------------
    # record_outcome — feeds both selector + feedback loop + mutation engine
    # -------------------------------------------------------------------------

    def record_outcome(
        self,
        pack_id: str,
        task_context: Optional[Dict[str, Any]],
        success: bool,
        tokens_used: int = 0,
        time_taken: float = 0.0,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Record a pack execution outcome.

        This method:
          1. Persists the outcome to the V3 SQLite DB.
          2. Feeds the contextual selector (Thompson Sampling posterior update).
          3. Feeds the feedback loop (signal recording).
          4. Feeds the mutation engine (drift / A/B tracking).

        Args:
            pack_id:      The pack that was selected.
            task_context: Optional task context dict (same keys as search()).
            success:      Whether the execution succeeded.
            tokens_used:  Number of tokens consumed (for cost tracking).
            time_taken:   Seconds elapsed (for latency tracking).
            agent_id:     Optional agent identifier for per-agent stats.
        """
        # Determine task category
        category = "other"
        if task_context:
            if classify_task is not None:
                category = classify_task(
                    task_type=task_context.get("task_type"),
                    error_type=task_context.get("error_type"),
                    language=task_context.get("language"),
                    keywords=task_context.get("keywords"),
                    file_path=task_context.get("file_path"),
                ) or "other"
            elif task_context.get("task_type"):
                category = task_context["task_type"]

        ts = datetime.now(timezone.utc).isoformat()

        # 1. Persist to SQLite
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO outcomes
                   (pack_id, agent_id, task_category, success, tokens_used, time_taken, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (pack_id, agent_id, category, int(success), tokens_used, time_taken, ts),
            )
            conn.commit()

        # 2. Feed the contextual selector
        self._selector.record_outcome(pack_id, category, success)

        # 3. Feed the feedback loop (defensively check for record method)
        try:
            if hasattr(self._feedback, "record"):
                self._feedback.record(
                    pack_id=pack_id,
                    task_context=task_context,
                    success=success,
                    tokens_used=tokens_used,
                    time_taken=time_taken,
                    agent_id=agent_id,
                )
        except Exception as e:
            logger.warning("FeedbackLoop.record failed: %s", e)

        # 4. Feed the mutation engine (A/B outcome attribution)
        # Priority: (a) in-memory A/B context from search() →
        #           (b) session_id path (MCP users) →
        #           (c) skip (CLI without prior search)
        try:
            if hasattr(self._mutation, "record_outcome"):
                ab_recorded = False

                # Path (a): use in-memory A/B context captured at search() time
                if self._last_ab_context:
                    test_id = self._last_ab_context.get("test_id", "")
                    variant = self._last_ab_context.get("variant", "")
                    if test_id and variant:
                        self._mutation.record_outcome(test_id, variant, success)
                        ab_recorded = True
                        self._last_ab_context = None  # clear after use

                # Path (b): fall back to session_id (MCP users)
                if not ab_recorded and session_id:
                    try:
                        from borg.core import session as session_module
                        session = session_module.get_session(session_id) or {}
                        sv = session.get("selected_variant")
                        if sv:
                            self._mutation.record_outcome(sv["test_id"], sv["variant"], success)
                            ab_recorded = True
                    except Exception:
                        pass

                # Path (d): no A/B context — feed mutation engine directly for drift tracking
                if not ab_recorded:
                    try:
                        self._mutation.record_outcome(pack_id, category, success, tokens_used, time_taken)
                    except TypeError:
                        # Real MutationEngine.record_outcome(test_id, variant, success) doesn't
                        # accept extended params — skip silently in that case
                        pass
        except Exception as e:
            logger.warning("MutationEngine.record_outcome failed: %s", e)

    # -------------------------------------------------------------------------
    # should_mutate — checks if a pack should be mutated
    # -------------------------------------------------------------------------

    def should_mutate(self, pack_id: str) -> bool:
        """Check if a pack has enough poor outcomes to warrant mutation.

        A pack is a mutation candidate when it has:
          - At least 5 recorded outcomes in the V3 DB
          - Success rate below 50%

        Args:
            pack_id: The pack to check.

        Returns:
            True if the pack meets mutation criteria.
        """
        with self._conn() as conn:
            cur = conn.execute(
                """SELECT COUNT(*), SUM(success)
                   FROM outcomes WHERE pack_id = ?""",
                (pack_id,),
            )
            row = cur.fetchone()
            if row is None:
                return False
            count = row[0] or 0
            successes = row[1] or 0
        if count < 5:
            return False
        return (successes / count) < 0.5

    # -------------------------------------------------------------------------
    # get_dashboard — aggregated stats
    # -------------------------------------------------------------------------

    def get_dashboard(self) -> Dict[str, Any]:
        """Return aggregated V3 stats covering packs, outcomes, quality, drift, and mutations.

        Returns:
            Dict with keys:
              - total_outcomes
              - total_packs
              - success_rate
              - avg_tokens
              - avg_time
              - quality_scores  (per-pack dict)
              - drift_alerts   (list of dicts)
              - mutation_stats  (dict: suggested, running, completed)
              - ab_tests        (list of active A/B tests)
        """
        with self._conn() as conn:
            # Outcome stats
            cur = conn.execute("SELECT COUNT(*), SUM(success), SUM(tokens_used), SUM(time_taken) FROM outcomes")
            row = cur.fetchone()
            total_outcomes = row[0] or 0
            total_success  = row[1] or 0
            total_tokens   = row[2] or 0
            total_time     = row[3] or 0.0

            success_rate = (total_success / total_outcomes) if total_outcomes > 0 else 0.0
            avg_tokens   = (total_tokens  / total_outcomes) if total_outcomes > 0 else 0
            avg_time     = (total_time    / total_outcomes) if total_outcomes > 0 else 0.0

            # Unique packs
            cur = conn.execute("SELECT COUNT(DISTINCT pack_id) FROM outcomes")
            total_packs = cur.fetchone()[0] or 0

            # Per-pack quality scores
            cur = conn.execute(
                """SELECT pack_id,
                          COUNT(*) as n,
                          ROUND(100.0 * SUM(success) / COUNT(*), 1) as rate
                   FROM outcomes
                   GROUP BY pack_id"""
            )
            quality_scores = {
                r[0]: {"outcomes": r[1], "success_rate": r[2]}
                for r in cur.fetchall()
            }

            # Drift alerts (packs with <40% success rate over last 20 outcomes)
            drift_alerts = []
            cur = conn.execute(
                """SELECT pack_id,
                          COUNT(*) as n,
                          ROUND(100.0 * SUM(success) / COUNT(*), 1) as rate
                   FROM (SELECT * FROM outcomes ORDER BY id DESC LIMIT 20)
                   GROUP BY pack_id
                   HAVING rate < 40"""
            )
            for r in cur.fetchall():
                drift_alerts.append({
                    "pack_id": r[0],
                    "recent_outcomes": r[1],
                    "recent_success_rate": r[2],
                })

            # A/B test stats
            cur = conn.execute(
                "SELECT status, COUNT(*) FROM ab_tests GROUP BY status"
            )
            mutation_stats = {"suggested": 0, "running": 0, "completed": 0, "failed": 0}
            for status, count in cur.fetchall():
                if status in mutation_stats:
                    mutation_stats[status] = count

            # Active A/B tests
            cur = conn.execute(
                """SELECT id, original_pack_id, mutant_pack_id, mutation_type, status, created_at
                   FROM ab_tests WHERE status = 'running'
                   ORDER BY created_at DESC LIMIT 20"""
            )
            ab_tests = [
                {
                    "id": r[0],
                    "original_pack_id": r[1],
                    "mutant_pack_id": r[2],
                    "mutation_type": r[3],
                    "status": r[4],
                    "created_at": r[5],
                }
                for r in cur.fetchall()
            ]

        # Mutation engine suggestions
        try:
            suggestions = self._mutation.suggest_mutations()
        except Exception:
            suggestions = []

        # Drift from mutation engine
        try:
            drift_items = self._mutation.check_drift()
        except Exception:
            drift_items = []

        if drift_items and not isinstance(drift_items[0], dict):
            drift_items = [{"pack_id": d} for d in drift_items]

        return {
            "total_outcomes": total_outcomes,
            "total_packs": total_packs,
            "success_rate": round(success_rate, 4),
            "avg_tokens": round(avg_tokens, 2),
            "avg_time": round(avg_time, 2),
            "quality_scores": quality_scores,
            "drift_alerts": drift_alerts + drift_items,
            "mutation_stats": mutation_stats,
            "ab_tests": ab_tests,
            "mutation_suggestions": suggestions if isinstance(suggestions, list) else [],
        }

    # -------------------------------------------------------------------------
    # run_maintenance — periodic upkeep
    # -------------------------------------------------------------------------

    def run_maintenance(self) -> Dict[str, Any]:
        """Run periodic V3 maintenance.

        Checks:
          1. A/B tests for completion
          2. Drift detection
          3. Mutation suggestions for underperforming packs

        This should be called periodically (e.g., once per hour or after a batch
        of executions).

        Returns:
            Dict with keys: ab_tests_checked, drift_alerts, mutations_suggested
        """
        results: Dict[str, Any] = {
            "ab_tests_checked": 0,
            "drift_alerts": [],
            "mutations_suggested": [],
        }

        # 1. Check A/B tests
        try:
            ab_results = self._mutation.check_ab_tests()
            results["ab_tests_checked"] = len(ab_results) if ab_results else 0
        except Exception as e:
            logger.warning("A/B check failed: %s", e)

        # 2. Check drift
        try:
            drift_results = self._mutation.check_drift()
            if drift_results:
                if isinstance(drift_results[0], dict):
                    results["drift_alerts"] = drift_results
                else:
                    results["drift_alerts"] = [{"pack_id": d} for d in drift_results]
        except Exception as e:
            logger.warning("Drift check failed: %s", e)

        # 3. Suggest mutations for underperforming packs
        try:
            suggestions = self._mutation.suggest_mutations()
            if suggestions:
                results["mutations_suggested"] = suggestions
        except Exception as e:
            logger.warning("Mutation suggestion failed: %s", e)

        # 4. Trace maintenance
        try:
            from borg.core.traces import traces_maintenance
            trace_stats = traces_maintenance()
            results["trace_maintenance"] = trace_stats
        except Exception as e:
            logger.warning("Trace maintenance failed: %s", e)

        return results

    # -------------------------------------------------------------------------
    # Convenience: record_feedback_signal
    # -------------------------------------------------------------------------

    def record_feedback_signal(
        self,
        signal_type: str,
        value: float,
        agent_id: Optional[str] = None,
        pack_id: Optional[str] = None,
    ) -> None:
        """Record a raw feedback signal (e.g., frustration, satisfaction score).

        Args:
            signal_type: Identifier for the signal (e.g. "frustration", "latency").
            value:       Numeric value of the signal.
            agent_id:    Optional agent that generated the signal.
            pack_id:     Optional pack the signal relates to.
        """
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO feedback_signals (agent_id, pack_id, signal_type, value, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (agent_id, pack_id, signal_type, value, ts),
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # Maintenance counter — persisted in DB, survives restarts
    # -------------------------------------------------------------------------

    def _get_maintenance_counter(self) -> int:
        """Get the current maintenance invocation counter from DB."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM maintenance_state WHERE key = 'feedback_count'"
            ).fetchone()
            return row[0] if row else 0

    def _inc_maintenance_counter(self) -> int:
        """Increment the maintenance counter and return the new value.

        Uses INSERT OR CONFLICT to atomically upsert the counter.
        """
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO maintenance_state (key, value, updated_at)
                VALUES ('feedback_count', 1, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET value = value + 1, updated_at = datetime('now')
            """)
            conn.commit()
        return self._get_maintenance_counter()

    def _reset_maintenance_counter(self) -> None:
        """Reset the maintenance counter to zero."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE maintenance_state SET value = 0 WHERE key = 'feedback_count'"
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # For testing: inject a real selector for unit testing
    # -------------------------------------------------------------------------

    def _set_selector(self, selector) -> None:
        """Replace the selector (used by unit tests)."""
        self._selector = selector

    def _set_mutation(self, engine) -> None:
        """Replace the mutation engine (used by unit tests)."""
        self._mutation = engine

    def _set_feedback(self, loop) -> None:
        """Replace the feedback loop (used by unit tests)."""
        self._feedback = loop
