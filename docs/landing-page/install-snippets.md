> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

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

Expected: Claude lists tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

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
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. For a concrete failure in MCP, call error_lookup(input="<exact error or failing command output>"); it is the plain-English alias for borg_rescue(input="<exact error or failing command output>") and returns the same ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue "<exact error>". Use borg_observe(task="<exact task or error>", context="<tech stack>") for broader task-start guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After the outcome, record it with borg_feedback if you used a pack session, or borg_record_failure if you are recording a concrete error-pattern success/failure.
```
