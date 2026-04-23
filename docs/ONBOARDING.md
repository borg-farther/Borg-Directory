# Borg Claude Onboarding (deterministic)

## one command

```bash
borg setup-claude --scope user --verify --fix
```

`--verify` is enabled by default now; keep it explicit in docs/scripts for readability.
if you need to bypass handshake temporarily: `--no-verify`.

## what the human does

just run the command above, restart claude, ask:

> what mcp tools do you have from borg?

## what borg does automatically

1. resolves mcp launch command (`borg-mcp` if present, else `python -m borg.integrations.mcp_server`)
2. writes config to the selected scope:
   - `user` → `~/.claude.json`
   - `project` → `./.mcp.json`
   - `desktop` → `~/.config/claude/claude_desktop_config.json`
3. enforces absolute `BORG_HOME` in env (`~` is not used)
4. creates `BORG_HOME` if missing (`--fix`)
5. backs up existing config before modifying (`*.bak`)
6. verifies runtime via MCP initialize handshake (`--verify`)

## success gates (binary)

- gate 1: setup command exits `0`
- gate 2: target config file exists and contains `mcpServers.borg`
- gate 3: verify reports `PASS (initialize handshake ok)`

## failure handling

if setup fails, the output explicitly says which gate failed:

- missing/invalid `BORG_HOME`
- unable to spawn MCP server
- no initialize response from runtime

rerun with `--fix` for auto-remediation of local directory/preflight issues.

## security & reliability defaults

- no shell expansion dependency for `BORG_HOME`
- no overwrite of unrelated mcp servers (merge semantics)
- config backup on change
- project instructions (`CLAUDE.md`) are only touched for `project`/`desktop` scopes to avoid surprise edits in user-home setup
