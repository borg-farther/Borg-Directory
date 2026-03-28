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
from borg.core.search import borg_search, borg_pull, borg_try, borg_init
from borg.core.search import generate_feedback as _core_generate_feedback
from borg.core.apply import apply_handler
from borg.core.publish import action_publish, action_list
from borg.core.convert import convert_auto, convert_skill, convert_claude_md, convert_cursorrules
from borg.core.dirs import get_borg_dir
from borg.core.session import load_persisted_sessions, _active_sessions
from borg.db.reputation import ReputationEngine
from borg.db.store import AgentStore


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
    raw = borg_search(args.query, mode=args.mode)
    if args.json:
        _print_json(raw)
        return 0
    data = json.loads(raw)
    if not data.get("success"):
        print(f"Error: {data.get('error', 'Unknown')}", file=sys.stderr)
        return 1
    matches = data.get("matches", [])
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
    """Create a pack scaffold or convert from a skill."""
    raw = borg_init(args.name)
    if _require_success(raw, ctx=" (skill not found)"):
        data = json.loads(raw)
        # Print the generated YAML content
        print(data.get("content", raw))
        if data.get("validation_errors"):
            print("Validation errors:", file=sys.stderr)
            for err in data["validation_errors"]:
                print(f"  - {err}", file=sys.stderr)
        if data.get("safety_warnings"):
            print("Safety warnings:", file=sys.stderr)
            for w in data["safety_warnings"]:
                print(f"  - {w}", file=sys.stderr)
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    """Start applying a pack to a task."""
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
        print("Awaiting approval")
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_publish(args: argparse.Namespace) -> int:
    """Publish a pack to GitHub."""
    raw = action_publish(path=args.path)
    if _require_success(raw, ctx=" (publish failed)"):
        _print_json(raw)
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_feedback(args: argparse.Namespace) -> int:
    """Generate feedback from a session."""
    # Load the session to get execution data
    from borg.core.session import load_session

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


def _cmd_convert(args: argparse.Namespace) -> int:
    """Convert a SKILL.md, CLAUDE.md, or .cursorrules file to a workflow pack."""
    import yaml

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


def _cmd_list(args: argparse.Namespace) -> int:
    """List local packs."""
    raw = action_list()
    data = json.loads(raw)
    if not data.get("success"):
        print(f"Error: {data.get('error', 'Unknown')}", file=sys.stderr)
        return 1

    artifacts = data.get("artifacts", [])
    packs = [a for a in artifacts if a.get("type") == "pack"]

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
# reputation: show agent reputation profile
# ---------------------------------------------------------------------------

def _cmd_reputation(args: argparse.Namespace) -> int:
    """Show reputation profile for an agent."""
    store = AgentStore()
    engine = ReputationEngine(store)
    profile = engine.build_profile(args.agent_id)

    if profile.last_active_at:
        last_active = profile.last_active_at.strftime("%Y-%m-%d %H:%M UTC")
    else:
        last_active = "never"

    print(f"Reputation Profile for Agent: {args.agent_id}")
    print("=" * 50)
    print(f"  Contribution Score:  {profile.contribution_score:.2f}")
    print(f"  Access Tier:         {profile.access_tier.value}")
    print(f"  Free-Rider Status:    {profile.free_rider_status.value}")
    print(f"  Packs Published:      {profile.packs_published}")
    print(f"  Packs Consumed:       {profile.packs_consumed}")
    print(f"  Last Active:         {last_active}")
    return 0


# ---------------------------------------------------------------------------
# status: show borg system status
# ---------------------------------------------------------------------------

