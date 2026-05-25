"""
Borg MCP Server (T1.11) — AI Guild tools via Model Context Protocol (JSON-RPC 2.0 over stdio).

Exposed tools:
  - guild_search:  Search for borg workflow packs by keyword
  - guild_pull:     Fetch, validate, and store a pack locally
  - guild_try:     Preview a pack without saving
  - guild_init:     Initialise a new pack scaffold
  - guild_apply:    Execute a pack (start / checkpoint / complete)
  - guild_publish:  Publish a pack or feedback artifact
  - guild_feedback: Generate feedback draft after pack execution
  - guild_suggest:  Auto-suggest pack based on frustration signals
  - guild_observe:  Silent observation: structural guidance at task start
  - guild_convert:  Convert SKILL.md / CLAUDE.md / .cursorrules to pack

Zero imports from tools.* or guild_mcp.* — uses only borg.core.* and borg.integrations.*
"""

from __future__ import annotations

import contextvars
import json
import logging
logger = logging.getLogger(__name__)
import os
import re
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from borg import __version__ as BORG_VERSION

# Suppress default logging (MCP uses stdout for JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

from borg.core.traces import TraceCapture, save_trace
from borg.core import confidence_gate as _confidence_gate
from borg.core import negative_traces as _negative_traces_module
from borg.core import search as _search_module
from borg.core import trace_matcher as _trace_matcher_module
from borg.core.dirs import get_trace_db_path

# Thread-safe session tracking via contextvars
_current_session_id: contextvars.ContextVar[str] = contextvars.ContextVar('session_id', default='')
_current_agent_id: contextvars.ContextVar[str] = contextvars.ContextVar('agent_id', default='unknown')
_last_shown_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    '_last_shown_trace_id', default=None
)

# Global trace captures — one per session_id
_trace_captures: Dict[str, TraceCapture] = {}
_trace_lock = threading.Lock()  # Lock for thread-safe access to _trace_captures

# -------------------------------------------------------------------------
# Rate limiting (token bucket: 60 requests per minute)
# -------------------------------------------------------------------------
_rate_limit_lock = threading.Lock()
_rate_requests: List[float] = []  # Timestamps of recent requests
_RATE_LIMIT = 60  # requests per window
_RATE_WINDOW = 60.0  # window in seconds


def _check_rate_limit() -> bool:
    """Return True if request is allowed, False if rate limited."""
    with _rate_limit_lock:
        now = time.time()
        # Remove requests outside the window
        while _rate_requests and _rate_requests[0] < now - _RATE_WINDOW:
            _rate_requests.pop(0)
        if len(_rate_requests) >= _RATE_LIMIT:
            return False
        _rate_requests.append(now)
        return True


# -------------------------------------------------------------------------
# MCP request timeouts (30s)
# -------------------------------------------------------------------------
TOOL_TIMEOUT_SEC = 30

# Per-call timeout state (for threading.Timer fallback when SIGALRM unavailable)
_timeout_state: Dict[str, Any] = {}


def _timeout_handler(signum, frame):
    """Called when a tool call exceeds TOOL_TIMEOUT_SEC (SIGALRM path)."""
    raise TimeoutError(f"Tool call exceeded {TOOL_TIMEOUT_SEC}s timeout")


class _ThreadTimeout:
    """threading.Timer-based timeout for non-main threads."""
    def __init__(self, seconds: float):
        self.seconds = seconds
        self._timer: Optional[threading.Timer] = None
        self._cancelled = False
        self._exc_info = None

    def _do_timeout(self):
        self._exc_info = (TimeoutError, TimeoutError(f"Tool call exceeded {self.seconds}s timeout"), None)

    def __enter__(self):
        def do_timeout():
            self._do_timeout()
        self._timer = threading.Timer(self.seconds, do_timeout)
        self._timer.start()
        return self

    def __exit__(self, typ, val, tb):
        if self._timer:
            self._timer.cancel()
        if self._exc_info and isinstance(val, TimeoutError):
            raise self._exc_info[1]
        return False

    def did_timeout(self) -> bool:
        return self._exc_info is not None


_MAINTENANCE_INTERVAL: int = 10  # Run maintenance every N feedback calls


def init_trace_capture(session_id: str, task: str = "", agent_id: str = ""):
    """Initialize trace capture for a session."""
    global _trace_captures
    with _trace_lock:
        _trace_captures[session_id] = TraceCapture(task=task, agent_id=agent_id)


def _trace_has_meaningful_root_cause(trace: Dict[str, Any]) -> bool:
    """Return True when a trace has enough root-cause signal to persist."""
    return len(str(trace.get("root_cause") or "").strip()) >= 10


def _save_trace_if_meaningful(trace: Dict[str, Any]) -> bool:
    """Persist trace only when it is not a hollow auto-capture."""
    if not _trace_has_meaningful_root_cause(trace):
        logger.warning("borg: skipped hollow trace")
        return False
    save_trace(trace)
    return True


def _feed_trace_capture(tool_name: str, args: Dict[str, Any], result: str):
    """Accumulate a tool call into the active trace capture for the current session."""
    session_id = _current_session_id.get()
    if not session_id:
        return  # No active session
    global _trace_captures
    with _trace_lock:
        capture = _trace_captures.get(session_id)
        if capture is None:
            return  # No active capture for this session
        capture.on_tool_call(tool_name, args, result)

        # Auto-save at 45 calls (before agent wastes more tokens)
        if capture.tool_calls >= 45:
            if capture.task:  # Only save if we have a task
                trace = capture.extract_trace(outcome="auto_truncated")
                if trace["tool_calls"] > 5:
                    _save_trace_if_meaningful(trace)
            del _trace_captures[session_id]

