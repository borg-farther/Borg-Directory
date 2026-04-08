"""
Borg CLI — shell commands wrapping the core engine.

Usage:
    borg search <query>        — search for packs
    borg pull <uri>           — fetch and save pack locally
    borg try <uri>            — preview pack without saving
    borg init <name>          — create pack scaffold or convert from skill
    borg apply <pack> --task  — start applying a pack
    borg publish <path>       — publish pack to GitHub
    borg feedback <session_id> — generate feedback from session
    borg debug <error>        — get structured guidance for an error
    borg generate <pack>      — export pack to .cursorrules / .clinerules / CLAUDE.md / .windsurfrules
    borg list                 — list local packs
    borg autopilot            — zero-config setup (install MCP + skill + auto-suggest)
    borg setup-claude         — configure borg MCP for Claude Code
    borg setup-cursor         — configure borg MCP for Cursor
    borg version              — show version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from borg import __version__


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_json(raw: str) -> None:
    """Parse JSON and print pretty; fall back to raw string."""
    try:
        data = json.loads(raw)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        print(raw)


def _require_success(raw: str, ctx: str = "") -> bool:
    """Print error and return False if the JSON result has success=False."""
    try:
        data = json.loads(raw)
        if not data.get("success", True):
            error = data.get("error", "Unknown error")
            print(f"Error{ctx}: {error}", file=sys.stderr)
            return False
        return True
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def _cmd_search(args: argparse.Namespace) -> int:
    """Search for packs matching a query."""
    from borg.core.search import borg_search

    raw = borg_search(args.query, mode=args.mode)
    if args.json:
        _print_json(raw)
        return 0
    data = json.loads(raw)
    if not data.get("success"):
        print(f"Error: {data.get('error', 'Unknown')}", file=sys.stderr)
        return 1
    _test_filter = ("test-pack", "smoke-test", "wf-test", "test-call", "my-test", "fresh-pack", "old-pack", "my-pack", "guild:--", "test-scaffold", "stress-project", "test-e2e", "e2e-test")
    matches = [m for m in data.get("matches", [])
               if not any(m.get("name", "").startswith(p) or m.get("id", "").startswith(p) for p in _test_filter)]
    if not matches:
        print("No packs found.")
        return 0
    print(f"{'Name':<35} {'Confidence':<12} {'Tier':<8} {'Problem Class'}")
    print("-" * 90)
    for p in matches:
        name = p.get("name", "?")
        conf = p.get("confidence", "?")
        tier = p.get("tier", "?")
        problem_class = (p.get("problem_class") or "")[:60]
        print(f"{name:<35} {conf:<12} {tier:<8} {problem_class}")
    print(f"\nTotal: {len(matches)} pack(s)")
    return 0


def _cmd_pull(args: argparse.Namespace) -> int:
    """Fetch and save a pack locally."""
    from borg.core.search import borg_pull

    raw = borg_pull(args.uri)
    if _require_success(raw):
        data = json.loads(raw)
        print(f"Pulled pack '{data.get('name')}' -> {data.get('path')}")
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_try(args: argparse.Namespace) -> int:
    """Preview a pack without saving."""
    from borg.core.search import borg_try

    raw = borg_try(args.uri)
    if args.json:
        _print_json(raw)
        return 0 if json.loads(raw).get("success") else 1
    if _require_success(raw, ctx=" (pack not found or invalid)"):
        data = json.loads(raw)
        phases = data.get("phases", [])
        phase_names = ", ".join(p.get("name", "?") for p in phases) if phases else "none"
        verdict = data.get("verdict", "unknown")
        verdict_symbol = "✓" if verdict == "safe" else "✗"
        print(f"Pack: {data.get('id', '?')} ({data.get('problem_class', '?')})")
        print(f"Confidence: {data.get('confidence', '?')}")
        print(f"Phases ({len(phases)}): {phase_names}")
        print(f"Verdict: {verdict_symbol} {verdict}")
        errors = data.get("validation_errors", [])
        if errors:
            print(f"Validation errors ({len(errors)}):")
            for e in errors:
                print(f"  - {e}")
        threats = data.get("safety_threats", [])
        if threats:
            print(f"Safety threats ({len(threats)}):")
            for t in threats:
                print(f"  - {t}")
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    """Scaffold a new pack from scratch or convert from a skill."""
    import yaml as _yaml
    from datetime import datetime, timezone

    import re as _re
    name = args.name
    if not _re.match(r'^[a-zA-Z0-9_-]+$', name):
        print(f"Error: Pack name must contain only letters, numbers, hyphens, underscores. Got: '{name}'", file=sys.stderr)
        return 1
    problem_class = getattr(args, "problem_class", "general") or "general"
    mental_model = getattr(args, "mental_model", "fast-thinker") or "fast-thinker"

    guild_dir = Path.home() / ".hermes" / "guild"
    pack_dir = guild_dir / name
    pack_dir.mkdir(parents=True, exist_ok=True)

    scaffold = {
        "type": "workflow_pack",
        "version": "1.0",
        "id": name,
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
    content = _yaml.safe_dump(scaffold, default_flow_style=False, sort_keys=False)
    pack_file = pack_dir / "pack.yaml"
    pack_file.write_text(content, encoding="utf-8")
    print(f"Created pack scaffold: {pack_file}")
    print(f"Edit {pack_file} to define your phases and prompts.")
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    """Start applying a pack to a task."""
    from borg.core.apply import apply_handler

    raw = apply_handler(
        action="start",
        pack_name=args.pack,
        task=args.task,
    )
    if args.json:
        _print_json(raw)
        return 0 if json.loads(raw).get("success") else 1
    if _require_success(raw, ctx=" (pack not found)"):
        data = json.loads(raw)
        session_id = data.get("session_id", "?")
        phases = data.get("phases", [])
        phase_names = ", ".join(p.get("name", "?") for p in phases) if phases else "none"
        print(f"Session ID: {session_id}")
        print(f"Phases ({len(phases)}): {phase_names}")
        print()
        print("Session started. In your agent (MCP), use:")
        print(f"  borg_apply(action='checkpoint', session_id='{session_id}', phase_result='done')")
        print("to advance through each phase. Or use borg_search to find the pack first.")
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_publish(args: argparse.Namespace) -> int:
    """Publish a pack to GitHub."""
    from borg.core.publish import action_publish

    raw = action_publish(path=args.path)
    if _require_success(raw, ctx=" (publish failed)"):
        _print_json(raw)
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_feedback(args: argparse.Namespace) -> int:
    """Generate feedback from a session."""
    from borg.core.session import load_session
    from borg.core.search import generate_feedback as _core_generate_feedback

    session = load_session(args.session_id)
    if not session:
        print(f"Error: Session not found: {args.session_id}", file=sys.stderr)
        return 1

    raw = _core_generate_feedback(
        pack_id=session.get("pack_id", ""),
        pack_version=session.get("pack_version", "unknown"),
        execution_log=session.get("phase_results", []),
        task_description=session.get("task", ""),
        outcome=session.get("outcome", ""),
    )
    print(json.dumps(raw, indent=2))
    return 0


def _cmd_feedback_v3(args: argparse.Namespace) -> int:
    """Record an outcome for a debug guidance session (V3 feedback loop)."""
    from borg.core.v3_integration import BorgV3
    from borg.core.pack_taxonomy import load_pack_by_problem_class

    # Resolve pack_id
    pack_id = args.pack
    problem_class = args.problem_class

    if not pack_id and not problem_class:
        print("Error: must provide --pack or --problem-class", file=sys.stderr)
        return 1

    if problem_class:
        pack = load_pack_by_problem_class(problem_class)
        if not pack:
            print(f"Error: no pack found for problem_class '{problem_class}'", file=sys.stderr)
            return 1
        pack_id = pack.get("id", pack.get("name", problem_class))
    else:
        pack_id = args.pack

    # Determine success
    success = args.success.lower() in ("yes", "true", "1", "y")
    time_taken = args.time or 0.0
    tokens_used = args.tokens or 0

    # Record to V3
    task_context = {"task_category": problem_class or "unknown"}
    try:
        v3 = BorgV3(db_path="~/.hermes/guild/borg_v3.db")
        v3.record_outcome(
            pack_id=pack_id,
            task_context=task_context,
            success=success,
            tokens_used=tokens_used,
            time_taken=time_taken,
        )
        status = "✓ success" if success else "✗ failure"
        print(f"Recorded: {pack_id} [{problem_class or 'unknown'}] — {status}")
        return 0
    except Exception as e:
        print(f"Error recording outcome: {e}", file=sys.stderr)
        return 1


def _cmd_debug(args: argparse.Namespace) -> int:
    """Get structured debugging guidance for an error message."""
    from borg.core.pack_taxonomy import debug_error, classify_error, PROBLEM_CLASSES

    error_message = " ".join(args.error)

    # Show classification without full guidance if --classify only
    if args.classify:
        pc = classify_error(error_message)
        if pc:
            print(f"problem_class: {pc}")
        else:
            print("No matching problem class.")
            print(f"Known classes: {', '.join(PROBLEM_CLASSES)}")
        return 0

    # Full guidance
    result = debug_error(error_message, show_evidence=not args.quiet)
    print(result)

    # Append FailureMemory warnings if error_message is provided
    if error_message and not args.quiet:
        try:
            from borg.core.failure_memory import FailureMemory
            fm = FailureMemory()
            memory = fm.recall(error_message)
            if memory and (memory.get("wrong_approaches") or memory.get("correct_approaches")):
                print()
                wrong = memory.get("wrong_approaches", [])
                correct = memory.get("correct_approaches", [])
                if wrong:
                    top = wrong[0]
                    print(f"⚠️ Other agents tried: {top.get('approach', 'unknown')} "
                          f"and failed ({top.get('failure_count', 0)} times). Try a different approach.")
                if correct:
                    top = correct[0]
                    print(f"✅ Instead, try: {top.get('approach', 'unknown')} "
                          f"(succeeded {top.get('success_count', 0)} times).")
        except Exception:
            pass  # Never let FailureMemory break the CLI

    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    """Interactive onboarding — get value from borg in 30 seconds."""
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║          Welcome to the Borg Collective          ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()
    print("  Your agent forgets everything between sessions.")
    print("  Borg remembers.")
    print()
    print("  ── Try it now ─────────────────────────────────────")
    print()
    print("  Paste any error message you're dealing with:")
    print()

    try:
        error = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 0

    if not error:
        print()
        print("  No error entered. Try:")
        print("    borg debug 'your error message here'")
        print()
        return 0

    # Run debug
    from borg.core.pack_taxonomy import debug_error
    print()
    result = debug_error(error, show_evidence=True)
    print(result)

    # Auto-record feedback
    try:
        from borg.core.pack_taxonomy import classify_error
        from borg.core.v3_integration import BorgV3
        pc = classify_error(error)
        if pc:
            v3 = BorgV3(db_path="~/.hermes/guild/borg_v3.db")
            v3.record_outcome(
                pack_id=pc,
                task_context={"task_category": pc, "source": "borg_start"},
                success=True,
                tokens_used=0,
                time_taken=0.0,
            )
    except Exception:
        pass

    # Next steps
    print()
    print("  ── What's next ───────────────────────────────────")
    print()
    print("  • Run again anytime:   borg debug 'your error'")
    print("  • Browse workflows:    borg search debugging")
    print("  • Export for Cursor:   borg generate systematic-debugging --format cursorrules")
    print("  • Export for Claude:   borg setup-claude")
    print("  • Record what worked:  borg feedback-v3 --pack systematic-debugging --success yes")
    print()
    print("  The more you use borg, the smarter it gets.")
    print("  Resistance is futile.")
    print()
    return 0


def _cmd_convert(args: argparse.Namespace) -> int:
    """Convert a SKILL.md, CLAUDE.md, or .cursorrules file to a workflow pack."""
    import yaml
    from borg.core.convert import convert_auto, convert_skill, convert_claude_md, convert_cursorrules
    try:
        if args.format == "auto":
            pack = convert_auto(args.path)
        elif args.format == "skill":
            pack = convert_skill(args.path)
        elif args.format == "claude":
            pack = convert_claude_md(args.path)
        elif args.format == "cursorrules":
            pack = convert_cursorrules(args.path)
        else:
            print(f"Error: Unknown format '{args.format}'. Use: auto, skill, claude, cursorrules", file=sys.stderr)
            return 1
        print(yaml.safe_dump(pack, default_flow_style=False, sort_keys=False))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_generate(args: argparse.Namespace) -> int:
    """Export a pack to platform-specific rule files."""
    from borg.core.generator import generate_rules, generate_to_files, load_pack

    try:
        pack = load_pack(args.pack)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    fmt = args.format
    output_dir = getattr(args, "output", None)

    if output_dir:
        written = generate_to_files(pack, format=fmt, output_dir=output_dir)
        for filename, filepath in written.items():
            print(f"  {filename} -> {filepath}")
        return 0
    else:
        result = generate_rules(pack, format=fmt)
        if isinstance(result, dict):
            for fmt_name, content in result.items():
                from borg.core.generator import FORMAT_FILENAMES
                print(f"=== {FORMAT_FILENAMES[fmt_name]} ===")
                print(content)
                print()
        else:
            print(result)
        return 0


def _cmd_list(args: argparse.Namespace) -> int:
    """List local packs."""
    from borg.core.publish import action_list

    raw = action_list()
    data = json.loads(raw)
    if not data.get("success"):
        print(f"Error: {data.get('error', 'Unknown')}", file=sys.stderr)
        return 1

    artifacts = data.get("artifacts", [])
    # Filter out test/smoke packs that shouldn't appear in production
    _test_patterns = ("test-pack", "smoke-test", "wf-test", "test-call", "my-test", "fresh-pack", "old-pack", "my-pack", "guild:--", "test-scaffold", "stress-project", "test-e2e", "e2e-test")
    packs = [a for a in artifacts if a.get("type") == "pack" 
             and not any(a.get("name", "").startswith(p) or a.get("id", "").startswith(p) for p in _test_patterns)]

    if not packs:
        print("No local packs found.")
        return 0

    print(f"{'Name':<30} {'ID':<40} {'Confidence'}")
    print("-" * 80)
    for p in packs:
        name = p.get("name", "?")
        pid = p.get("id", "")
        conf = p.get("confidence", "?")
        print(f"{name:<30} {pid:<40} {conf}")
    print(f"\nTotal: {len(packs)} pack(s)")
    return 0


def _cmd_observe(args: argparse.Namespace) -> int:
    """Record a task/context observation as a trace in ~/.borg/traces.db.

    This is the CLI counterpart to the MCP borg_observe tool. Calling this
    records a minimal trace entry (task + optional context/error) via
    borg.core.traces so that subsequent `borg search` calls can surface it.

    Added in v3.2.4 to fix the observe→search roundtrip bug discovered in the
    P1.1 MiniMax experiment (docs/20260408-1118_borg_roadmap).
    """
    from borg.core.traces import TraceCapture, save_trace

    task = " ".join(args.task).strip() if isinstance(args.task, list) else (args.task or "").strip()
    if not task:
        print("Error: observe requires a non-empty task description", file=sys.stderr)
        return 1

    context = getattr(args, "context", "") or ""
    error = getattr(args, "error", "") or ""
    agent_id = getattr(args, "agent", "") or "cli"

    try:
        capture = TraceCapture(task=task, agent_id=agent_id)
        # Synthesize a minimum set of tool calls so the trace has content:
        # one stub 'observe' call carrying the context/error text so the
        # keywords/error patterns extractors have something to chew on.
        if context or error:
            capture.on_tool_call(
                tool_name="observe",
                args={"task": task, "context": context},
                result=error or context,
            )
        trace = capture.extract_trace(
            outcome="observed",
            root_cause="",
            approach_summary=context[:500] if context else "",
        )
        trace["source"] = "observe-cli"
        trace_id = save_trace(trace)
        print(f"Recorded trace {trace_id} for task: {task[:80]}")
        if args.json:
            print(json.dumps({
                "success": True,
                "trace_id": trace_id,
                "task": task,
                "source": "observe-cli",
            }))
        return 0
    except Exception as e:
        print(f"Error recording observation: {e}", file=sys.stderr)
        return 1


def _cmd_version(args: argparse.Namespace) -> int:
    """Show version."""
    print(f"borg {__version__}")
    return 0


# ---------------------------------------------------------------------------
# Borg setup helpers (shared logic for Claude Code and Cursor)
# ---------------------------------------------------------------------------

import shutil
import yaml

# Path to this file's parent (borg/)
BORG_PACKAGE_DIR = Path(__file__).parent.resolve()
# Path to guild-v2 root (one level up from borg/)
BORG_ROOT_DIR = BORG_PACKAGE_DIR.parent


def _get_python_path() -> str:
    """Return the PYTHONPATH to use in MCP config."""
    return str(BORG_ROOT_DIR)


def _borg_mcp_server_entry(python_path: str) -> dict:
    """Return the mcpServers entry for the borg MCP server (camelCase for Claude/Cursor)."""
    return {
        "mcpServers": {
            "borg": {
                "enabled": True,
                "command": "python",
                "args": ["-m", "borg.integrations.mcp_server"],
                "env": {"PYTHONPATH": python_path},
            }
        }
    }


# ---------------------------------------------------------------------------
# CLAUDE.md instructions template (for Claude Code)
# ---------------------------------------------------------------------------

CLAUDE_MD_TEMPLATE = """\

