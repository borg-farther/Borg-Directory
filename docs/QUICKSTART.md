# Borg quickstart

Use this when you want the shortest safe path.

## Install

Install package `agent-borg`; it provides the `borg` CLI and `borg-mcp` MCP server command.

Do **not** install `borg`, `borgbackup`, `brew install borgbackup`, `apt install borgbackup`, `apt-get install borgbackup`, `dnf install borgbackup`, or `pacman -S borg`. Those are unrelated to this AI-agent tool.

### macOS

```bash
python3 --version  # must be 3.10+
brew install pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
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
borg version
borg-doctor --json
```

Full OS-specific install guide: [`INSTALL.md`](INSTALL.md).

## Get first value

```bash
borg rescue "ModuleNotFoundError: No module named flask"
```

Look for:

- `ACTION` — what to try next
- `STOP` — what dead-end to avoid
- `VERIFY` — exact check to rerun
- `CONFIDENCE` — tested/observed/inferred, or `NO_CONFIDENT_MATCH`

## Connect Claude Code

Prerequisite: `borg version` and `borg-doctor --json` pass.

```bash
borg setup-claude --scope user --verify --fix
```

Wait for:

```text
Verify: PASS (initialize handshake ok)
```

Then fully quit and restart Claude Code. In Claude Code, ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists Borg tools such as `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

## Prime the agent

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and record the outcome with borg_rate(helpful=True/False).
```

## More

- Full README: [`../README.md`](../README.md)
- Install guide: [`INSTALL.md`](INSTALL.md)
- Detailed setup: [`TRYING_BORG.md`](TRYING_BORG.md)
- MCP setup: [`MCP_SETUP.md`](MCP_SETUP.md)
- First-10 beta contract: [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md)
