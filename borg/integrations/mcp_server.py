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
import os
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Suppress default logging (MCP uses stdout for JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

from borg.core.traces import TraceCapture, save_trace

# Thread-safe session tracking via contextvars
_current_session_id: contextvars.ContextVar[str] = contextvars.ContextVar('session_id', default='')
_current_agent_id: contextvars.ContextVar[str] = contextvars.ContextVar('agent_id', default='unknown')

# Global trace captures — one per session_id
_trace_captures: Dict[str, TraceCapture] = {}

_MAINTENANCE_INTERVAL: int = 10  # Run maintenance every N feedback calls


def init_trace_capture(session_id: str, task: str = "", agent_id: str = ""):
    """Initialize trace capture for a session."""
    global _trace_captures
    _trace_captures[session_id] = TraceCapture(task=task, agent_id=agent_id)


def _feed_trace_capture(tool_name: str, args: Dict[str, Any], result: str):
    """Accumulate a tool call into the active trace capture for the current session."""
    session_id = _current_session_id.get()
    if not session_id:
        return  # No active session
    global _trace_captures
    capture = _trace_captures.get(session_id)
    if capture is None:
        return  # No active capture for this session
    capture.on_tool_call(tool_name, args, result)

    # Auto-save at 45 calls (before agent wastes more tokens)
    if capture.tool_calls >= 45:
        if capture.task:  # Only save if we have a task
            trace = capture.extract_trace(outcome="auto_truncated")
            if trace["tool_calls"] > 5:
                save_trace(trace)
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
                    "description": "Target GitHub repo (defaults to bensargotest-sys/guild-packs)",
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
        "name": "borg_observe",
        "description": (
            "Silent observation: analyzes the current task and returns structural guidance from proven approaches. "
            "Call this at the start of any task to get battle-tested strategies. "
            "Returns specific phase-by-phase guidance if a relevant pack exists, or general best practices if not. "
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
            "Auto-detects format from filename or allows explicit format specification."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the source file (SKILL.md, CLAUDE.md, or .cursorrules).",
                },
                "format": {
                    "type": "string",
                    "enum": ["auto", "skill", "claude", "cursorrules"],
                    "description": "Format of the source file. 'auto' detects from filename.",
                    "default": "auto",
                },
            },
            "required": ["path"],
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
            "Recall collective failure memory for an error. Returns approaches that other agents "
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
            },
            "required": ["error_message"],
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
]

# ---------------------------------------------------------------------------
# Server metadata
# ---------------------------------------------------------------------------

SERVER_INFO = {"name": "borg-mcp-server", "version": "1.0.0"}

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
    """Lazily get or create the BorgV3 singleton instance."""
    from borg.core.v3_integration import BorgV3

    BORG_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "borg"
    BORG_DIR.mkdir(parents=True, exist_ok=True)
    db_path = str(BORG_DIR / "borg_v3.db")
    return BorgV3(db_path=db_path)


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
        BORG_DIR = Path.home() / ".hermes" / "guild"
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

        BORG_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "guild"
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
            BORG_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "guild"
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
        capture = _trace_captures.get(session_id_from_ctx)
        if capture is not None:
            if capture.tool_calls > 5:
                trace = capture.extract_trace(
                    outcome="success",
                    root_cause=what_changed[:200] if what_changed else "",
                    approach_summary=where_to_reuse[:200] if where_to_reuse else ""
                )
                save_trace(trace)
            del _trace_captures[session_id_from_ctx]

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
                return json.dumps({"success": False, "error": "Session not found: {session_id}"})

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
        FEEDBACK_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "guild" / "feedback"
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

        # Periodic maintenance: run every N invocations (counter persisted in V3 DB)
        try:
            v3 = _get_borg_v3()
            count = v3._inc_maintenance_counter()
            if count >= _MAINTENANCE_INTERVAL:
                v3._reset_maintenance_counter()
                maintenance_result = v3.run_maintenance()
                logger.debug(f"Periodic maintenance: {maintenance_result}")
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
            return "{}"

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