## Borg Workflow Packs (borg)

This project uses **Borg Workflow Packs** — battle-tested phase-by-phase approaches
stored as versioned YAML packs. When you hit a wall or start a complex task, borg helps.

### Available Commands

```bash
# Search for a relevant pack
borg search <query>

# Preview a pack before adopting it
borg try <pack-uri>

# Pull and apply a pack to your task
borg apply <pack-name> --task "<task description>"

# Get structured feedback after completing a pack
borg feedback <session-id>
```

### MCP Tools (for Claude Code agent)

If Claude Code has the guild MCP server configured, these tools are available:

- `borg_observe` — call at task start for structural guidance
- `borg_search` — search for relevant packs by keyword
- `borg_suggest` — auto-suggest after 2+ consecutive failures

### Setup

If the guild MCP server isn't configured yet, run:
```bash
borg setup-claude
```
"""


# ---------------------------------------------------------------------------
# .cursorrules instructions template (for Cursor)
# ---------------------------------------------------------------------------

CURSOR_RULES_TEMPLATE = """\

## Borg Workflow Packs (borg)

This project uses **Borg Workflow Packs** — battle-tested phase-by-phase approaches
stored as versioned YAML packs. When you hit a wall or start a complex task, borg helps.

### Available Commands

```bash
# Search for a relevant pack
borg search <query>

# Preview a pack before adopting it
borg try <pack-uri>

# Pull and apply a pack to your task
borg apply <pack-name> --task "<task description>"

# Get structured feedback after completing a pack
borg feedback <session-id>
```

