# Borg public self-serve launch closure plan

Generated: 2026-05-14 18:39 UTC

## Current state

Borg is **public waitlist / narrow-beta ready** on branch `public-waitlist-readiness-20260514`.

Hard evidence already completed:

- Pushed branch: `public-waitlist-readiness-20260514`
- Pushed head observed in prior run: `a20921610b7d41bcc7db71361f1271c347ecbc58`
- Required local gates: PASS
- pipx proof: PASS
- security baseline: PASS
- privacy/prompt-injection/atom/firewall tests: PASS
- source canaries: PASS
- first-10 invite packet exists
- first-10 scoreboard exists and truthfully reports `verified_external_users=0`

## Remaining self-serve blockers

Only two true blockers remain for full public self-serve launch:

1. **Live MCP runtime identity**
   - Need: supervised live reload/cutover and live canary.
   - Done criteria:
     - served `borg_runtime_fingerprint` shows expected source/hash/version;
     - live `mcp_borg_observe` unrelated readiness prompt returns `NO_CONFIDENT_MATCH` and no stale plugin/BORG_HOME guidance;
     - live permission-denied prompt still returns permission guidance;
     - result is recorded in `eval/live_mcp_self_serve_canary.json` and docs.
   - Constraint: autonomous agent must not restart/kill/signal gateway. This needs an approved human-operated reload window or a safe platform-level reload command explicitly outside the prohibited gateway-kill path.

2. **First 10 real external users**
   - Need: real external-user outcome evidence, not simulations.
   - Done criteria:
     - 10 consented real external user rows in `eval/first_10_user_scoreboard.json`;
     - ≥8/10 install successes;
     - ≥6/10 useful `ACTION / STOP / VERIFY` rescue moments;
     - 0 critical privacy/security failures;
     - every blocker/miss categorized;
     - at least one repeat-use/follow-up signal recorded.

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

### Phase B — first-10 user sprint

Use `docs/20260514_FIRST_10_USER_INVITE_PACKET.md` exactly.

For each user:

1. Send invite and privacy warning.
2. Record consent.
3. User runs one of:
   - `pipx install git+https://github.com/borg-farther/Borg-Directory.git`
   - fallback venv install from same repo URL.
4. User runs:
   - `borg --version`
   - `borg rescue "<redacted real error>"`
5. Record fields in `eval/first_10_user_scoreboard.json`.
6. If a privacy/security incident happens, pause public launch and fix before continuing.

### Phase C — final launch gate

After Phase A and B pass, run all release gates again:

```bash
python -m pytest -q borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_runtime_fingerprint.py
python scripts/build_borg_proof_dashboard.py
python scripts/borg_proof_dashboard_lint.py
python -m pytest -q eval/tests/test_borg_proof_dashboard.py
python eval/run_first_user_release_gate.py
python scripts/security_gate_check.py
python -m pytest -q borg/tests/test_privacy_structured.py borg/tests/test_prompt_injection.py borg/tests/test_atom_policy.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_privacy.py
python scripts/fix_public_launch_blockers_safe.py
```

Then write final launch artifacts:

- `eval/public_self_serve_launch_go_no_go.json`
- `docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md`

## Final go/no-go rule

Public self-serve launch is **GO** only if:

- live MCP canary: PASS;
- first-10 scoreboard: PASS thresholds;
- local/security/pipx gates: PASS;
- repo branch is pushed and reviewable;
- docs claim scrub remains PASS;
- no critical privacy/security incident exists.

Until then: public self-serve launch remains **NO**.