def borg_observe(task: str = "", context: str = "", context_dict: dict = None, project_path: str = None) -> str:
    """Silent observation: return structural guidance for a task if a relevant pack exists.

    Uses classify_task to extract keywords from the task description, then searches
    borg packs using text mode (no embeddings needed). Returns a concise phase-by-phase
    guide when a relevant pack is found. Returns empty string if no relevant pack found.

    Args:
        task: Task description (required).
        context: Optional additional context (environment, language, constraints).
        context_dict: Optional runtime context dict for conditional phase evaluation.
            Keys: error_message (str), error_type (str), attempts (int),
            has_recent_changes (bool), error_in_test (bool).
        project_path: Optional path to the project for change awareness.
            If provided and context contains an error, cross-references the error
            with recently changed files.

    Returns:
        A concise structural guide string, or empty string if no relevant pack found.
    """
    try:
        if not task:
            return ""

        # Normalize context_dict
        eval_context = context_dict or {}

        # Import classify_task here to avoid circular imports and to allow
        # the function to work even if the search module changes
        try:
            from borg.core.search import classify_task, borg_search as _core_search
        except ImportError:
            return ""

        # Extract search keywords from task description
        # e.g. "fix TypeError in auth module" -> ["debug"]
        # e.g. "pytest tests failing" -> ["test"]
        search_terms = classify_task(task)
        if not search_terms:
            # Fallback keywords for common task types
            search_terms = ["debug"]

        # ITEM 3.3: Use V3 search path when context_dict provides rich error context.
        # This properly forwards error_type to classify_task for better task classification.
        all_matches = []
        if context_dict and isinstance(context_dict, dict) and (context_dict.get("error_type") or context_dict.get("error_message")):
            try:
                v3 = _get_borg_v3()
                keywords = _extract_keywords(task) if task else []
                task_type = search_terms[0] if search_terms else ""
                task_context = {
                    "task_type": task_type,
                    "keywords": keywords,
                    "error_type": context_dict.get("error_type", ""),
                    "error_message": context_dict.get("error_message", ""),
                    "attempts": context_dict.get("attempts", 0),
                }
                v3_results = v3.search(task, task_context=task_context)
                if v3_results:
                    all_matches = v3_results
            except Exception:
                pass  # Fall back to V2 search below

        # V2 search fallback (or if no rich context available)
        if not all_matches:
            for term in search_terms:
                search_result = _core_search(term, mode="text")
                try:
                    parsed = json.loads(search_result)
                    if parsed.get("success") and parsed.get("matches"):
                        all_matches.extend(parsed["matches"])
                except (json.JSONDecodeError, TypeError):
                    continue

        if not all_matches:
            return ""

        # Deduplicate by name, preferring higher confidence
        seen_names: set = set()
        unique_matches: list = []
        for match in all_matches:
            name = match.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                unique_matches.append(match)

        if not unique_matches:
            return ""

        # Pick the best match (prefer "tested" confidence, then any non-none tier)
        best_match = None
        for match in unique_matches:
            tier = match.get("tier", "unknown")
            confidence = match.get("confidence", "")
            if tier not in ("none", "") and best_match is None:
                best_match = match
            if confidence == "tested" and best_match is not match:
                # Prefer tested packs
                best_match = match

        if best_match is None:
            return ""

        pack_name = best_match.get("name", best_match.get("id", ""))

        # ---------------------------------------------------------------------
        # 1. FIND THE BEST LOCAL PACK: Scan ALL local packs for the richest
        # match. Prefer packs with start_signals and conditions over plain ones.
        # This overrides the search result if a better local pack exists.
        # ---------------------------------------------------------------------
        import yaml
        HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
        guild_dir = HERMES_HOME / "guild"
        pack_name = best_match.get("name", "")
        
        full_pack = None
        best_pack_score = -1
        if guild_dir.exists():
            for pack_yaml in guild_dir.glob("*/pack.yaml"):
                try:
                    candidate = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
                    if not isinstance(candidate, dict):
                        continue
                    candidate_id = candidate.get("id", "")
                    candidate_name = candidate_id.split("/")[-1]
                    problem_class_str = str(candidate.get("problem_class", "")).lower()
                    dir_name = pack_yaml.parent.name.lower()
                    
                    # Score: does this pack match the search terms?
                    score = 0
                    matched = False
                    for term in search_terms:
                        term_l = term.lower()
                        if term_l in candidate_name or term_l in dir_name or term_l in problem_class_str:
                            matched = True
                            score += 10
                    
                    # Bonus: packs with start_signals and conditions are richer
                    if candidate.get("start_signals"):
                        score += 20  # strongly prefer packs with signals
                    if any(p.get("skip_if") for p in candidate.get("phases", []) if isinstance(p, dict)):
                        score += 10
                    # Prefer clean dir names
                    if "guild:--" not in dir_name and "converted" not in dir_name:
                        score += 5
                    
                    if matched and score > best_pack_score:
                        full_pack = candidate
                        best_pack_score = score
                        pack_name = candidate_name or pack_yaml.parent.name
                except Exception:
                    continue

        # Use local pack data if available, otherwise fall back to search metadata
        if full_pack and isinstance(full_pack, dict):
            problem_class = full_pack.get("problem_class", best_match.get("problem_class", ""))
            phases_data = full_pack.get("phases", best_match.get("phases", []))
            anti_patterns = full_pack.get("anti_patterns", best_match.get("anti_patterns", []))
            checkpoint = full_pack.get("checkpoint", best_match.get("checkpoint", ""))
            start_signals = full_pack.get("start_signals", [])
            # Prefer local pack confidence if available
            local_confidence = full_pack.get("provenance", {}).get("confidence") if full_pack.get("provenance") else None
            confidence = local_confidence or best_match.get("confidence", "unknown")
        else:
            problem_class = best_match.get("problem_class", "")
            phases_data = best_match.get("phases", [])
            anti_patterns = best_match.get("anti_patterns", [])
            checkpoint = best_match.get("checkpoint", "")
            start_signals = best_match.get("start_signals", [])
            confidence = best_match.get("confidence", "unknown")

        # Build condensed guide with human-visible attribution
        lines = []
        lines.append(f"🧠 Borg found a proven approach: **{pack_name}** (confidence: {confidence})")
        lines.append(f"This approach has been tested across multiple agents. Telling the user:")
        lines.append(f"\"Using a community-proven {confidence} approach for this type of task.\"")
        lines.append("")
        lines.append(f"For this type of task, follow this structure:")

        # Check for matching start signals based on error context
        if start_signals and context:
            from borg.core.signals import match_start_signal
            matched_signal = match_start_signal(start_signals, context)
            if matched_signal:
                start_here = matched_signal.get("start_here", [])
                avoid = matched_signal.get("avoid", [])
                reasoning = matched_signal.get("reasoning", "")
                if start_here:
                    lines.append("")
                    lines.append(f"🎯 Start here: {', '.join(start_here)}")
                if avoid:
                    lines.append(f"⚠️ Avoid: {', '.join(avoid)}")
                if reasoning:
                    lines.append(f"Why: {reasoning}")

        # Check failure memory and add collective intelligence warnings
        if context:
            try:
                from borg.core.failure_memory import FailureMemory
                fm = FailureMemory()
                memory = fm.recall(context)
                if memory and (memory.get("wrong_approaches") or memory.get("correct_approaches")):
                    lines.append("")
                    wrong = memory.get("wrong_approaches", [])
                    correct = memory.get("correct_approaches", [])
                    if wrong:
                        top_wrong = wrong[0]
                        lines.append(
                            f"⚠️ Other agents tried: {top_wrong.get('approach', 'unknown')} "
                            f"and failed ({top_wrong.get('failure_count', 0)} times). "
                            f"Try a different approach."
                        )
                    if correct:
                        top_correct = correct[0]
                        lines.append(
                            f"✅ Instead, try: {top_correct.get('approach', 'unknown')} "
                            f"(succeeded {top_correct.get('success_count', 0)} times)."
                        )
            except Exception:
                # Never let failure memory break observe
                pass

        if phases_data:
            lines.append("Phases:")
            if isinstance(phases_data, list):
                for i, phase in enumerate(phases_data, 1):
                    if isinstance(phase, dict):
                        phase_name = phase.get("name", f"phase-{i}")
                        phase_desc = phase.get("description", "")

                        # Evaluate skip_if conditions
                        from borg.core.conditions import (
                            evaluate_skip_conditions,
                            evaluate_inject_conditions,
                            evaluate_context_prompts,
                        )

                        should_skip, skip_reason = evaluate_skip_conditions(phase, eval_context)
                        if should_skip:
                            lines.append(f"  Phase {i}: {phase_name} — SKIPPED ({skip_reason})")
                            continue

                        lines.append(f"  Phase {i}: {phase_name} — {phase_desc}")

                        # Evaluate inject_if and append messages
                        inject_messages = evaluate_inject_conditions(phase, eval_context)
                        for msg in inject_messages:
                            lines.append(f"    → {msg}")

                        # Evaluate context_prompts and append prompts
                        context_prompts = evaluate_context_prompts(phase, eval_context)
                        for cp in context_prompts:
                            lines.append(f"    📌 {cp}")
                    elif isinstance(phase, str):
                        lines.append(f"  Phase {i}: {phase}")
            elif isinstance(phases_data, int):
                # Just a count — show phase names if available
                phase_names = best_match.get("phase_names", [])
                if phase_names:
                    for i, name in enumerate(phase_names[:8], 1):  # Limit to 8 phases
                        lines.append(f"  Phase {i}: {name}")
                else:
                    lines.append(f"  ({phases_data} phases — run guild_try for full details)")

        if anti_patterns:
            if isinstance(anti_patterns, list):
                anti_str = "; ".join(str(a) for a in anti_patterns)
            else:
                anti_str = str(anti_patterns)
            lines.append(f"Key anti-patterns to avoid: {anti_str}")

        if checkpoint:
            lines.append(f"Checkpoint before fixing: {checkpoint}")

        # Extract error_message from context for TraceMatcher lookup
        error_msg = ""
        if context_dict and isinstance(context_dict, dict):
            error_msg = context_dict.get("error_message", "")
        
        # Use TraceMatcher to find relevant prior traces
        if task:
            try:
                from borg.core.trace_matcher import TraceMatcher
                matcher = TraceMatcher()
                relevant_traces = matcher.find_relevant(task, error=error_msg, top_k=2)
                if relevant_traces:
                    lines.append("")
                    lines.append("📜 Prior investigations:")
                    for trace in relevant_traces:
                        trace_info = matcher.format_for_agent(trace)
                        if trace_info:
                            lines.append(f"  • {trace_info}")
            except Exception:
                pass  # Never let TraceMatcher break observe

        # Change awareness: cross-reference error with recent changes
        if project_path and context:
            try:
                from borg.core.changes import detect_recent_changes, cross_reference_error
                changes = detect_recent_changes(project_path=project_path, hours=24)
                if changes.get('is_git_repo'):
                    note = cross_reference_error(changes, context)
                    if note:
                        lines.append(f"\n📝 Note: {note}")
            except Exception:
                # Don't fail on change awareness errors
                pass

        guidance = "\n".join(lines)
        return json.dumps({
            "success": True,
            "observed": True,
            "guidance": guidance,
        })

    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        # Fail silently — guild_observe should never break an agent's flow
        # But still return valid JSON so the MCP transport is not broken
        return json.dumps({"success": True, "observed": False, "guidance": ""})


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