### MCP Tools (for Cursor agent)

If Cursor has the guild MCP server configured, these tools are available:

- `borg_observe` — call at task start for structural guidance
- `borg_search` — search for relevant packs by keyword
- `borg_suggest` — auto-suggest after 2+ consecutive failures

### Setup

If the guild MCP server isn't configured yet, run:
```bash
borg setup-cursor
```
"""


# ---------------------------------------------------------------------------
# setup-claude: configure guild MCP for Claude Code
# ---------------------------------------------------------------------------

def _cmd_setup_claude(args: argparse.Namespace) -> int:
    """Configure guild MCP server for Claude Code.

    Creates (or updates) ~/.config/claude/claude_desktop_config.json with the guild
    MCP server entry, and appends borg instructions to ./CLAUDE.md in the current
    directory.
    """
    home = Path.home()
    claude_config_dir = home / ".config" / "claude"
    claude_config_file = claude_config_dir / "claude_desktop_config.json"

    python_path = _get_python_path()
    new_entry = _borg_mcp_server_entry(python_path)
    changes: list[str] = []

    # 1. Install Claude Code MCP config
    claude_config_dir.mkdir(parents=True, exist_ok=True)

    if claude_config_file.exists():
        try:
            config = json.loads(claude_config_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"[setup-claude] Warning: could not read existing config: {e}")
            config = {}
    else:
        config = {}

    existing_servers = config.get("mcpServers", {})
    borg_entry = new_entry["mcpServers"]["borg"]
    entry_changed = existing_servers.get("borg") != borg_entry

    if entry_changed:
        config["mcpServers"] = {**existing_servers, "borg": borg_entry}
        claude_config_file.write_text(json.dumps(config, indent=2) + "\n")
        changes.append(f"  • claude_desktop_config.json → {claude_config_file}")
    else:
        print("[setup-claude] MCP server already configured in claude_desktop_config.json")

    # 2. Install CLAUDE.md in current directory
    claude_md = Path.cwd() / "CLAUDE.md"
    instructions = CLAUDE_MD_TEMPLATE.lstrip("\n")

    if claude_md.exists():
        existing = claude_md.read_text()
        if instructions in existing:
            print("[setup-claude] CLAUDE.md already contains borg instructions — skipping")
        elif "# Guild" in existing or "## Guild" in existing or "# Borg" in existing or "## Borg" in existing:
            # Guild section exists but content differs — replace the whole section
            import re
            # Remove any existing Guild/Borg Workflow Packs section (handles leading newline optional)
            pattern = r"(\n)?## (?:Guild|Borg) Workflow Packs.*?(?=\n## |\Z)"
            new_content = re.sub(pattern, "\n" + instructions, existing, flags=re.DOTALL)
            if new_content == existing:
                # Pattern didn't match (e.g. it's at the end without another header) — just append
                new_content = existing.rstrip() + "\n" + instructions + "\n"
            claude_md.write_text(new_content)
            changes.append(f"  • CLAUDE.md (updated guild section) → {claude_md.resolve()}")
        else:
            claude_md.write_text(existing.rstrip() + "\n" + instructions + "\n")
            changes.append(f"  • CLAUDE.md (appended) → {claude_md.resolve()}")
    else:
        claude_md.write_text("# Project CLAUDE.md\n" + instructions + "\n")
        changes.append(f"  • CLAUDE.md (created) → {claude_md.resolve()}")

    if not changes:
        print("[setup-claude] Everything already set up! Borg is ready.")
        return 0

    print("[setup-claude] Claude Code setup complete!")
    for c in changes:
        print(c)
    print()
    print("Next steps:")
    print("  1. Restart Claude Code (or reload the MCP server config)")
    print("  2. Borg MCP tools (borg_observe, borg_search, borg_suggest) will be available")
    print("  3. Run 'borg search <query>' to find relevant packs")
    return 0


# ---------------------------------------------------------------------------
# setup-cursor: configure guild MCP for Cursor
# ---------------------------------------------------------------------------

def _cmd_setup_cursor(args: argparse.Namespace) -> int:
    """Configure borg MCP server for Cursor.

    Creates (or updates) .cursor/mcp.json with the borg MCP server entry,
    and appends borg instructions to .cursorrules in the current directory.
    """
    cursor_dir = Path.cwd() / ".cursor"
    cursor_mcp_file = cursor_dir / "mcp.json"

    python_path = _get_python_path()
    new_entry = _borg_mcp_server_entry(python_path)
    changes: list[str] = []

    # 1. Install Cursor MCP config
    cursor_dir.mkdir(parents=True, exist_ok=True)

    if cursor_mcp_file.exists():
        try:
            config = json.loads(cursor_mcp_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"[setup-cursor] Warning: could not read existing config: {e}")
            config = {}
    else:
        config = {}

    existing_servers = config.get("mcpServers", {})
    borg_entry = new_entry["mcpServers"]["borg"]
    entry_changed = existing_servers.get("borg") != borg_entry

    if entry_changed:
        config["mcpServers"] = {**existing_servers, "borg": borg_entry}
        cursor_mcp_file.write_text(json.dumps(config, indent=2) + "\n")
        changes.append(f"  • mcp.json → {cursor_mcp_file}")
    else:
        print("[setup-cursor] MCP server already configured in .cursor/mcp.json")

    # 2. Install .cursorrules in current directory
    cursor_rules = Path.cwd() / ".cursorrules"
    instructions = CURSOR_RULES_TEMPLATE.lstrip("\n")

    if cursor_rules.exists():
        existing = cursor_rules.read_text()
        if instructions in existing:
            print("[setup-cursor] .cursorrules already contains borg instructions — skipping")
        elif "# Guild" in existing or "## Guild" in existing or "# Borg" in existing or "## Borg" in existing:
            # Guild section exists but content differs — replace the whole section
            import re
            # Remove any existing Guild/Borg Workflow Packs section (handles leading newline optional)
            pattern = r"(\n)?## (?:Guild|Borg) Workflow Packs.*?(?=\n## |\Z)"
            new_content = re.sub(pattern, "\n" + instructions, existing, flags=re.DOTALL)
            if new_content == existing:
                # Pattern didn't match (e.g. it's at the end without another header) — just append
                new_content = existing.rstrip() + "\n" + instructions + "\n"
            cursor_rules.write_text(new_content)
            changes.append(f"  • .cursorrules (updated guild section) → {cursor_rules.resolve()}")
        else:
            cursor_rules.write_text(existing.rstrip() + "\n" + instructions + "\n")
            changes.append(f"  • .cursorrules (appended) → {cursor_rules.resolve()}")
    else:
        cursor_rules.write_text(instructions + "\n")
        changes.append(f"  • .cursorrules (created) → {cursor_rules.resolve()}")

    if not changes:
        print("[setup-cursor] Everything already set up! Borg is ready.")
        return 0

    print("[setup-cursor] Cursor setup complete!")
    for c in changes:
        print(c)
    print()
    print("Next steps:")
    print("  1. Restart Cursor (or reload the MCP server config)")
    print("  2. Borg MCP tools (borg_observe, borg_search, borg_suggest) will be available")
    print("  3. Run 'borg search <query>' to find relevant packs")
    return 0


# ---------------------------------------------------------------------------
# Zero-config autopilot
# ---------------------------------------------------------------------------

HERMES_SKILL_TEMPLATE = """\
# Borg Autopilot — Zero-Config Borg Experience

