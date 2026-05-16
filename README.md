# Borg — collective memory for AI agents

**Install:** `pip install agent-borg`  
**CLI:** `borg`  
**MCP server:** `borg-mcp`  
**Canonical repo:** https://github.com/borg-farther/Borg-Directory

Borg helps coding agents avoid rediscovering the same fixes and dead ends. When an agent hits an error, it can check Borg first, get prior guidance, and record whether the guidance helped.

Borg is not marketed here as a magic success-rate booster. Current local security/readiness gates are green; statistically significant external agent-level lift is still unproven.

---

## 1. Install

```bash
python3 -m pip install agent-borg
borg version
borg-doctor --json
```

Expected first check:

```text
borg version   # prints the installed version, currently 3.3.3 in this repo
borg-doctor    # returns ok=true / PASS-style checks when the install is healthy
```

For isolated installs:

```bash
pipx install agent-borg
```

For controlled or offline environments, pre-download wheels on a connected machine and install from that local wheelhouse:

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

## 2. One-command Claude setup

```bash
borg setup-claude --scope user --verify --fix
```

What this does:

1. Finds the MCP launch command.
2. Creates Borg home storage if missing.
3. Writes user-level Claude MCP config.
4. Runs an MCP initialize verification.
5. Prints a binary pass/fail result with remediation if something is wrong.

If your agent config needs manual MCP wiring, use this:

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

Fallback if `borg-mcp` is not on PATH:

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

---

## 3. First useful commands

```bash
# Fastest day-one value: paste an error, get ACTION / STOP / VERIFY
borg rescue "ModuleNotFoundError: No module named flask"

# Pipe failing command output into Borg
pytest -q 2>&1 | borg rescue --json

# Interactive onboarding uses the same rescue engine
borg start

# First-10 beta contract / readiness packet
borg first-10
borg first-10 --json

# Search existing guidance
borg search "django migration table already exists"

# Preview a workflow pack safely
borg try borg://hermes/systematic-debugging

# Pull the pack locally
borg pull borg://hermes/systematic-debugging

# Apply it to a real task
borg apply systematic-debugging --task "Fix Django migration table already exists error"

# After completion, generate feedback
borg feedback <session_id>
```

For Python callers:

```python
import borg

hits = borg.check("TypeError: unsupported operand type(s)", top_k=3)
for hit in hits:
    print(hit.get("name"), hit.get("tier"))
```

---

## 4. Agent instruction / priming

Put this in your project `CLAUDE.md`, agent system prompt, or first user message:

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, and disclose when retrieved guidance is weak or does not fit. After the fix, call borg_rate(helpful=True/False) or record the outcome.
```

Why: agents often do not discover optional tools unless explicitly primed.

---

## 5. MCP tools

Core tools available through the MCP server include:

- `borg_rescue` — agent-ready ACTION / STOP / VERIFY packet for concrete failures
- `borg_observe` — passive guidance before a technical fix
- `borg_search` — search packs / traces
- `borg_try` — preview a pack before saving
- `borg_pull` — fetch and validate a pack
- `borg_apply` — phase-by-phase execution
- `borg_feedback` — structured feedback artifact
- `borg_suggest` — suggest after repeated failures
- `borg_convert` — convert skills/rules into Borg-compatible artifacts
- `borg_publish` — publish artifacts with safety gates
- `borg_first_10` — first-10 beta gates, smoke path, priming paragraph, feedback fields

Use `borg_rescue` for concrete errors/failing command output. Use `borg_observe` first for broader debugging/config/install/deploy/test tasks.

---

## 6. What is proven right now

Current local gate snapshot in this repo:

- Version consistency: PASS
- First-user install surface: PASS
- Security/privacy/prompt-injection surface: PASS
- Learning-atom safety tests: PASS
- Local 10/100/1000 logical-user soak: PASS
- Latest focused verification: source + wheel + PyPI first-user gates must pass; first-user public launch remains gated by real external-user evidence

Canonical local artifacts:

- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
- [`GO_NO_GO_DECISION.md`](GO_NO_GO_DECISION.md)
- [`docs/20260504-1123_BORG_PRODUCTION_1000_READINESS_STATUS.md`](docs/20260504-1123_BORG_PRODUCTION_1000_READINESS_STATUS.md)
- [`docs/FIRST_10_BETA_READINESS.md`](docs/FIRST_10_BETA_READINESS.md)
- [`eval/uat_scoreboard_snapshot.json`](eval/uat_scoreboard_snapshot.json)
- [`docs/SECURITY_HARDENING_BASELINE.md`](docs/SECURITY_HARDENING_BASELINE.md)
- [`docs/PRIVACY_MODEL.md`](docs/PRIVACY_MODEL.md)
- [`docs/PROMPT_INJECTION_THREAT_MODEL.md`](docs/PROMPT_INJECTION_THREAT_MODEL.md)
- [`docs/TRUST_AND_PROMOTION.md`](docs/TRUST_AND_PROMOTION.md)
- [`docs/REVOCATION_AND_DELETION.md`](docs/REVOCATION_AND_DELETION.md)

---

## 7. Honest limitations

Not yet proven:

- Statistically significant agent-level success lift.
- Real external-user network effects.
- Global/federated multi-node reliability.
- Broad non-Python generalization.
- Navigation cache as a shipped first-user feature.

Security boundary:

- Learning atoms are signed, privacy-scanned, prompt-injection scanned, and revocable.
- Ed25519 primitives exist, but do not interpret that as “every pack from every source is cryptographically trusted” unless the specific command reports verified signature state.

---

## 8. For evaluators

If you are evaluating Borg, run this exact smoke path from a clean environment:

```bash
python3 -m venv /tmp/borg-smoke
. /tmp/borg-smoke/bin/activate
python -m pip install --upgrade pip
python -m pip install agent-borg
borg version
borg-doctor --json
borg search "django migration table already exists"
borg first-10 --json
python - <<'PY'
import borg
print(borg.check('TypeError: unsupported operand type(s)', top_k=2))
PY
```

Then connect MCP using `borg setup-claude --scope user --verify --fix` or the manual config above.

A good first evaluation is whether Borg reduces redundant investigation, not whether it magically solves every bug.

---

## 9. Development verification

From a source checkout:

```bash
python -m pytest -q borg/tests/test_public_api_check.py borg/tests/test_version_consistency.py borg/tests/test_runtime_doctor.py
python scripts/security_gate_check.py
BORG_READINESS_SOAK_SECONDS=5 python eval/run_readiness_gates.py
python eval/uat_scoreboard.py
```

---

## License

MIT. See [`LICENSE`](LICENSE).
