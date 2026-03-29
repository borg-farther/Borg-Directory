"""
Hermes Plugin — Borg Auto-Suggest Bridge
========================================

Installs borg auto-suggest into the Hermes agent loop without touching
run_agent.py. This plugin is fully opt-in.

Installation (one of two ways):

  1. Symlink into ~/.hermes/plugins/ (recommended for dev):
       ln -s /root/hermes-workspace/borg/hermes-plugin ~/.hermes/plugins/borg

  2. pip install the whole agent-borg package (it registers via entry-points).

What this plugin does:
  - Registers ``borg_autosuggest`` as a callable tool (toolset: skills).
  - Patches ``tools.borg_autosuggest.check_for_suggestion`` to delegate to
    ``borg.integrations.agent_hook`` so existing autosuggest callers
    automatically get borg suggestions.
  - Registers ``on_consecutive_failure`` and ``on_task_start`` hooks that
    log borg pack suggestions at the right moments.

Config options (in ~/.hermes/config.yaml → agent section):

    borg:
      autosuggest_enabled: true       # master switch (default: true)
      error_threshold: 3              # consecutive failures before triggering
      proactive_suggest: true        # also call borg_on_task_start on new tasks

Only the ``borg.autosuggest_enabled`` key is new; all others existed before.
When ``autosuggest_enabled`` is false the plugin is a no-op (safe to keep installed).
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("borg.hermes_plugin")

# -----------------------------------------------------------------------------
# Guard — honour HERMES_BORG_ENABLED without touching any existing logic
# -----------------------------------------------------------------------------

_BORG_ENABLED = os.getenv("HERMES_BORG_ENABLED", "true").lower() in (
    "1", "true", "yes", "on",
)

_AUTOSUGGEST_ENABLED = True  # flipped False by register() if config says so

# -----------------------------------------------------------------------------
# Imports — lazy so we don't break the agent if agent-borg isn't installed
# -----------------------------------------------------------------------------


def _patch_borg_autosuggest() -> bool:
    """
    Monkey-patch ``tools.borg_autosuggest.check_for_suggestion`` so it
    delegates to ``borg.integrations.agent_hook.borg_on_failure``.

    Returns True if patching succeeded, False otherwise.
    """
    try:
        from tools import borg_autosuggest as original
        from borg.integrations import agent_hook

        _original_check = original.check_for_suggestion

        def _delegating_check(
            conversation_context: str,
            failure_count: int = 0,
            task_type: str = "",
            tried_packs=None,
        ):
            # Translate set/list type
            tried = list(tried_packs) if tried_packs else None
            result = agent_hook.borg_on_failure(
                context=conversation_context,
                failure_count=failure_count,
                tried_packs=tried,
            )
            if result is None:
                return "{}"
            import json
            return json.dumps({"suggestion": result, "pack_name": "", "pack_uri": ""})

        # Swap the function in place
        original.check_for_suggestion = _delegating_check
        logger.info("Patched tools.borg_autosuggest.check_for_suggestion → borg")
        return True

    except Exception as exc:
        logger.warning("Could not patch borg_autosuggest (agent-borg may not be installed): %s", exc)
        return False


# -----------------------------------------------------------------------------
# Optional: register lifecycle hooks (informational logging only since
# run_agent.py does not yet call invoke_hook for on_consecutive_failure /
# on_task_start — these are documented for future use)
# -----------------------------------------------------------------------------


def _register_lifecycle_hooks(manager) -> None:
    """Register on_consecutive_failure and on_task_start hooks if supported."""
    try:
        from borg.integrations import agent_hook

        def on_consecutive_failure_hook(
            task_description: str = "",
            error_context: str = "",
            failure_count: int = 0,
            **kwargs,
        ) -> None:
            suggestion = agent_hook.borg_on_failure(
                context=error_context or task_description,
                failure_count=failure_count,
                tried_packs=None,
            )
            if suggestion:
                logger.info(
                    "[Borg on_consecutive_failure] %s",
                    suggestion,
                )

        def on_task_start_hook(task_description: str = "", **kwargs) -> None:
            if not _AUTOSUGGEST_ENABLED:
                return
            suggestion = agent_hook.borg_on_task_start(task_description)
            if suggestion:
                logger.info(
                    "[Borg on_task_start] %s",
                    suggestion,
                )

        manager.register_hook("on_consecutive_failure", on_consecutive_failure_hook)
        manager.register_hook("on_task_start", on_task_start_hook)
        logger.info("Registered borg lifecycle hooks")
    except Exception as exc:
        logger.debug("Lifecycle hooks not registered (agent-borg may not be fully installed): %s", exc)


# -----------------------------------------------------------------------------
# Tool registration
# -----------------------------------------------------------------------------


def _make_borg_autosuggest_tool():
    """
    Build the borg_autosuggest tool schema and handler.

    This tool wraps borg_on_failure and borg_on_task_start for direct LLM use.
    """
    from borg.integrations import agent_hook

    schema = {
        "name": "borg_autosuggest",
        "description": (
            "Ask Borg for an auto-suggested pack. "
            "Use when the agent has failed 2+ times on the same problem, "
            "or at the start of a complex task to proactively discover packs. "
            "Returns a formatted suggestion string or None."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["failure", "task_start"],
                    "description": "'failure' = after consecutive errors (default); 'task_start' = proactive suggestion at start of task.",
                    "default": "failure",
                },
                "context": {
                    "type": "string",
                    "description": "Recent conversation / error text providing context.",
                },
                "failure_count": {
                    "type": "integer",
                    "description": "Number of consecutive failed attempts (used in failure mode).",
                    "default": 2,
                },
                "task_description": {
                    "type": "string",
                    "description": "Free-text task description (used in task_start mode).",
                },
                "tried_packs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Pack names already attempted (exclude from suggestions).",
                },
            },
            "required": ["context"],
        },
    }

    def handler(args, **kw):
        mode = args.get("mode", "failure")
        context = args.get("context", "")
        failure_count = args.get("failure_count", 2)
        task_description = args.get("task_description", "")
        tried_packs = args.get("tried_packs")

        if mode == "task_start":
            result = agent_hook.borg_on_task_start(task_description or context)
        else:
            result = agent_hook.borg_on_failure(
                context=context,
                failure_count=failure_count,
                tried_packs=tried_packs,
            )

        if result is None:
            return "No borg suggestion available."
        return result

    return schema, handler


# -----------------------------------------------------------------------------
# Plugin entry point
# -----------------------------------------------------------------------------


def register(ctx) -> None:
    """
    Called by the Hermes plugin system when this plugin is loaded.

    Args:
        ctx: PluginContext instance from hermes_cli.plugins.
    """
    global _AUTOSUGGEST_ENABLED

    # Check config for autosuggest_enabled (only if config is available)
    try:
        import yaml
        config_path = os.path.expanduser("~/.hermes/config.yaml")
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
            agent_cfg = config.get("agent", {})
            borg_cfg = agent_cfg.get("borg", {})
            if not borg_cfg.get("autosuggest_enabled", True):
                _AUTOSUGGEST_ENABLED = False
                logger.info("Borg autosuggest disabled by config — plugin is a no-op")
                return
    except Exception as exc:
        logger.debug("Could not read config.yaml (using defaults): %s", exc)

    if not _BORG_ENABLED:
        logger.info("HERMES_BORG_ENABLED=false — plugin is a no-op")
        return

    # Step 1: Patch the built-in autosuggest to use borg
    _patch_borg_autosuggest()

    # Step 2: Register the borg_autosuggest tool
    try:
        schema, handler = _make_borg_autosuggest_tool()
        ctx.register_tool(
            name=schema["name"],
            toolset="skills",
            schema=schema,
            handler=handler,
            description=schema["description"],
            emoji="💡",
        )
    except Exception as exc:
        logger.warning("Could not register borg_autosuggest tool: %s", exc)

    # Step 3: Register lifecycle hooks (informational — see note above)
    try:
        _register_lifecycle_hooks(ctx._manager)
    except Exception as exc:
        logger.debug("Could not register lifecycle hooks: %s", exc)

    logger.info("Borg plugin loaded successfully")
