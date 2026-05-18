# Borg Claude onboarding

## One command

```bash
borg setup-claude --scope user --verify --fix
```

Then fully restart Claude Code and ask:

```text
what MCP tools do you have from Borg?
```

## What Borg does

1. resolves the MCP launch command (`borg-mcp`, or Python module fallback);
2. writes/merges the Borg MCP server into the selected config;
3. creates Borg home storage if missing;
4. writes an absolute `BORG_HOME` path;
5. backs up existing config before modification;
6. verifies the MCP initialize handshake.

## Binary success gates

- setup command exits `0`;
- target config contains `mcpServers.borg`;
- setup prints `PASS (initialize handshake ok)`.

## If setup fails

Read the printed gate failure. Common fixes:

- install Borg in the active Python environment: `python3 -m pip install agent-borg`;
- use `--fix` so Borg can create missing local directories;
- use an absolute `BORG_HOME` path in manual configs;
- restart the agent host after config changes.

## Agent priming

```text
{PRIMING_PARAGRAPH}
```