def borg_recall(error_message: str = "") -> str:
    """Recall collective failure memory for an error.

    Returns approaches that other agents tried and failed, as well as
    approaches that succeeded. If no matching memory is found, returns null.

    Args:
        error_message: The error message to look up in failure memory.

    Returns:
        JSON string with wrong_approaches (sorted by frequency) and
        correct_approaches (sorted by frequency), or null if no match.
    """
    try:
        from borg.core.failure_memory import FailureMemory

        if not error_message:
            return json.dumps({"success": False, "error": "error_message is required"})

        fm = FailureMemory()
        result = fm.recall(error_message)

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
            "wrong_approaches": result.get("wrong_approaches", []),
            "correct_approaches": result.get("correct_approaches", []),
            "total_sessions": result.get("total_sessions", 0),
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


def borg_convert(path: str = "", format: str = "auto") -> str:
    """Convert a SKILL.md, CLAUDE.md, or .cursorrules file into a workflow pack.

    Args:
        path: Path to the source file.
        format: Source format - 'auto' (detect from filename), 'skill', 'claude', 'cursorrules'.
    """
    try:
        import yaml
        from borg.core import convert as convert_module

        if not path:
            return json.dumps({"success": False, "error": "path is required"})

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
                "error": f"Unknown format: {format}. Use: auto, skill, claude, cursorrules"
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
    protected by a timeout to prevent hangs.
    """
    try:
        # Install timeout alarm (Unix only)
        if hasattr(signal, "SIGALRM"):
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(TOOL_TIMEOUT_SEC)

        try:
            result = _call_tool_impl(name, arguments)
        finally:
            # Cancel alarm and restore handler
            if hasattr(signal, "SIGALRM"):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        # Feed tool call into trace capture (skip borg internal tools to avoid noise)
        if name not in ("borg_search", "borg_observe", "borg_suggest", "borg_feedback", "borg_publish"):
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

    elif name == "borg_convert":
        return borg_convert(
            path=arguments.get("path", ""),
            format=arguments.get("format", "auto"),
        )

    elif name == "borg_context":
        return borg_context(
            project_path=arguments.get("project_path", "."),
            hours=arguments.get("hours", 24),
        )

    elif name == "borg_recall":
        return borg_recall(
            error_message=arguments.get("error_message", ""),
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

    elif name == "borg_observe":
        return borg_observe(
            task=arguments.get("task", ""),
            context=arguments.get("context", ""),
            context_dict=arguments.get("context_dict"),
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
    """Run the MCP server on stdio. Reads JSON-RPC requests from stdin, writes responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            response = make_error(None, -32700, f"Parse error: {e}")
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
