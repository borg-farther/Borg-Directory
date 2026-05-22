> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg MCP integration guide

Use this guide when you run an AI agent and want it to consult Borg directly.

Borg is the product name. Install package `agent-borg`; it provides:

- `borg` — CLI
- `borg-mcp` — MCP server command
- `borg-doctor` — diagnostics

Do **not** install `borg`, `borgbackup`, `brew install borgbackup`, `apt install borgbackup`, `dnf install borgbackup`, or `pacman -S borg`; those are unrelated.

For OS-specific install commands, start with [`INSTALL.md`](INSTALL.md). For the full MCP setup reference, use [`MCP_SETUP.md`](MCP_SETUP.md).

## Why connect an agent?

A human can run `borg rescue ...` manually, but an agent can use Borg at the moment it matters: before it burns another tool call on a known dead end.

Connected agents can:

- call `error_lookup` for concrete failures and receive `ACTION / STOP / VERIFY`; `borg_rescue` is the canonical Borg tool name and returns the same packet;
- call `borg_observe` before technical fixes to check known approaches;
- search related packs/traces with `borg_search`;
- disclose `NO_CONFIDENT_MATCH` when Borg has no good hit instead of forcing weak advice.

Borg output is advisory. The agent should still verify with the exact failing command or smallest regression test.

## Verify the local commands first

macOS/Linux:

```bash
command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

Windows PowerShell:

```powershell
where.exe borg
where.exe borg-mcp
borg version
borg-doctor --json
```

## Claude Code

```bash
borg setup-claude --scope user --verify --fix
```

Expected output includes:

```text
Verify: PASS (initialize handshake ok)
```

Then fully quit and restart Claude Code. In a new session, ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

## Hermes Agent

Add Borg to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  borg:
    enabled: true
    command: borg-mcp
    args: []
    env:
      BORG_HOME: /absolute/path/to/.borg
```

Restart Hermes Agent. Expected tools may be listed as `error_lookup` / `borg_rescue` / `borg_observe` / `borg_search`, or with a Hermes server prefix such as `mcp_borg_borg_rescue`.

## OpenClaw

If your OpenClaw build supports stdio MCP servers, add this block to OpenClaw's documented MCP config location for your version:

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": [],
      "env": {
        "BORG_HOME": "/absolute/path/to/.borg"
      }
    }
  }
}
```

Restart OpenClaw and verify it can see Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`.

OpenClaw note: Borg does not currently publish a verified one-command OpenClaw installer. Use OpenClaw's current MCP config path and avoid stale `guild-*` setup docs.

## Generic MCP config

Use this for Cursor, Cline, Continue, Goose, Codex-style CLIs, or any stdio MCP client:

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": [],
      "env": {
        "BORG_HOME": "/absolute/path/to/.borg"
      }
    }
  }
}
```

If your MCP client cannot find `borg-mcp`, use an absolute path.

macOS/Linux:

```bash
command -v borg-mcp
```

Windows PowerShell:

```powershell
where.exe borg-mcp
```

Avoid bare `python` or `python3` in MCP configs unless you know that exact interpreter has `agent-borg` installed.

## Core first-user MCP tools

- `error_lookup` — plain-English alias for `borg_rescue`; use this first for concrete failures.
- `borg_rescue` — canonical Borg ACTION / STOP / VERIFY packet for concrete failures.
- `borg_observe` — guidance before technical fixes.
- `borg_search` — search packs and traces.
- `borg_try` — preview a pack.
- `borg_apply` — start/checkpoint/complete pack execution.
- `borg_feedback` — generate feedback from a completed session.
- `borg_record_failure` — record success/failure for a concrete error pattern.
- `borg_suggest` — suggest after repeated failures.
- `borg_first_10` — first-10 beta gates and smoke path.

## Prime the agent once

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. For a concrete failure in MCP, call error_lookup(input="<exact error or failing command output>"); it is the plain-English alias for borg_rescue(input="<exact error or failing command output>") and returns the same ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue "<exact error>". Use borg_observe(task="<exact task or error>", context="<tech stack>") for broader task-start guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After the outcome, record it with borg_feedback if you used a pack session, or borg_record_failure if you are recording a concrete error-pattern success/failure.
```
