# borg value communication dashboard

## operator benefits (validated internally)
- first visible value path after PyPI release: `pipx install agent-borg==3.3.14` -> `borg rescue "<redacted error>"` -> ACTION / STOP / VERIFY
- pre-release value path: local wheel/source first-user gate is green, but this is not public self-serve proof
- local/synthetic gate status: first-user release gate and logical load gates are green in current artifacts
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
- controlled first-10 PyPI beta infrastructure: **NO-GO for this source revision** — publish `agent-borg==3.3.14`, then rerun fresh-install/stdio MCP package evidence before inviting testers
- supervised local first-user path: GO in current artifacts
- public self-serve launch: **NO-GO until first-10 row-derived external evidence passes**
- 100 real-user rollout: **NO-GO until 10 external users, >=8 installs, >=6 useful rescues, and 0 critical incidents**
- decision: controlled first-10 beta invites may not start for `agent-borg==3.3.14` until PyPI latest, fresh-install, and stdio MCP package evidence are green; no broad self-serve or frontier-better-than claim

## evidence
- `eval/public_self_serve_launch_gate_snapshot.json`
- `eval/real_user_rollout_gate_snapshot.json`
- `eval/first_10_user_scoreboard.json`
- `eval/pypi_fresh_install_snapshot.json`
- `eval/first_user_release_gate_snapshot.json`
