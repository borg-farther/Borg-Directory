# Borg roadmap

Rev: 2026-05-22

## Product nucleus

Borg is failure memory for AI coding agents: a local CLI/MCP server that turns a concrete error, traceback, failed test, install issue, config failure, or deployment failure into `ACTION / STOP / VERIFY` guidance with explicit confidence and `NO_CONFIDENT_MATCH` when it does not know.

## Current public state

- Published controlled-beta package line: `agent-borg==3.3.13`; production PyPI upload and fresh-install + stdio MCP canary are green for the local/PyPI package path.
- CLI command: `borg`.
- MCP server command: `borg-mcp`.
- GitHub default branch: `main` at `borg-farther/Borg-Directory`.
- Controlled first-10 beta infrastructure: GO for up to 10 controlled public-package testers with consented evidence capture; PyPI latest, fresh-install, and stdio MCP canaries are green for `agent-borg==3.3.13`.
- Public self-serve launch: NO-GO until row-derived first-10 external evidence passes.
- Served remote MCP: separate NO-GO channel until live runtime fingerprint/canary passes.

Do **not** install unrelated packages named `borg`, `borgbackup`, `guild-packs`, `guildpacks`, or `guild-mcp` for this product.

## Near-term roadmap

### P0 — first-10 external proof

- [ ] Recruit 10 consented external users.
- [ ] Record every row in `eval/first_10_user_scoreboard.json`.
- [ ] Reach at least 8 successful installs.
- [ ] Reach at least 6 useful `ACTION / STOP / VERIFY` rescue moments.
- [ ] Keep critical privacy/security incidents at 0.
- [ ] Rerun `python eval/public_self_serve_launch_gate.py` and keep the public verdict honest.

### P1 — served remote MCP cutover

- [ ] Run a supervised runtime reload/cutover only through approved operator procedure.
- [ ] Capture served runtime fingerprint: path, version, source hash, schema hash, and start time.
- [ ] Run live canaries for unrelated prompts, concrete errors, and permission-denied failures.
- [ ] Record proof in `eval/live_mcp_self_serve_canary.json` and `docs/LIVE_MCP_SELF_SERVE_CANARY.md`.

### P2 — first-user polish from evidence

Build only what first users prove is missing:

- install/PATH confusion;
- unclear first command;
- weak rescue match;
- confusing MCP setup;
- privacy/consent anxiety;
- docs that send users to stale paths.

### P3 — measured utility

- [ ] Run controlled external A/B tasks only after first-10 evidence exists.
- [ ] Measure useful rescue rate, avoided dead-end rate, repeat use within 7 days, and task completion deltas.
- [ ] Do not claim measured external lift until a documented controlled benchmark supports it.

## What is intentionally not claimed yet

- measured external agent-level success lift;
- public self-serve launch readiness;
- 100-real-user readiness;
- broad non-Python ecosystem coverage;
- global/federated multi-node reliability.

## Canonical gates

```bash
python eval/run_pypi_fresh_install_canary.py
python eval/public_self_serve_launch_gate.py
python eval/real_user_rollout_gate.py
python scripts/security_gate_check.py
python -m pytest -q tests/readiness/test_public_self_serve_launch_gate.py tests/packaging/test_docs_install_clarity.py
```

A failed public-launch gate is expected until real first-10 evidence passes. Do not hide that blocker.
