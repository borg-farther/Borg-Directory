# Borg — collective memory for AI agents

Borg helps coding agents avoid rediscovering the same fixes and dead ends.
Give it an error or task; it returns an `ACTION / STOP / VERIFY` packet, or a clear `NO_CONFIDENT_MATCH` when it does not know.

**Install package:** `agent-borg`  
**Installed CLI:** `borg`  
**MCP server command:** `borg-mcp`  
**Canonical repo:** https://github.com/borg-farther/Borg-Directory
**Canonical/no-loss policy:** [`docs/CANONICAL_REPO.md`](docs/CANONICAL_REPO.md)

Name warning: Borg is the product name and `borg` is the command, but the package you install is **`agent-borg`**.
Do **not** run `pip install borg`, `brew install borgbackup`, `apt install borgbackup`, `apt-get install borgbackup`, `dnf install borgbackup`, or `pacman -S borg`; those install unrelated Borg/BorgBackup software and will not provide Borg's AI-agent MCP tools.

Borg is not marketed here as a magic success-rate booster. Current local security/readiness gates are green; statistically significant external agent-level lift is still unproven.

## For people running AI agents

If you run Claude Code, Hermes Agent, OpenClaw, or any MCP-capable coding agent, connect Borg once as a local MCP server.
Choose the setup path by the **agent host** you run, not by the model inside it. If you use Hermes with Claude, GPT, OpenRouter, or another provider, follow the **Hermes Agent** path.

Why: the agent can check prior fixes and dead ends before burning tool calls. It gets `ACTION / STOP / VERIFY`, can avoid repeated failed loops, and should disclose `NO_CONFIDENT_MATCH` when Borg has no good hit.

How:

1. Install `agent-borg` and verify `borg-mcp`.
2. Connect your agent host:
   - Claude Code: `borg setup-claude --scope user --verify --fix`
   - Hermes Agent, including Hermes with Claude/GPT models: add `mcp_servers.borg` in `~/.hermes/config.yaml`
   - OpenClaw / generic MCP: add `mcpServers.borg` with `"command": "borg-mcp"`
3. Restart the agent and ask: `what MCP tools do you have from Borg?`

Details: [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md).

---

## 1. Install `agent-borg`

Requires Python 3.10+. For normal users, prefer `pipx`: it installs the CLI cleanly without polluting your system Python.

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

No Homebrew?

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install agent-borg
exec "$SHELL" -l

command -v borg
borg version
borg-doctor --json
```

Do not run `brew install borgbackup`; that installs BorgBackup, not this project.

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

Fedora/RHEL:

```bash
sudo dnf install -y pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
borg version
borg-doctor --json
```

Arch:

```bash
sudo pacman -Syu --needed python-pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
borg version
borg-doctor --json
```

If your distro has no `pipx` package:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install agent-borg
exec "$SHELL" -l

command -v borg
borg version
borg-doctor --json
```

Do not run `apt install borgbackup`, `apt-get install borgbackup`, `dnf install borgbackup`, or `pacman -S borg`; those install BorgBackup/other packages, not this project.

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

If `py` is unavailable, replace `py` with `python`.

### Optional Python-environment install

If you intentionally want Borg inside the active Python environment instead of an isolated CLI install:

```bash
python3 -m pip install agent-borg
python3 -m pip install 'agent-borg[embeddings]'  # optional semantic search
python3 -m pip install 'agent-borg[crypto]'      # optional Ed25519 signing support
python3 -m pip install 'agent-borg[all]'         # optional dev + semantic + crypto
```

Windows PowerShell:

```powershell
py -m pip install agent-borg
py -m pip install "agent-borg[embeddings]"
py -m pip install "agent-borg[crypto]"
py -m pip install "agent-borg[all]"
```

For controlled or offline environments:

```bash
python -m pip download agent-borg -d ./wheelhouse
python -m pip install --no-index --find-links ./wheelhouse agent-borg
borg version
borg-doctor --json
```

Full install guide: [`docs/INSTALL.md`](docs/INSTALL.md).

---

## 2. First useful command

```bash
borg rescue "ModuleNotFoundError: No module named flask"
```

Expected shape:

```text
ACTION: what to try next
STOP: what dead-end to avoid
VERIFY: exact check to rerun
CONFIDENCE: tested / observed / inferred / NO_CONFIDENT_MATCH
```

More day-one commands:

```bash
pytest -q 2>&1 | borg rescue --json
borg search "django migration table already exists"
borg try systematic-debugging
borg apply systematic-debugging --task "Fix Django migration table already exists error"
borg first-10 --json
```

Python API:

```python
import borg

hits = borg.check("TypeError: unsupported operand type(s)", top_k=3)
for hit in hits:
    print(hit.get("name"), hit.get("tier"))
```

