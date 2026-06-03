# Borg public self-serve launch closure plan

Generated: 2026-05-14 18:39 UTC

## Current state

Borg's controlled first-10 package path is **NO-GO for package metadata plus runtime/ops proof**, not for package installability. `agent-borg==3.3.17` is the metadata-correct package target; fresh runtime canaries are pending until upload and verification. Served-runtime freshness and ops/watchdog/proof-dashboard consistency remain red, so package-level evidence capture stays paused until package metadata and release-control gates are green. New hardening PRs must still pass their own CI before merge.

Public self-serve launch remains **NO-GO** until row-derived first-10 external-user evidence passes. Served remote MCP remains a separate runtime cutover/canary channel, not proven by the PyPI stdio release.

Hard evidence already completed or pending:

- Branch/source readiness for 3.3.16: release main proof exists; this post-release proof branch still needs its own PR CI and post-merge main proof
- Local source first-user release gate for `agent-borg==3.3.17`: green in current artifacts, but must be rerun after any package-impacting source change
- Fresh PyPI install/MCP/generate/OpenClaw canary for `agent-borg==3.3.17`: PASS from production PyPI
- self-service ops/watchdog gates: PASS for package-level evidence capture; broad public self-serve remains blocked by first-10 rows
- security baseline: PASS in local gates
- privacy/prompt-injection/atom/firewall tests: PASS in local gates
- first-10 invite packet exists
- first-10 scoreboard exists and truthfully reports `verified_external_users=0`

## Remaining self-serve blockers

Three true blocker classes remain before broader launch claims:

1. **Runtime/ops proof and post-release proof branch evidence**
   - Need: served-runtime fingerprint/canary at `agent-borg==3.3.17`, green ops watchdog/proof dashboard, this post-release proof branch PR CI, protected merge, and post-merge main proof.
   - Until that exact chain is green, public-package evidence capture stays paused even though production PyPI package canaries pass.

2. **First 10 real external users**
   - Need: real external-user outcome evidence, not simulations.
   - Done criteria:
     - 10 consented real external user rows in `eval/first_10_user_scoreboard.json`;
     - ≥8/10 install successes;
     - ≥6/10 useful `ACTION / STOP / VERIFY` rescue moments;
     - 0 critical privacy/security failures;
     - every blocker/miss categorized;
     - at least one repeat-use/follow-up signal recorded.

3. **Served remote MCP runtime identity**
   - Separate channel from local PyPI/stdin MCP.
   - Need: supervised live reload/cutover and live canary.
   - Done criteria:
     - served `borg_runtime_fingerprint` shows expected source/hash/version;
     - live `mcp_borg_observe` unrelated readiness prompt returns `NO_CONFIDENT_MATCH` and no stale plugin/BORG_HOME guidance;
     - live permission-denied prompt still returns permission guidance;
     - result is recorded in `eval/live_mcp_self_serve_canary.json` and docs.
   - Constraint: autonomous agent must not restart/kill/signal gateway. This needs an approved human-operated reload window or a safe platform-level reload command explicitly outside the prohibited gateway-kill path.

## Exact execution sequence

### Phase A — live MCP canary closure

1. Pick a supervised reload window.
2. Human/operator performs safe reload/cutover according to Hermes ops policy. Do not kill the gateway blindly.
3. Immediately run:
   - `borg_runtime_fingerprint`
   - live unrelated readiness `borg_observe` canary
   - live permission-denied `borg_observe` canary
4. Write:
   - `eval/live_mcp_self_serve_canary.json`
   - `docs/LIVE_MCP_SELF_SERVE_CANARY.md`
5. If any stale guidance appears, self-serve remains NO.

### Phase B — package release/canary closure

Prior 3.3.10 proof lives in:

- `docs/20260522_BORG_3310_RELEASE_PREFLIGHT_PUBLISHED.md` (historical)
- `eval/pypi_fresh_install_snapshot.json` (current exact-version package canary)

Current package path status: `agent-borg==3.3.17` is the metadata-correct package target; production PyPI upload and fresh runtime canary are pending. Controlled first-10 is capped at 0 until package metadata, served-runtime freshness, runtime/ops/release-control proof pass; broad public self-serve remains NO-GO until row-derived first-10 evidence passes.

### Phase C — first-10 user sprint

Use `docs/20260514_FIRST_10_USER_INVITE_PACKET.md` exactly.

For each user:

1. Send invite and privacy warning.
2. Record consent.
3. User runs one of:
   - `pipx install agent-borg==3.3.17`
   - fallback venv install from PyPI: `/tmp/borg-beta-venv/bin/python -m pip install agent-borg==3.3.17`
   - source-branch install only for maintainer-approved pre-release testing, never the default first-10 path.
4. User runs:
   - `borg --version`
   - `borg rescue "<redacted real error>"`
5. Record fields in `eval/first_10_user_scoreboard.json`.
6. If a privacy/security incident happens, pause public launch and fix before continuing.

### Phase D — final launch gate

After Phases A and C pass, rerun the canonical gates:

```bash
python eval/run_pypi_fresh_install_canary.py
python eval/public_self_serve_launch_gate.py
python eval/real_user_rollout_gate.py
python scripts/build_borg_proof_dashboard.py
python scripts/borg_proof_dashboard_lint.py
python -m pytest -q tests/readiness/test_public_self_serve_launch_gate.py eval/tests/test_real_user_rollout_gate.py eval/tests/test_borg_proof_dashboard.py
```

Then refresh final launch artifacts:

- `eval/public_self_serve_launch_go_no_go.json`
- `docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md`

## Final go/no-go rule

Public self-serve launch is **GO** only if:

- first-10 scoreboard: PASS thresholds;
- package PyPI/fresh-install/stdio MCP canary: PASS;
- served remote MCP canary: PASS if remote MCP is part of the launch surface;
- repo branch is pushed and reviewable;
- docs claim scrub remains PASS;
- no critical privacy/security incident exists.

Until then: public self-serve launch remains **NO**.
