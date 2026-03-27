"""
Guild CLI — shell commands wrapping the core engine.

Usage:
    guild search <query>        — search for packs
    guild pull <uri>           — fetch and save pack locally
    guild try <uri>            — preview pack without saving
    guild init <name>          — create pack scaffold or convert from skill
    guild apply <pack> --task  — start applying a pack
    guild publish <path>       — publish pack to GitHub
    guild feedback <session_id> — generate feedback from session
    guild list                 — list local packs
    guild version              — show version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from guild import __version__
from guild.core.search import guild_search, guild_pull, guild_try, guild_init
from guild.core.search import generate_feedback as _core_generate_feedback
from guild.core.apply import apply_handler
from guild.core.publish import action_publish, action_list
from guild.core.convert import convert_auto, convert_skill, convert_claude_md, convert_cursorrules


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
    raw = guild_search(args.query, mode=args.mode)
    _print_json(raw)
    return 0


def _cmd_pull(args: argparse.Namespace) -> int:
    """Fetch and save a pack locally."""
    raw = guild_pull(args.uri)
    if _require_success(raw):
        data = json.loads(raw)
        print(f"Pulled pack '{data.get('name')}' -> {data.get('path')}")
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_try(args: argparse.Namespace) -> int:
    """Preview a pack without saving."""
    raw = guild_try(args.uri)
    if _require_success(raw, ctx=" (pack not found or invalid)"):
        _print_json(raw)
    else:
        _print_json(raw)
        return 1
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    """Create a pack scaffold or convert from a skill."""
    raw = guild_init(args.name)
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
    if _require_success(raw, ctx=" (pack not found)"):
        _print_json(raw)
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
    from guild.core.session import load_session

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
    print(f"guild {__version__}")
    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="guild",
        description="Guild — Semantic reasoning cache for AI agents.",
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
    p.set_defaults(func=_cmd_search)

    # guild pull <uri>
    p = sub.add_parser("pull", help="Fetch and save pack locally")
    p.add_argument("uri", help="Pack URI (guild://, https://, or local path)")
    p.set_defaults(func=_cmd_pull)

    # guild try <uri>
    p = sub.add_parser("try", help="Preview pack without saving")
    p.add_argument("uri", help="Pack URI")
    p.set_defaults(func=_cmd_try)

    # guild init <name>
    p = sub.add_parser("init", help="Create pack scaffold or convert from skill")
    p.add_argument("name", help="Skill name to convert")
    p.set_defaults(func=_cmd_init)

    # guild apply <pack> --task <task>
    p = sub.add_parser("apply", help="Start applying a pack")
    p.add_argument("pack", help="Pack name")
    p.add_argument("--task", required=True, help="Task description")
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

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