# ---------------------------------------------------------------------------
# Tool definitions (MCP schema)
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "borg_search",
        "description": (
            "Search for borg workflow packs by keyword or semantic similarity. Searches local packs and the remote index. "
            "Returns matching packs with their metadata (name, problem class, tier, confidence). "
            "Use mode='semantic' or mode='hybrid' for semantic search when embeddings are available. "
            "When task_context is provided, uses the V3 contextual search path."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query (keywords to match against pack names, descriptions, "
                        "problem classes). Empty returns all packs."
                    ),
                },
                "mode": {
                    "type": "string",
                    "enum": ["text", "semantic", "hybrid"],
                    "description": (
                        "Search mode: 'text' for keyword matching, 'semantic' for vector similarity search, "
                        "'hybrid' for combined text + semantic. Defaults to 'text'."
                    ),
                    "default": "text",
                },
                "task_context": {
                    "type": "object",
                    "description": (
                        "V3 task context for contextual search. "
                        "Keys: task_type (str), keywords (list of str), agent_id (str, optional)."
                    ),
                    "properties": {
                        "task_type": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "agent_id": {"type": "string"},
                    },
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "borg_pull",
        "description": (
            "Fetch, validate, and store a borg pack locally. Downloads from URI, runs safety scan, "
            "and saves to ~/.hermes/guild/. Returns pack metadata and proof gate status."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "description": "Guild pack URI (guild://domain/name, https://..., or /local/path)",
                }
            },
            "required": ["uri"],
        },
    },
    {
        "name": "borg_try",
        "description": (
            "Preview a borg workflow pack without saving it. Shows pack metadata, phases, proof gates, "
            "safety scan results, and trust tier. Use before guild_pull to check if a pack is worth adopting."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "description": "Guild pack URI (guild://domain/name, https://..., or /local/path)",
                }
            },
            "required": ["uri"],
        },
    },
    {
        "name": "borg_init",
        "description": (
            "Scaffold a new borg workflow pack in the local borg directory. "
            "Creates the directory structure and a minimal pack.yaml template."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pack_name": {
                    "type": "string",
                    "description": "Unique name for the new pack (used as directory name).",
                },
                "problem_class": {
                    "type": "string",
                    "description": "Problem class (e.g. classification, extraction, reasoning).",
                    "default": "general",
                },
                "mental_model": {
                    "type": "string",
                    "description": "Mental model (e.g. fast-thinker, slow-thinker).",
                    "default": "fast-thinker",
                },
            },
            "required": ["pack_name"],
        },
    },
    {
        "name": "borg_apply",
        "description": (
            "Execute a borg workflow pack with phase tracking. Multi-action: "
            "action='start' loads a pulled pack and returns an approval summary; "
            "action='checkpoint' logs a phase result (passed/failed); "
            "action='complete' finalizes and generates feedback."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "checkpoint", "complete"],
                    "description": "Action: start, checkpoint, or complete",
                },
                "pack_name": {
                    "type": "string",
                    "description": "Name of the pack (must be pulled first, for action='start')",
                },
                "task": {
                    "type": "string",
                    "description": "Task description — what you're applying the pack to (for action='start')",
                },
                "session_id": {
                    "type": "string",
                    "description": "Active session ID from guild_apply_start (for checkpoint/complete)",
                },
                "ab_test": {
                    "type": "object",
                    "description": "A/B test info if selected pack is a variant (for action='start')",
                    "properties": {
                        "test_id": {"type": "string"},
                        "variant": {"type": "string"},
                    },
                },
                "phase_name": {
                    "type": "string",
                    "description": (
                        "Phase name to checkpoint, or '__approval__' to approve execution "
                        "(for action='checkpoint')"
                    ),
                },
                "status": {
                    "type": "string",
                    "enum": ["passed", "failed"],
                    "description": "Checkpoint result (for action='checkpoint')",
                },
                "evidence": {
                    "type": "string",
                    "description": "Evidence supporting the checkpoint result (optional, for action='checkpoint')",
                },
                "outcome": {
                    "type": "string",
                    "description": "Final outcome description (optional, for action='complete')",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "borg_publish",
        "description": (
            "Publish a guild artifact (workflow pack or feedback) for validation and publishing. "
            "Validates proof gates and safety, then creates a GitHub PR. "
            "Falls back to local outbox if gh CLI is unavailable."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "publish"],
                    "description": "Action: 'list' to show available artifacts, 'publish' to publish one",
                },
                "pack_name": {
                    "type": "string",
                    "description": "Name of the pack to publish (for action='publish')",
                },
                "feedback_name": {
                    "type": "string",
                    "description": "Name of the feedback to publish (for action='publish')",
                },
                "path": {
                    "type": "string",
                    "description": "Explicit path to artifact file (for action='publish')",
                },
                "repo": {
                    "type": "string",
                    "description": "Target GitHub repo (defaults to BORG_PACK_REPO or borg-farther/Borg-Directory)",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "borg_feedback",
        "description": (
            "Generate a feedback draft for a completed pack execution. "
            "Reads the execution session log and produces a structured feedback artifact. "
            "When task_context is provided, also records outcome to V3."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID of the completed pack execution.",
                },
                "what_changed": {
                    "type": "string",
                    "description": "Brief description of what changed in this execution vs. the original pack.",
                    "default": "",
                },
                "where_to_reuse": {
                    "type": "string",
                    "description": "Guidance on where this feedback can be reused.",
                    "default": "",
                },
                "success": {
                    "type": "boolean",
                    "description": "Whether the pack execution was successful (V3 parameter).",
                },
                "tokens_used": {
                    "type": "integer",
                    "description": "Number of tokens used in the execution (V3 parameter).",
                },
                "time_taken": {
                    "type": "number",
                    "description": "Time taken for the execution in seconds (V3 parameter).",
                },
                "task_context": {
                    "type": "object",
                    "description": "V3 task context for outcome recording.",
                    "properties": {
                        "task_type": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "agent_id": {"type": "string"},
                    },
                },
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "borg_suggest",
        "description": (
            "Auto-suggest a borg workflow pack based on frustration signals and task context. "
            "Triggers when failure_count >= 2 or when frustration keywords are detected. "
            "Searches borg packs by classified task terms and returns top matches."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Recent conversation context (messages, errors, task description).",
                },
                "failure_count": {
                    "type": "integer",
                    "description": "Number of consecutive failed attempts. Suggestion triggers at >= 2.",
                    "default": 0,
                },
                "task_type_hint": {
                    "type": "string",
                    "description": "Optional explicit task type hint (e.g. 'debug', 'test', 'review').",
                },
                "tried_packs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of pack names already tried (excluded from suggestions).",
                },
            },
            "required": ["context"],
        },
    },
    {
        "name": "borg_rescue",
        "description": (
            "Agent-ready day-one rescue packet. Given an error, failing command output, or agent transcript, "
            "returns ACTION, STOP, VERIFY, human receipt, automation policy, and optional full guidance. "
            "Use this when the agent is about to debug or has hit a technical failure."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Error, failing command output, task text, or recent agent transcript.",
                },
                "source": {
                    "type": "string",
                    "description": "Caller provenance tag (default: mcp).",
                    "default": "mcp",
                },
                "show_guidance": {
                    "type": "boolean",
                    "description": "Include full legacy guidance block (default: true).",
                    "default": True,
                },
            },
            "required": ["input"],
        },
    },
    {
        "name": "error_lookup",
        "description": (
            "Plain-English alias for borg_rescue. Given an error, failing command output, or agent transcript, "
            "returns the same ACTION, STOP, VERIFY, confidence, human receipt, and automation policy as borg_rescue. "
            "Use this as the first-user MCP tool name for concrete failures."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Error, failing command output, task text, or recent agent transcript.",
                },
                "source": {
                    "type": "string",
                    "description": "Caller provenance tag (default: mcp).",
                    "default": "mcp",
                },
                "show_guidance": {
                    "type": "boolean",
                    "description": "Include full legacy guidance block (default: true).",
                    "default": True,
                },
            },
            "required": ["input"],
        },
    },
    {
        "name": "borg_first_10",
        "description": (
            "Machine-readable first-10 beta readiness contract: seven gates, clean-user smoke path, "
            "agent priming paragraph, feedback fields, and GO/NO-GO success metric."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "borg_runtime_fingerprint",
        "description": (
            "Report the exact loaded Borg MCP runtime path, source hashes, BORG_HOME, process id, "
            "and a confidence-gate canary. Use this before any reload/cutover to prove what code "
            "the served process is actually running. It performs no restart and no mutation."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "borg_observe",
        "description": (
            "Silent observation: analyzes the current task and returns confidence-labeled structural guidance. "
            "Call this at the start of non-trivial debugging/testing/review tasks to get recorded or seeded strategies. "
            "Returns specific phase-by-phase guidance only when a relevant pack exists, or explicit no-match guidance. "
            "Supports conditional phases: when context includes error_message, error_type, attempts, "
            "has_recent_changes, or error_in_test, skip_if/inject_if/context_prompts conditions are evaluated."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Task description — what you're about to work on.",
                },
                "context": {
                    "type": "string",
                    "description": "Optional additional context (environment, language, constraints).",
                },
                "context_dict": {
                    "type": "object",
                    "description": (
                        "Optional runtime context for conditional phase evaluation. "
                        "Keys: error_message (str), error_type (str), attempts (int), "
                        "has_recent_changes (bool), error_in_test (bool)."
                    ),
                    "properties": {
                        "error_message": {"type": "string"},
                        "error_type": {"type": "string"},
                        "attempts": {"type": "integer"},
                        "has_recent_changes": {"type": "boolean"},
                        "error_in_test": {"type": "boolean"},
                    },
                },
                "project_path": {
                    "type": "string",
                    "description": (
                        "Optional path to the project directory for change awareness. "
                        "If provided, cross-references the error with recently changed files."
                    ),
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "borg_convert",
        "description": (
            "Convert a SKILL.md, CLAUDE.md, or .cursorrules file into a borg workflow pack. "
            "Auto-detects format from filename or allows explicit format specification. "
            "Use format='openclaw' to convert the entire pack registry to OpenClaw skill format."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the source file (SKILL.md, CLAUDE.md, or .cursorrules). Not needed for format='openclaw'.",
                },
                "format": {
                    "type": "string",
                    "enum": ["auto", "skill", "claude", "cursorrules", "openclaw"],
                    "description": "Format of the source file. 'auto' detects from filename. 'openclaw' converts entire registry.",
                    "default": "auto",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Output directory for OpenClaw conversion (default: ./openclaw-skills/). Only used when format='openclaw'.",
                },
            },
            "required": ["format"],
        },
    },
    {
        "name": "borg_generate",
        "description": (
            "Generate platform-specific rules files from a borg workflow pack. "
            "Takes a pack name or pack data and outputs rules in the specified format "
            "native to each AI IDE platform (Cursor, Cline, Claude Code, Windsurf)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pack": {
                    "type": "string",
                    "description": (
                        "Pack name (e.g. 'systematic-debugging') or pack identifier. "
                        "The pack must be available in the local registry."
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["cursorrules", "clinerules", "claude-md", "windsurfrules", "all"],
                    "description": (
                        "Output format. 'cursorrules' → .cursorrules (Cursor), "
                        "'clinerules' → .clinerules (Cline), "
                        "'claude-md' → CLAUDE.md (Claude Code), "
                        "'windsurfrules' → .windsurfrules (Windsurf), "
                        "'all' → all four formats at once."
                    ),
                    "default": "cursorrules",
                },
            },
            "required": ["pack", "format"],
        },
    },
    {
        "name": "borg_context",
        "description": (
            "Detect recent git changes in a project directory. Returns recently changed files, "
            "uncommitted changes, and recent commit messages. Use this to understand what changed "
            "in the codebase recently when debugging errors."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the git repository. Defaults to '.' (current directory).",
                    "default": ".",
                },
                "hours": {
                    "type": "integer",
                    "description": "Look for changes in the last N hours. Defaults to 24.",
                    "default": 24,
                },
            },
            "required": ["project_path"],
        },
    },
    {
        "name": "borg_recall",
        "description": (
            "Recall failure memory for an error. Returns approaches that agents "
            "tried and failed, as well as approaches that succeeded. Use this before attempting "
            "a fix to avoid known wrong paths."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_message": {
                    "type": "string",
                    "description": "The error message to look up in failure memory.",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Agent namespace to search. Defaults to 'default'.",
                    "default": "default",
                },
            },
            "required": ["error_message"],
        },
    },
    {
        "name": "borg_record_failure",
        "description": (
            "Record a failure or success outcome for an error pattern in failure memory. "
            "This writes to the failure memory store so other agents can benefit from the learning. "
            "Call this after attempting a fix — record 'success' if it worked, 'failure' if it did not."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_pattern": {
                    "type": "string",
                    "description": "The error message or pattern encountered (e.g. \"NoneType has no attribute 'split'\").",
                },
                "pack_id": {
                    "type": "string",
                    "description": "The borg pack being used (e.g. 'systematic-debugging').",
                },
                "phase": {
                    "type": "string",
                    "description": "The phase being executed when the error occurred (e.g. 'investigate_root_cause').",
                },
                "approach": {
                    "type": "string",
                    "description": "What the agent tried to fix the error (e.g. 'Added if val is not None check').",
                },
                "outcome": {
                    "type": "string",
                    "enum": ["success", "failure"],
                    "description": "Result of the approach: 'success' or 'failure'.",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Agent namespace to write to. Defaults to 'default'.",
                    "default": "default",
                },
            },
            "required": ["error_pattern", "pack_id", "phase", "approach", "outcome"],
        },
    },
    {
        "name": "borg_delete_failure",
        "description": (
            "Delete a failure memory record for an error pattern. "
            "Use this to retract wrong entries or clear test data. "
            "Returns success=True if deleted, success=True with found=False if not found."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_pattern": {
                    "type": "string",
                    "description": "The error pattern whose record should be deleted.",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Agent namespace to delete from. Defaults to 'default'.",
                    "default": "default",
                },
            },
            "required": ["error_pattern"],
        },
    },
    {
        "name": "borg_reputation",
        "description": (
            "Query agent reputation and trust information from the ReputationEngine. "
            "Provides access to contribution scores, access tiers, free-rider status, and pack trust. "
            "Use this to understand an agent's standing in the guild before consuming their packs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_profile", "get_pack_trust", "get_free_rider_status"],
                    "description": "Action to perform: 'get_profile' for agent reputation, 'get_pack_trust' for pack trust, 'get_free_rider_status' for free-rider info",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to query (for get_profile and get_free_rider_status actions).",
                },
                "pack_id": {
                    "type": "string",
                    "description": "Pack ID to query (for get_pack_trust action).",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "borg_analytics",
        "description": (
            "Query ecosystem health metrics and analytics from the AnalyticsEngine. "
            "Returns ecosystem-wide health, pack usage statistics, adoption metrics, and time-series data. "
            "Use this to understand the overall state of the guild ecosystem."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ecosystem_health", "pack_usage", "adoption", "timeseries"],
                    "description": "Action: 'ecosystem_health' for overall ecosystem metrics, 'pack_usage' for a specific pack's stats, 'adoption' for adoption metrics, 'timeseries' for time-series data.",
                },
                "pack_id": {
                    "type": "string",
                    "description": "Pack ID to query (for pack_usage and adoption actions).",
                },
                "metric": {
                    "type": "string",
                    "description": "Metric name for timeseries action: 'pack_publishes', 'executions', 'avg_quality_score', or 'active_agents'.",
                },
                "period": {
                    "type": "string",
                    "description": "Time period for timeseries: 'daily', 'weekly', or 'monthly'. Defaults to 'daily'.",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back for timeseries. Defaults to 30.",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "borg_dashboard",
        "description": (
            "Query the Borg V3 dashboard — aggregated stats from the V3 outcomes database. "
            "Returns total outcomes, success rates, quality scores per pack, drift alerts, "
            "mutation stats, and A/B test status. Use this to monitor pack performance "
            "and system health."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "borg_dojo",
        "description": (
            "Borg Dojo — training improvement pipeline. Run session analysis, view learning curves, "
            "generate reports, and check system health. Actions: "
            "'analyze' runs session analysis over the last N days; "
            "'report' generates a formatted improvement report (cli, telegram, or discord format); "
            "'history' shows the learning curve with historical snapshots; "
            "'status' returns a quick health summary with error rates and weakest tools."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["analyze", "report", "history", "status"],
                    "description": "Action to perform: 'analyze' runs session analysis, 'report' generates formatted report, 'history' shows learning curve, 'status' returns health summary.",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back for analysis (default: 7).",
                    "default": 7,
                },
                "report_format": {
                    "type": "string",
                    "enum": ["cli", "telegram", "discord"],
                    "description": "Report format for 'report' action: 'cli', 'telegram', or 'discord'. Defaults to 'telegram'.",
                    "default": "telegram",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "borg_clusters",
        "description": (
            "Discover problem clusters in Borg's trace database. "
            "Uses KMeans clustering when sklearn is available, keyword grouping as fallback. "
            "Finds: common failure patterns, related error types, recurring problems. "
            "Returns clusters with size, success/failure counts, root causes, and sample traces."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["discover", "detail", "by_technology"],
                    "description": "'discover' finds problem clusters; 'detail' gets traces in a cluster; 'by_technology' groups by tech stack.",
                    "default": "discover",
                },
                "cluster_id": {
                    "type": "string",
                    "description": "Cluster ID for 'detail' action (e.g. 'cluster_0' or 'tech:python').",
                },
                "n_clusters": {
                    "type": "integer",
                    "description": "Target number of clusters for 'discover' (default: 8).",
                    "default": 8,
                },
                "min_trace_count": {
                    "type": "integer",
                    "description": "Minimum traces per cluster for 'discover' (default: 3).",
                    "default": 3,
                },
            },
            "required": ["action"],
        },
    },
]

# ---------------------------------------------------------------------------
# Server metadata
# ---------------------------------------------------------------------------

SERVER_INFO = {"name": "borg-mcp-server", "version": BORG_VERSION}

CAPABILITIES = {"tools": {}}

# ---------------------------------------------------------------------------
# Guild core imports (lazy to avoid circular imports)
# ---------------------------------------------------------------------------


def _get_core_modules():
    """Lazily import borg core modules to avoid import errors during testing."""
    from borg.core import uri as uri_module
    from borg.core import publish as publish_module
    from borg.core import session as session_module
    from borg.core import safety as safety_module
    from borg.core import schema as schema_module
    return uri_module, publish_module, session_module, safety_module, schema_module


# -------------------------------------------------------------------------
# V3 helper functions
# -------------------------------------------------------------------------

def _get_borg_v3():
    """Lazily get or create the BorgV3 instance using centralized Borg paths."""
    from borg.core.v3_integration import BorgV3

    return BorgV3()


def _extract_keywords(text: str) -> List[str]:
    """Extract lowercase words longer than 2 characters from text.

    Args:
        text: Input text to extract keywords from.

    Returns:
        List of lowercase keywords (words > 2 chars).
    """
    import re
    words = re.findall(r"\b\w+\b", text.lower())
    return [w for w in words if len(w) > 2]


# ---------------------------------------------------------------------------
# Tool implementations (wired to borg.core.*)
# ---------------------------------------------------------------------------

def borg_search(query: str = "", mode: str = "text", task_context: Dict[str, Any] = None) -> str:
    """Search for packs matching the query string.

    Args:
        query: Search query string.
        mode: Search mode - 'text', 'semantic', or 'hybrid'.
            Defaults to 'text'.
        task_context: Optional V3 task context dict with keys:
            - task_type (str): Type of task (e.g. 'debug', 'test', 'review')
            - keywords (list): List of keyword strings
            - agent_id (str, optional): Agent identifier
            When provided, uses the V3 contextual search path.
    """
    try:
        # V3 path: if task_context is provided, use BorgV3 search
        if task_context:
            v3 = _get_borg_v3()
            task_type = task_context.get("task_type", "")
            keywords = task_context.get("keywords", [])

            # Build a combined query from task_type and keywords
            search_terms = [task_type] + keywords if task_type else keywords
            combined_query = " ".join(search_terms) if search_terms else query

            results = v3.search(combined_query, task_context=task_context)

            # Format results to match expected MCP response format
            matches = []
            for r in results:
                match_item = {
                    "pack_id": r.get("pack_id", r.get("name", "")),
                    "name": r.get("name", ""),
                    "category": r.get("category", r.get("problem_class", "")),
                    "score": r.get("score", 0.0),
                }
                # Pass through A/B test info if present
                if r.get("ab_test"):
                    match_item["ab_test"] = r["ab_test"]
                matches.append(match_item)

            return json.dumps({
                "success": True,
                "contextual": True,
                "matches": matches,
                "query": combined_query,
            })

        # V2 path: standard search
        uri_module, _, _, _, _ = _get_core_modules()
        if not query:
            names = uri_module.get_available_pack_names()
            return json.dumps({"success": True, "packs": [{"name": n} for n in names], "total": len(names)})

        # Import search module with optional semantic support
        try:
            from borg.core import search as search_module
            result = search_module.borg_search(query, mode=mode)
            return result
        except ImportError:
            # Fall back to fuzzy match if search module unavailable
            pass

        # Fuzzy match fallback
        matches = uri_module.fuzzy_match_pack(query)
        packs = []
        for name in matches:
            packs.append({"name": name, "match": "fuzzy" if name != query else "exact"})
        return json.dumps({"success": True, "packs": packs, "total": len(packs), "query": query})
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e)})


