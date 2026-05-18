# Borg — collective memory for AI agents

Borg helps coding agents avoid rediscovering the same fixes and dead ends.
Give it an error or task; it returns an `ACTION / STOP / VERIFY` packet, or a clear `NO_CONFIDENT_MATCH` when it does not know.

**Install:** `pip install agent-borg`  
**CLI:** `borg`  
**MCP server:** `borg-mcp`  
**Canonical repo:** https://github.com/borg-farther/Borg-Directory

Borg is not marketed here as a magic success-rate booster. Current local security/readiness gates are green; statistically significant external agent-level lift is still unproven.

---

## 1. Install

```bash
python3 -m pip install agent-borg
borg version
borg-doctor --json
```

For isolated installs:

```bash
pipx install agent-borg
```

For controlled or offline environments:

```bash
python -m pip download agent-borg -d ./wheelhouse
python -m pip install --no-index --find-links ./wheelhouse agent-borg
```

Optional extras:

```bash
pip install 'agent-borg[embeddings]'   # semantic search
pip install 'agent-borg[crypto]'       # Ed25519 signing support
pip install 'agent-borg[all]'          # dev + semantic + crypto
```

Requires Python 3.10+.

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

Claude Code one-command setup:

```bash
borg setup-claude --scope user --verify --fix
```

Then fully restart Claude Code and confirm Borg tools appear.

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

If `borg-mcp` is not on PATH:

```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"],
      "env": { "BORG_HOME": "/absolute/path/to/.borg" }
    }
  }
}
```

Use absolute paths in MCP env blocks. Do not rely on `~` expansion inside MCP clients.

More setup detail: [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md).

---

## 4. Prime the agent

Put this in `CLAUDE.md`, an agent system prompt, or the first user message:

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and record the outcome with borg_rate(helpful=True/False).
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

Then connect MCP with `borg setup-claude --scope user --verify --fix` or the manual config above.

A good first evaluation is whether Borg reduces redundant investigation, not whether it magically solves every bug.

---

## Docs

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — short copy-paste path
- [`docs/TRYING_BORG.md`](docs/TRYING_BORG.md) — detailed first-user setup
- [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md) — MCP setup details
- [`docs/READINESS.md`](docs/READINESS.md) — current readiness status
- [`docs/archive/`](docs/archive/) — historical audits, experiments, and internal planning artifacts; not current product claims

---

## License

MIT. See [`LICENSE`](LICENSE).
