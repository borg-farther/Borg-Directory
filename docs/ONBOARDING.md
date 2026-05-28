# Borg Claude onboarding

## Prerequisite

Install package `agent-borg`; it provides the `borg` CLI and `borg-mcp` MCP server command.

Do **not** install `borg` or `borgbackup`; those are unrelated. If you are not installed yet, use [`INSTALL.md`](INSTALL.md).

Verify first:

```bash
borg version
borg-doctor --json
```

## One command

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

Expected: Claude lists Borg MCP tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

## What Borg does

1. resolves the MCP launch command (`borg-mcp`);
2. writes/merges the Borg MCP server into the selected config;
3. creates Borg home storage if missing;
4. writes an absolute `BORG_HOME` path;
5. backs up existing config before modification;
6. verifies the MCP initialize handshake.

## Binary success gates

- setup command exits `0`;
- target config contains `mcpServers.borg`;
- setup prints `PASS (initialize handshake ok)`;
- after restart, Claude lists Borg tools.

## If setup fails

Read the printed gate failure. Common fixes:

- install the correct package: `pipx install agent-borg`;
- use `--fix` so Borg can create missing local directories;
- use an absolute `BORG_HOME` path in manual configs;
- restart the agent host after config changes;
- if Claude Code says `borg not found`, fully quit/reopen it after `pipx ensurepath`.

## Agent priming

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. For a concrete failure in MCP, call error_lookup(input="<exact error or failing command output>"); it is the plain-English alias for borg_rescue(input="<exact error or failing command output>") and returns the same ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue "<exact error>". Use borg_observe(task="<exact task or error>", context="<tech stack>") for broader task-start guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After an MCP rescue/error_lookup with an intervention_id, record the outcome with borg_record_outcome(...); for pack sessions use borg_feedback/feedback-v3; for concrete reusable error-pattern success/failure use borg_record_failure.
```
