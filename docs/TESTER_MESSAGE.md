# Borg first-user tester onboarding

**Install:** `pipx install agent-borg`
Fallback: `python3 -m pip install --user agent-borg`

**First value check:**

```bash
borg version
borg-doctor --json
borg rescue "ModuleNotFoundError: No module named flask"
borg first-10 --json
```

Expected rescue shape: `ACTION`, `STOP`, `VERIFY`, and `CONFIDENCE`.

**MCP setup for Claude Code:**

```bash
borg setup-claude --scope user --verify --fix
```

Fully restart Claude Code, then ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

**First MCP call for a concrete failure:**

```text
error_lookup(input="<exact error or failing command output>", show_guidance=False)
```

If your host only shows canonical Borg names, use:

```text
borg_rescue(input="<exact error or failing command output>", show_guidance=False)
```

Use `borg_observe(task="<task>", context="<tech stack>")` for broader task-start guidance when there is not yet exact failing output.

**What we need from you:**

- install path and OS;
- exact outputs from the commands above;
- one real error you tried with `error_lookup` / `borg rescue`;
- whether the `ACTION / STOP / VERIFY` packet saved time or avoided a dead end;
- anything confusing or counterintuitive.
