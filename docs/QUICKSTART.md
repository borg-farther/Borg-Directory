# Borg quickstart

Use this when you want the shortest safe path.

## Install

Current usable smoke path is GitHub source from the public repo on `main`. It provides the `borg` CLI and `borg-mcp` MCP server command without relying on the stale current PyPI artifact.

Do **not** install `borg`, `borgbackup`, `brew install borgbackup`, `apt install borgbackup`, `apt-get install borgbackup`, `dnf install borgbackup`, or `pacman -S borg`. Those are unrelated to this AI-agent tool.

```bash
python3 -m venv /tmp/borg-source-smoke
. /tmp/borg-source-smoke/bin/activate
python -m pip install --upgrade pip
python -m pip install 'git+https://github.com/borg-farther/Borg-Directory.git@main'

command -v borg
borg version
borg-doctor --json
```

PyPI package install (`agent-borg`) returns after the next immutable release passes the fresh-install/OpenClaw canary.

### Package install path after next PyPI canary

The OS-specific commands below are the package-install path for the next immutable release, not current-source proof while PyPI fresh-install/OpenClaw is red.

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

MCP equivalent for agents: `error_lookup(input="ModuleNotFoundError: No module named flask")`; `borg_rescue(...)` remains the canonical Borg tool name and returns the same packet.

Look for:

- `ACTION` — what to try next
- `STOP` — what dead-end to avoid
- `VERIFY` — exact check to rerun
- `CONFIDENCE` — tested/observed/inferred, or `NO_CONFIDENT_MATCH`

## Connect your agent

Claude Code:

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

Expected: Claude lists Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

Hermes Agent, OpenClaw, and generic MCP clients: use [`MCP_SETUP.md`](MCP_SETUP.md).

## Prime the agent

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. For a concrete failure in MCP, call error_lookup(input="<exact error or failing command output>"); it is the plain-English alias for borg_rescue(input="<exact error or failing command output>") and returns the same ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue "<exact error>". Use borg_observe(task="<exact task or error>", context="<tech stack>") for broader task-start guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After an MCP rescue/error_lookup with an intervention_id, record the outcome with borg_record_outcome(...); for pack sessions use borg_feedback/feedback-v3; for concrete reusable error-pattern success/failure use borg_record_failure.
```

## More

- Full README: [`../README.md`](../README.md)
- Install guide: [`INSTALL.md`](INSTALL.md)
- Detailed setup: [`TRYING_BORG.md`](TRYING_BORG.md)
- MCP setup: [`MCP_SETUP.md`](MCP_SETUP.md)
- First-10 beta contract: [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md)
