# Borg MCP setup

Install package `agent-borg`; it provides the `borg` CLI and the `borg-mcp` MCP server command. If you have not installed it yet, use [`INSTALL.md`](INSTALL.md).

Do **not** install `borg` or `borgbackup`; those are unrelated to this AI-agent tool.

## Why connect an agent to Borg?

If you run Claude Code, Hermes Agent, OpenClaw, Cursor, Cline, Continue, Goose, or another MCP-capable coding agent, connect Borg once as a local MCP server.
Choose the setup path by the **agent host**, not by the model provider. If you run Hermes with Claude, GPT, OpenRouter, Anthropic, OpenAI, or another model backend, use the **Hermes Agent** section.

Why:

- The agent can call `error_lookup` on a concrete failure and get an `ACTION / STOP / VERIFY` packet. `error_lookup` is a plain-English alias for `borg_rescue`, which remains the canonical Borg tool name.
- The agent can call `borg_observe` before a technical fix to check known approaches and dead ends.
- The agent can avoid repeated failed loops before spending more tool calls.
- If Borg has no confident match, the agent should disclose `NO_CONFIDENT_MATCH` instead of forcing advice.

Treat Borg output as advisory. It should guide the next check, not replace verification with the exact failing command or smallest regression test.

## Preflight

Run this in the same shell environment that launches your agent host:

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

If `borg-mcp` is not found, fix PATH first or use the absolute path returned by `command -v borg-mcp` / `where.exe borg-mcp` in the config snippets below.

## Claude Code

Recommended one-command setup:

```bash
borg setup-claude --scope user --verify --fix
```

Expected output includes:

```text
Verify: PASS (initialize handshake ok)
```

Then fully quit and restart Claude Code. In the new session, ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

## Hermes Agent

Use this section for Hermes Agent regardless of whether Hermes is using Claude, GPT, OpenRouter, Anthropic, OpenAI, or another model provider.

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

Use an absolute `BORG_HOME`; do not rely on `~` expansion inside MCP subprocess environments.

Restart Hermes Agent so MCP tools are rediscovered. In a new Hermes session, ask:

```text
what MCP tools do you have from Borg?
```

Expected: Hermes lists Borg MCP tools. Depending on Hermes tool naming, they may appear as bare Borg tool names such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or with a server prefix such as `mcp_borg_borg_rescue`.

## OpenClaw

If your OpenClaw build supports stdio MCP servers, add Borg to OpenClaw's documented MCP config location for your OpenClaw version.

Use this server block:

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

Then fully restart OpenClaw and verify it can see Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`.

OpenClaw path note: Borg does not currently publish a verified one-command OpenClaw installer. Use OpenClaw's current MCP config path rather than copying stale `guild-*` setup docs.

## Generic MCP clients

Use this for Cursor, Cline, Continue, Goose, Codex-style CLIs, or any stdio MCP client that accepts `mcpServers` JSON:

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

If the MCP client cannot find `borg-mcp`, locate it and use the absolute path as `command`.

macOS/Linux:

```bash
command -v borg-mcp
```

Windows PowerShell:

```powershell
where.exe borg-mcp
```

Avoid bare `python` or `python3` in MCP config unless you are certain that exact interpreter has `agent-borg` installed.
Use absolute paths in MCP env blocks. Do not rely on `~` expansion inside MCP clients.

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

Advanced/admin tools may also be exposed by the server, but first users should start with the tools above.

## Prime the agent once

Agents often do not discover optional tools without a small instruction. Put this in `CLAUDE.md`, an agent system prompt, or the first user message:

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. For a concrete failure in MCP, call error_lookup(input="<exact error or failing command output>"); it is the plain-English alias for borg_rescue(input="<exact error or failing command output>") and returns the same ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue "<exact error>". Use borg_observe(task="<exact task or error>", context="<tech stack>") for broader task-start guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After an MCP rescue/error_lookup with an intervention_id, record the outcome with borg_record_outcome(...); for pack sessions use borg_feedback/feedback-v3; for concrete reusable error-pattern success/failure use borg_record_failure.
```

## Verify manually

```bash
borg-doctor --json
```

For raw JSON-RPC stdio testing:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | borg-mcp
```

## Troubleshooting

### `borg-mcp` not found

Install the correct package and refresh PATH:

```bash
pipx install --force agent-borg
pipx ensurepath
exec "$SHELL" -l
command -v borg-mcp
```

Windows PowerShell:

```powershell
py -m pipx install --force agent-borg
py -m pipx ensurepath
```

Then close and reopen PowerShell and run:

```powershell
where.exe borg-mcp
```

### MCP tools do not appear

1. Fully restart the agent host/IDE.
2. Confirm the JSON/YAML config is valid.
3. Confirm the configured `BORG_HOME` path is absolute.
4. Run `borg-doctor --json` and fix any failed check.
5. For Claude Code, rerun `borg setup-claude --scope user --verify --fix`.
