# Borg — failure memory for AI coding agents

Borg is a local CLI and MCP server that helps coding agents avoid repeating known debugging dead ends.
Give Borg an error, traceback, failed test, install problem, config failure, or deployment failure; it returns a short rescue packet:

- `ACTION` — the next thing to try
- `STOP` — a dead end to avoid
- `VERIFY` — the exact command or test to rerun
- `CONFIDENCE` — tested / observed / inferred, or `NO_CONFIDENT_MATCH`

- **Install package:** `agent-borg`
- **Installed CLI:** `borg`
- **MCP server command:** `borg-mcp`
- **Canonical repo:** https://github.com/borg-farther/Borg-Directory

**Status:** `agent-borg==3.3.19` is the target source/local release candidate for the current source line. A `3.3.19` wheel is now the latest on PyPI (published 2026-06-10), superseding 3.3.18; exact-version PyPI fresh-install/stdio MCP proof for 3.3.19 is not green yet. Controlled first-10 beta remains **NO-GO** until package/source provenance, served-runtime freshness, release-governance, ops/watchdog, docs-claim, and evidence-intake guardrails are green. Broad public self-serve launch, 100-user rollout, served/remote MCP, and measured external lift are **not claimed** until row-derived external-user evidence passes.

## Try Borg in 60 seconds

```bash
pipx install agent-borg
borg rescue "ModuleNotFoundError: No module named flask" --short
```

Expected abbreviated shape:

```text
BORG RESCUE
status: matched
match: missing_dependency [tested]

ACTION
  - ...

STOP
  - ...

VERIFY
  - ...
```

> **Install-name note:** Borg is the product name, and `borg` is the command after install. The Python package to install is **`agent-borg`**.
>
> Use `pipx install agent-borg` or `python3 -m pip install agent-borg`. Do **not** use `pip install borg`, `brew install borgbackup`, `apt install borgbackup`, `apt-get install borgbackup`, `dnf install borgbackup`, or `pacman -S borg`; those install unrelated Borg/BorgBackup software and will not provide Borg's AI-agent MCP tools.

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

Details: [`docs/MCP_SETUP.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/MCP_SETUP.md).

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

Full install guide: [`docs/INSTALL.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/INSTALL.md).

---

## 2. First useful command

```bash
borg rescue "ModuleNotFoundError: No module named flask"
```

MCP equivalent for agents: `error_lookup(input="ModuleNotFoundError: No module named flask")`; `borg_rescue(...)` remains the canonical Borg tool name and returns the same packet.

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

`borg.check()` returns confidence-gated pack matches; an empty list means no
confident match — never a confident-but-irrelevant hit. For a full rescue packet
(ACTION / STOP / VERIFY, confidence, and an explicit `NO_CONFIDENT_MATCH`) from
your own Python code, call the rescue engine directly:

```python
from borg.core.rescue import rescue

packet = rescue("ModuleNotFoundError: No module named 'requests'", source="my-agent")
print(packet.status, packet.problem_class, packet.confidence)  # matched missing_dependency tested
if packet.success:
    print(packet.action[0])  # install the distribution for import `requests` ...
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

Expected: Claude lists Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

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

More setup detail: [`docs/MCP_SETUP.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/MCP_SETUP.md).

---

## 4. Prime the agent

