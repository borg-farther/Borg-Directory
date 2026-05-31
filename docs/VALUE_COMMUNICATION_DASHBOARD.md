# borg value communication dashboard

## operator benefits (validated internally)
- first visible value path for controlled beta: `pipx install agent-borg==3.3.15` -> `borg rescue "<redacted error>"` -> ACTION / STOP / VERIFY
- controlled package beta path: **NO-GO right now** — `agent-borg==3.3.15` exists on PyPI, but the same-version upload predates the current source hardening revision, so package proof is stale until a new immutable version is published and freshly canaried
- local/synthetic gate status: first-user release gate and logical load gates are green in current artifacts; synthetic users are not external-user evidence
- external-user proof status: **not proven yet**; verified external users remain `0`
- measured savings status: **0 measured rows, 0.0 net minutes saved, 0 net tokens saved**; savings are not claimed until consented external-user rows include before/after measurements
- statistically significant agent-level lift: **not claimed** until a controlled external-user benchmark passes

## measured savings contract
- source of truth: `eval/first_10_user_scoreboard.json` rows, recomputed by `eval/first_10_evidence.py`
- allowed measurement fields: `baseline_minutes_without_borg`, `actual_minutes_with_borg`, `net_minutes_saved`, `baseline_tokens_without_borg`, `actual_tokens_with_borg`, `net_tokens_saved`, `savings_counterfactual_basis`, `dead_end_avoided_confirmed`, `user_confirmed_value`
- validator rule: `net_*_saved` must equal baseline minus actual; forged aggregate fields block public self-serve
- dashboard rule: public `value.json` and proof dashboard may show only row-derived measured savings, never estimates from a rescue call
- rescue rule: `borg rescue --json` exposes `value_receipt.measurement_status=ready_to_measure` and `savings_claim_type=none` until a later first-10 row records the outcome

## readiness status
- controlled first-10 PyPI beta: **NO-GO right now** — `agent-borg==3.3.15` package proof is stale for the current source revision, and served-runtime freshness plus release-governance gates are red; invite 0 consented external users until a new immutable package version, release controls, and ops/watchdog proof are green
- supervised local first-user path: GO in current artifacts
- public self-serve launch: **NO-GO until first-10 row-derived external evidence passes**
- 100 real-user rollout: **NO-GO until 10 external users, >=8 installs, >=6 useful rescues, and 0 critical incidents**
- decision: package proof is **not current** for `agent-borg==3.3.15` because the PyPI upload predates this source revision; controlled first-10 beta must wait for a new immutable package version, served-runtime freshness, release governance, ops/watchdog, and proof-dashboard gates; no broad self-serve, served remote MCP, 100-user, measured-savings, or frontier-better-than claim

## evidence
- `eval/public_self_serve_launch_gate_snapshot.json`
- `eval/real_user_rollout_gate_snapshot.json`
- `eval/first_10_user_scoreboard.json`
- `eval/pypi_fresh_install_snapshot.json`
- `eval/served_runtime_fingerprint_snapshot.json`
- `eval/release_governance_snapshot.json`
- `eval/ops_readiness_watchdog_snapshot.json`
- `eval/first_user_release_gate_snapshot.json`
