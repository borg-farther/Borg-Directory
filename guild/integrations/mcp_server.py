"""
Guild MCP Server (T1.11) — AI Guild tools via Model Context Protocol (JSON-RPC 2.0 over stdio).

Exposed tools:
  - guild_search:  Search for guild workflow packs by keyword
  - guild_pull:     Fetch, validate, and store a pack locally
  - guild_try:     Preview a pack without saving
  - guild_init:     Initialise a new pack scaffold
  - guild_apply:    Execute a pack (start / checkpoint / complete)
  - guild_publish:  Publish a pack or feedback artifact
  - guild_feedback: Generate feedback draft after pack execution
  - guild_suggest:  Auto-suggest pack based on frustration signals
  - guild_convert:  Convert SKILL.md / CLAUDE.md / .cursorrules to pack

Zero imports from tools.* or guild_mcp.* — uses only guild.core.* and guild.integrations.*
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Suppress default logging (MCP uses stdout for JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

# ---------------------------------------------------------------------------
# Tool definitions (MCP schema)
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "guild_search",
        "description": (
            "Search for guild workflow packs by keyword or semantic similarity. Searches local packs and the remote index. "
            "Returns matching packs with their metadata (name, problem class, tier, confidence). "
            "Use mode='semantic' or mode='hybrid' for semantic search when embeddings are available."
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
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "guild_pull",
        "description": (
            "Fetch, validate, and store a guild pack locally. Downloads from URI, runs safety scan, "
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
        "name": "guild_try",
        "description": (
            "Preview a guild workflow pack without saving it. Shows pack metadata, phases, proof gates, "
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
        "name": "guild_init",
        "description": (
            "Scaffold a new guild workflow pack in the local guild directory. "
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
        "name": "guild_apply",
        "description": (
            "Execute a guild workflow pack with phase tracking. Multi-action: "
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
        "name": "guild_publish",
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
        "name": "guild_feedback",
        "description": (
            "Generate a feedback draft for a completed pack execution. "
            "Reads the execution session log and produces a structured feedback artifact."
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
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "guild_suggest",
        "description": (
            "Auto-suggest a guild workflow pack based on frustration signals and task context. "
            "Triggers when failure_count >= 2 or when frustration keywords are detected. "
            "Searches guild packs by classified task terms and returns top matches."
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
        "name": "guild_convert",
        "description": (
            "Convert a SKILL.md, CLAUDE.md, or .cursorrules file into a guild workflow pack. "
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
]

# ---------------------------------------------------------------------------
# Server metadata
# ---------------------------------------------------------------------------

SERVER_INFO = {"name": "guild-mcp-server", "version": "1.0.0"}

CAPABILITIES = {"tools": {}}

# ---------------------------------------------------------------------------
# Guild core imports (lazy to avoid circular imports)
# ---------------------------------------------------------------------------


def _get_core_modules():
    """Lazily import guild core modules to avoid import errors during testing."""
    from guild.core import uri as uri_module
    from guild.core import publish as publish_module
    from guild.core import session as session_module
    from guild.core import safety as safety_module
    from guild.core import schema as schema_module
    return uri_module, publish_module, session_module, safety_module, schema_module


# ---------------------------------------------------------------------------
# Tool implementations (wired to guild.core.*)
# ---------------------------------------------------------------------------

def guild_search(query: str = "", mode: str = "text") -> str:
    """Search for packs matching the query string.

    Args:
        query: Search query string.
        mode: Search mode - 'text', 'semantic', or 'hybrid'.
            Defaults to 'text'.
    """
    try:
        uri_module, _, _, _, _ = _get_core_modules()
        if not query:
            names = uri_module.get_available_pack_names()
            return json.dumps({"success": True, "packs": [{"name": n} for n in names], "total": len(names)})

        # Import search module with optional semantic support
        try:
            from guild.core import search as search_module
            result = search_module.guild_search(query, mode=mode)
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


def guild_pull(uri: str = "") -> str:
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
        GUILD_DIR = Path.home() / ".hermes" / "guild"
        pack_dir = GUILD_DIR / pack_name
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


def guild_try(uri: str = "") -> str:
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


def guild_init(pack_name: str = "", problem_class: str = "general", mental_model: str = "fast-thinker") -> str:
    """Scaffold a new pack in the local guild directory."""
    try:
        import yaml
        from datetime import datetime, timezone

        if not pack_name:
            return json.dumps({"success": False, "error": "pack_name is required"})

        GUILD_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "guild"
        pack_dir = GUILD_DIR / pack_name
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


def guild_apply(
    action: str = "",
    pack_name: str = "",
    task: str = "",
    session_id: str = "",
    phase_name: str = "",
    status: str = "",
    evidence: str = "",
    outcome: str = "",
) -> str:
    """Execute a guild pack with session tracking (start / checkpoint / complete)."""
    try:
        _, _, session_module, _, _ = _get_core_modules()

        if action == "start":
            if not pack_name or not task:
                return json.dumps({"success": False, "error": "pack_name and task are required for action=start"})

            # Load pack
            GUILD_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "guild"
            pack_file = GUILD_DIR / pack_name / "pack.yaml"
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
                "log_path": GUILD_DIR / "executions" / f"{session_id}.jsonl",
                "execution_log_path": GUILD_DIR / "executions" / f"{session_id}.jsonl",
                "events": [],
                "phase_results": [],
                "approved": False,
            }
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

            # Log event
            session_module.log_event(session_id, {
                "type": "checkpoint",
                "phase_name": phase_name,
                "status": status,
                "evidence": evidence,
            })

            # Update phase status in session
            phases = session.get("phases", [])
            for p in phases:
                if p.get("name") == phase_name:
                    p["status"] = status
                    break

            session["phase_results"].append({"phase": phase_name, "status": status, "evidence": evidence})
            session_module.save_session(session)

            approved = session.get("approved", False)
            if phase_name == "__approval__" and status == "passed":
                approved = True
                session["approved"] = True
                session_module.save_session(session)

            return json.dumps({
                "success": True,
                "session_id": session_id,
                "phase_name": phase_name,
                "status": status,
                "approved": approved,
            })

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


def guild_publish(
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


def guild_feedback(
    session_id: str = "",
    what_changed: str = "",
    where_to_reuse: str = "",
    publish: bool = False,
) -> str:
    """Generate a feedback artifact for a completed session.

    1. Loads the execution session.
    2. Generates a structured feedback draft via generate_feedback().
    3. Saves the draft as a YAML file in ~/.hermes/guild/feedback/.
    4. Optionally publishes via action_publish.
    5. Returns the full feedback draft for agent review.

    Args:
        session_id: Session ID of the completed pack execution (required).
        what_changed: Brief description of what changed in this execution.
        where_to_reuse: Guidance on where this feedback can be reused.
        publish: If True, immediately publish the feedback via action_publish.
    """
    try:
        import uuid
        import yaml
        from datetime import datetime, timezone
        from pathlib import Path

        _, publish_module, session_module, _, _ = _get_core_modules()
        from guild.core.search import generate_feedback

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


def guild_suggest(
    context: str = "",
    failure_count: int = 0,
    task_type_hint: str = "",
    tried_packs: Optional[List[str]] = None,
) -> str:
    """Auto-suggest a guild pack based on frustration signals and task context.

    Triggers when failure_count >= 2 or frustration keywords are detected.
    Searches guild packs by classified task terms and returns top matches.

    Args:
        context: Recent conversation context (messages, errors, task description).
        failure_count: Number of consecutive failed attempts (triggers at >= 2).
        task_type_hint: Optional explicit task type hint.
        tried_packs: Optional list of pack names already tried (excluded).
    """
    try:
        from guild.core.search import check_for_suggestion as _check_for_suggestion

        if not context:
            return "{}"

        result = _check_for_suggestion(
            conversation_context=context,
            failure_count=failure_count,
            task_type=task_type_hint,
            tried_packs=tried_packs or [],
        )
        return result
    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def guild_convert(path: str = "", format: str = "auto") -> str:
    """Convert a SKILL.md, CLAUDE.md, or .cursorrules file into a workflow pack.

    Args:
        path: Path to the source file.
        format: Source format - 'auto' (detect from filename), 'skill', 'claude', 'cursorrules'.
    """
    try:
        import yaml
        from guild.core import convert as convert_module

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
# Tool dispatch
# -------------------------------------------------------------------------

def call_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Dispatch a tool call to the appropriate guild function. Returns JSON string."""
    try:
        if name == "guild_search":
            return guild_search(query=arguments.get("query", ""))

        elif name == "guild_pull":
            return guild_pull(uri=arguments.get("uri", ""))

        elif name == "guild_try":
            return guild_try(uri=arguments.get("uri", ""))

        elif name == "guild_init":
            return guild_init(
                pack_name=arguments.get("pack_name", ""),
                problem_class=arguments.get("problem_class", "general"),
                mental_model=arguments.get("mental_model", "fast-thinker"),
            )

        elif name == "guild_apply":
            return guild_apply(
                action=arguments.get("action", ""),
                pack_name=arguments.get("pack_name", ""),
                task=arguments.get("task", ""),
                session_id=arguments.get("session_id", ""),
                phase_name=arguments.get("phase_name", ""),
                status=arguments.get("status", ""),
                evidence=arguments.get("evidence", ""),
                outcome=arguments.get("outcome", ""),
            )

        elif name == "guild_publish":
            return guild_publish(
                action=arguments.get("action", "publish"),
                path=arguments.get("path", ""),
                pack_name=arguments.get("pack_name", ""),
                feedback_name=arguments.get("feedback_name", ""),
                repo=arguments.get("repo", ""),
            )

        elif name == "guild_feedback":
            return guild_feedback(
                session_id=arguments.get("session_id", ""),
                what_changed=arguments.get("what_changed", ""),
                where_to_reuse=arguments.get("where_to_reuse", ""),
            )

        elif name == "guild_suggest":
            return guild_suggest(
                context=arguments.get("context", ""),
                failure_count=arguments.get("failure_count", 0),
                task_type_hint=arguments.get("task_type_hint", ""),
                tried_packs=arguments.get("tried_packs"),
            )

        elif name == "guild_convert":
            return guild_convert(
                path=arguments.get("path", ""),
                format=arguments.get("format", "auto"),
            )

        else:
            return json.dumps({"success": False, "error": f"Unknown tool: {name}"})

    except (KeyboardInterrupt, SystemExit):
        raise
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


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
