"""
Hermes Plugin — Guild v2 Auto-Suggest Bridge
=============================================

Installs guild-v2 auto-suggest into the Hermes agent loop without touching
run_agent.py. This plugin is fully opt-in.

Installation (one of two ways):

  1. Symlink into ~/.hermes/plugins/ (recommended for dev):
       ln -s /root/hermes-workspace/guild-v2/hermes-plugin ~/.hermes/plugins/guild-v2

  2. pip install the whole guild-v2 package (it registers via entry-points).

What this plugin does:
  - Registers ``guild_v2_autosuggest`` as a callable tool (toolset: skills).
  - Patches ``tools.guild_autosuggest.check_for_suggestion`` to delegate to
    ``borg.integrations.agent_hook`` so existing autosuggest callers
    (including run_agent.py's _maybe_inject_guild_suggestion) automatically
    get guild-v2 suggestions.
  - Registers ``on_consecutive_failure`` and ``on_task_start`` hooks that
    log guild-v2 pack suggestions at the right moments.

Config options (in ~/.hermes/config.yaml → agent section):

    guild:
      autosuggest_enabled: true       # master switch (default: true)
      error_threshold: 3              # consecutive failures before triggering
      proactive_suggest: true        # also call guild_on_task_start on new tasks
      v2_bridge_enabled: true        # use guild-v2 engine (default: true)

Only the ``guild.v2_bridge_enabled`` key is new; all others existed before.
When ``v2_bridge_enabled`` is false the plugin is a no-op (safe to keep installed).
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("guild.hermes_plugin")

# -----------------------------------------------------------------------------
# Guard — honour HERMES_GUILD_V2_ENABLED without touching any existing logic
# -----------------------------------------------------------------------------

_GUILD_V2_ENABLED = os.getenv("HERMES_GUILD_V2_ENABLED", "true").lower() in (
    "1", "true", "yes", "on",
)

_V2_BRIDGE_ENABLED = True  # flipped False by register() if config says so

# -----------------------------------------------------------------------------
# Imports — lazy so we don't break the agent if guild-v2 isn't installed
# -----------------------------------------------------------------------------


def _patch_guild_autosuggest() -> bool:
    """
    Monkey-patch ``tools.guild_autosuggest.check_for_suggestion`` so it
    delegates to ``borg.integrations.agent_hook.guild_on_failure``.

    Returns True if patching succeeded, False otherwise.
    """
    try:
        from tools import guild_autosuggest as original
        from borg.integrations import agent_hook

        _original_check = original.check_for_suggestion

        def _delegating_check(
            conversation_context: str,
            failure_count: int = 0,
            task_type: str = "",
            tried_packs=None,
        ):
            # Translate set/list type差异
            tried = list(tried_packs) if tried_packs else None
            result = agent_hook.guild_on_failure(
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
        logger.info("Patched tools.guild_autosuggest.check_for_suggestion → guild_v2")
        return True

    except Exception as exc:
        logger.warning("Could not patch guild_autosuggest (guild-v2 may not be installed): %s", exc)
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
            suggestion = agent_hook.guild_on_failure(
                context=error_context or task_description,
                failure_count=failure_count,
                tried_packs=None,
            )
            if suggestion:
                logger.info(
                    "[Guild v2 on_consecutive_failure] %s",
                    suggestion,
                )

        def on_task_start_hook(task_description: str = "", **kwargs) -> None:
            if not _V2_BRIDGE_ENABLED:
                return
            suggestion = agent_hook.guild_on_task_start(task_description)
            if suggestion:
                logger.info(
                    "[Guild v2 on_task_start] %s",
                    suggestion,
                )

        manager.register_hook("on_consecutive_failure", on_consecutive_failure_hook)
        manager.register_hook("on_task_start", on_task_start_hook)
        logger.info("Registered guild-v2 lifecycle hooks")
    except Exception as exc:
        logger.debug("Lifecycle hooks not registered (guild-v2 may not be fully installed): %s", exc)


# -----------------------------------------------------------------------------
# Tool registration
# -----------------------------------------------------------------------------


def _make_guild_v2_autosuggest_tool():
    """
    Build the guild_v2_autosuggest tool schema and handler.

    This tool wraps guild_on_failure and guild_on_task_start for direct LLM use.
    """
    from borg.integrations import agent_hook

    schema = {
        "name": "guild_v2_autosuggest",
        "description": (
            "Ask Guild v2 for an auto-suggested pack. "
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
            result = agent_hook.guild_on_task_start(task_description or context)
        else:
            result = agent_hook.guild_on_failure(
                context=context,
                failure_count=failure_count,
                tried_packs=tried_packs,
            )

        if result is None:
            return "No guild-v2 suggestion available."
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
    global _V2_BRIDGE_ENABLED

    # Check config for v2_bridge_enabled (only if config is available)
    try:
        import yaml
        config_path = os.path.expanduser("~/.hermes/config.yaml")
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
            agent_cfg = config.get("agent", {})
            guild_cfg = agent_cfg.get("guild", {})
            if not guild_cfg.get("v2_bridge_enabled", True):
                _V2_BRIDGE_ENABLED = False
                logger.info("Guild v2 bridge disabled by config — plugin is a no-op")
                return
    except Exception as exc:
        logger.debug("Could not read config.yaml (using defaults): %s", exc)

    if not _GUILD_V2_ENABLED:
        logger.info("HERMES_GUILD_V2_ENABLED=false — plugin is a no-op")
        return

    # Step 1: Patch the built-in autosuggest to use guild-v2
    _patch_guild_autosuggest()

    # Step 2: Register the guild_v2_autosuggest tool
    try:
        schema, handler = _make_guild_v2_autosuggest_tool()
        ctx.register_tool(
            name=schema["name"],
            toolset="skills",
            schema=schema,
            handler=handler,
            description=schema["description"],
            emoji="💡",
        )
    except Exception as exc:
        logger.warning("Could not register guild_v2_autosuggest tool: %s", exc)

    # Step 3: Register lifecycle hooks (informational — see note above)
    try:
        _register_lifecycle_hooks(ctx._manager)
    except Exception as exc:
        logger.debug("Could not register lifecycle hooks: %s", exc)

    logger.info("Guild v2 plugin loaded successfully")
