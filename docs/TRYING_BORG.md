# Trying Borg

This is the detailed first-user setup guide. The shortest path is in [`QUICKSTART.md`](QUICKSTART.md); OS-specific install details are in [`INSTALL.md`](INSTALL.md).

## 1. Install

Borg requires Python 3.10+.

Borg is the product name. The package you install is `agent-borg`; that package gives you the `borg` CLI, `borg-mcp` MCP server command, and `borg-doctor` diagnostic command.

Do **not** install these for Borg:

- `pip install borg`
- `brew install borgbackup`
- `apt install borgbackup`
- `apt-get install borgbackup`
- `dnf install borgbackup`
- `pacman -S borg`

Those are unrelated to this AI-agent tool.

### macOS

```bash
python3 --version  # must be 3.10+
brew install pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

### Linux

Debian/Ubuntu:

```bash
python3 --version  # must be 3.10+
sudo apt update
sudo apt install -y pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

Other Linux:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

### Windows PowerShell

```powershell
py -3 --version  # must be 3.10+
py -m pip install --user pipx
py -m pipx ensurepath
py -m pipx install agent-borg
```

Close and reopen PowerShell, then verify:

```powershell
where.exe borg
where.exe borg-mcp
borg version
borg-doctor --json
```

If `borg` is not found, see [`INSTALL.md#if-something-went-wrong`](INSTALL.md#if-something-went-wrong).

## 2. First value check

```bash
borg rescue "ModuleNotFoundError: No module named flask"
```

MCP equivalent for agents: `error_lookup(input="ModuleNotFoundError: No module named flask")`; `borg_rescue(...)` remains the canonical Borg tool name and returns the same packet.

Expected shape:

```text
ACTION: ...
STOP: ...
VERIFY: ...
CONFIDENCE: ...
```

If Borg has no confident match, it should say `NO_CONFIDENT_MATCH` instead of forcing unrelated advice.

## 3. Search and pack workflow

```bash
borg search "django migration table already exists"
borg try systematic-debugging
borg pull borg://hermes/systematic-debugging
borg apply systematic-debugging --task "Fix login bug where users get 401"
```

After a real outcome, record feedback:

```bash
borg feedback-v3 --pack systematic-debugging --success yes
# or
borg feedback-v3 --pack systematic-debugging --success no
```

This records outcome data. Shared learning depends on explicit publishing/aggregation and is still being validated.

## 4. Agent setup

Claude Code one-command setup:

Prerequisite: `borg version` and `borg-doctor --json` pass.

```bash
borg setup-claude --scope user --verify --fix
```

What this does:

1. resolves the MCP launch command;
2. writes/merges `mcpServers.borg` into the selected config;
3. creates Borg home storage if missing;
4. uses an absolute `BORG_HOME` path;
5. runs an MCP initialize handshake and prints PASS/FAIL.

Expected output includes:

```text
Verify: PASS (initialize handshake ok)
```

After setup, fully quit and restart Claude Code.

Then ask Claude Code:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

Hermes Agent, OpenClaw, and generic MCP clients: use [`MCP_SETUP.md`](MCP_SETUP.md).

## 5. Generic MCP setup

Prefer the setup command above when using Claude Code. For any stdio MCP client that accepts `mcpServers` JSON:

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

If the client cannot find `borg-mcp`, locate it first:

macOS/Linux:

```bash
command -v borg-mcp
```

Windows PowerShell:

```powershell
where.exe borg-mcp
```

Use that absolute path as the MCP `command`. Avoid bare `python`/`python3` in MCP config unless you are certain that exact interpreter has `agent-borg` installed.

## 6. Agent priming

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. For a concrete failure in MCP, call error_lookup(input="<exact error or failing command output>"); it is the plain-English alias for borg_rescue(input="<exact error or failing command output>") and returns the same ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue "<exact error>". Use borg_observe(task="<exact task or error>", context="<tech stack>") for broader task-start guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After the outcome, record it with borg_feedback if you used a pack session, or borg_record_failure if you are recording a concrete error-pattern success/failure.
```

## 7. Readiness boundary

Borg's controlled first-10 public-package beta is conditional GO for `agent-borg==3.3.14` only while PyPI latest, fresh-install, stdio MCP, cold-start trust, self-service ops, and watchdog gates remain green. Borg is not yet claiming public self-serve launch readiness or agent-level success lift at statistical confidence. See [`READINESS.md`](READINESS.md).