## Purpose

Borg Autopilot is a **self-configuring skill** that makes agent-borg work automatically,
without any user setup or CLAUDE.md editing. A Hermes user only needs agent-borg installed
and the MCP server configured — this skill tells the agent **when** and **how** to use it.

## Trigger Conditions

Apply this skill automatically when ANY of these conditions are met:

### 1. Debug / Test / Review Detection (on task start)
When the task description contains keywords like:
- `debug`, `debugging`, `fix`, `crash`, `error`, `exception`, `stack trace`, `segfault`
- `test`, `testing`, `unit test`, `integration test`, `pytest`, `jest`
- `review`, `code review`, `pr review`, `pull request`, `audit`
- `performance`, `profiling`, `benchmark`, `optimize`, `slow`
- `security`, `vulnerability`, `CVE`, `exploit`

**Action:** Call `borg_on_task_start(task_description)` and include the result
in your reasoning. If a pack is suggested, mention it proactively to the user.

### 2. Failure Detection (after 2+ consecutive failures)
When the agent has failed 2 or more consecutive times on the same task:
- Call `borg_on_failure(context=recent_conversation, failure_count=N)`
- Inject the returned suggestion into your context as a **system message**

### 3. Phase-by-Phase Pack Application
When applying a borg pack, follow this strict sequence:
1. **Before applying:** Run `borg try <pack_uri>` to preview phases and validate safety
2. **Start:** Run `borg apply <pack> --task "<task description>"`
3. **Per phase:** Read the phase description, complete the work, then advance
4. **Track progress:** Log each completed phase in your context
5. **On completion:** Generate feedback with `borg feedback <session_id>`