---

## 3. Connect an agent with MCP

Prerequisite: `borg version` and `borg-doctor --json` pass in the same environment that launches your agent host.

Claude Code one-command setup:

```bash
borg setup-claude --scope user --verify --fix
```

Expected output includes:

```text
Verify: PASS (initialize handshake ok)
```

Then fully quit and restart Claude Code so it reloads PATH and MCP config.
In a new Claude Code session, ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists Borg tools such as `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

Hermes Agent uses `mcp_servers.borg` in `~/.hermes/config.yaml`. OpenClaw and most other MCP-capable agents use an `mcpServers.borg` JSON block.

Manual MCP config for any stdio MCP client:

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

If the MCP client cannot find `borg-mcp`, first locate it:

macOS/Linux:

```bash
command -v borg-mcp
```

Windows PowerShell:

```powershell
where.exe borg-mcp
```

Then use that absolute path as the MCP `command`. Avoid bare `python`/`python3` in MCP config unless you are certain that exact interpreter has `agent-borg` installed.
Use absolute paths in MCP env blocks. Do not rely on `~` expansion inside MCP clients.

More setup detail: [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md).

---

## 4. Prime the agent

Put this in `CLAUDE.md`, an agent system prompt, or the first user message:

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After the outcome, record it with borg_feedback if you used a pack session, or borg_record_failure if you are recording a concrete error-pattern success/failure.
```

Why: agents often do not discover optional tools unless explicitly primed.

---

## 5. What is ready now

Ready for **controlled first-10 beta sharing**:

- Install, CLI, Python API, and MCP entrypoints are present.
- First-user rescue path returns ACTION / STOP / VERIFY.
- Security/privacy/prompt-injection surface: PASS.
- GitHub CI and security gates are green on the current default branch.
- First-10 beta contract is published: [`docs/FIRST_10_BETA_READINESS.md`](docs/FIRST_10_BETA_READINESS.md).

Not yet claimed:

- Statistically significant agent-level success lift.
- Real external-user network effects.
- Public self-serve launch readiness.
- Broad non-Python coverage.
- Global/federated multi-node reliability.

Public self-serve launch remains gated by real external-user evidence. Current threshold: At least 6 of the first 10 users get one relevant ACTION/STOP/VERIFY moment without maintainer handholding, and every miss is recorded as NO_CONFIDENT_MATCH or explicit negative feedback instead of being hidden.

Current public status: [`docs/READINESS.md`](docs/READINESS.md).

---

## 6. Security and privacy

Start here:

- [`docs/SECURITY_HARDENING_BASELINE.md`](docs/SECURITY_HARDENING_BASELINE.md)
- [`docs/PRIVACY_MODEL.md`](docs/PRIVACY_MODEL.md)
- [`docs/PROMPT_INJECTION_THREAT_MODEL.md`](docs/PROMPT_INJECTION_THREAT_MODEL.md)
- [`docs/TRUST_AND_PROMOTION.md`](docs/TRUST_AND_PROMOTION.md)
- [`docs/REVOCATION_AND_DELETION.md`](docs/REVOCATION_AND_DELETION.md)

Do not paste API keys, passwords, cookies, tokens, private repo contents, customer data, or unsanitized private stack traces into public issues.

---

## 7. Clean evaluator smoke path

Use the package name `agent-borg`; the CLI command after install is `borg`. Do not substitute `borg`, `borgbackup`, Homebrew BorgBackup, or apt/dnf/pacman BorgBackup.

```bash
python3 -m venv /tmp/borg-smoke
. /tmp/borg-smoke/bin/activate
python -m pip install --upgrade pip
python -m pip install agent-borg
borg version
borg-doctor --json
borg rescue "ModuleNotFoundError: No module named flask" --json
borg search "django migration table already exists"
borg first-10 --json
```

Then connect MCP with `borg setup-claude --scope user --verify --fix`, fully restart Claude Code, and verify Claude lists Borg tools such as `borg_rescue`, `borg_observe`, and `borg_search`.

A good first evaluation is whether Borg reduces redundant investigation, not whether it magically solves every bug.

---

## Docs

- [`docs/INSTALL.md`](docs/INSTALL.md) — OS-specific install guide and wrong-package troubleshooting
- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — short copy-paste path
- [`docs/TRYING_BORG.md`](docs/TRYING_BORG.md) — detailed first-user setup
- [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md) — MCP setup details
- [`docs/READINESS.md`](docs/READINESS.md) — current readiness status
- [`docs/archive/`](docs/archive/) — historical audits, experiments, and internal planning artifacts; not current product claims

---

## License

MIT. See [`LICENSE`](LICENSE).