Put this in `CLAUDE.md`, an agent system prompt, or the first user message:

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. For a concrete failure in MCP, call error_lookup(input="<exact error or failing command output>"); it is the plain-English alias for borg_rescue(input="<exact error or failing command output>") and returns the same ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue "<exact error>". Use borg_observe(task="<exact task or error>", context="<tech stack>") for broader task-start guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After an MCP rescue/error_lookup with an intervention_id, record the outcome with borg_record_outcome(...); for pack sessions use borg_feedback/feedback-v3; for concrete reusable error-pattern success/failure use borg_record_failure.
```

Why: agents often do not discover optional tools unless explicitly primed.

---

## 5. What is ready now

`agent-borg==3.3.19` is the target source/package line; a `3.3.19` wheel is now the latest on PyPI (superseding 3.3.18), but exact-version PyPI runtime proof for the current source is not current yet. Release governance is enforced on GitHub `main` with exact required checks and CODEOWNERS review. Served-runtime freshness and first-10 external-user evidence remain separate blockers.

- Install, CLI, Python API, generated-rules/OpenClaw export, and stdio MCP entrypoints pass from the local/source release-candidate path; exact-version PyPI runtime proof for the published `agent-borg==3.3.19` is not recorded green yet.
- First-user rescue path returns ACTION / STOP / VERIFY or `NO_CONFIDENT_MATCH`.
- Security/privacy/prompt-injection surface: PASS in CI/local gates.
- Generated rules and OpenClaw export are covered by first-user/package gates.
- PyPI latest/fresh-install/stdio MCP proof for `agent-borg==3.3.19` is not green yet for the current source revision. Controlled first-10 testers must **not** be invited until package proof, served-runtime freshness, ops/watchdog, docs-claim, and evidence intake are green. Current cap: 0; broad public self-serve remains evidence-gated after first-10.
- Self-service ops guardrails are present: bad-answer intake, install/MCP support intake, first-10 evidence intake, support/SLA, rollback/comms dry-run, and watchdog workflow.
- First-10 beta contract is published: [`docs/FIRST_10_BETA_READINESS.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/FIRST_10_BETA_READINESS.md).

Do **not** route this into controlled first-10, broad public self-serve, or 100 real users yet. Invite **0** controlled testers until served-runtime freshness is green and the first-10 evidence contract is ready to capture consented external-user rows; after those gates pass, the first-10 evidence contract may cap a consented cohort at 10. `python eval/public_self_serve_launch_gate.py` must still keep broad public self-serve blocked until real first-10 evidence passes.

Not yet claimed:

- Measured external agent success lift.
- Real external-user network effects.
- Public self-serve launch readiness.
- Broad non-Python coverage.
- Global/federated multi-node reliability.

Public self-serve launch remains gated by real external-user evidence. Current threshold: 10 consented external users, at least 8 successful installs, at least 6 useful ACTION / STOP / VERIFY rescue moments without maintainer handholding, and 0 critical privacy/security incidents.

Current public status: [`docs/READINESS.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/READINESS.md).

---

## 6. Security and privacy

Start here:

- [`docs/SECURITY_HARDENING_BASELINE.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/SECURITY_HARDENING_BASELINE.md)
- [`docs/PRIVACY_MODEL.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/PRIVACY_MODEL.md)
- [`docs/PROMPT_INJECTION_THREAT_MODEL.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/PROMPT_INJECTION_THREAT_MODEL.md)
- [`docs/TRUST_AND_PROMOTION.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/TRUST_AND_PROMOTION.md)
- [`docs/REVOCATION_AND_DELETION.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/REVOCATION_AND_DELETION.md)

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

Then connect MCP with `borg setup-claude --scope user --verify --fix`, fully restart Claude Code, and verify Claude lists Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`.

A good first evaluation is whether Borg reduces redundant investigation, not whether it magically solves every bug.

---

## Docs

- [`docs/README.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md) — current-docs index; anything not listed there is historical/internal and not a current product claim
- [`docs/INSTALL.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/INSTALL.md) — OS-specific install guide and wrong-package troubleshooting
- [`docs/QUICKSTART.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/QUICKSTART.md) — short copy-paste path
- [`docs/TRYING_BORG.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/TRYING_BORG.md) — detailed first-user setup
- [`docs/CHANNELS_AND_INSTALL_METHODS.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/CHANNELS_AND_INSTALL_METHODS.md) — exact channel/install-method matrix: PyPI, GitHub, local, stdio MCP, generated rules, OpenClaw, Docker/Smithery, and NO-GO boundaries
- [`docs/MCP_SETUP.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/MCP_SETUP.md) — MCP setup details
- [`docs/READINESS.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/READINESS.md) — current readiness status
- [`docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md) — canonical public launch gate output
- [`docs/CANONICAL_REPO.md`](https://github.com/borg-farther/Borg-Directory/blob/main/docs/CANONICAL_REPO.md) — internal canonical repo / no-loss preservation policy for operators
- [`docs/archive/`](https://github.com/borg-farther/Borg-Directory/tree/main/docs/archive/) — historical audits, experiments, and internal planning artifacts; not current product claims

---

## License

MIT. See [`LICENSE`](https://github.com/borg-farther/Borg-Directory/blob/main/LICENSE).