### 4. Completion Feedback
After a pack session completes (success or failure):
- Call `borg feedback <session_id>` to get structured feedback
- Present the feedback to the user in a clear summary

## Available Commands

```bash
borg try <uri>     # Preview a pack (always do this first)
borg apply <pack> --task "<task description>"  # Start applying
borg feedback <session_id>  # Get session feedback
borg search <query>  # Search for relevant packs
```

## Python API

```python
from borg.integrations.agent_hook import borg_on_failure, borg_on_task_start

# On task start — proactive suggestion
suggestion = borg_on_task_start("fixing pytest failures")
# Returns: "You might find this useful: systematic-debugging [tested]..."

# After 2+ failures — reactive injection
suggestion = borg_on_failure(context="...", failure_count=2)
# Returns: "Borg pack available: systematic-debugging..."
```

## Agent Behavior Rules

1. **Always check borg first** for debug/test/review tasks
2. **Never apply a pack without previewing** with `borg try` first
3. **Apply packs phase by phase** — don't skip steps
4. **Generate feedback** after every pack session
5. **Respect tried_packs** — don't suggest the same failed pack twice
6. **Safety first** — if `borg try` shows safety threats, warn before proceeding
"""


HERMES_MCP_CONFIG_TEMPLATE = """\
mcp_servers:
  borg:
    enabled: true
    command: python
    args:
      - "-m"
      - "borg.integrations.mcp_server"
    env:
      PYTHONPATH: {python_path}
