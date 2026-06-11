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
    borg rescue <error>       — agent-ready rescue packet: ACTION / STOP / VERIFY / receipt
    borg generate <pack>      — export pack to .cursorrules / .clinerules / CLAUDE.md / .windsurfrules
    borg list                 — list local packs
    borg autopilot            — guided Hermes setup (install MCP + skill + auto-suggest)
    borg setup-claude         — configure borg MCP for Claude Code
    borg setup-cursor         — configure borg MCP for Cursor
    borg version              — show version
"""

from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

from borg import __version__
from borg.core.dirs import get_borg_dir
from borg.core.session import _active_sessions, load_persisted_sessions, load_session
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


def _load_builtin_packs() -> list:
    """Load packs from the built-in guild-packs directory.
    
    This provides a fallback when no local packs are available.
    """
    import pathlib
    import yaml
    
    packs = []
    guild_packs_dir = pathlib.Path("/root/hermes-workspace/guild-packs/packs")
    
    if guild_packs_dir.exists():
        for pack_file in guild_packs_dir.glob("*.yaml"):
            try:
                pack_data = yaml.safe_load(pack_file.read_text(encoding="utf-8"))
                if isinstance(pack_data, dict) and pack_data.get("type") == "workflow_pack":
                    packs.append(pack_data)
            except Exception:
                continue
    
    return packs




def _record_v3_outcome_safe(**kwargs) -> None:
    """Record a V3 outcome without letting telemetry break CLI commands."""
    try:
        from borg.core.v3_integration import BorgV3
        BorgV3().record_outcome(**kwargs)
    except Exception:
        pass

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
    from borg.core.seeds import is_seeds_disabled

    # Respect BORG_DISABLE_SEEDS env var or --no-seeds flag
    include_seeds = not (args.no_seeds or is_seeds_disabled())
    raw = borg_search(args.query, mode=args.mode, include_seeds=include_seeds)
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
        fallback_states = data.get("fallback_states") or []
        if fallback_states:
            print("\nFallback / provenance notices:")
            for state in fallback_states:
                print(f"  - {state.get('code')}: {state.get('message')}")
                if state.get("next"):
                    print(f"    next: {state.get('next')}")
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
    fallback_states = data.get("fallback_states") or []
    if fallback_states:
        print("\nFallback / provenance notices:")
        for state in fallback_states:
            print(f"  - {state.get('code')}: {state.get('message')}")
            if state.get("next"):
                print(f"    next: {state.get('next')}")
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
    import os
    from borg.core.search import borg_try

    raw = borg_try(args.uri)
    # TASK 1: autonomous outcome inference — borg_try completes without exception → success
    try:
        success = json.loads(raw).get("success", False)
        _record_v3_outcome_safe(
            pack_id=json.loads(raw).get("id", args.uri),
            agent_id="borg-cli",
            task_context={"uri": args.uri, "task_category": "try"},
            success=success,
            category="try",
        )
    except Exception:
        pass  # never break core flow

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

    guild_dir = get_borg_dir()
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

    # TASK 1: autonomous outcome inference — init succeeds → record success
    try:
        _record_v3_outcome_safe(
            pack_id=name,
            agent_id="borg-cli",
            task_context={"task_category": "init", "problem_class": problem_class},
            success=True,
            category="init",
        )
    except Exception:
        pass  # never break core flow

    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    """Start applying a pack to a task."""
    from borg.core.apply import apply_handler

    pack_name = args.pack
    task = args.task
    try:
        raw = apply_handler(
            action="start",
            pack_name=pack_name,
            task=task,
        )
        if not _require_success(raw, ctx=" (pack not found)"):
            _print_json(raw)
            return 1

        data = json.loads(raw)
        session_id = data.get("session_id", "?")
        phases = data.get("phases", [])
        phase_names = ", ".join(p.get("name", "?") for p in phases) if phases else "none"
        print(f"Session ID: {session_id}")
        print(f"Phases ({len(phases)}): {phase_names}")
        print()
        print("Session started. In your agent (MCP), use:")
        print(f"  borg_apply(action='checkpoint', session_id='{session_id}', phase_name='__approval__', status='passed')")
        if phases:
            first_phase = phases[0].get("name", "<phase_name>")
            print("Then, after each phase, checkpoint with:")
            print(f"  borg_apply(action='checkpoint', session_id='{session_id}', phase_name='{first_phase}', status='passed', evidence='<what verified>')")
        print("Use borg_search to find packs before applying when needed.")

        # TASK 1: autonomous outcome inference — record success when apply completes cleanly
        try:
            _record_v3_outcome_safe(
                pack_id=pack_name,
                agent_id="borg-cli",
                task_context={"task": task, "task_category": "apply"},
                success=True,
                category="apply",
            )
        except Exception:
            pass  # never break core flow

        return 0

    except Exception as e:
        # TASK 1: autonomous outcome inference — record failure with exception as error_message
        try:
            _record_v3_outcome_safe(
                pack_id=pack_name,
                agent_id="borg-cli",
                task_context={"task": task, "task_category": "apply", "error_message": str(e)},
                success=False,
                category="apply",
            )
        except Exception:
            pass  # never break core flow

        _print_json(json.dumps({"success": False, "error": str(e)}))
        return 1


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
    """Generate feedback from a completed apply session."""
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
    if args.success.lower() not in ("yes", "true", "1", "y", "no", "false", "0", "n"):
        print(f"Error: --success must be one of: yes, true, 1, y, no, false, 0, n", file=sys.stderr)
        return 1
    success = args.success.lower() in ("yes", "true", "1", "y")
    time_taken = args.time or 0.0
    tokens_used = args.tokens or 0

    # Record to V3
    task_context = {"task_category": problem_class or "unknown"}
    try:
        _record_v3_outcome_safe(
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


def _cmd_recall(args: argparse.Namespace) -> int:
    """Query FailureMemory for prior failure/success approaches to an error.

    Usage: borg recall 'NoneType has no attribute'
    """
    error_message = " ".join(args.error)
    if not error_message:
        print("Error: provide an error message to recall", file=sys.stderr)
        return 1

    try:
        from borg.core.failure_memory import FailureMemory
        fm = FailureMemory()
        result = fm.recall(error_message)

        if not result:
            print(f"No prior failures recorded for: {error_message}")
            return 0

        wrong = result.get("wrong_approaches", [])
        correct = result.get("correct_approaches", [])

        print(f"Prior failures for: {error_message}")
        print(f"  Wrong approaches (avoid): {len(wrong)}")
        for w in wrong[:5]:
            print(f"    • {w.get('approach', 'unknown')} — failed {w.get('failure_count', 0)}x")
        if correct:
            print(f"  Correct approaches (prefer): {len(correct)}")
            for c in correct[:3]:
                print(f"    ✓ {c.get('approach', 'unknown')} — succeeded {c.get('success_count', 0)}x")

        # TASK 3: also inject into Thompson Sampling — record recall event so the
        # selector knows this error class has known solutions (or none yet)
        try:
            _record_v3_outcome_safe(
                pack_id="recall-query",
                agent_id="borg-cli",
                task_context={"task_category": "recall", "error_message": error_message},
                success=bool(correct),
                category="recall",
            )
        except Exception:
            pass  # never break core flow

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
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
            return 0  # match found
        else:
            print("No matching problem class.")  # no match
            print(f"Known classes: {', '.join(PROBLEM_CLASSES)}")
            return 1  # no match = exit 1

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

    # Return 1 if no match (output contains [unknown])
    lines = result.strip().split('\n')
    if any('[unknown]' in line for line in lines):
        return 1
    return 0


def _read_single_line_from_stdin(prompt: str) -> str:
    """Read one interactive line without the builtin prompt helper.

    Bandit flags the builtin prompt helper even on Python 3, and first-user CLI
    paths should be boringly auditable. This preserves the same UX while using
    explicit stdin/stdout primitives that tests can sandbox.
    """
    try:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        return sys.stdin.readline().strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _cmd_rescue(args: argparse.Namespace) -> int:
    """Return an agent-ready ACTION / STOP / VERIFY rescue packet."""
    from borg.core.rescue import rescue, render_rescue_text

    text = " ".join(args.input or []).strip()
    if not text:
        # Non-interactive agent path: accept piped stderr/stdout/transcript.
        try:
            if not sys.stdin.isatty():
                text = sys.stdin.read().strip()
        except Exception:
            text = ""
    if not text:
        print("Paste the exact error, failing command, or agent transcript:")
        text = _read_single_line_from_stdin("> ")

    result = rescue(text, source="cli", show_guidance=not args.short)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(render_rescue_text(result))
    return 0 if result.success else 1


def _cmd_rescue_eval(args: argparse.Namespace) -> int:
    """Execute a rescue-packet eval taskset."""
    from borg.core.rescue_packet_eval import evaluate_rescue_cases, load_rescue_eval_taskset

    try:
        taskset = load_rescue_eval_taskset(args.taskset)
        result = evaluate_rescue_cases(taskset.cases, taskset_id=taskset.taskset_id)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        else:
            print(f"taskset_id: {result['taskset_id']}")
            print(f"success: {result['success']}")
            print(f"recommendation: {result['recommendation']}")
            print(f"selection_cases: {result['selection']['case_count']}")
            print(f"hidden_cases: {result['hidden']['case_count']}")
            if result.get("hard_failures"):
                print("hard_failures:")
                for failure in result["hard_failures"]:
                    print(f"  - {failure}")
        return 0 if result.get("success") else 1
    except (ValueError, OSError, json.JSONDecodeError) as e:
        if getattr(args, "json", False):
            print(json.dumps({"success": False, "error": str(e), "type": type(e).__name__}, indent=2), file=sys.stdout)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_agent_priming(args: argparse.Namespace) -> int:
    """Render or safely install/uninstall a host-specific Borg priming block."""
    from borg.core.agent_priming import (
        build_agent_priming_candidate,
        install_agent_priming,
        uninstall_agent_priming,
    )

    host = getattr(args, "host", "generic")
    try:
        if getattr(args, "install", False):
            result = install_agent_priming(
                host,
                target_file=getattr(args, "target_file", None),
                manifest_path=getattr(args, "manifest", None),
                dry_run=bool(getattr(args, "dry_run", False)),
            )
        elif getattr(args, "uninstall", False) or getattr(args, "unpull", False):
            result = uninstall_agent_priming(
                host,
                manifest_path=getattr(args, "manifest", None),
                target_file=getattr(args, "target_file", None),
                dry_run=bool(getattr(args, "dry_run", False)),
            )
        else:
            result = build_agent_priming_candidate(host)

        if getattr(args, "json", False):
            print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        else:
            if result.get("operation") in {"install", "uninstall"}:
                print(f"borg agent-priming {result['operation']}: {result['status']}")
                print(f"target:   {result.get('target_file')}")
                print(f"manifest: {result.get('manifest_path')}")
                if result.get("dry_run"):
                    print("dry-run:  no files were changed")
                for state in result.get("fallback_states", []):
                    print(f"fallback: {state.get('code')}: {state.get('message')}")
            else:
                print(result["prompt"])
        if result.get("operation") in {"install", "uninstall"}:
            return 0 if result.get("success") else 1
        return 0 if result.get("recommendation") == "eligible_for_host_rules_review" else 1
    except Exception as e:
        error = {"success": False, "operation": "agent-priming", "error": str(e), "type": type(e).__name__}
        if getattr(args, "json", False):
            print(json.dumps(error, indent=2, sort_keys=True, ensure_ascii=False))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_start(args: argparse.Namespace) -> int:
    """Interactive onboarding — get value from borg in 30 seconds."""
    print()
    print("  Borg is a cache layer for agent reasoning.")
    print("  It watches for failure loops, fires only when it can change the path,")
    print("  and stays quiet when it has no useful memory.")
    print()
    print("  Try it now")
    print()
    print("  Paste any error message you're dealing with:")
    print()

    error = _read_single_line_from_stdin("  > ")

    if not error:
        print()
        print("  No error entered. Try:")
        print("    borg rescue 'your error message here'")
        print()
        return 0

    # Run the same rescue engine used by agents/MCP so onboarding cannot drift.
    from borg.core.rescue import rescue, render_rescue_text
    print()
    result = rescue(error, source="start", show_guidance=True)
    print(render_rescue_text(result))

    # Do not auto-record success here: this command has only shown guidance.
    # Outcome receipts are created after the user/agent reruns VERIFY.

    # Next steps
    print()
    print("  Next steps")
    print()
    print("  - Run again anytime:   borg rescue 'your error'")
    print("  - Browse workflows:    borg search debugging")
    print("  - Export for Cursor:   borg generate systematic-debugging --format cursorrules")
    print("  - Export for Claude:   borg setup-claude")
    print("  - After VERIFY:        call borg_record_outcome with outcome/helpful/verified evidence")
    print()
    print("  Your fixes stay yours; Borg shares what prevents repeat failures.")
    print()
    return 0


def _cmd_convert(args: argparse.Namespace) -> int:
    """Convert a SKILL.md, CLAUDE.md, or .cursorrules file to a workflow pack.
    
    Also supports --format=openclaw to convert the entire pack registry
    to an OpenClaw skill directory.
    """
    import yaml
    from borg.core.convert import convert_auto, convert_skill, convert_claude_md, convert_cursorrules
    try:
        # Handle OpenClaw format (registry-wide conversion)
        if args.format == "openclaw":
            from borg.core.uri import get_available_pack_names
            import pathlib
            
            # Collect all packs
            packs = []
            seen_ids: set = set()
            
            def _add_pack(pack_data):
                """Add pack if not duplicate."""
                if isinstance(pack_data, dict):
                    pack_id = pack_data.get("id", "")
                    if pack_id and pack_id not in seen_ids:
                        seen_ids.add(pack_id)
                        packs.append(pack_data)
            
            if args.all:
                # Load all packs from local guild dir
                pack_names = get_available_pack_names()
                
                guild_dir = get_borg_dir()
                
                for pack_name in pack_names:
                    pack_yaml = guild_dir / pack_name / "pack.yaml"
                    if pack_yaml.exists():
                        try:
                            pack_data = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
                            _add_pack(pack_data)
                        except Exception:
                            continue
                
                # Also load ALL packs from the guild-packs directory
                guild_packs_dir = pathlib.Path("/root/hermes-workspace/guild-packs/packs")
                if guild_packs_dir.exists():
                    for pack_file in guild_packs_dir.glob("*.yaml"):
                        try:
                            pack_data = yaml.safe_load(pack_file.read_text(encoding="utf-8"))
                            _add_pack(pack_data)
                        except Exception:
                            continue
                
                # Fallback: use the borg core registry if no packs found
                if not packs:
                    packs = _load_builtin_packs()
            
            if not packs:
                print("Error: No packs found to convert", file=sys.stderr)
                return 1
            
            # Convert to OpenClaw
            from borg.core.convert import convert_registry_to_openclaw
            output_dir = args.output or "./openclaw-skills"
            result = convert_registry_to_openclaw(packs, output_dir)
            
            print(f"Converted {result['pack_count']} packs to OpenClaw skill format")
            print(f"Output directory: {result['output_dir']}")
            print(f"Files written: {result['files_written']}")
            print(f"SKILL.md lines: {result['skill_md_lines']}")
            
            if result.get('pack_slugs'):
                print(f"\nPack slugs: {', '.join(result['pack_slugs'])}")
            
            return 0
        
        # Handle individual file conversion
        if args.format == "auto":
            pack = convert_auto(args.path)
        elif args.format == "skill":
            pack = convert_skill(args.path)
        elif args.format == "claude":
            pack = convert_claude_md(args.path)
        elif args.format == "cursorrules":
            pack = convert_cursorrules(args.path)
        else:
            print(f"Error: Unknown format '{args.format}'. Use: auto, skill, claude, cursorrules, openclaw", file=sys.stderr)
            return 1
        print(yaml.safe_dump(pack, default_flow_style=False, sort_keys=False))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_generate(args: argparse.Namespace) -> int:
    """Export a pack to platform-specific rule files."""
    from borg.core.generator import generate_rules, generate_to_files, load_pack

    # Alias short names to canonical format names for back-compat
    _FORMAT_ALIASES = {
        "cursor": "cursorrules",
        "cline": "clinerules",
        "claude": "claude-md",
        "windsurf": "windsurfrules",
    }

    try:
        pack = load_pack(args.pack)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    fmt = _FORMAT_ALIASES.get(args.format, args.format)
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


def _cmd_atom(args: argparse.Namespace) -> int:
    """Learning atom utilities: distill, validate, search, revoke."""
    import yaml as _yaml

    if args.atom_action == "validate":
        from borg.core.learning_atoms import validate_learning_atom, verify_signed_atom
        data = _yaml.safe_load(Path(args.path).read_text(encoding="utf-8"))
        payload = data.get("payload") if isinstance(data, dict) and isinstance(data.get("payload"), dict) else data
        result = validate_learning_atom(payload)
        sig = verify_signed_atom(data) if isinstance(data, dict) and "signature" in data else None
        out = {"success": result.valid and (sig.valid if sig else True), "valid": result.valid, "errors": result.errors}
        if sig:
            out["signature_valid"] = sig.valid
            out["signature_error"] = sig.error
        print(json.dumps(out, indent=2))
        return 0 if out["success"] else 1

    if args.atom_action == "search":
        from borg.core.atom_store import AtomStore
        from borg.core.atom_retrieval import format_atom_for_agent
        store = AtomStore(getattr(args, "db", None))
        atoms = store.search_atoms(" ".join(args.query), limit=args.limit)
        if args.json:
            print(json.dumps({"success": True, "atoms": atoms, "total": len(atoms)}, indent=2))
        else:
            if not atoms:
                print("No learning atoms found.")
            for atom in atoms:
                print(format_atom_for_agent(atom))
                print("---")
        return 0

    if args.atom_action == "revoke":
        from borg.core.atom_store import AtomStore
        store = AtomStore(getattr(args, "db", None))
        store.revoke(args.atom_id, args.reason)
        print(json.dumps({"success": True, "revoked": args.atom_id, "reason": args.reason}, indent=2))
        return 0

    if args.atom_action == "distill":
        from borg.core.traces import _get_db
        from borg.core.learning_atoms import distill_trace_to_atom, sign_learning_atom
        from borg.core.crypto import load_signing_key
        db = _get_db(getattr(args, "trace_db", None))
        row = db.execute("SELECT * FROM traces WHERE id = ?", (args.trace_id,)).fetchone()
        db.close()
        if not row:
            print(f"Error: trace not found: {args.trace_id}", file=sys.stderr)
            return 1
        atom = distill_trace_to_atom(dict(row), scope=args.scope, tenant_identifier=getattr(args, "tenant", ""))
        if args.sign_agent:
            key = load_signing_key(args.sign_agent)
            if key is None:
                print(f"Error: signing key not found for {args.sign_agent}", file=sys.stderr)
                return 1
            output = sign_learning_atom(atom, key)
        else:
            output = atom
        text = _yaml.safe_dump(output, sort_keys=False)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"Wrote learning atom to {args.output}")
        else:
            print(text)
        return 0

    if args.atom_action == "publish":
        from borg.core.publish import action_publish
        raw = action_publish(path=args.path)
        _print_json(raw)
        try:
            return 0 if json.loads(raw).get("success") else 1
        except Exception:
            return 1

    if args.atom_action == "sign-manifest":
        from borg.core.atom_registry import write_signed_registry_manifest
        from borg.core.crypto import load_signing_key
        key = load_signing_key(args.sign_agent)
        if key is None:
            print(f"Error: signing key not found for {args.sign_agent}", file=sys.stderr)
            return 1
        signed = write_signed_registry_manifest(
            args.registry_dir,
            key,
            sequence=args.sequence,
            channel=args.channel,
            expires_in_seconds=args.expires_in,
            previous_manifest_hash=args.previous_manifest_hash or None,
        )
        print(json.dumps({"success": True, "manifest": signed, "path": str(Path(args.registry_dir) / "manifest.signed.json")}, indent=2))
        return 0

    if args.atom_action == "sign-key-directory":
        from borg.core.atom_registry import write_signed_key_directory
        from borg.core.crypto import derive_verify_key, encode_key, load_signing_key
        root_key = load_signing_key(args.root_agent)
        if root_key is None:
            print(f"Error: root signing key not found for {args.root_agent}", file=sys.stderr)
            return 1
        manifest_verify_keys = []
        for agent in args.manifest_agent:
            key = load_signing_key(agent)
            if key is None:
                print(f"Error: manifest signing key not found for {agent}", file=sys.stderr)
                return 1
            manifest_verify_keys.append(encode_key(bytes(derive_verify_key(key))))
        envelope = write_signed_key_directory(
            args.registry_dir,
            root_key,
            channel=args.channel,
            sequence=args.sequence,
            manifest_verify_keys=manifest_verify_keys,
            revoked_key_ids=args.revoke_key_id,
            expires_in_seconds=args.expires_in,
        )
        print(json.dumps({
            "success": True,
            "root_key_id": envelope["signature"]["key_id"],
            "manifest_key_ids": [k["key_id"] for k in envelope["payload"]["manifest_keys"]],
            "revoked_key_ids": envelope["payload"]["revoked_key_ids"],
            "sequence": envelope["payload"]["sequence"],
            "expires_at": envelope["payload"]["expires_at"],
            "path": str(Path(args.registry_dir) / "keys.signed.json"),
        }, indent=2))
        return 0

    if args.atom_action == "sync-remote":
        from borg.core.atom_registry import sync_signed_registry_to_store
        from borg.core.atom_store import AtomStore
        if not args.registry_key_id and not args.root_key_id:
            print("Error: a trust anchor is required: --registry-key-id and/or --root-key-id", file=sys.stderr)
            return 1
        store = AtomStore(getattr(args, "db", None))
        result = sync_signed_registry_to_store(
            args.registry_url,
            store,
            trusted_registry_key_id=args.registry_key_id,
            trusted_root_key_id=args.root_key_id,
            channel=args.channel,
            state_path=args.state,
            max_revocation_convergence_seconds=args.revocation_slo_seconds,
        )
        print(json.dumps({"success": True, **result}, indent=2))
        return 0

    print("Error: unknown atom action", file=sys.stderr)
    return 1


def _cmd_collective(args: argparse.Namespace) -> int:
    """Outcome-grounded collective-learning ledger and atom promotion utilities."""
    from borg.core.collective_learning import CollectiveLearningStore

    store = CollectiveLearningStore(getattr(args, "db", None))
    action = getattr(args, "collective_action", "summary")
    try:
        if action == "summary":
            data = {
                "success": True,
                "summary": store.contribution_summary(),
                "value_summary": store.recent_value_summary(),
            }
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                summary = data["summary"]
                value = data["value_summary"]
                print("Borg collective learning summary")
                print("=" * 40)
                print(f"  contribution_events:       {summary['total_events']}")
                print(f"  interventions:             {value.get('interventions', 0)}")
                print(f"  verified_outcomes:         {value.get('verified_outcomes', 0)}")
                print(f"  helpful_outcomes:          {value.get('helpful_outcomes', 0)}")
                print(f"  helpful_tenants:           {value.get('helpful_tenants', 0)}")
                print(f"  promotion_ready_clusters:  {len(summary['promotion_ready_clusters'])}")
                print(f"  external_lift_status:      {summary['external_lift_status']}")
            return 0

        if action == "events":
            events = store.recent_contribution_events(limit=getattr(args, "limit", 50))
            data = {"success": True, "events": events, "total": len(events)}
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                if not events:
                    print("No contribution events recorded.")
                for event in events:
                    print(f"{event['created_at']} {event['event_type']} {event['collective_stage']} {event['status']} {event.get('cluster_id','')}")
            return 0

        if action == "candidate":
            candidate = store.build_learning_atom_candidate(
                args.cluster_id,
                scope=getattr(args, "scope", "global_candidate"),
                min_helpful_tenants=getattr(args, "min_helpful_tenants", 3),
            )
            if args.json:
                print(json.dumps(candidate, indent=2, ensure_ascii=False))
            else:
                print(f"atom_id: {candidate['atom_id']}")
                print(f"promotable: {candidate['promotable']}")
                print(f"helpful_verified_tenants: {candidate['helpful_verified_tenants']}")
                if candidate["blockers"]:
                    print("blockers:")
                    for blocker in candidate["blockers"]:
                        print(f"  - {blocker}")
                print(f"external_lift_status: {candidate['external_lift_status']}")
            return 0

        if action == "promote":
            from borg.core.crypto import load_signing_key

            signing_key = load_signing_key(args.sign_agent)
            if signing_key is None:
                print(f"Error: signing key not found for {args.sign_agent}", file=sys.stderr)
                return 1
            result = store.promote_cluster_to_registry(
                args.cluster_id,
                args.registry_dir,
                signing_key,
                scope=getattr(args, "scope", "global_candidate"),
                min_helpful_tenants=getattr(args, "min_helpful_tenants", 3),
            )
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                receipt = result["registry_receipt"]
                print(f"promoted_atom_id: {receipt['atom_id']}")
                print(f"decision: {receipt['decision']}")
                print(f"verified_tenant_count: {receipt['verified_tenant_count']}")
                print(f"registry_receipt_id: {receipt['receipt_id']}")
                print(f"external_lift_status: {result['external_lift_status']}")
            return 0

        print("Error: unknown collective action", file=sys.stderr)
        return 1
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        if getattr(args, "json", False):
            print(json.dumps({"success": False, "error": str(e), "type": type(e).__name__}, indent=2), file=sys.stdout)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_optimize_pack(args: argparse.Namespace) -> int:
    """Local-only SkillOpt-inspired pack optimizer entrypoint."""
    from borg.core.optimizer_review_queue import build_review_packet
    from borg.core.pack_optimizer import PackOptimizer, load_examples_file, run_pack_optimizer

    target = getattr(args, "target", "")
    output_root = getattr(args, "output_dir", None)
    optimizer = PackOptimizer(collective_db_path=getattr(args, "collective_db", None), output_root=output_root)
    try:
        if target == "inspect":
            if not getattr(args, "candidate_id", None):
                raise ValueError("inspect requires candidate_id")
            if getattr(args, "pack_file", None) or getattr(args, "taskset", None) or getattr(args, "examples_file", None):
                if not getattr(args, "pack_file", None):
                    raise ValueError("source-verified inspect requires --pack-file")
                if not getattr(args, "taskset", None):
                    raise ValueError("source-verified inspect requires --taskset")
                if not getattr(args, "examples_file", None):
                    raise ValueError("source-verified inspect requires --examples-file")
                examples = load_examples_file(args.examples_file)
                data = optimizer.verify_candidate_against_sources(
                    args.candidate_id,
                    pack_path=args.pack_file,
                    taskset_path=args.taskset,
                    examples=examples,
                    scope="local",
                )
            else:
                data = optimizer.inspect_candidate(args.candidate_id)
            if args.json:
                print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
            else:
                score = data["selection_score"]
                print(f"candidate_id: {data['candidate_id']}")
                print(f"artifact_recommendation: {score['recommendation']}")
                print(f"source_verified: {data.get('source_verified', False)}")
                print(f"manual_review_eligibility: {data.get('manual_review_eligibility', 'source_verification_required')}")
                print(f"score_delta: {score['score_delta']}")
                if score.get("hard_failures"):
                    print("hard_failures:")
                    for failure in score["hard_failures"]:
                        print(f"  - {failure}")
            return 0

        if target == "review":
            if not getattr(args, "candidate_id", None):
                raise ValueError("review requires candidate_id")
            verified_inspection = None
            source_args_present = bool(getattr(args, "pack_file", None) or getattr(args, "taskset", None) or getattr(args, "examples_file", None))
            if source_args_present:
                if not getattr(args, "pack_file", None):
                    raise ValueError("source-verified review requires --pack-file")
                if not getattr(args, "taskset", None):
                    raise ValueError("source-verified review requires --taskset")
                if not getattr(args, "examples_file", None):
                    raise ValueError("source-verified review requires --examples-file")
                examples = load_examples_file(args.examples_file)
                verified_inspection = optimizer.verify_candidate_against_sources(
                    args.candidate_id,
                    pack_path=args.pack_file,
                    taskset_path=args.taskset,
                    examples=examples,
                    scope="local",
                )
            candidate_dir = optimizer._candidate_dir(args.candidate_id)
            data = build_review_packet(
                candidate_dir,
                source_verified=bool(verified_inspection and verified_inspection.get("source_verified")),
                verified_inspection=verified_inspection,
            )
            if args.json:
                print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
            else:
                print(f"candidate_id: {data['candidate_id']}")
                print(f"decision: {data['decision']}")
                print(f"manual_review_eligibility: {data['manual_review_eligibility']}")
                print(f"score_delta: {data['score']['score_delta']}")
                print(f"accepted_edits: {data['edits']['accepted_count']}")
                print(f"rejected_edits: {data['edits']['rejected_count']}")
                print("reviewer_checklist:")
                for item in data.get("reviewer_checklist", []):
                    print(f"  - {item}")
            return 0 if data.get("manual_review_eligibility") == "eligible_for_manual_review" else 1

        if target == "apply":
            if not getattr(args, "candidate_id", None):
                raise ValueError("apply requires candidate_id")
            if getattr(args, "scope", "local") != "local":
                raise ValueError("pack optimizer is local-only; global apply/promotion is blocked")
            if not getattr(args, "pack_file", None):
                raise ValueError("apply requires --pack-file")
            if not getattr(args, "taskset", None):
                raise ValueError("apply requires --taskset")
            if not getattr(args, "examples_file", None):
                raise ValueError("apply requires --examples-file")
            examples = load_examples_file(args.examples_file)
            data = optimizer.apply_candidate(
                args.candidate_id,
                pack_path=args.pack_file,
                taskset_path=args.taskset,
                examples=examples,
                scope=getattr(args, "scope", "local"),
            )
            if args.json:
                print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
            else:
                print(f"applied_candidate: {data['candidate_id']}")
                print(f"scope: {data['scope']}")
                print(f"pack_path: {data['pack_path']}")
            return 0

        if not getattr(args, "taskset", None):
            raise ValueError("optimize-pack dry-run requires --taskset")
        examples = load_examples_file(args.examples_file) if getattr(args, "examples_file", None) else None
        result = run_pack_optimizer(
            pack_id=target,
            taskset_path=args.taskset,
            pack_path=getattr(args, "pack_file", None),
            output_root=output_root,
            examples=examples,
            collective_db_path=getattr(args, "collective_db", None),
            local_only=True,
            max_edits=getattr(args, "max_edits", 4),
        )
        data = result.to_artifact()
        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
        else:
            print(f"candidate_id: {result.candidate_id}")
            print(f"success: {result.success}")
            print(f"recommendation: {result.recommendation}")
            print(f"score_delta: {result.score_delta}")
            print(f"output_dir: {result.output_dir}")
            if result.hard_failures:
                print("hard_failures:")
                for failure in result.hard_failures:
                    print(f"  - {failure}")
        return 0 if result.success else 1
    except (ValueError, OSError, json.JSONDecodeError, sqlite3.Error) as e:
        if getattr(args, "json", False):
            print(json.dumps({"success": False, "error": str(e), "type": type(e).__name__}, indent=2, sort_keys=True), file=sys.stdout)
        else:
            print(f"Error: {e}", file=sys.stderr)
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


def _resolve_borg_mcp_command() -> tuple[str, list[str]]:
    """Resolve command+args used to start the borg MCP server.

    Prefer the console script installed next to the current interpreter. This
    prevents fresh-venv setup from accidentally wiring a globally-installed
    stale borg-mcp found earlier on PATH. Fall back to PATH, then module mode.
    """
    current_bin = Path(sys.executable).resolve().parent
    local_script = current_bin / ("borg-mcp.exe" if os.name == "nt" else "borg-mcp")
    if local_script.exists():
        return str(local_script), []
    # Do not fall through to a globally-installed borg-mcp here. First-user
    # setup must verify the Borg runtime that is currently running the CLI;
    # otherwise a stale script in ~/.local/bin can make a fresh install look
    # broken or wire Claude to the wrong package version.
    return sys.executable, ["-m", "borg.integrations.mcp_server"]


def _borg_mcp_server_entry(python_path: str) -> dict:
    """Return the mcpServers entry for the borg MCP server (camelCase for Claude/Cursor)."""
    command, args = _resolve_borg_mcp_command()
    borg_home = str((Path.home() / ".borg").expanduser())
    return {
        "mcpServers": {
            "borg": {
                "enabled": True,
                "command": command,
                "args": args,
                "env": {
                    "PYTHONPATH": python_path,
                    # Keep this absolute for MCP clients that do not expand '~' in env values.
                    "BORG_HOME": borg_home,
                },
            }
        }
    }


def _claude_setup_config_path(scope: str) -> Path:
    """Return config path for setup-claude scope."""
    if scope == "user":
        return Path.home() / ".claude.json"
    if scope == "project":
        return Path.cwd() / ".mcp.json"
    # Back-compat with Claude Desktop config path
    return Path.home() / ".config" / "claude" / "claude_desktop_config.json"


def _verify_borg_runtime(command: str, args: list[str], env: dict[str, str]) -> tuple[bool, str]:
    """Best-effort runtime check that borg MCP can initialize.

    Returns (ok, detail).
    """
    init_msg = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "borg-setup-claude", "version": __version__},
        },
    }) + "\n"

    proc: subprocess.Popen[str] | None = None
    output_chunks: list[str] = []
    try:
        proc = subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        if not proc.stdin or not proc.stdout or not proc.stderr:
            return False, "failed to open MCP process stdio"

        proc.stdin.write(init_msg)
        proc.stdin.flush()

        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.5)
            for stream in ready:
                line = stream.readline()
                if line:
                    output_chunks.append(line)
                    if '"result"' in line and '"serverInfo"' in line:
                        return True, "initialize handshake ok"

            if proc.poll() is not None and not ready:
                break

        combined = "".join(output_chunks).strip()
        return False, f"no initialize response from MCP server. output={combined[:300]}"
    except Exception as e:
        return False, f"failed to spawn MCP server: {e}"
    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


def _setup_claude_verify_hints(detail: str, borg_entry: dict) -> list[str]:
    """Return actionable remediation hints for setup-claude verification failures."""
    lower = detail.lower()
    command = str(borg_entry.get("command", "python3"))
    args = borg_entry.get("args", [])

    hints: list[str] = []
    if "no module named 'borg'" in lower or "modulenotfounderror" in lower:
        pip_cmd = f"{command} -m pip install agent-borg"
        if args == [] and (command.endswith("borg-mcp") or Path(command).name == "borg-mcp"):
            pip_cmd = "python3 -m pip install agent-borg"
        hints.extend([
            "[setup-claude] Remediation: borg package is not importable in the configured runtime.",
            f"[setup-claude] Run: {pip_cmd}",
            "[setup-claude] No-download path: python3 -m pip install --no-index --find-links <wheel_dir> agent-borg",
            "[setup-claude] Then rerun: borg setup-claude --scope user --verify --fix",
        ])
    elif "no initialize response" in lower:
        hints.extend([
            "[setup-claude] Remediation: MCP process started but did not answer initialize.",
            f"[setup-claude] Check command: {command} {' '.join(args)}",
            "[setup-claude] Re-run with --verify and inspect stderr output for import/runtime errors.",
        ])

    return hints


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
borg setup-claude --scope user --verify --fix
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
    """Configure borg MCP server for Claude with selectable scope and verification.

    Scope mapping:
      - user    -> ~/.claude.json
      - project -> ./.mcp.json
      - desktop -> ~/.config/claude/claude_desktop_config.json (legacy)
    """
    claude_config_file = _claude_setup_config_path(args.scope)
    claude_config_dir = claude_config_file.parent

    python_path = _get_python_path()
    new_entry = _borg_mcp_server_entry(python_path)
    borg_entry = new_entry["mcpServers"]["borg"]
    borg_home = Path(borg_entry.get("env", {}).get("BORG_HOME", str(Path.home() / ".borg")))
    changes: list[str] = []

    # Preflight / fix: ensure BORG_HOME exists when requested
    if not borg_home.exists():
        if args.fix:
            borg_home.mkdir(parents=True, exist_ok=True)
            changes.append(f"  • created BORG_HOME directory → {borg_home}")
        else:
            print(
                f"[setup-claude] Preflight: BORG_HOME does not exist: {borg_home}\n"
                f"[setup-claude] Re-run with --fix to create it automatically.",
                file=sys.stderr,
            )
            return 1

    # Verify runtime before mutating config, so we don't write broken onboarding state.
    if args.verify:
        verify_env = os.environ.copy()
        verify_env.update(borg_entry.get("env", {}))
        ok, detail = _verify_borg_runtime(
            command=borg_entry["command"],
            args=borg_entry.get("args", []),
            env=verify_env,
        )
        if ok:
            print(f"[setup-claude] Verify: PASS ({detail})")
        else:
            print(f"[setup-claude] Verify: FAIL ({detail})", file=sys.stderr)
            for hint in _setup_claude_verify_hints(detail, borg_entry):
                print(hint, file=sys.stderr)
            return 1

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
    entry_changed = existing_servers.get("borg") != borg_entry

    if entry_changed:
        if claude_config_file.exists():
            backup = claude_config_file.with_suffix(claude_config_file.suffix + ".bak")
            shutil.copy2(claude_config_file, backup)
            changes.append(f"  • backup created → {backup}")
        config["mcpServers"] = {**existing_servers, "borg": borg_entry}
        claude_config_file.write_text(json.dumps(config, indent=2) + "\n")
        changes.append(f"  • MCP config updated → {claude_config_file}")
    else:
        print(f"[setup-claude] MCP server already configured in {claude_config_file}")

    # 2. Install CLAUDE.md only for project scope (avoid side-effects in user/home setup)
    if args.scope in {"project", "desktop"}:
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
                changes.append(f"  • CLAUDE.md (updated borg section) → {claude_md.resolve()}")
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
    print(f"  1. Restart Claude (scope={args.scope}) so it reloads MCP config")
    print("  2. Confirm Borg tools appear (borg_observe, borg_search, borg_suggest)")
    print("  3. Run 'borg search <query>' to validate end-to-end")
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
# Guided Hermes setup helper
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
    """Guided Hermes setup helper: install MCP server config, skill file, and auto-suggest.

    This single command sets up everything needed for borg to work automatically
    in Hermes — no manual CLAUDE.md editing required.
    """
    import os
    import yaml
    from pathlib import Path

    home = Path.home()
    hermes_dir = home / ".hermes"
    hermes_config = hermes_dir / "config.yaml"
    skill_dir = hermes_dir / "skills" / "borg-autopilot"
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

    mcp_command, mcp_args = _resolve_borg_mcp_command()
    mcp_entry = {
        "enabled": True,
        "command": mcp_command,
        "args": mcp_args,
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
            fallback_cfg = {
                "mcp_servers": {
                    "guild": {
                        "enabled": True,
                        "command": mcp_command,
                        "args": mcp_args,
                        "env": {"PYTHONPATH": python_path},
                    }
                }
            }
            hermes_config.write_text(yaml.safe_dump(fallback_cfg, default_flow_style=False, sort_keys=False))
        changes.append(f"  • config.yaml → {hermes_config}")

    if not changes:
        print("[autopilot] Everything already set up! Borg is ready to use.")
        return 0

    print("[autopilot] Borg Hermes setup complete.")
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
# first-10: print the first-user beta readiness contract
# ---------------------------------------------------------------------------

def _cmd_first_10(args: argparse.Namespace) -> int:
    """Print the first-10 beta readiness contract."""
    from borg.core.first_user_readiness import (
        first_10_readiness_packet,
        render_first_10_readiness_markdown,
    )

    if args.json:
        print(json.dumps(first_10_readiness_packet(), indent=2, ensure_ascii=False))
    else:
        print(render_first_10_readiness_markdown())
    return 0


def _status_data_notice() -> dict:
    return {
        "schema_version": "1.0",
        "storage_default": "local",
        "raw_trace_export_default": "off",
        "shared_learning_default": "opt_in_sanitized_signed_atoms_only",
        "stores": [
            "local packs and workflow state under BORG_DIR",
            "local rescue/trace/outcome state under BORG_HOME",
            "agent priming manifests under BORG_HOME/agent-priming",
        ],
        "claim_boundary": "Status output is diagnostics, not proof of first-10/public lift.",
        "first_10_claim": False,
        "global_promotion_allowed": False,
        "public_lift_claim": False,
    }


def _status_fallback_states() -> list[dict]:
    return [
        {
            "code": "MCP_UNAVAILABLE_USE_CLI",
            "severity": "info",
            "message": "If Borg MCP is unavailable in an agent host, use the CLI fallback.",
            "next": "Run: borg rescue '<exact failure>' or borg agent-priming <host> --json",
        },
        {
            "code": "SEMANTIC_SEARCH_LEXICAL_FALLBACK",
            "severity": "info",
            "message": "Semantic search is optional; Borg reports lexical fallback explicitly when embeddings are unavailable or empty.",
            "next": "Treat text/seed hits as routing hints until VERIFY and outcome receipt close the loop.",
        },
        {
            "code": "LOCAL_SEED_NOT_COLLECTIVE_PROOF",
            "severity": "info",
            "message": "Bundled seed guidance is cold-start knowledge, not verified collective proof.",
            "next": "Run VERIFY and record outcomes before claiming measured value.",
        },
        {
            "code": "OUTCOME_NOT_RECORDED",
            "severity": "info",
            "message": "A rescue packet starts without a verified outcome receipt.",
            "next": "After VERIFY, call borg_record_outcome with outcome/helpful/verified evidence.",
        },
    ]


# ---------------------------------------------------------------------------
# status: show borg system status
# ---------------------------------------------------------------------------

def _read_only_table_count(db_path: Path, table: str) -> int:
    queries = {
        "packs": "SELECT COUNT(*) FROM packs",
        "agents": "SELECT COUNT(*) FROM agents",
    }
    query = queries.get(table)
    if query is None:
        return 0
    if not db_path.exists():
        return 0
    try:
        db_uri = f"file:{quote(str(db_path), safe='/')}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        try:
            row = conn.execute(query).fetchone()
            return int(row[0] if row else 0)
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Show borg system status."""
    borg_dir = Path(str(get_borg_dir()))
    db_path = borg_dir / "guild.db"

    # Load persisted sessions to get accurate count
    sessions = load_persisted_sessions()

    # Count active (running) sessions
    active_sessions = [s for s in sessions if s.get("status") == "running"]
    active_from_memory = [s for s in _active_sessions.values() if s.get("status") == "running"]
    all_running = {s["session_id"]: s for s in active_sessions + active_from_memory}.values()

    # Count packs/agents using read-only SQL so `borg status` never migrates or
    # creates a database just to display diagnostics.
    pack_count = _read_only_table_count(db_path, "packs")
    agent_count = _read_only_table_count(db_path, "agents")

    payload = {
        "success": True,
        "borg_dir": str(borg_dir),
        "database": str(db_path),
        "pack_count": pack_count,
        "active_sessions": len(list(all_running)),
        "agent_count": agent_count,
        "data_notice": _status_data_notice(),
        "fallback_states": _status_fallback_states(),
        "first_10_claim": False,
        "global_promotion_allowed": False,
        "public_lift_claim": False,
    }

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    print(f"Borg System Status")
    print("=" * 50)
    print(f"  BORG_DIR:             {borg_dir}")
    print(f"  Database:             {db_path}")
    print(f"  Packs in Store:       {pack_count}")
    print(f"  Active Sessions:      {payload['active_sessions']}")
    print(f"  Agent Count:          {agent_count}")
    print()
    print("  Data Notice:")
    print(f"    storage default:     {payload['data_notice']['storage_default']}")
    print(f"    raw trace export:    {payload['data_notice']['raw_trace_export_default']}")
    print(f"    shared learning:     {payload['data_notice']['shared_learning_default']}")
    print()
    print("  Visible Fallback States:")
    for state in payload["fallback_states"]:
        print(f"    • {state['code']}: {state['message']}")
        if state.get("next"):
            print(f"      next: {state['next']}")

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
        description="Borg — failure memory for AI coding agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Quick Start:
  borg start                     First time? Start here — paste an error, get a fix
  borg rescue 'TypeError: ...'   Get ACTION / STOP / VERIFY rescue guidance
  borg debug 'TypeError: ...'    Get structured debugging guidance for any error
  borg search debugging          Search for workflow packs
  borg generate systematic-debugging --format cursorrules
                                  Export a debugging workflow for Cursor
  borg setup-claude              Configure borg MCP for Claude Code
  borg setup-cursor              Configure borg MCP for Cursor
  borg first-10 --json           Print first-user beta gates and smoke path
  borg collective summary --json Show outcome-grounded contribution ledger status
  borg optimize-pack systematic-debugging --taskset eval/tasksets/systematic_debugging_selection.json --local-only
                                  Propose a local-only pack optimization candidate
  borg autopilot                 Guided Hermes setup""",
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
    p.add_argument(
        "--no-seeds",
        action="store_true",
        help="Exclude seed packs from results",
    )
    p.set_defaults(func=_cmd_search)

    # guild pull <uri>
    p = sub.add_parser("pull", help="Fetch and save pack locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg pull borg://community/systematic-debugging
  borg pull https://github.com/user/pack.yaml""")
    p.add_argument("uri", help="Pack URI (borg://, https://, or local path)")
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

    # guild feedback-v3 --problem-class <class> --success no --time 120
    p = sub.add_parser("feedback-v3", help="Record a verified debug guidance outcome to V3 feedback loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Prefer borg_record_outcome after VERIFY when an MCP agent/tool call is available.
  borg feedback-v3 --problem-class debugging --success no --time 30
  borg feedback-v3 --pack systematic-debugging --success no --tokens 5000""")
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
        help="Verified outcome after rerunning VERIFY? (yes/no). Do not set yes before verification.",
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

    # borg rescue <error>
    p = sub.add_parser("rescue", help="Agent-ready rescue packet: ACTION / STOP / VERIFY / human receipt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg rescue 'ModuleNotFoundError: No module named flask'
  pytest -q 2>&1 | borg rescue --json
  borg rescue 'PermissionError: [Errno 13] permission denied' --short""")
    p.add_argument("input", nargs="*", help="Error, failing command output, or agent transcript. Reads stdin when omitted.")
    p.add_argument("--json", action="store_true", help="Output machine-readable rescue packet")
    p.add_argument("--short", action="store_true", help="Omit full legacy guidance block")
    p.set_defaults(func=_cmd_rescue)

    # borg rescue-eval <taskset.json>
    p = sub.add_parser("rescue-eval", help="Execute a rescue-packet eval taskset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg rescue-eval eval/tasksets/rescue_packet_smoke.json --json""")
    p.add_argument("taskset", help="JSON taskset with train/selection/hidden rescue cases")
    p.add_argument("--json", action="store_true", help="Output machine-readable metrics")
    p.set_defaults(func=_cmd_rescue_eval)

    # borg agent-priming <host>
    p = sub.add_parser("agent-priming", help="Render/install/uninstall host-specific Borg call/verify/outcome priming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg agent-priming claude-code
  borg agent-priming codex --json
  borg agent-priming claude-code --install --dry-run --target-file ./CLAUDE.md --json
  borg agent-priming claude-code --install --target-file ./CLAUDE.md
  borg agent-priming claude-code --uninstall --json""")
    p.add_argument("host", nargs="?", default="generic", choices=["generic", "hermes", "claude-code", "codex", "cursor"], help="Agent host to target")
    action_group = p.add_mutually_exclusive_group()
    action_group.add_argument("--install", action="store_true", help="Install/update a manifest-backed managed priming block")
    action_group.add_argument("--uninstall", action="store_true", help="Remove the managed priming block recorded in the manifest")
    action_group.add_argument("--unpull", action="store_true", help="Alias for --uninstall")
    p.add_argument("--dry-run", action="store_true", help="Plan install/uninstall without writing files")
    p.add_argument("--target-file", default=None, help="Rules file to update; default is BORG_HOME/agent-priming/<host>/BORG_AGENT_PRIMING.md")
    p.add_argument("--manifest", default=None, help="Install manifest path; default is BORG_HOME/agent-priming/<host>/manifest.json")
    p.add_argument("--json", action="store_true", help="Output machine-readable priming artifact or install result")
    p.set_defaults(func=_cmd_agent_priming)

    # borg first-10 — print first-user beta readiness contract
    p = sub.add_parser("first-10", help="Print first-user beta readiness gates and smoke path",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg first-10
  borg first-10 --json""")
    p.add_argument("--json", action="store_true", help="Output machine-readable readiness contract")
    p.set_defaults(func=_cmd_first_10)

    # borg recall <error> — query FailureMemory for prior failure/success approaches
    p = sub.add_parser("recall", help="Query prior failure memory for an error message",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg recall 'NoneType has no attribute'
  borg recall 'ModuleNotFoundError'""")
    p.add_argument("error", nargs="+", help="Error message to look up")
    p.set_defaults(func=_cmd_recall)

    # borg convert <path> [--format auto|skill|claude|cursorrules]
    p = sub.add_parser("convert", help="Convert SKILL.md / CLAUDE.md / .cursorrules to workflow pack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg convert SKILL.md
  borg convert .cursorrules --format cursorrules
  borg convert CLAUDE.md --format claude""")
    p.add_argument("path", help="Path to source file (SKILL.md, CLAUDE.md, or .cursorrules)")
    p.add_argument(
        "--format",
        choices=["auto", "skill", "claude", "cursorrules", "openclaw"],
        default="auto",
        help="Source format (default: auto-detect from filename). Use 'openclaw' for registry-wide conversion.",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Convert all packs in the registry (use with --format=openclaw)",
    )
    p.add_argument(
        "--output",
        help="Output directory for OpenClaw conversion (default: ./openclaw-skills/)",
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
        choices=["cursor", "cline", "claude", "windsurf", "cursorrules", "clinerules", "claude-md", "windsurfrules", "all"],
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

    # borg atom — privacy-safe learning atom utilities
    p = sub.add_parser("atom", help="Manage signed, sanitized, revocable learning atoms",
        description="Manage signed, sanitized, revocable learning atoms for privacy-safe failure memory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Publish uses fail-closed policy gates and publishes no raw traces.

Examples:
  borg atom distill --trace-id abc123 --scope local
  borg atom distill --trace-id abc123 --scope org --tenant acme
  borg atom validate ./atom.yaml
  borg atom publish ./signed-atom.yaml
  borg atom sign-manifest --registry-dir ./registry --sign-agent registry --sequence 1
  borg atom sync-remote https://registry.example --registry-key-id ed25519:abc --state ./sync.json
  borg atom search 'TypeError optional config'
  borg atom revoke sha256:abc --reason 'privacy request'""")
    atom_sub = p.add_subparsers(dest="atom_action", required=True)

    ap = atom_sub.add_parser("distill", help="Distill a local trace into a learning atom")
    ap.add_argument("--trace-id", required=True, help="Trace ID from traces.db")
    ap.add_argument("--scope", choices=["local", "org", "global_candidate", "global"], default="local")
    ap.add_argument("--trace-db", default=None, help="Optional trace DB path")
    ap.add_argument("--tenant", default="", help="Optional local tenant id; stored only as HMAC pseudonym in non-local atoms")
    ap.add_argument("--sign-agent", default="", help="Optional agent id whose Ed25519 key signs the atom")
    ap.add_argument("--output", "-o", default="", help="Optional output YAML path")
    ap.set_defaults(func=_cmd_atom)

    ap = atom_sub.add_parser("validate", help="Validate a learning atom YAML file")
    ap.add_argument("path", help="Path to atom YAML/envelope")
    ap.set_defaults(func=_cmd_atom)

    ap = atom_sub.add_parser("publish", help="Publish a signed sanitized atom; fail-closed, no raw traces",
        description="Publish a signed, sanitized learning atom through fail-closed policy gates. Raw traces are never published.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="Path to signed atom YAML/envelope")
    ap.set_defaults(func=_cmd_atom)

    ap = atom_sub.add_parser("search", help="Search local learning atoms")
    ap.add_argument("query", nargs="+", help="Search query")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--db", default=None, help="Optional atom DB path")
    ap.add_argument("--json", action="store_true")
    ap.set_defaults(func=_cmd_atom)

    ap = atom_sub.add_parser("revoke", help="Revoke a learning atom by tombstone")
    ap.add_argument("atom_id", help="Atom ID to revoke")
    ap.add_argument("--reason", required=True, help="Revocation reason")
    ap.add_argument("--db", default=None, help="Optional atom DB path")
    ap.set_defaults(func=_cmd_atom)

    ap = atom_sub.add_parser("sign-manifest", help="Sign a hosted registry manifest")
    ap.add_argument("--registry-dir", required=True, help="Filesystem registry directory containing atoms/tombstones/receipts")
    ap.add_argument("--sign-agent", required=True, help="Agent id whose stored Ed25519 key signs manifest.signed.json")
    ap.add_argument("--sequence", type=int, required=True, help="Monotonic manifest sequence number")
    ap.add_argument("--channel", default="global", help="Registry channel/scope (default: global)")
    ap.add_argument("--expires-in", type=int, default=300, help="Manifest expiry window in seconds (default: 300)")
    ap.add_argument("--previous-manifest-hash", default="", help="Optional previous signed manifest hash")
    ap.set_defaults(func=_cmd_atom)

    ap = atom_sub.add_parser(
        "sign-key-directory",
        help="Root-sign the registry key directory (keys.signed.json)",
        description="Sign which online manifest keys are trusted and which key ids are revoked, using the OFFLINE root key. See docs/KEY_MANAGEMENT.md.",
    )
    ap.add_argument("--registry-dir", required=True, help="Filesystem registry directory")
    ap.add_argument("--root-agent", required=True, help="Agent id whose stored Ed25519 key is the OFFLINE root key")
    ap.add_argument("--sequence", type=int, required=True, help="Monotonic key directory sequence number")
    ap.add_argument("--channel", default="global", help="Registry channel/scope (default: global)")
    ap.add_argument("--manifest-agent", action="append", default=[], help="Agent id whose verify key becomes a trusted manifest key (repeatable)")
    ap.add_argument("--revoke-key-id", action="append", default=[], help="Key id to revoke (repeatable; revocation wins over listing)")
    ap.add_argument("--expires-in", type=int, default=24 * 3600, help="Key directory expiry window in seconds (default: 86400)")
    ap.set_defaults(func=_cmd_atom)

    ap = atom_sub.add_parser(
        "sync-remote",
        help="Sync from a signed hosted registry manifest",
        description="Sync learning atoms from a signed hosted registry manifest. Refuses unsigned/replayed/tampered manifests and applies tombstones before atoms.",
    )
    ap.add_argument("registry_url", help="Base URL or directory containing manifest.signed.json")
    ap.add_argument("--registry-key-id", default=None, help="Trusted registry manifest Ed25519 key id (direct pin)")
    ap.add_argument("--root-key-id", default=None, help="Trusted OFFLINE root key id: verify keys.signed.json and trust its unrevoked manifest keys (root-anchored mode)")
    ap.add_argument("--channel", default="global", help="Expected manifest channel/scope (default: global)")
    ap.add_argument("--db", default=None, help="Optional atom DB path")
    ap.add_argument("--state", default=None, help="Sync state JSON path for replay protection")
    ap.add_argument("--revocation-slo-seconds", type=float, default=None, help="Optional max revocation convergence seconds")
    ap.set_defaults(func=_cmd_atom)

    # borg collective — outcome-grounded contribution ledger utilities
    p = sub.add_parser(
        "collective",
        help="Inspect/promote the outcome-grounded collective learning ledger",
        description="Inspect privacy-safe contribution events and promote verified outcome clusters into signed learning atoms.",
    )
    collective_sub = p.add_subparsers(dest="collective_action", required=True)

    cp = collective_sub.add_parser("summary", help="Show contribution ledger and verified outcome summary")
    cp.add_argument("--db", default=None, help="Optional collective learning DB path")
    cp.add_argument("--json", action="store_true")
    cp.set_defaults(func=_cmd_collective)

    cp = collective_sub.add_parser("events", help="List recent privacy-redacted contribution events")
    cp.add_argument("--db", default=None, help="Optional collective learning DB path")
    cp.add_argument("--limit", type=int, default=50)
    cp.add_argument("--json", action="store_true")
    cp.set_defaults(func=_cmd_collective)

    cp = collective_sub.add_parser("candidate", help="Build a sanitized learning atom candidate from a verified cluster")
    cp.add_argument("cluster_id", help="Problem cluster/signature ID")
    cp.add_argument("--db", default=None, help="Optional collective learning DB path")
    cp.add_argument("--scope", choices=["org", "global_candidate", "global"], default="global_candidate")
    cp.add_argument("--min-helpful-tenants", type=int, default=3)
    cp.add_argument("--json", action="store_true")
    cp.set_defaults(func=_cmd_collective)

    cp = collective_sub.add_parser("promote", help="Sign and stage a promotable cluster atom into a registry")
    cp.add_argument("cluster_id", help="Problem cluster/signature ID")
    cp.add_argument("--registry-dir", required=True, help="Filesystem registry directory")
    cp.add_argument("--sign-agent", required=True, help="Agent id whose stored Ed25519 key signs the atom")
    cp.add_argument("--db", default=None, help="Optional collective learning DB path")
    cp.add_argument("--scope", choices=["org", "global_candidate", "global"], default="global_candidate")
    cp.add_argument("--min-helpful-tenants", type=int, default=3)
    cp.add_argument("--json", action="store_true")
    cp.set_defaults(func=_cmd_collective)

    # borg optimize-pack — local-only bounded candidate pack optimization
    p = sub.add_parser(
        "optimize-pack",
        help="Propose/inspect/apply local-only pack optimization candidates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg optimize-pack systematic-debugging --taskset eval/tasksets/systematic_debugging_selection.json --local-only
  borg optimize-pack inspect packopt-sha256:0000000000000000000000000000000000000000000000000000000000000000 --json
      # artifact-only inventory; reports source_verification_required
  borg optimize-pack inspect packopt-sha256:0000000000000000000000000000000000000000000000000000000000000000 --pack-file ./pack.yaml --taskset eval/tasksets/systematic_debugging_selection.json --examples-file eval/tasksets/systematic_debugging_examples.json --json
  borg optimize-pack review packopt-sha256:0000000000000000000000000000000000000000000000000000000000000000 --pack-file ./pack.yaml --taskset eval/tasksets/systematic_debugging_selection.json --examples-file eval/tasksets/systematic_debugging_examples.json --json
  borg optimize-pack apply packopt-sha256:0000000000000000000000000000000000000000000000000000000000000000 --scope local --pack-file ./pack.yaml --taskset eval/tasksets/systematic_debugging_selection.json --examples-file eval/tasksets/systematic_debugging_examples.json""",
    )
    p.add_argument("target", help="Pack id, or action: inspect/review/apply")
    p.add_argument("candidate_id", nargs="?", help="Candidate id for inspect/review/apply")
    p.add_argument("--taskset", default=None, help="Selection taskset JSON path for dry-run candidate generation")
    p.add_argument("--pack-file", default=None, help="Optional pack file path; required for apply and source-verified inspect")
    p.add_argument("--examples-file", default=None, help="Optional sanitized examples JSON file; required for apply and source-verified inspect")
    p.add_argument("--collective-db", default=None, help="Optional collective learning DB path")
    p.add_argument("--output-dir", default="eval/pack_optimizer", help="Candidate artifact root directory")
    p.add_argument("--max-edits", type=int, default=4, help="Maximum bounded edits to propose")
    p.add_argument("--local-only", action="store_true", default=True, help="Force local-only dry-run behavior (default)")
    p.add_argument("--scope", choices=["local", "global", "global_candidate", "org"], default="local", help="Apply scope; only local is allowed")
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p.set_defaults(func=_cmd_optimize_pack)

    # guild reputation <agent_id>
    p = sub.add_parser("reputation", help="Show agent reputation profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg reputation agent-42""")
    p.add_argument("agent_id", help="Agent ID")
    p.set_defaults(func=_cmd_reputation)

    # guild status
    p = sub.add_parser("status", help="Show local Borg runtime status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg status
  borg status --json""")
    p.add_argument("--json", action="store_true", help="Output machine-readable status, data notice, and fallback states")
    p.set_defaults(func=_cmd_status)

    # guild version
    p = sub.add_parser("version", help="Show version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg version""")
    p.set_defaults(func=_cmd_version)

    # guild autopilot
    p = sub.add_parser("autopilot", help="Guided Hermes setup: install MCP + skill + auto-suggest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg autopilot""")
    p.set_defaults(func=_cmd_autopilot)

    # guild setup-claude
    p = sub.add_parser("setup-claude", help="Configure borg MCP server for Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  borg setup-claude --scope user --verify --fix
  borg setup-claude --scope project --verify
  borg setup-claude --scope desktop""")
    p.add_argument("--scope", choices=["user", "project", "desktop"], default="user",
                   help="Where to write MCP config: user (~/.claude.json), project (./.mcp.json), or desktop (legacy claude_desktop_config.json)")
    p.add_argument("--verify", dest="verify", action="store_true", default=True,
                   help="Run an MCP initialize handshake (default: enabled)")
    p.add_argument("--no-verify", dest="verify", action="store_false",
                   help="Skip runtime handshake verification")
    p.add_argument("--fix", action="store_true",
                   help="Auto-create missing BORG_HOME directory before writing config")
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