def _cmd_status(args: argparse.Namespace) -> int:
    """Show borg system status."""
    borg_dir = get_borg_dir()
    db_path = borg_dir / "guild.db"

    # Load persisted sessions to get accurate count
    sessions = load_persisted_sessions()

    # Count active (running) sessions
    active_sessions = [s for s in sessions if s.get("status") == "running"]
    active_from_memory = [s for s in _active_sessions.values() if s.get("status") == "running"]
    all_running = {s["session_id"]: s for s in active_sessions + active_from_memory}.values()

    # Count packs in store
    store = AgentStore()
    packs = store.list_packs(limit=10000)
    pack_count = len(packs)

    # Count agents
    agents = store.list_agents(limit=10000)
    agent_count = len(agents)

    print(f"Borg System Status")
    print("=" * 50)
    print(f"  BORG_DIR:             {borg_dir}")
    print(f"  Database:             {db_path}")
    print(f"  Packs in Store:       {pack_count}")
    print(f"  Active Sessions:      {len(list(all_running))}")
    print(f"  Agent Count:          {agent_count}")

    running = list(all_running)
    if running:
        print()
        print("  Running Sessions:")
        for s in running:
            session_id = s.get("session_id", "?")
            pack_name = s.get("pack_name", "?")
            status = s.get("status", "?")
            print(f"    • {session_id}  [{status}]  ({pack_name})")

    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="borg",
        description="Borg — Semantic reasoning cache for AI agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # guild search <query>
    p = sub.add_parser("search", help="Search for packs")
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
    p = sub.add_parser("pull", help="Fetch and save pack locally")
    p.add_argument("uri", help="Pack URI (guild://, https://, or local path)")
    p.set_defaults(func=_cmd_pull)

    # guild try <uri>
    p = sub.add_parser("try", help="Preview pack without saving")
    p.add_argument("uri", help="Pack URI")
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON for programmatic use",
    )
    p.set_defaults(func=_cmd_try)

    # guild init <name>
    p = sub.add_parser("init", help="Create pack scaffold or convert from skill")
    p.add_argument("name", help="Skill name to convert")
    p.set_defaults(func=_cmd_init)

    # guild apply <pack> --task <task>
    p = sub.add_parser("apply", help="Start applying a pack")
    p.add_argument("pack", help="Pack name")
    p.add_argument("--task", required=True, help="Task description")
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON for programmatic use",
    )
    p.set_defaults(func=_cmd_apply)

    # guild publish <path>
    p = sub.add_parser("publish", help="Publish pack to GitHub")
    p.add_argument("path", help="Path to pack YAML or pack name")
    p.set_defaults(func=_cmd_publish)

    # guild feedback <session_id>
    p = sub.add_parser("feedback", help="Generate feedback from session")
    p.add_argument("session_id", help="Session ID")
    p.set_defaults(func=_cmd_feedback)

    # guild convert <path> [--format auto|skill|claude|cursorrules]
    p = sub.add_parser("convert", help="Convert SKILL.md / CLAUDE.md / .cursorrules to workflow pack")
    p.add_argument("path", help="Path to source file (SKILL.md, CLAUDE.md, or .cursorrules)")
    p.add_argument(
        "--format",
        choices=["auto", "skill", "claude", "cursorrules"],
        default="auto",
        help="Source format (default: auto-detect from filename)",
    )
    p.set_defaults(func=_cmd_convert)

    # guild list
    p = sub.add_parser("list", help="List local packs")
    p.set_defaults(func=_cmd_list)

    # guild version
    p = sub.add_parser("version", help="Show version")
    p.set_defaults(func=_cmd_version)

    # guild autopilot
    p = sub.add_parser("autopilot", help="Zero-config setup: install MCP + skill + auto-suggest")
    p.set_defaults(func=_cmd_autopilot)

    # guild setup-claude
    p = sub.add_parser("setup-claude", help="Configure guild MCP server for Claude Code")
    p.set_defaults(func=_cmd_setup_claude)

    # guild setup-cursor
    p = sub.add_parser("setup-cursor", help="Configure guild MCP server for Cursor")
    p.set_defaults(func=_cmd_setup_cursor)

    # guild reputation <agent_id>
    p = sub.add_parser("reputation", help="Show reputation profile for an agent")
    p.add_argument("agent_id", help="Agent ID")
    p.set_defaults(func=_cmd_reputation)

    # guild status
    p = sub.add_parser("status", help="Show borg system status")
    p.set_defaults(func=_cmd_status)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