"""


def _cmd_autopilot(args: argparse.Namespace) -> int:
    """Zero-config autopilot: install MCP server config, skill file, and auto-suggest.

    This single command sets up everything needed for borg to work automatically
    in Hermes — no manual CLAUDE.md editing required.
    """
    import os
    import yaml
    from pathlib import Path

    home = Path.home()
    hermes_dir = home / ".hermes"
    hermes_config = hermes_dir / "config.yaml"
    skill_dir = hermes_dir / "skills" / "guild-autopilot"
    skill_file = skill_dir / "SKILL.md"

    python_path = str(Path(__file__).parent.parent.parent.resolve())

    changes: list[str] = []

    # 1. Ensure ~/.hermes directory exists
    hermes_dir.mkdir(parents=True, exist_ok=True)

    # 2. Install skill file
    skill_dir.mkdir(parents=True, exist_ok=True)
    existing_content = ""
    if skill_file.exists():
        existing_content = skill_file.read_text()

    if existing_content == HERMES_SKILL_TEMPLATE:
        print("[autopilot] Skill already installed — skipping SKILL.md")
    else:
        skill_file.write_text(HERMES_SKILL_TEMPLATE)
        changes.append(f"  • SKILL.md → {skill_file}")

    # 3. Install or update MCP server config
    if hermes_config.exists():
        config_text = hermes_config.read_text()
        try:
            config = yaml.safe_load(config_text) or {}
        except yaml.YAMLError:
            config = {}
    else:
        config = {}

    mcp_entry = {
        "enabled": True,
        "command": "python",
        "args": ["-m", "borg.integrations.mcp_server"],
        "env": {"PYTHONPATH": python_path},
    }

    mcp_servers = config.get("mcp_servers", {})
    guild_entry = mcp_servers.get("guild", {})

    # Only update if different
    if guild_entry == mcp_entry:
        print("[autopilot] MCP server already configured — skipping config.yaml")
    else:
        mcp_servers["guild"] = mcp_entry
        config["mcp_servers"] = mcp_servers

        # Preserve existing content structure as much as possible
        try:
            new_text = yaml.safe_dump(config, default_flow_style=False, sort_keys=False)
            hermes_config.write_text(new_text)
        except yaml.YAMLError as e:
            print(f"[autopilot] Warning: could not preserve config.yaml formatting: {e}")
            # Fall back: just rewrite entirely
            hermes_config.write_text(
                f"mcp_servers:\n  guild:\n    enabled: true\n    command: python\n    args:\n      - -m\n      - borg.integrations.mcp_server\n    env:\n      PYTHONPATH: {python_path}\n"
            )
        changes.append(f"  • config.yaml → {hermes_config}")

    if not changes:
        print("[autopilot] Everything already set up! Borg is ready to use.")
        return 0

    print("[autopilot] Zero-config guild setup complete!")
    print()
    print("What was configured:")
    for c in changes:
        print(c)
    print()
    print("Hermes will now:")
    print("  1. Auto-detect debug/test/review tasks and suggest guild packs")
    print("  2. Suggest packs after 2+ consecutive failures")
    print("  3. Apply packs phase-by-phase with feedback on completion")
    print()
    print("No CLAUDE.md editing needed — the SKILL.md handles everything.")

    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="borg",
        description="Borg — Semantic reasoning cache for AI agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Quick Start:
  borg start                     First time? Start here — paste an error, get a fix
  borg debug 'TypeError: ...'    Get structured debugging guidance for any error
  borg search debugging          Search for workflow packs
  borg generate systematic-debugging --format cursorrules
                                  Export a debugging workflow for Cursor
  borg setup-claude              Configure borg MCP for Claude Code
  borg setup-cursor              Configure borg MCP for Cursor
  borg autopilot                 Zero-config setup for Hermes""",
    )
    parser.add_argument("--version", "-V", action="version", version=f"borg {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # guild search <query>
    p = sub.add_parser("search", help="Search for packs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg search debugging
  borg search 'python import error'
  borg search testing --mode semantic""")
    p.add_argument("query", help="Search query")
    p.add_argument(
        "--mode",
        choices=["text", "semantic", "hybrid"],
        default="text",
        help="Search mode (default: text)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON for programmatic use",
    )
    p.set_defaults(func=_cmd_search)

    # guild pull <uri>
    p = sub.add_parser("pull", help="Fetch and save pack locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg pull guild://community/systematic-debugging
  borg pull https://github.com/user/pack.yaml""")
    p.add_argument("uri", help="Pack URI (guild://, https://, or local path)")
    p.set_defaults(func=_cmd_pull)

    # guild try <uri>
    p = sub.add_parser("try", help="Preview pack without saving",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg try systematic-debugging
  borg try systematic-debugging --json""")
    p.add_argument("uri", help="Pack URI")
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON for programmatic use",
    )
    p.set_defaults(func=_cmd_try)

    # guild init <name> [--problem-class] [--mental-model]
    p = sub.add_parser("init", help="Scaffold a new pack from scratch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg init my-debugging-workflow
  borg init api-testing --problem-class testing
  borg init perf-tuning --mental-model slow-thinker""")
    p.add_argument("name", help="Pack name (used as directory name)")
    p.add_argument("--problem-class", default="general", help="Problem class (default: general)")
    p.add_argument("--mental-model", default="fast-thinker", help="Mental model (default: fast-thinker)")
    p.set_defaults(func=_cmd_init)

    # guild apply <pack> --task <task>
    p = sub.add_parser("apply", help="Start applying a pack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg apply systematic-debugging --task 'fix failing test in auth module'
  borg apply systematic-debugging --task 'debug segfault' --json""")
    p.add_argument("pack", help="Pack name")
    p.add_argument("--task", required=True, help="Task description")
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON for programmatic use",
    )
    p.set_defaults(func=_cmd_apply)

    # guild publish <path>
    p = sub.add_parser("publish", help="Publish pack to GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg publish systematic-debugging
  borg publish ./my-pack/pack.yaml""")
    p.add_argument("path", help="Path to pack YAML or pack name")
    p.set_defaults(func=_cmd_publish)

    # guild feedback <session_id>
    p = sub.add_parser("feedback", help="Generate feedback from session",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg feedback abc123
  borg feedback session-2024-01-15-001""")
    p.add_argument("session_id", help="Session ID")
    p.set_defaults(func=_cmd_feedback)

    # guild feedback-v3 --problem-class <class> --success yes --time 120
    p = sub.add_parser("feedback-v3", help="Record debug guidance outcome to V3 feedback loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg feedback-v3 --pack systematic-debugging --success yes
  borg feedback-v3 --problem-class debugging --success no --time 30
  borg feedback-v3 --pack systematic-debugging --success yes --tokens 5000""")
    p.add_argument(
        "--pack",
        default=None,
        help="Pack ID (or use --problem-class to look it up)",
    )
    p.add_argument(
        "--problem-class",
        default=None,
        dest="problem_class",
        help="Problem class (pack looked up automatically)",
    )
    p.add_argument(
        "--success",
        required=True,
        help="Did the guidance help? (yes/no)",
    )
    p.add_argument(
        "--time",
        type=float,
        default=None,
        help="Time to resolve in minutes (optional)",
    )
    p.add_argument(
        "--tokens",
        type=int,
        default=None,
        help="Tokens used (optional)",
    )
    p.set_defaults(func=_cmd_feedback_v3)

    # guild debug <error>
    p = sub.add_parser("debug", help="Get structured debugging guidance for an error",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg debug 'TypeError: NoneType has no attribute get'
  borg debug 'ModuleNotFoundError: No module named flask'
  borg debug 'segmentation fault' --classify""")
    p.add_argument("error", nargs="+", help="Error message or traceback")
    p.add_argument(
        "--classify",
        action="store_true",
        help="Only classify the error — don't show full guidance",
    )
    p.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress evidence statistics in output",
    )
    p.set_defaults(func=_cmd_debug)

    # guild convert <path> [--format auto|skill|claude|cursorrules]
    p = sub.add_parser("convert", help="Convert SKILL.md / CLAUDE.md / .cursorrules to workflow pack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg convert SKILL.md
  borg convert .cursorrules --format cursorrules
  borg convert CLAUDE.md --format claude""")
    p.add_argument("path", help="Path to source file (SKILL.md, CLAUDE.md, or .cursorrules)")
    p.add_argument(
        "--format",
        choices=["auto", "skill", "claude", "cursorrules"],
        default="auto",
        help="Source format (default: auto-detect from filename)",
    )
    p.set_defaults(func=_cmd_convert)

    # guild generate <pack> [--format] [--output]
    p = sub.add_parser("generate", help="Export pack to .cursorrules / .clinerules / CLAUDE.md / .windsurfrules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg generate systematic-debugging --format all
  borg generate systematic-debugging --format cursorrules --output ./rules/
  borg generate systematic-debugging --format claude-md""")
    p.add_argument("pack", help="Pack name")
    p.add_argument(
        "--format",
        choices=["cursorrules", "clinerules", "claude-md", "windsurfrules", "all"],
        default="all",
        help="Output format (default: all)",
    )
    p.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory (default: print to stdout)",
    )
    p.set_defaults(func=_cmd_generate)

    # guild list
    p = sub.add_parser("list", help="List local packs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg list""")
    p.set_defaults(func=_cmd_list)

    # borg observe <task> [--context ...] [--error ...]
    p = sub.add_parser("observe", help="Record an observation as a trace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg observe 'fix django authentication bug'
  borg observe 'debug failing test in auth module' --context 'TypeError on login'
  borg observe 'migrate database schema' --error 'OperationalError: no such column'

Writes a trace to ~/.borg/traces.db so subsequent 'borg search' calls can
surface it. This is the CLI counterpart to the MCP borg_observe tool. Added
in v3.2.4 to fix the observe→search roundtrip bug from the P1.1 experiment.""")
    p.add_argument("task", nargs="+", help="Task description (required)")
    p.add_argument("--context", default="", help="Additional context (optional)")
    p.add_argument("--error", default="", help="Error message to associate with the trace (optional)")
    p.add_argument("--agent", default="cli", help="Agent id for provenance (default: cli)")
    p.add_argument("--json", action="store_true", help="Output raw JSON")
    p.set_defaults(func=_cmd_observe)

    # guild version
    p = sub.add_parser("version", help="Show version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg version""")
    p.set_defaults(func=_cmd_version)

    # guild autopilot
    p = sub.add_parser("autopilot", help="Zero-config setup: install MCP + skill + auto-suggest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg autopilot""")
    p.set_defaults(func=_cmd_autopilot)

    # guild setup-claude
    p = sub.add_parser("setup-claude", help="Configure guild MCP server for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg setup-claude""")
    p.set_defaults(func=_cmd_setup_claude)

    # guild setup-cursor
    p = sub.add_parser("setup-cursor", help="Configure guild MCP server for Cursor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg setup-cursor""")
    p.set_defaults(func=_cmd_setup_cursor)

    # borg start — interactive onboarding
    p = sub.add_parser("start", help="Get started — paste an error, get a fix in 30 seconds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg start              Interactive onboarding — paste an error, get guidance
  
First time? Just run:
  pip install agent-borg && borg start""")
    p.set_defaults(func=_cmd_start)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
