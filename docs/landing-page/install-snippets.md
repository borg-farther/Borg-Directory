# Borg install snippets

Use these snippets on landing pages or agent setup pages. Keep the name distinction visible:

- Install package: `agent-borg`
- CLI command: `borg`
- MCP server command: `borg-mcp`

Do **not** tell users to install `borg` or `borgbackup`; those are unrelated.

## macOS

```bash
brew install pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l
borg version
borg-doctor --json
```

## Linux

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l
borg version
borg-doctor --json
```

## Windows PowerShell

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
py -m pipx install agent-borg
# close and reopen PowerShell
where.exe borg
borg version
borg-doctor --json
```

## Claude Code setup

```bash
borg setup-claude --scope user --verify --fix
```

Then fully quit and restart Claude Code. Ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists tools such as `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

## Generic MCP config

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": [],
      "env": { "BORG_HOME": "/absolute/path/to/.borg" }
    }
  }
}
```

If `borg-mcp` is not on PATH, locate it with `command -v borg-mcp` on macOS/Linux or `where.exe borg-mcp` on Windows, then use that absolute path as `command`.

## Agent priming snippet

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After the outcome, record it with borg_feedback if you used a pack session, or borg_record_failure if you are recording a concrete error-pattern success/failure.
```