def borg_pull(uri: str = "") -> str:
    """Fetch a pack from URI and save it locally."""
    try:
        uri_module, _, _, safety_module, schema_module = _get_core_modules()
        if not uri:
            return json.dumps({"success": False, "error": "URI cannot be empty"})

        # Resolve URI
        resolved = uri_module.resolve_guild_uri(uri)

        # Fetch content
        content, err = uri_module.fetch_with_retry(resolved)
        if err:
            return json.dumps({"success": False, "error": f"Failed to fetch: {err}"})

        # Validate YAML
        try:
            pack = schema_module.parse_workflow_pack(content)
        except ValueError as ve:
            return json.dumps({"success": False, "error": f"Invalid pack YAML: {ve}"})

        # Safety scan
        safety_issues = safety_module.scan_pack_safety(pack)

        # Save to local guild dir
        pack_name = pack.get("id", "unknown").replace("/", "-")
        from borg.core.dirs import get_borg_dir
        BORG_DIR = get_borg_dir()
        pack_dir = BORG_DIR / pack_name
        pack_dir.mkdir(parents=True, exist_ok=True)
        pack_file = pack_dir / "pack.yaml"
        pack_file.write_text(content, encoding="utf-8")

        return json.dumps({
            "success": True,
            "pack_name": pack_name,
            "pack_id": pack.get("id"),
            "problem_class": pack.get("problem_class"),
            "phase_count": len(pack.get("phases", [])),
            "safety_issues": safety_issues,
            "saved_to": str(pack_file),
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_try(uri: str = "") -> str:
    """Preview a pack without saving it."""
    try:
        uri_module, _, _, safety_module, schema_module = _get_core_modules()
        if not uri:
            return json.dumps({"success": False, "error": "URI cannot be empty"})

        # Resolve and fetch
        resolved = uri_module.resolve_guild_uri(uri)
        content, err = uri_module.fetch_with_retry(resolved)
        if err:
            return json.dumps({"success": False, "error": f"Failed to fetch: {err}"})

        # Parse
        try:
            pack = schema_module.parse_workflow_pack(content)
        except ValueError as ve:
            return json.dumps({"success": False, "error": f"Invalid pack YAML: {ve}"})

        # Safety scan
        safety_issues = safety_module.scan_pack_safety(pack)

        provenance = pack.get("provenance", {})
        return json.dumps({
            "success": True,
            "preview": True,
            "pack_id": pack.get("id"),
            "version": pack.get("version"),
            "problem_class": pack.get("problem_class"),
            "mental_model": pack.get("mental_model"),
            "trust_tier": provenance.get("confidence", "unknown"),
            "phase_count": len(pack.get("phases", [])),
            "phases": [
                {
                    "name": p.get("name", ""),
                    "description": p.get("description", ""),
                    "checkpoint": p.get("checkpoint", ""),
                }
                for p in pack.get("phases", [])
            ],
            "safety_issues": safety_issues,
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_init(pack_name: str = "", problem_class: str = "general", mental_model: str = "fast-thinker") -> str:
    """Scaffold a new pack in the local borg directory."""
    try:
        import yaml
        from datetime import datetime, timezone

        if not pack_name:
            return json.dumps({"success": False, "error": "pack_name is required"})

        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', pack_name):
            return json.dumps({"success": False, "error": f"pack_name must contain only letters, numbers, hyphens, underscores. Got: '{pack_name}'"})

        from borg.core.dirs import get_borg_dir
        BORG_DIR = get_borg_dir()
        pack_dir = BORG_DIR / pack_name
        pack_dir.mkdir(parents=True, exist_ok=True)

        scaffold = {
            "type": "workflow_pack",
            "version": "1.0",
            "id": pack_name,
            "problem_class": problem_class,
            "mental_model": mental_model,
            "provenance": {
                "author": "agent://init",
                "created": datetime.now(timezone.utc).isoformat(),
                "confidence": "guessed",
            },
            "phases": [
                {
                    "name": "phase-1",
                    "description": "Describe this phase",
                    "checkpoint": "done",
                    "anti_patterns": [],
                    "prompts": ["Describe the prompt for this phase"],
                },
            ],
        }
        content = yaml.safe_dump(scaffold, default_flow_style=False, sort_keys=False)
        pack_file = pack_dir / "pack.yaml"
        pack_file.write_text(content, encoding="utf-8")

        return json.dumps({
            "success": True,
            "pack_name": pack_name,
            "path": str(pack_file),
            "hint": "Edit pack.yaml to define phases and prompts",
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_apply(
    action: str = "",
    pack_name: str = "",
    task: str = "",
    session_id: str = "",
    phase_name: str = "",
    status: str = "",
    evidence: str = "",
    outcome: str = "",
    ab_test: dict = None,
) -> str:
    """Execute a borg pack with session tracking (start / checkpoint / complete)."""
    try:
        _, _, session_module, _, _ = _get_core_modules()

        if action == "start":
            if not pack_name or not task:
                return json.dumps({"success": False, "error": "pack_name and task are required for action=start"})

            # Load pack
            from borg.core.dirs import get_borg_dir
            BORG_DIR = get_borg_dir()
            pack_file = BORG_DIR / pack_name / "pack.yaml"
            if not pack_file.exists():
                return json.dumps({"success": False, "error": f"Pack not found: {pack_name}. Run guild_pull first."})

            import yaml
            pack_data = yaml.safe_load(pack_file.read_text(encoding="utf-8"))
            if not isinstance(pack_data, dict):
                return json.dumps({"success": False, "error": "Invalid pack file"})

            # Create session
            import uuid
            from datetime import datetime, timezone
            session_id = str(uuid.uuid4())[:8]

            # Set session context for thread-safe trace access before initializing trace
            _current_session_id.set(session_id)

            # Get agent_id from MCP initialize context (defaults to 'unknown')
            agent_id = _current_agent_id.get()

            # Initialize trace capture for this session
            init_trace_capture(session_id, task=task, agent_id=agent_id)

            phases = pack_data.get("phases", [])
            session: Dict[str, Any] = {
                "session_id": session_id,
                "pack_id": pack_data.get("id", pack_name),
                "pack_name": pack_name,
                "pack_version": pack_data.get("version", "unknown"),
                "task": task,
                "problem_class": pack_data.get("problem_class", ""),
                "phases": phases,
                "phase_index": 0,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "log_path": BORG_DIR / "executions" / f"{session_id}.jsonl",
                "execution_log_path": BORG_DIR / "executions" / f"{session_id}.jsonl",
                "events": [],
                "phase_results": [],
                "approved": False,
            }
            # Store A/B test variant selection if provided
            if ab_test:
                session["selected_variant"] = ab_test
            session_module.register_session(session)
            session_module.save_session(session)

            return json.dumps({
                "success": True,
                "session_id": session_id,
                "pack_name": pack_name,
                "phase_count": len(phases),
                "status": "active",
                "phases": [
                    {"index": i, "name": p.get("name", f"phase-{i}"), "description": p.get("description", "")}
                    for i, p in enumerate(phases)
                ],
                "hint": f"Use session_id={session_id} for checkpoint/complete",
            })

        elif action == "checkpoint":
            if not session_id or not phase_name:
                return json.dumps({"success": False, "error": "session_id and phase_name are required for action=checkpoint"})

            session = session_module.get_active_session(session_id)
            if not session:
                # Try loading from disk
                session = session_module.load_session(session_id)
                if not session:
                    return json.dumps({"success": False, "error": f"Session not found: {session_id}"})

            # Evaluate inject_if conditions for this phase
            inject_messages = []
            phases = session.get("phases", [])
            for p in phases:
                if isinstance(p, dict) and p.get("name") == phase_name:
                    from borg.core.conditions import evaluate_inject_conditions
                    # Build eval_context from the session's stored context if available
                    eval_context = session.get("eval_context", {})
                    inject_messages = evaluate_inject_conditions(p, eval_context)
                    break

            # Log event
            session_module.log_event(session_id, {
                "type": "checkpoint",
                "phase_name": phase_name,
                "status": status,
                "evidence": evidence,
            })

            # Update phase status in session
            for p in phases:
                if isinstance(p, dict) and p.get("name") == phase_name:
                    p["status"] = status
                    break

            session["phase_results"].append({"phase": phase_name, "status": status, "evidence": evidence})
            session_module.save_session(session)

            approved = session.get("approved", False)
            if phase_name == "__approval__" and status == "passed":
                approved = True
                session["approved"] = True
                session_module.save_session(session)

            response = {
                "success": True,
                "session_id": session_id,
                "phase_name": phase_name,
                "status": status,
                "approved": approved,
            }
            if inject_messages:
                response["inject_messages"] = inject_messages
            return json.dumps(response)

        elif action == "complete":
            if not session_id:
                return json.dumps({"success": False, "error": "session_id is required for action=complete"})

            session = session_module.get_active_session(session_id)
            if not session:
                session = session_module.load_session(session_id)
                if not session:
                    return json.dumps({"success": False, "error": f"Session not found: {session_id}"})

            session["status"] = "complete"
            session["outcome"] = outcome
            session_module.save_session(session)
            session_module.log_event(session_id, {"type": "complete", "outcome": outcome})

            return json.dumps({
                "success": True,
                "session_id": session_id,
                "status": "complete",
                "outcome": outcome,
                "phase_results": session.get("phase_results", []),
                "hint": "Use guild_feedback(session_id=...) to generate feedback",
            })

        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}. Use: start, checkpoint, complete"})

    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_publish(
    action: str = "list",
    path: str = "",
    pack_name: str = "",
    feedback_name: str = "",
    repo: str = "",
) -> str:
    """Publish or list guild artifacts."""
    try:
        _, publish_module, _, _, _ = _get_core_modules()

        if action == "list":
            return publish_module.action_list()

        elif action == "publish":
            return publish_module.action_publish(
                path=path,
                pack_name=pack_name,
                feedback_name=feedback_name,
                repo=repo,
            )

        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}. Use: list, publish"})

    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_feedback(
    session_id: str = "",
    what_changed: str = "",
    where_to_reuse: str = "",
    publish: bool = False,
    success: bool = None,
    tokens_used: int = 0,
    time_taken: float = 0.0,
    task_context: Dict[str, Any] = None,
) -> str:
    """Generate a feedback artifact for a completed session.

    1. Loads the execution session.
    2. Generates a structured feedback draft via generate_feedback().
    3. Saves the draft as a YAML file in ~/.hermes/guild/feedback/.
    4. Optionally publishes via action_publish.
    5. If task_context is provided, also records outcome to V3.

    Args:
        session_id: Session ID of the completed pack execution (required).
        what_changed: Brief description of what changed in this execution.
        where_to_reuse: Guidance on where this feedback can be reused.
        publish: If True, immediately publish the feedback via action_publish.
        success: Whether the pack execution was successful (V3 parameter).
        tokens_used: Number of tokens used in the execution (V3 parameter).
        time_taken: Time taken for the execution in seconds (V3 parameter).
        task_context: V3 task context dict for outcome recording (V3 parameter).
    """
    try:
        # Set session context for thread-safe trace access
        _current_session_id.set(session_id)

        # Finalize any active trace capture for this session
        session_id_from_ctx = _current_session_id.get()
        global _trace_captures
        with _trace_lock:
            capture = _trace_captures.get(session_id_from_ctx)
            if capture is not None:
                if capture.tool_calls > 5:
                    # TASK 2: Extract error-driven task_description from tool call outputs
                    import re
                    error_pattern = re.compile(
                        r'(\w+Error|\w+Exception|SyntaxError|TypeError|ValueError|ImportError|AttributeError)\s*[:\-]?\s*(.{10,60})',
                        re.IGNORECASE
                    )
                    task_description = ''
                    tool_calls = capture.calls
                    for call in tool_calls[-3:]:
                        output = str(call.get('result', ''))
                        match = error_pattern.search(output)
                        if match:
                            task_description = f"{match.group(1)}: {match.group(2)}"
                            break

                    # TASK 1: Infer outcome from last 3 tool call outputs
                    last_outputs = ' '.join(
                        str(c.get('result', '')).lower() for c in tool_calls[-3:]
                    )
                    success_signals = ['ok:', 'passed', 'success', '0 failed', 'done', 'fixed', 'test passed']
                    failure_signals = ['error:', 'traceback', 'exception', 'failed', 'fatal', 'assert']
                    has_success = any(s in last_outputs for s in success_signals)
                    has_failure = any(s in last_outputs for s in failure_signals)
                    if has_failure:
                        inferred_outcome = 'failure'
                    elif has_success:
                        inferred_outcome = 'success'
                    else:
                        inferred_outcome = 'unknown'

                    # TASK 2: Set error-driven task_description on capture before extraction
                    if task_description:
                        capture.task = task_description

                    trace = capture.extract_trace(
                        outcome=inferred_outcome,
                        root_cause=what_changed[:200] if what_changed else "",
                        approach_summary=where_to_reuse[:200] if where_to_reuse else ""
                    )
                    _save_trace_if_meaningful(trace)
                    del _trace_captures[session_id_from_ctx]

                    # Do not recursively call borg_feedback here: this block already runs
                    # inside _trace_lock, and recursion deadlocks on the same lock. V3 outcome
                    # recording happens below when task_context is supplied by the caller.

        import uuid
        import yaml
        from datetime import datetime, timezone
        from pathlib import Path

        _, publish_module, session_module, _, _ = _get_core_modules()
        from borg.core.search import generate_feedback

        if not session_id:
            return json.dumps({"success": False, "error": "session_id is required"})

        session = session_module.get_active_session(session_id)
        if not session:
            session = session_module.load_session(session_id)
            if not session:
                return json.dumps({"success": False, "error": f"Session not found: {session_id}"})

        # Collect execution log and compute hash
        log_path = Path(session.get("execution_log_path", ""))
        log_hash = session_module.compute_log_hash(log_path) if log_path else ""

        # Build execution_log from phase_results for generate_feedback
        execution_log = session.get("phase_results", [])
        pack_id = session.get("pack_id", session.get("pack_name", "unknown"))
        pack_version = session.get("pack_version", "1.0.0")
        task_description = session.get("task", session.get("problem_class", ""))
        outcome = session.get("outcome", "")

        # Generate the feedback using the core function
        feedback = generate_feedback(
            pack_id=pack_id,
            pack_version=pack_version,
            execution_log=execution_log,
            task_description=task_description,
            outcome=outcome,
            execution_log_hash=log_hash,
        )

        # Override/extend with caller-supplied context
        if what_changed:
            feedback["what_changed"] = what_changed
        if where_to_reuse:
            feedback["where_to_reuse"] = where_to_reuse

        # Add metadata
        feedback_id = f"fb-{uuid.uuid4().hex[:8]}"
        feedback["id"] = feedback_id
        feedback["problem_class"] = session.get("problem_class", "unknown")
        feedback["mental_model"] = session.get("mental_model", "unknown")
        feedback["provenance"]["author"] = "agent://feedback"
        feedback["provenance"]["created"] = datetime.now(timezone.utc).isoformat()

        # Compute stats
        passed = sum(1 for r in execution_log if r.get("status") == "passed")
        failed = sum(1 for r in execution_log if r.get("status") == "failed")
        feedback["stats"] = {
            "total_phases": len(execution_log),
            "passed": passed,
            "failed": failed,
        }

        # Save feedback as YAML
        from borg.core.dirs import get_borg_dir
        FEEDBACK_DIR = get_borg_dir() / "feedback"
        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        fb_file = FEEDBACK_DIR / f"{feedback_id}.yaml"
        fb_file.write_text(yaml.safe_dump(feedback, default_flow_style=False), encoding="utf-8")

        # Optionally publish
        publish_result = None
        if publish:
            publish_result = json.loads(
                publish_module.action_publish(
                    path=str(fb_file),
                    feedback_name=feedback_id,
                )
            )
            if not publish_result.get("success"):
                # Publication failed but draft is still saved
                publish_result["warning"] = "Draft saved but publication failed"

        # V3: record outcome if task_context is provided
        if task_context:
            try:
                v3 = _get_borg_v3()
                agent_id = task_context.get("agent_id")
                v3.record_outcome(
                    pack_id=pack_id,
                    task_context=task_context,
                    success=success if success is not None else (failed == 0),
                    tokens_used=tokens_used,
                    time_taken=time_taken,
                    agent_id=agent_id,
                    session_id=session_id,
                )
            except Exception:
                # Never let V3 recording break feedback generation
                pass

        # Close the trace feedback loop — record whether the shown trace helped
        _shown_trace = _last_shown_trace_id.get()
        if _shown_trace:
            try:
                from borg.core.trace_matcher import TraceMatcher
                _success_val = success if success is not None else True
                TraceMatcher().record_outcome(_shown_trace, helped=_success_val)
                logger.debug("Trace %s helpfulness recorded: %s", _shown_trace, _success_val)
            except Exception:
                pass
            _last_shown_trace_id.set(None)

        # Periodic maintenance: run every N invocations (counter persisted in V3 DB)
        try:
            v3 = _get_borg_v3()
            count = v3._inc_maintenance_counter()
            if count >= _MAINTENANCE_INTERVAL:
                v3._reset_maintenance_counter()
                maintenance_result = v3.run_maintenance()
                pass  # maintenance_result logged if logging configured
        except Exception:
            pass  # Never let maintenance break feedback

        return json.dumps({
            "success": True,
            "feedback_id": feedback_id,
            "path": str(fb_file),
            "feedback": feedback,
            "phase_results": execution_log,
            "stats": feedback["stats"],
            "published": publish if publish else None,
            "publish_result": publish_result,
            "hint": "Review the feedback draft above. Use guild_publish to refine and submit.",
        })

    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_dashboard() -> str:
    """Query the Borg V3 dashboard — aggregated stats from the V3 outcomes database.

    Returns total outcomes, success rates, quality scores per pack, drift alerts,
    mutation stats, and A/B test status.

    Returns:
        JSON string with dashboard stats.
    """
    try:
        v3 = _get_borg_v3()
        dash = v3.get_dashboard()
        return json.dumps({
            "success": True,
            **dash,
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_suggest(
    context: str = "",
    failure_count: int = 0,
    task_type_hint: str = "",
    tried_packs: Optional[List[str]] = None,
) -> str:
    """Auto-suggest a borg pack based on frustration signals and task context.

    Triggers when failure_count >= 2 or frustration keywords are detected.
    Searches borg packs by classified task terms and returns top matches.

    Args:
        context: Recent conversation context (messages, errors, task description).
        failure_count: Number of consecutive failed attempts (triggers at >= 2).
        task_type_hint: Optional explicit task type hint.
        tried_packs: Optional list of pack names already tried (excluded).
    """
    try:
        from borg.core.search import check_for_suggestion as _check_for_suggestion

        if not context:
            return json.dumps({"success": False, "error": "context required for borg_suggest"})

        # V3 path: when failure_count >= 2, use V3 contextual suggestion
        if failure_count >= 2:
            v3 = _get_borg_v3()
            # Extract keywords from context
            keywords = _extract_keywords(context)
            task_type = task_type_hint or (keywords[0] if keywords else "")

            task_context = {
                "task_type": task_type,
                "keywords": keywords,
            }

            results = v3.search(context, task_context=task_context)
            if results:
                top = results[0]
                return json.dumps({
                    "success": True,
                    "has_suggestion": True,
                    "contextual": True,
                    "suggestions": [{
                        "pack_id": top.get("pack_id", top.get("name", "")),
                        "name": top.get("name", ""),
                        "score": top.get("score", 0.0),
                        "reason": f"Based on your {task_type} context",
                    }],
                })

        result = _check_for_suggestion(
            conversation_context=context,
            failure_count=failure_count,
            task_type=task_type_hint,
            tried_packs=tried_packs or [],
        )
        try:
            parsed = json.loads(result)
            if not parsed.get("has_suggestion"):
                return json.dumps({"success": True, "has_suggestion": False, "suggestions": []})
            return json.dumps({"success": True, **parsed})
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"success": True, "has_suggestion": False, "suggestions": []})
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})



def _format_action_output(conf_header, worked, failed):
    """Format borg output: stop warning, action, confirmation, detail."""
    out = []
    # Stop warning - only if 2+ real failure traces
    if len(failed) >= 2:
        bad = next((t.get('approach_summary') or t.get('root_cause','') for t in failed if t.get('approach_summary') or t.get('root_cause')), None)
        if bad:
            out.append(f"STOP AVOID: {str(bad)[:100]}")
            out.append(f"  {len(failed)} agents tried this. Most failed.")
            out.append("")
    # Primary action
    if worked:
        action = worked[0].get('approach_summary') or worked[0].get('root_cause','')
        if action:
            out.append(f"ACTION: {str(action)[:120]}")
            out.append("")
    # Confirmation from header
    real_line = next((l for l in conf_header.split("\n") if "Real traces:" in l), "")
    conf_line = next((l for l in conf_header.split("\n") if "BORG [" in l), "")
    if conf_line:
        out.append(f"CONFIRMED: {real_line.strip()} | {conf_line.strip()}")
        out.append("")
    out.append("-- DETAIL --")
    out.append(conf_header)
    # Assemble final output
    full_output = "\n".join(out)

    # Short form: ACTION + CONFIDENCE only (~80 tokens) for pre_llm_call injection
    if short:
        action_line = next((l for l in out if l.startswith('ACTION:')), '')
        conf_line = next((l for l in out if l.startswith('CONFIDENCE:')), '')
        if action_line:
            return action_line[:120] + ('\n' + conf_line[:80] if conf_line else '')
        # Fallback: first 200 chars
        return full_output[:200]

    return full_output


def _maybe_rebuild_index():
    """Rebuild semantic index if traces DB is newer than index cache."""
    try:
        import os as _os
        from borg.core.dirs import get_embedding_index_path, get_trace_db_path
        db_path = str(get_trace_db_path())
        idx_path = str(get_embedding_index_path())
        if not _os.path.exists(idx_path):
            return  # Will be built on first semantic search
        db_mtime = _os.path.getmtime(db_path)
        idx_mtime = _os.path.getmtime(idx_path)
        if db_mtime > idx_mtime + 60:  # DB modified >60s after index
            import threading as _th
            from borg.core.embeddings import build_index_from_db
            from borg.core.traces import TRACE_DB_PATH
            def _rebuild():
                try:
                    build_index_from_db(TRACE_DB_PATH, force_rebuild=True)
                    logger.info('borg: index auto-rebuilt')
                except Exception as _e:
                    logger.debug('borg: index rebuild failed: %s', _e)
            _th.Thread(target=_rebuild, daemon=True).start()
    except Exception:
        pass

def _no_confident_match_response(tech: str = "") -> str:
    return _confidence_gate.no_confident_match_response(tech)


def _trace_match_is_confident(trace: dict, min_similarity: float = 0.45, query: str = "") -> bool:
    return _confidence_gate.trace_match_is_confident(trace, min_similarity=min_similarity, query=query)


def _trace_db_path() -> str:
    """Return the trace database path using the same source of truth as traces.py."""
    return str(get_trace_db_path())


def _extract_verify_from_trace(trace: dict) -> str:
    """Produce a deterministic verification step from a matched trace."""
    if not isinstance(trace, dict):
        return "rerun the exact failing command and the smallest regression test"
    files_modified = trace.get("files_modified") or trace.get("key_files") or ""
    if isinstance(files_modified, list) and files_modified:
        return f"rerun the failing command and inspect changed file {files_modified[0]}"
    if isinstance(files_modified, str) and files_modified.strip() and files_modified.strip() != "[]":
        return "rerun the failing command and verify the touched files still match the fix"
    errors = trace.get("errors_encountered") or trace.get("error_patterns") or ""
    if errors:
        return "rerun the exact command that produced the matched error pattern"
    return "rerun the exact failing command and the smallest regression test"


def _pack_match_is_confident(query: str, pack: dict) -> bool:
    return _confidence_gate.pack_match_is_confident(query, pack)


def _strip_embedded_borg_guidance(message: str) -> str:
    return _confidence_gate.strip_embedded_borg_guidance(message)


def _normalize_query_for_matching(message: str) -> str:
    return _confidence_gate.normalize_query_for_matching(message)


def _permission_guidance_matches_task(task: str, context: str = "") -> bool:
    return _confidence_gate.permission_guidance_matches_task(task, context)


def _guidance_is_safe_to_inject(guidance: str, task: str, context: str = "") -> bool:
    return _confidence_gate.guidance_is_safe_to_inject(guidance, task, context)


def borg_rescue(input: str = "", source: str = "mcp", show_guidance: bool = True) -> str:
    """Return an agent-ready day-one rescue packet as JSON."""
    try:
        from borg.core.rescue import rescue

        result = rescue(input, source=source or "mcp", show_guidance=bool(show_guidance))
        return json.dumps(result.to_dict(), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def error_lookup(input: str = "", source: str = "mcp", show_guidance: bool = True) -> str:
    """Plain-English MCP alias for :func:`borg_rescue`.

    First users search for an "error lookup" tool before they know Borg's
    internal naming.  Keep the alias behaviorally identical to borg_rescue so
    docs, MCP discovery, and agent priming all point to one rescue contract.
    """
    return borg_rescue(input=input, source=source or "mcp", show_guidance=show_guidance)


def borg_first_10() -> str:
    """Return the first-10 beta readiness contract as JSON."""
    try:
        from borg.core.first_user_readiness import first_10_readiness_packet
        return json.dumps(first_10_readiness_packet(), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_runtime_fingerprint() -> str:
    """Return exact loaded runtime paths/hashes plus a confidence-gate canary."""
    try:
        from borg.core.runtime_fingerprint import runtime_fingerprint_json
        return runtime_fingerprint_json()
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_observe(task: str = "", context: str = "", context_dict: dict = None, project_path: str = None, short: bool = False) -> str:
    _maybe_rebuild_index()
    # Auto-seed collective traces on first use
    try:
        from borg.core.seed_loader import ensure_seeded
        ensure_seeded()
    except Exception:
        pass
    """Silent observation: return structured guidance for a task if a relevant pack exists.

    Returns a string with:
    - BORG [confidence] header with real/synthetic trace counts
    - SYNTHESIS: 2-3 sentence mentor paragraph (on-demand LLM)
    - DETAIL: WHAT WORKED, WHAT FAILED, PACK GUIDANCE

    Returns empty string only if no guidance found at all.
    """
    _last_shown_trace_id.set(None)
    output_parts = []
    has_guidance = False
    query = f"{task} {context}".strip()

    # Preserve the historical observe contract: classify exactly the raw task
    # once. Call through the imported module object so monkeypatches still work,
    # without executing imports while import-error tests patch builtins.__import__.
    try:
        _classified_terms = _search_module.classify_task(task)
    except Exception:
        _classified_terms = []

    # Detect technology for confidence stats
    tech = _detect_technology(task, context)

    # ---- Build detail text (raw bullets) first ----
    raw_detail_parts = []

    # Positive traces (semantic search first, then keyword fallback)
    positive_traces = []
    try:
        from borg.core.embeddings import semantic_search
        from borg.core.traces import TRACE_DB_PATH
        # --- HYBRID: embedding + BM25 with RRF ---
        from borg.core.bm25_index import get_bm25_index, rrf_fusion
        embedding_results = semantic_search(
            query=query, db_path=TRACE_DB_PATH,
            top_k=10, min_similarity=0.3, outcome_filter="success"
        )
        try:
            bm25_idx = get_bm25_index(str(TRACE_DB_PATH))
            bm25_results = bm25_idx.search(query, top_k=10)
        except Exception:
            bm25_results = []
        if embedding_results and bm25_results:
            emb_pairs = [(t.get("id",""),t.get("similarity",0)) for t in embedding_results]
            fused = rrf_fusion(emb_pairs, bm25_results)
            fused_ids = [d for d,_ in fused[:3]]
            positive_traces = [t for t in embedding_results if t.get("id","") in fused_ids][:3]
            if not positive_traces:
                positive_traces = embedding_results[:3]
        elif embedding_results:
            positive_traces = embedding_results[:3]
        else:
            positive_traces = []
    except Exception:
        pass
    if not positive_traces:
        try:
            positive_traces = _trace_matcher_module.TraceMatcher().find_relevant(task=task, error=context, top_k=3)
        except Exception:
            pass

    # Fail closed on explicit low-confidence semantic trace hits before any
    # rendering path can turn them into ACTION/WHAT WORKED guidance.
    positive_traces = [t for t in (positive_traces or []) if _trace_match_is_confident(t, query=query)]

    #  Dead-end intent override
    # If agent explicitly mentions a known dead-end in their query,
    # force a STOP warning as the lead result regardless of semantic rank
    try:
        _dead_ends_detected = _detect_dead_end_intent(task)
    except NameError:
        _dead_ends_detected = []
    if _dead_ends_detected:
        try:
            from borg.core.retrieval import semantic_search as _ss
            for _de in _dead_ends_detected:
                _stop_hits = _ss(
                    query=_de['keyword'] + ' permission denied',
                    db_path=TRACE_DB_PATH, top_k=5,
                    min_similarity=0.2, outcome_filter='failure'
                )
                if _stop_hits:
                    # Found a matching STOP trace  add it to front of positive_traces
                    # so it appears in the "WHAT FAILED" section prominently
                    _stop_t = _stop_hits[0]
                    _stop_t['_forced_stop'] = True
                    positive_traces = [_stop_t] + positive_traces
                    break
        except Exception:
            pass

    if positive_traces:
        best = positive_traces[0]
        trace_id = best.get('id', '')
        if trace_id:
            _last_shown_trace_id.set(trace_id)
            try:
                _trace_matcher_module.TraceMatcher().record_shown(trace_id)
            except Exception:
                pass
        section = [f"WHAT WORKED ({len(positive_traces)} prior session{'s' if len(positive_traces)>1 else ''})"]
        if best.get('root_cause', '').strip():
            section.append(f"   Root cause: {best['root_cause'][:300]}")
        if best.get('approach_summary', '').strip():
            section.append(f"   Approach: {best['approach_summary'][:300]}")
        causal = best.get('causal_intervention', '')
        if causal:
            section.append(f"   → What fixed it: {causal}")
        tool_seq = best.get('tool_sequence', [])
        if isinstance(tool_seq, str):
            try:
                tool_seq = json.loads(tool_seq)
            except Exception:
                tool_seq = []
        if tool_seq:
            section.append(f"   Tool sequence: {' → '.join(tool_seq[:4])}")
        sim = best.get('similarity', 0)
        if sim > 0:
            section.append(f"   Confidence: {sim:.0%} semantic match")
        raw_detail_parts.append('\n'.join(section))
        has_guidance = True

    # Negative traces
    try:
        dead_ends = _negative_traces_module.get_dead_end_patterns(task=task, error=context)
        if dead_ends.get('dead_ends'):
            section = [f"WHAT FAILED ({dead_ends['total_failure_sessions']} prior sessions)"]
            section.append("   Skip these approaches:")
            for de in dead_ends['dead_ends']:
                section.append(f"   • {de['count']} agent{'s' if de['count']>1 else ''} tried: {de['approach'][:150]}")
                if de.get('root_cause'):
                    section.append(f"     Why it failed: {de['root_cause'][:100]}")
            raw_detail_parts.append('\n'.join(section))
            has_guidance = True
    except Exception as e:
        logger.debug(f"borg_observe: negative traces failed: {e}")

    # Pack guidance
    try:
        try:
            _raw_search = _search_module.borg_search(task[:100], mode="text")
        except TypeError:
            # Backward-compatible for tests/plugins monkeypatching borg_search
            # with the older one-arg signature.
            _raw_search = _search_module.borg_search(task[:100])
        search_result = json.loads(_raw_search)
        pack_matches_all = [m for m in search_result.get('matches', []) if m.get('type') == 'pack' or m.get('source') == 'seed']
        # Filter packs to same technology domain  avoid cross-domain contamination
        pack_matches = [m for m in pack_matches_all if not tech or
                       tech in str(m.get('technology', '')).lower() or
                       tech in str(m.get('name', '')).lower() or
                       tech in str(m.get('solution', '')).lower()[:100]]
        # Do not fall back to all packs when the domain filter eliminates them:
        # that is exactly how unrelated seed guidance leaked into observe.
        pack_matches = [m for m in pack_matches if _pack_match_is_confident(query, m)]
        if pack_matches:
            best_pack = pack_matches[0]
            solution = best_pack.get('solution', '').strip()
            if solution:
                section = [f"PACK GUIDANCE ({best_pack.get('name', 'unknown')})"]
                section.append(solution[:400])
                raw_detail_parts.append('\n'.join(section))
                has_guidance = True
    except Exception as e:
        logger.debug(f"borg_observe: pack guidance failed: {e}")

    if not has_guidance:
        return _no_confident_match_response(tech)

    # ---- Build confidence header ----
    raw_detail_text = '\n'.join(raw_detail_parts)
    header = _build_confidence_header(tech, task)

    # ---- Attempt LLM synthesis ----
    synthesis = None
    try:
        from borg.core.synthesis import synthesise
        synthesis = synthesise(raw_detail_text)
    except Exception as e:
        logger.debug(f"synthesis integration error: {e}")

    # ---- Assemble final response  action-first ----
    divider = "-" * 60
    out = []

    # 1. BEST ACTION  most important, goes first
    if positive_traces:
        _best = positive_traces[0]
        _action = (
            _best.get('causal_intervention') or
            _best.get('approach_summary') or
            _best.get('root_cause') or ''
        ).strip()
        # SQL fallback if semantic search returned empty fields
        if not _action and tech:
            try:
                import sqlite3 as _sq2
                _db3 = _sq2.connect(_trace_db_path())
                _row = _db3.execute(
                    "SELECT causal_intervention, approach_summary, root_cause FROM traces "
                    "WHERE technology=? AND outcome IN ('success','fixed','partial') "
                    "AND (causal_intervention!='' OR approach_summary!='' OR root_cause!='') "
                    "AND (source IS NULL OR source NOT IN ('seed_pack','e2e_test')) "
                    "ORDER BY helpfulness_score DESC LIMIT 1", (tech,)).fetchone()
                _db3.close()
                if _row:
                    _action = (_row[0] or _row[1] or _row[2] or '').strip()
            except Exception:
                pass
        if _action:
            out.append(f"ACTION: {_action[:150]}")
            out.append("")
    elif locals().get('pack_matches'):
        # Synthetic/seed-only guidance still needs the first-user contract to be
        # action-first.  Keep it explicitly tied to the matched pack so it is not
        # mistaken for real-trace evidence.
        _pack_solution = (pack_matches[0].get('solution') or '').strip()
        _pack_first_step = next((ln.strip() for ln in _pack_solution.splitlines() if ln.strip()), '')
        if _pack_first_step:
            out.append(f"ACTION: from matched seed pack, {_pack_first_step[:120]}")
            out.append("")

    # 2. VERIFY  always present for first-user contract
    pack_matches_available = bool(locals().get('pack_matches'))
    if positive_traces:
        _verify = _extract_verify_from_trace(positive_traces[0])
    elif pack_matches_available:
        _verify = "execute the pack's first checkpoint, then rerun the exact failing command"
    else:
        _verify = "rerun the exact failing command and the smallest regression test"
    out.append(f"VERIFY: {_verify[:150]}")
    out.append("")

    # 3. STOP WARNING  only real failure patterns
    try:
        import sqlite3 as _sq
        _db2 = _sq.connect(_trace_db_path())
        _fails = _db2.execute(
            "SELECT approach_summary, root_cause FROM traces "
            "WHERE technology=? AND outcome='failure' "
            "AND (source IS NULL OR source NOT IN ('seed_pack','e2e_test')) "
            "AND (approach_summary IS NOT NULL OR root_cause IS NOT NULL) LIMIT 3",
            (tech,)).fetchall()
        _db2.close()
        if len(_fails) >= 2:
            _bad = next((_r[0] or _r[1] for _r in _fails if _r[0] or _r[1]), None)
            if _bad:
                out.append(f"STOP  {len(_fails)} agents tried this approach and failed:")
                out.append(f"  {str(_bad)[:120]}")
                out.append("")
    except Exception:
        pass
    if locals().get('pack_matches') and not any(l.startswith('STOP') or l.startswith('AVOID') for l in out):
        _pack_name = str(pack_matches[0].get('name') or '').lower()
        if 'permission' in _pack_name:
            out.append("STOP: do not use chmod 777 or blanket sudo; identify the exact file, owner, and minimum required permission.")
        else:
            out.append("STOP: do not force unrelated fixes; follow the matched pack checkpoint and verify against the exact failing command.")
        out.append("")

    # 3. CONFIDENCE signal
    _conf_line = next((l for l in header.split("\n") if "BORG [" in l), "")
    _real_line = next((l for l in header.split("\n") if "Real traces:" in l), "")
    if _conf_line:
        out.append(f"CONFIDENCE: {_real_line.strip()} | {_conf_line.strip()}")
        out.append("")
        # 2b. Surface dead_ends from matched traces
        try:
            _de_items = []
            for _pt in (positive_traces[:3] + (embedding_results[:10] if embedding_results else [])):
                _de_raw = _pt.get("dead_ends", "[]") if isinstance(_pt, dict) else ""
                if _de_raw and _de_raw != "[]":
                    try:
                        _de_list = json.loads(_de_raw) if isinstance(_de_raw, str) else (_de_raw or [])
                    except Exception:
                        _de_list = []
                    for _d in _de_list:
                        if _d and str(_d).strip():
                            _de_items.append(str(_d).strip())
            if _de_items:
                out.append("AVOID: " + "; ".join(_de_items))
                out.append("")
        except Exception:
            pass

    # 4. Full detail
    out.append(divider)
    if synthesis:
        out.extend(["SYNTHESIS", synthesis, divider, "DETAIL", raw_detail_text])
    else:
        out.append(raw_detail_text)
    out.append(divider)

    #  Deterministic STOP injection (correct location)
    _HARD = {
        r'sudo\s+npm': 'STOP: sudo npm creates root-owned node_modules, breaks ALL future npm. Fix: npm config set prefix ~/.npm-global',
        r'sudo\s+pip': 'STOP: sudo pip damages system Python. Use venv or pip install --user instead.',
        r'--no-cache\b': 'STOP: --no-cache skips package sources, cannot fix package-not-found. Run apt-get update in a separate layer.',
        r'\bas\s+any\b|cast.*\bany\b': 'STOP: Casting to any hides the error. Fix the actual type mismatch instead.',
        r'chmod\s+777': 'STOP: chmod 777 is a security hole. Identify the actual user/group needing access.',
    }
    _joined = "\n".join(out)
    _tl = task.lower()
    if 'STOP' not in _joined and 'AVOID' not in _joined:
        for _p, _msg in _HARD.items():
            if re.search(_p, _tl):
                _joined = _msg + '\n' + ''*50 + '\n' + _joined
                break
    return _joined



def borg_rate(helpful: bool, trace_id: str = None, comment: str = "") -> str:
    """
    Rate the most recent Borg guidance. Call this after attempting the suggested fix.
    helpful=True if it worked, False if it didn't.
    This improves Borg confidence scoring over time.
    """
    import sqlite3 as _sql
    from borg.core.dirs import get_trace_db_path
    from datetime import datetime as _dt
    try:
        _db_path = str(get_trace_db_path())
        _db = _sql.connect(_db_path)

        # Get the most recently shown trace
        if trace_id:
            _tid = trace_id
        else:
            _tid = _last_shown_trace_id.get()  # ContextVar  set by borg_observe
        if _tid:
            if helpful:
                _db.execute("UPDATE traces SET helpfulness_score = MIN(1.0, helpfulness_score + 0.05), times_helped = times_helped + 1 WHERE id=?", (_tid,))
            else:
                _db.execute("UPDATE traces SET helpfulness_score = MAX(0.0, helpfulness_score - 0.05), times_shown = times_shown + 1 WHERE id=?", (_tid,))
            _db.commit()
            _db.close()
            status = "worked" if helpful else "didn't work"
            return f"BORG: Feedback recorded  guidance {status}. Score updated for trace {_tid[:8]}."
        else:
            # Rate by technology if no specific trace
            _db.close()
            return "BORG: No recent trace to rate. Call borg_observe first."
    except Exception as _e:
        return f"BORG: Rate error: {_e}"

def _detect_technology(task: str, context: str) -> str:
    """Infer the primary technology domain from active task + context text."""
    text = _normalize_query_for_matching(f"{task} {context}").lower()
    tech_map = {
        'django': ['django', 'django.db', 'makemigrations', 'migrate'],
        'python': ['python', 'pip', 'venv', 'virtualenv'],
        'typescript': ['typescript', 'ts error', 'tsc', 'tsconfig', '.ts file', 'cannot find module', 'type script', 'argument of type', 'not assignable to type'],
    'nodejs': ['node.js', 'nodejs', 'npm err', 'eacces', 'node_modules', 'require(', 'module not found'],
        'javascript': ['javascript', 'typescript', 'node', 'npm', 'js', 'ts'],
        'rust': ['rust', 'cargo', 'borrow checker', 'lifetime'],
        'docker': ['docker', 'container', 'dockerfile', 'docker-compose'],
        'git': ['git', 'commit', 'branch', 'merge'],
        'postgres': ['postgresql', 'postgres', 'psql'],
        'mysql': ['mysql', 'mariadb'],
        'auth': ['jwt', 'oauth', 'auth', 'token', 'session'],
        'ci': ['github actions', 'gitlab ci', 'workflow', 'yaml'],
        'fastapi': ['fastapi', 'fast api', 'starlette', 'uvicorn', 'pydantic', '422 unprocessable'],
        'typescript': ['typescript', 'ts error', 'tsc', 'tsconfig', '.ts file', 'type error', 'cannot find module', 'type script'],
        'nodejs': ['node.js', 'nodejs', 'npm err', 'eacces', 'node_modules', 'require(', 'module not found', 'package.json'],
        'github-actions': ['github actions', 'github action', 'workflow yaml', '.github/workflows', 'actions/'],
        'docker': ['docker', 'dockerfile', 'docker build', 'container', 'docker-compose', 'apt-get', 'unable to locate package'],
        'rust': ['rust', 'cargo', 'rustc', 'borrow checker', 'lifetime', 'ownership', 'borrowing'],
    }
    for tech, keywords in tech_map.items():
        for kw in keywords:
            if re.search(r"[a-z0-9]", kw) and len(kw) <= 4:
                if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text):
                    return tech
            elif kw in text:
                return tech
    return ''


def _build_confidence_header(tech: str, task: str) -> str:
    """Build the BORG confidence header with real/synthetic trace stats."""
    from datetime import datetime, timezone
    import sqlite3 as _sqlite3, os as _os

    # Guard: empty tech = SYNTHETIC ONLY, do not query all traces
    if not tech or not tech.strip():
        return "BORG [SYNTHETIC ONLY]\nReal traces: 0 | Synthetic: 0\nNo domain detected.\n" + "\u2500" * 50

    try:
        db_path = _trace_db_path()
        _db = _sqlite3.connect(db_path)
        _db.row_factory = _sqlite3.Row
        _stats = _db.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN source IS NULL OR source NOT IN ('seed', 'seed_pack', 'e2e_test', 'hermy-bootstrap') THEN 1 ELSE 0 END) as real_count,
                ROUND(AVG(helpfulness_score), 2) as avg_helpfulness,
                MAX(created_at) as most_recent
            FROM traces
            WHERE technology = ?
                OR technology = CASE WHEN ? = 'javascript' THEN 'typescript'
                                     WHEN ? = 'typescript' THEN 'javascript'
                                     ELSE NULL END
                OR keywords LIKE ?
        """, (tech, tech, tech, f'%{tech}%')).fetchone()
        _db.close()
    except Exception:
        return f"BORG [UNKNOWN]\nReal traces: 0 | Synthetic: 0\n" + "\u2500" * 50

    total = _stats[0] if _stats else 0
    real_count = _stats[1] if _stats else 0
    avg_help = _stats[2] if _stats else 0.0
    most_recent = _stats[3] if _stats else None
    synthetic_count = max(0, total - (real_count or 0))

    # Recency
    recency_note = ""
    if most_recent:
        try:
            ts = datetime.fromisoformat(most_recent.replace('Z', '+00:00'))
            days_ago = (datetime.now(timezone.utc) - ts).days
            recency_note = f"Most recent: {days_ago}d ago"
        except Exception:
            pass

    # Confidence label
    if (real_count or 0) == 0:
        label = "SYNTHETIC ONLY"
        note = "No real agent sessions -- guidance is from seed packs, unverified"
    elif (real_count or 0) < 3:
        label = "LOW CONFIDENCE"
        note = f"Only {real_count} real agent session(s) -- treat as preliminary"
    elif (real_count or 0) < 10:
        label = "MODERATE CONFIDENCE"
        note = f"{real_count} real sessions, avg helpfulness {avg_help}"
    else:
        label = "HIGH CONFIDENCE"
        note = f"{real_count} real sessions, avg helpfulness {avg_help}"

    return (
        f"BORG [{label}]\n"
        f"Real traces: {real_count or 0} | Synthetic: {synthetic_count} | {recency_note}\n"
        f"{note}\n"
        + "\u2500" * 50
    )

def borg_context(project_path: str = ".", hours: int = 24) -> str:
    """Detect recent git changes in a project directory.

    Args:
        project_path: Path to the git repository. Defaults to '.'.
        hours: Look for changes in the last N hours. Defaults to 24.

    Returns:
        JSON string with recent files, uncommitted changes, and last commits.
    """
    try:
        from borg.core.changes import detect_recent_changes

        result = detect_recent_changes(project_path=project_path, hours=hours)
        return json.dumps({
            "success": True,
            **result,
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_recall(error_message: str = "", agent_id: str = "default") -> str:
    """Recall failure memory for an error.

    Returns approaches that other agents tried and failed, as well as
    approaches that succeeded. If no matching memory is found, returns null.

    Args:
        error_message: The error message to look up in failure memory.
        agent_id:     Agent namespace to search. Defaults to "default".

    Returns:
        JSON string with wrong_approaches (sorted by frequency) and
        correct_approaches (sorted by frequency), or null if no match.
    """
    try:
        from borg.core.failure_memory import FailureMemory

        if not error_message:
            return json.dumps({"success": False, "error": "error_message is required"})

        fm = FailureMemory()
        result = fm.recall(error_message, agent_id=agent_id)

        if result is None:
            return json.dumps({
                "success": True,
                "found": False,
                "wrong_approaches": [],
                "correct_approaches": [],
                "total_sessions": 0,
            })

        return json.dumps({
            "success": True,
            "found": True,
            "error_pattern": result.get("error_pattern", ""),
            "agent_id": result.get("agent_id", agent_id),
            "wrong_approaches": result.get("wrong_approaches", []),
            "correct_approaches": result.get("correct_approaches", []),
            "total_sessions": result.get("total_sessions", 0),
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_record_failure(
    error_pattern: str = "",
    pack_id: str = "",
    phase: str = "",
    approach: str = "",
    outcome: str = "",
    agent_id: str = "default",
) -> str:
    """Record a failure or success outcome for an error pattern.

    Writes to the failure memory store so other agents can benefit from the learning.
    Call this after attempting a fix — record 'success' if it worked, 'failure' if not.

    Args:
        error_pattern: The error message or pattern encountered.
        pack_id:      The borg pack being used (e.g. 'systematic-debugging').
        phase:        The phase being executed when the error occurred.
        approach:    What the agent tried to fix the error.
        outcome:     Either 'success' or 'failure'.
        agent_id:    Agent namespace to write to. Defaults to 'default'.

    Returns:
        JSON string with success=True and the recorded entry, or success=False on error.
    """
    try:
        from borg.core.failure_memory import FailureMemory

        if not error_pattern:
            return json.dumps({"success": False, "error": "error_pattern is required"})

        fm = FailureMemory()
        fm.record_failure(
            error_pattern=error_pattern,
            pack_id=pack_id,
            phase=phase,
            approach=approach,
            outcome=outcome,
            agent_id=agent_id,
        )
        return json.dumps({
            "success": True,
            "recorded": True,
            "error_pattern": error_pattern,
            "agent_id": agent_id,
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e), "type": "ValueError"})
    except (KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_delete_failure(error_pattern: str = "", agent_id: str = "default") -> str:
    """Delete a failure memory record for an error pattern.

    Use this to retract wrong entries or clear test data.

    Args:
        error_pattern: The error pattern whose record should be deleted.
        agent_id:     Agent namespace to delete from. Defaults to 'default'.

    Returns:
        JSON string: {"success": True, "deleted": True} if found and deleted,
        {"success": True, "deleted": False} if not found,
        or {"success": False, "error": ...} on error.
    """
    try:
        from borg.core.failure_memory import FailureMemory

        if not error_pattern:
            return json.dumps({"success": False, "error": "error_pattern is required"})

        fm = FailureMemory()
        deleted = fm.delete(error_pattern=error_pattern, agent_id=agent_id)
        return json.dumps({
            "success": True,
            "deleted": deleted,
            "error_pattern": error_pattern,
            "agent_id": agent_id,
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_reputation(action: str = "", agent_id: str = None, pack_id: str = None) -> str:
    """Query agent reputation and trust information.

    Args:
        action: The action to perform - 'get_profile', 'get_pack_trust', or 'get_free_rider_status'.
        agent_id: Agent ID to query (for get_profile and get_free_rider_status).
        pack_id: Pack ID to query (for get_pack_trust).

    Returns:
        JSON string with reputation data for the specified agent or pack.
    """
    try:
        from borg.db.reputation import ReputationEngine, AccessTier, FreeRiderStatus
        from borg.db.store import AgentStore

        if AgentStore is None:
            return json.dumps({"success": False, "error": "AgentStore not available"})

        if action == "get_profile":
            if not agent_id:
                return json.dumps({"success": False, "error": "agent_id is required for get_profile action"})
            try:
                store = AgentStore()
                engine = ReputationEngine(store)
                profile = engine.build_profile(agent_id)
                store.close()
                return json.dumps({
                    "success": True,
                    "agent_id": profile.agent_id,
                    "contribution_score": profile.contribution_score,
                    "access_tier": profile.access_tier.value,
                    "free_rider_status": profile.free_rider_status.value,
                    "peak_score": profile.peak_score,
                    "last_active_at": profile.last_active_at.isoformat() if profile.last_active_at else None,
                    "packs_published": profile.packs_published,
                    "quality_reviews_given": profile.quality_reviews_given,
                    "bug_reports_filed": profile.bug_reports_filed,
                    "documentation_contributions": profile.documentation_contributions,
                    "governance_votes_cast": profile.governance_votes_cast,
                    "packs_consumed": profile.packs_consumed,
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        elif action == "get_pack_trust":
            if not pack_id:
                return json.dumps({"success": False, "error": "pack_id is required for get_pack_trust action"})
            try:
                store = AgentStore()
                pack_data = store.get_pack(pack_id)
                store.close()
                if pack_data is None:
                    return json.dumps({"success": False, "error": f"Pack not found: {pack_id}"})
                return json.dumps({
                    "success": True,
                    "pack_id": pack_id,
                    "confidence": pack_data.get("confidence", "unknown"),
                    "adoption_count": pack_data.get("adoption_count", 0),
                    "last_validated": pack_data.get("last_validated"),
                    "tier": pack_data.get("tier", "unknown"),
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        elif action == "get_free_rider_status":
            if not agent_id:
                return json.dumps({"success": False, "error": "agent_id is required for get_free_rider_status action"})
            try:
                store = AgentStore()
                engine = ReputationEngine(store)
                profile = engine.build_profile(agent_id)
                store.close()
                return json.dumps({
                    "success": True,
                    "agent_id": profile.agent_id,
                    "free_rider_score": profile.free_rider_score,
                    "free_rider_status": profile.free_rider_status.value,
                    "packs_consumed": profile.packs_consumed,
                    "packs_published": profile.packs_published,
                    "quality_reviews_given": profile.quality_reviews_given,
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}. Use get_profile, get_pack_trust, or get_free_rider_status."})

    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_analytics(
    action: str = "",
    pack_id: str = None,
    metric: str = None,
    period: str = "daily",
    days: int = 30,
) -> str:
    """Query ecosystem health metrics and analytics from the AnalyticsEngine.

    Args:
        action: The action to perform - 'ecosystem_health', 'pack_usage', 'adoption', or 'timeseries'.
        pack_id: Pack ID to query (for pack_usage and adoption actions).
        metric: Metric name for timeseries action: 'pack_publishes', 'executions', 'avg_quality_score', or 'active_agents'.
        period: Time period for timeseries: 'daily', 'weekly', or 'monthly'. Defaults to 'daily'.
        days: Number of days to look back for timeseries. Defaults to 30.

    Returns:
        JSON string with analytics data for the specified action.
    """
    try:
        from borg.db.analytics import AnalyticsEngine
        from borg.db.store import AgentStore

        if AgentStore is None:
            return json.dumps({"success": False, "error": "AgentStore not available"})

        if action == "ecosystem_health":
            try:
                store = AgentStore()
                engine = AnalyticsEngine(store)
                health = engine.ecosystem_health()
                store.close()
                return json.dumps({
                    "success": True,
                    "total_agents": health.total_agents,
                    "active_contributors": health.active_contributors,
                    "active_consumers": health.active_consumers,
                    "contributor_ratio": health.contributor_ratio,
                    "avg_quality_score": health.avg_quality_score,
                    "avg_quality_trend": health.avg_quality_trend,
                    "domain_coverage": health.domain_coverage,
                    "total_packs": health.total_packs,
                    "tier_distribution": health.tier_distribution,
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        elif action == "pack_usage":
            if not pack_id:
                return json.dumps({"success": False, "error": "pack_id is required for pack_usage action"})
            try:
                store = AgentStore()
                engine = AnalyticsEngine(store)
                stats = engine.pack_usage_stats(pack_id)
                store.close()
                return json.dumps({
                    "success": True,
                    "pack_id": stats.pack_id,
                    "pull_count": stats.pull_count,
                    "apply_count": stats.apply_count,
                    "success_count": stats.success_count,
                    "failure_count": stats.failure_count,
                    "completion_rate": stats.completion_rate,
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        elif action == "adoption":
            if not pack_id:
                try:
                    store = AgentStore()
                    engine = AnalyticsEngine(store)
                    metrics = engine.ecosystem_adoption()
                    store.close()
                    return json.dumps({
                        "success": True,
                        "pack_id": None,
                        "unique_agents": metrics.unique_agents,
                        "unique_operators": metrics.unique_operators,
                    })
                except Exception as e:
                    return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})
            else:
                try:
                    store = AgentStore()
                    engine = AnalyticsEngine(store)
                    metrics = engine.adoption_metrics(pack_id)
                    store.close()
                    return json.dumps({
                        "success": True,
                        "pack_id": metrics.pack_id,
                        "unique_agents": metrics.unique_agents,
                        "unique_operators": metrics.unique_operators,
                    })
                except Exception as e:
                    return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        elif action == "timeseries":
            if not metric:
                return json.dumps({"success": False, "error": "metric is required for timeseries action"})
            try:
                store = AgentStore()
                engine = AnalyticsEngine(store)
                result = engine.timeseries(metric, period=period, days=days)
                store.close()
                return json.dumps({
                    "success": True,
                    "metric": result.metric,
                    "period": result.period,
                    "points": [
                        {
                            "timestamp": p.timestamp,
                            "period": p.period,
                            "metric": p.metric,
                            "value": p.value,
                            "label": p.label,
                        }
                        for p in result.points
                    ],
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}. Use ecosystem_health, pack_usage, adoption, or timeseries."})

    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_dojo(action: str = "", days: int = 7, report_format: str = "telegram") -> str:
    """Borg Dojo — training improvement pipeline via MCP.

    Args:
        action: The action to perform - 'analyze', 'report', 'history', or 'status'.
        days: Number of days to look back for analysis (default: 7).
        report_format: Format for 'report' action - 'cli', 'telegram', or 'discord'.

    Returns:
        JSON string with analysis results, report, history, or health status.
    """
    try:
        import time as _time
        from borg.dojo.pipeline import DojoPipeline, analyze_recent_sessions, get_cached_analysis
        from borg.dojo.learning_curve import LearningCurveTracker

        if action == "analyze":
            try:
                analysis = analyze_recent_sessions(days=days)
                return json.dumps({
                    "success": True,
                    "action": "analyze",
                    "days": days,
                    "schema_version": analysis.schema_version,
                    "sessions_analyzed": analysis.sessions_analyzed,
                    "total_tool_calls": analysis.total_tool_calls,
                    "total_errors": analysis.total_errors,
                    "overall_success_rate": analysis.overall_success_rate,
                    "user_corrections": analysis.user_corrections,
                    "skill_gaps_count": len(analysis.skill_gaps),
                    "weakest_tools": [
                        {
                            "tool_name": t.tool_name,
                            "failed_calls": t.failed_calls,
                            "success_rate": t.success_rate,
                            "top_error_category": t.top_error_category,
                        }
                        for t in (analysis.weakest_tools or [])[:5]
                    ],
                    "failure_reports": [
                        {
                            "tool_name": f.tool_name,
                            "error_category": f.error_category,
                            "error_snippet": f.error_snippet,
                            "session_id": f.session_id,
                            "timestamp": f.timestamp,
                            "confidence": f.confidence,
                        }
                        for f in (analysis.failure_reports or [])[:10]
                    ],
                })
            except FileNotFoundError:
                return json.dumps({"success": False, "error": "state.db not found. Is hermes running?"})
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        elif action == "report":
            try:
                pipeline = DojoPipeline()
                report = pipeline.run(days=days, auto_fix=False, report_fmt=report_format)
                return json.dumps({
                    "success": True,
                    "action": "report",
                    "format": report_format,
                    "report": report,
                })
            except FileNotFoundError:
                return json.dumps({"success": False, "error": "state.db not found. Is hermes running?"})
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        elif action == "history":
            try:
                tracker = LearningCurveTracker()
                snapshots = tracker.load_history()
                return json.dumps({
                    "success": True,
                    "action": "history",
                    "snapshot_count": len(snapshots),
                    "snapshots": [s.to_dict() for s in (snapshots or [])[-30:]],
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        elif action == "status":
            try:
                analysis = get_cached_analysis()
                if analysis is None:
                    try:
                        analysis = analyze_recent_sessions(days=min(days, 7))
                    except FileNotFoundError:
                        return json.dumps({"success": False, "error": "state.db not found. Is hermes running?"})
                    except Exception:
                        pass

                if analysis is None:
                    return json.dumps({
                        "success": True,
                        "action": "status",
                        "health": "unknown",
                        "message": "No analysis available. Run 'analyze' first.",
                    })

                health = "healthy"
                if analysis.overall_success_rate < 70:
                    health = "degraded"
                if analysis.overall_success_rate < 50:
                    health = "unhealthy"

                return json.dumps({
                    "success": True,
                    "action": "status",
                    "health": health,
                    "sessions_analyzed": analysis.sessions_analyzed,
                    "total_tool_calls": analysis.total_tool_calls,
                    "total_errors": analysis.total_errors,
                    "overall_success_rate": analysis.overall_success_rate,
                    "user_corrections": analysis.user_corrections,
                    "skill_gaps_count": len(analysis.skill_gaps),
                    "weakest_tools": [
                        {"tool_name": t.tool_name, "failed_calls": t.failed_calls}
                        for t in (analysis.weakest_tools or [])[:3]
                    ],
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})

        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}. Use: analyze, report, history, status."})

    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_convert(path: str = "", format: str = "auto", output_dir: str = "") -> str:
    """Convert a SKILL.md, CLAUDE.md, or .cursorrules file into a workflow pack.

    Args:
        path: Path to the source file.
        format: Source format - 'auto' (detect from filename), 'skill', 'claude', 'cursorrules', or 'openclaw'.
        output_dir: Output directory for OpenClaw conversion.
    """
    try:
        import yaml
        import pathlib
        from borg.core import convert as convert_module

        # Handle OpenClaw format (registry-wide conversion)
        if format == "openclaw":
            from borg.core.convert import convert_registry_to_openclaw

            # Collect all packs from the registry
            packs = []

            # Try to load from local guild dir
            from borg.core.dirs import get_borg_dir
            guild_dir = get_borg_dir()

            if guild_dir.exists():
                for pack_yaml in guild_dir.glob("*/pack.yaml"):
                    try:
                        pack_data = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
                        if isinstance(pack_data, dict):
                            packs.append(pack_data)
                    except Exception:
                        continue

            # Also try to load from the guild-packs directory
            guild_packs_dir = pathlib.Path("/root/hermes-workspace/guild-packs/packs")
            if guild_packs_dir.exists():
                for pack_file in guild_packs_dir.glob("*.yaml"):
                    try:
                        pack_data = yaml.safe_load(pack_file.read_text(encoding="utf-8"))
                        if isinstance(pack_data, dict):
                            # Avoid duplicates
                            pack_id = pack_data.get("id", "")
                            if not any(p.get("id") == pack_id for p in packs):
                                packs.append(pack_data)
                    except Exception:
                        continue

            # Fallback: return error if no packs found
            if not packs:
                return json.dumps({
                    "success": False,
                    "error": "No packs found in registry. Ensure packs are installed under BORG_HOME/guild or /root/hermes-workspace/guild-packs/packs/"
                })

            # Convert to OpenClaw
            out_dir = output_dir or "./openclaw-skills"
            result = convert_registry_to_openclaw(packs, out_dir)

            return json.dumps({
                "success": True,
                "pack_count": result["pack_count"],
                "output_dir": result["output_dir"],
                "files_written": result["files_written"],
                "skill_md_lines": result["skill_md_lines"],
                "pack_slugs": result["pack_slugs"],
            })

        # Handle individual file conversion
        if not path:
            return json.dumps({"success": False, "error": "path is required for non-openclaw formats"})

        # Call the appropriate converter based on format
        if format == "auto":
            pack = convert_module.convert_auto(path)
        elif format == "skill":
            pack = convert_module.convert_skill(path)
        elif format == "claude":
            pack = convert_module.convert_claude_md(path)
        elif format == "cursorrules":
            pack = convert_module.convert_cursorrules(path)
        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown format: {format}. Use: auto, skill, claude, cursorrules, openclaw"
            })

        # Dump pack to YAML
        content = yaml.safe_dump(pack, default_flow_style=False, sort_keys=False)

        return json.dumps({
            "success": True,
            "content": content,
            "pack": pack,
        })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def _borg_generate_handler(pack: str = "", format: str = "cursorrules") -> str:
    """Generate platform-specific rules files from a borg workflow pack.

    Args:
        pack: Pack name (e.g. 'systematic-debugging').
        format: Output format - 'cursorrules', 'clinerules', 'claude-md', 'windsurfrules', 'all'.
    """
    try:
        from borg.core.generator import generate_rules, load_pack, FORMAT_FILENAMES

        if not pack:
            return json.dumps({"success": False, "error": "pack name is required"})

        try:
            pack_data = load_pack(pack)
        except FileNotFoundError as e:
            return json.dumps({"success": False, "error": str(e)})

        result = generate_rules(pack_data, format=format)

        if isinstance(result, dict):
            # 'all' format returns dict of {format: content}
            files = {}
            for fmt, content in result.items():
                files[FORMAT_FILENAMES[fmt]] = content
            return json.dumps({
                "success": True,
                "pack": pack,
                "format": "all",
                "files": files,
            })
        else:
            filename = FORMAT_FILENAMES.get(format, format)
            return json.dumps({
                "success": True,
                "pack": pack,
                "format": format,
                "filename": filename,
                "content": result,
            })
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


# -------------------------------------------------------------------------
# Timeout configuration (seconds)
# -------------------------------------------------------------------------

TOOL_TIMEOUT_SEC = 30


def _timeout_handler(signum, frame):
    """Called when a tool call exceeds TOOL_TIMEOUT_SEC."""
    raise TimeoutError(f"Tool call exceeded {TOOL_TIMEOUT_SEC}s timeout")


# -------------------------------------------------------------------------
# Tool dispatch
# -------------------------------------------------------------------------

def call_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Dispatch a tool call to the appropriate guild function. Returns JSON string.

    All code paths return a JSON string (never raises). Tool execution is
    protected by a timeout to prevent hangs and rate limiting.
    """
    # Check rate limit first
    if not _check_rate_limit():
        return json.dumps({
            "success": False,
            "error": "Rate limit exceeded: maximum 60 requests per minute",
            "type": "RateLimitError"
        })

    try:
        # Try SIGALRM timeout first (main thread only)
        if hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread():
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(TOOL_TIMEOUT_SEC)
            use_signal_timeout = True
        else:
            use_signal_timeout = False

        try:
            result = _call_tool_impl(name, arguments)
        finally:
            if use_signal_timeout:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        # Feed tool call into trace capture (skip borg internal tools to avoid noise)
        if name not in ("borg_search", "borg_observe", "borg_rescue", "error_lookup", "borg_suggest", "borg_feedback", "borg_publish"):
            _feed_trace_capture(name, arguments, result)

        return result

    except TimeoutError as e:
        return json.dumps({"success": False, "error": str(e), "type": "TimeoutError"})
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def _call_tool_impl(name: str, arguments: Dict[str, Any]) -> str:
    """Inner implementation of call_tool — may raise exceptions (caught by call_tool)."""
    if name == "borg_search":
        return borg_search(
            query=arguments.get("query", ""),
            mode=arguments.get("mode", "text"),
            task_context=arguments.get("task_context"),
        )

    elif name == "borg_pull":
        return borg_pull(uri=arguments.get("uri", ""))

    elif name == "borg_try":
        return borg_try(uri=arguments.get("uri", ""))

    elif name == "borg_init":
        return borg_init(
            pack_name=arguments.get("pack_name", ""),
            problem_class=arguments.get("problem_class", "general"),
            mental_model=arguments.get("mental_model", "fast-thinker"),
        )

    elif name == "borg_apply":
        return borg_apply(
            action=arguments.get("action", ""),
            pack_name=arguments.get("pack_name", ""),
            task=arguments.get("task", ""),
            session_id=arguments.get("session_id", ""),
            phase_name=arguments.get("phase_name", ""),
            status=arguments.get("status", ""),
            evidence=arguments.get("evidence", ""),
            outcome=arguments.get("outcome", ""),
        )

    elif name == "borg_publish":
        return borg_publish(
            action=arguments.get("action", "publish"),
            path=arguments.get("path", ""),
            pack_name=arguments.get("pack_name", ""),
            feedback_name=arguments.get("feedback_name", ""),
            repo=arguments.get("repo", ""),
        )

    elif name == "borg_feedback":
        return borg_feedback(
            session_id=arguments.get("session_id", ""),
            what_changed=arguments.get("what_changed", ""),
            where_to_reuse=arguments.get("where_to_reuse", ""),
            success=arguments.get("success"),
            tokens_used=arguments.get("tokens_used", 0),
            time_taken=arguments.get("time_taken", 0.0),
            task_context=arguments.get("task_context"),
        )

    elif name == "borg_suggest":
        return borg_suggest(
            context=arguments.get("context", ""),
            failure_count=arguments.get("failure_count", 0),
            task_type_hint=arguments.get("task_type_hint", ""),
            tried_packs=arguments.get("tried_packs"),
        )

    elif name in ("borg_rescue", "error_lookup"):
        return borg_rescue(
            input=arguments.get("input", ""),
            source=arguments.get("source", "mcp"),
            show_guidance=arguments.get("show_guidance", True),
        )

    elif name == "borg_first_10":
        return borg_first_10()

    elif name == "borg_runtime_fingerprint":
        return borg_runtime_fingerprint()

    elif name == "borg_convert":
        return borg_convert(
            path=arguments.get("path", ""),
            format=arguments.get("format", "auto"),
            output_dir=arguments.get("output_dir"),
        )

    elif name == "borg_generate":
        return _borg_generate_handler(
            pack=arguments.get("pack", ""),
            format=arguments.get("format", "cursorrules"),
        )

    elif name == "borg_context":
        return borg_context(
            project_path=arguments.get("project_path", "."),
            hours=arguments.get("hours", 24),
        )

    elif name == "borg_recall":
        return borg_recall(
            error_message=arguments.get("error_message", ""),
            agent_id=arguments.get("agent_id", "default"),
        )

    elif name == "borg_record_failure":
        return borg_record_failure(
            error_pattern=arguments.get("error_pattern", ""),
            pack_id=arguments.get("pack_id", ""),
            phase=arguments.get("phase", ""),
            approach=arguments.get("approach", ""),
            outcome=arguments.get("outcome", ""),
            agent_id=arguments.get("agent_id", "default"),
        )

    elif name == "borg_delete_failure":
        return borg_delete_failure(
            error_pattern=arguments.get("error_pattern", ""),
            agent_id=arguments.get("agent_id", "default"),
        )

    elif name == "borg_reputation":
        return borg_reputation(
            action=arguments.get("action", ""),
            agent_id=arguments.get("agent_id"),
            pack_id=arguments.get("pack_id"),
        )

    elif name == "borg_analytics":
        return borg_analytics(
            action=arguments.get("action", ""),
            pack_id=arguments.get("pack_id"),
            metric=arguments.get("metric"),
            period=arguments.get("period", "daily"),
            days=arguments.get("days", 30),
        )

    elif name == "borg_dojo":
        return borg_dojo(
            action=arguments.get("action", ""),
            days=arguments.get("days", 7),
            report_format=arguments.get("report_format", "telegram"),
        )

    elif name == "borg_clusters":
        from borg.core.clustering import discover_clusters, get_cluster_detail, get_technology_clusters
        action = arguments.get("action", "discover")
        if action == "discover":
            result = discover_clusters(
                n_clusters=arguments.get("n_clusters", 8),
                min_trace_count=arguments.get("min_trace_count", 3),
            )
        elif action == "detail":
            result = get_cluster_detail(cluster_id=arguments.get("cluster_id", ""))
        elif action == "by_technology":
            result = get_technology_clusters()
        else:
            result = {"error": f"Unknown action: {action}"}
        return json.dumps({"success": True, "result": result})

    elif name == "borg_observe":
        return borg_observe(
            task=arguments.get("task", ""),
            context=arguments.get("context", ""),
            context_dict=arguments.get("context_dict"),
            project_path=arguments.get("project_path"),
        )

    elif name == "borg_dashboard":
        return borg_dashboard()

    else:
        return json.dumps({"success": False, "error": f"Unknown tool: {name}"})


# ---------------------------------------------------------------------------
# JSON-RPC response helpers
# ---------------------------------------------------------------------------

def make_response(id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    """Build a JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": id, "result": result}


def make_error(id: Any, code: int, message: str) -> Dict[str, Any]:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# Stdio transport helpers
# ---------------------------------------------------------------------------

def _to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8")


def _read_bytes(stream: Any, length: int) -> bytes:
    data = stream.read(length)
    return data if isinstance(data, bytes) else str(data).encode("utf-8")


def _iter_stdio_messages(stream: Any = None):
    """Yield ``(payload, framed)`` messages from stdio.

    Supports both legacy newline-delimited JSON-RPC and standard MCP
    ``Content-Length: N\r\n\r\n<body>`` framing. Borg historically emitted one
    JSON object per line; keeping that path preserves compatibility with older
    wrappers while allowing strict MCP clients to use the standard transport.
    """
    if stream is None:
        stream = getattr(sys.stdin, "buffer", sys.stdin)

    while True:
        line = stream.readline()
        if not line:
            break
        first = _to_bytes(line)
        if not first.strip():
            continue

        if not first.lower().startswith(b"content-length:"):
            yield first.strip().decode("utf-8"), False
            continue

        headers = [first.rstrip(b"\r\n")]
        while True:
            header_line = stream.readline()
            if not header_line:
                yield "", True
                break
            header = _to_bytes(header_line)
            if header in (b"\r\n", b"\n", b""):
                break
            headers.append(header.rstrip(b"\r\n"))
        else:  # pragma: no cover - loop cannot naturally fall through
            continue

        length = None
        for header in headers:
            name, _, value = header.partition(b":")
            if name.strip().lower() == b"content-length":
                try:
                    length = int(value.strip())
                except ValueError:
                    length = -1
                break

        if length is None or length < 0:
            yield "", True
            continue

        body = _read_bytes(stream, length)
        if len(body) != length:
            yield "", True
            continue
        yield body.decode("utf-8"), True


def _write_stdio_response(response: Dict[str, Any], *, framed: bool, output: Any = None) -> None:
    """Write a JSON-RPC response using the same framing as the request."""
    body = json.dumps(response, separators=(",", ":")).encode("utf-8")
    if framed:
        payload = b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
        stream: Any = output if output is not None else getattr(sys.stdout, "buffer", sys.stdout)
    else:
        payload = body + b"\n"
        stream = output if output is not None else getattr(sys.stdout, "buffer", sys.stdout)

    try:
        stream.write(payload)
    except TypeError:
        stream.write(payload.decode("utf-8"))
    stream.flush()


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle a single JSON-RPC request and return the response (or None for notifications)."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        # Extract agent_id from params if provided
        agent_id = params.get("agent_id", "unknown")
        _current_agent_id.set(agent_id)
        return make_response(req_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": SERVER_INFO,
            "capabilities": CAPABILITIES,
        })

    elif method == "notifications/initialized":
        # Client notification — no response needed
        return None

    elif method == "tools/list":
        return make_response(req_id, {"tools": TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result_text = call_tool(tool_name, arguments)

        # Parse result to determine isError
        try:
            parsed = json.loads(result_text)
            is_error = parsed.get("success") is False or "error" in parsed
        except (json.JSONDecodeError, TypeError):
            is_error = False

        return make_response(req_id, {
            "content": [{"type": "text", "text": result_text}],
            "isError": is_error,
        })

    elif method == "ping":
        return make_response(req_id, {})

    else:
        # Unknown method — error response for requests, None for notifications
        if req_id is not None:
            return make_error(req_id, -32601, f"Method not found: {method}")
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server on stdio. Supports MCP framed and newline JSON-RPC."""
    # Cold start — runs once on first install
    try:
        from borg.core.cold_start import run_if_needed
        run_if_needed()
    except Exception:
        pass  # never block startup

    from borg import __version__
    print(f"borg-mcp-server v{__version__} ready (stdio transport)", file=sys.stderr, flush=True)
    for payload, framed in _iter_stdio_messages():
        try:
            request = json.loads(payload)
        except json.JSONDecodeError as e:
            response = make_error(None, -32700, f"Parse error: {e}")
            _write_stdio_response(response, framed=framed)
            continue

        response = handle_request(request)
        if response is not None:
            _write_stdio_response(response, framed=framed)


# Short-form wrapper  guarantees short=True returns concise output
_borg_observe_orig = borg_observe
def borg_observe(task: str = "", context: str = "", context_dict: dict = None, project_path: str = None, short: bool = False) -> str:
    """Wrapper: inject deterministic hard-stops for known-bad task patterns,
    then optionally reduce to short-form ACTION+CONFIDENCE."""
    result = _borg_observe_orig(task=task, context=context, context_dict=context_dict, project_path=project_path, short=short)

    #  Deterministic dead-end STOP injection
    # These rules override semantic ranking  known anti-patterns
    # that ALWAYS fail, regardless of what positive traces say
    _HARD_STOPS = {
        r'sudo\s+npm': "STOP: sudo npm creates root-owned node_modules breaking ALL future npm. NEVER use sudo with npm.",
        r'sudo\s+pip': "STOP: sudo pip damages system Python. Use venv or pip install --user instead.",
        r'--no-cache\b': "STOP: --no-cache skips source lists  won't fix 'unable to locate package'. Run apt-get update separately.",
        r'\bas any\b|cast.*\bany\b': "STOP: Casting to any destroys type safety. Fix the actual type mismatch.",
        r'chmod\s+777': "STOP: chmod 777 is a security risk. Find the actual user/group needing access.",
    }
    _task_l = task.lower()
    for _pat, _stop_msg in _HARD_STOPS.items():
        if re.search(_pat, _task_l) and 'STOP' not in result and 'AVOID' not in result:
            result = _stop_msg + '\n' + '-'*50 + '\n' + result
            break

    if not _guidance_is_safe_to_inject(result, task, context):
        result = _no_confident_match_response(_detect_technology(task, context))

    if not short:
        return result

    lines = result.split("\n")
    stop_line = next((l for l in lines if l.startswith("STOP:")), "")
    if stop_line:
        return stop_line[:200]
    action = next((l for l in lines if l.startswith("ACTION:")), "")
    conf = next((l for l in lines if l.startswith("CONFIDENCE:")), "")
    if action:
        return action[:120] + ("\n" + conf[:80] if conf else "")
    return result[:200]


if __name__ == "__main__":
    main()
