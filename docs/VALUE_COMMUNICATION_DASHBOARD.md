# borg value communication dashboard

## operator benefits (validated internally)
- first visible value path after PyPI release: `pipx install agent-borg==3.3.9` -> `borg rescue "<redacted error>"` -> ACTION / STOP / VERIFY
- pre-release value path: local wheel/source first-user gate is green, but this is not public self-serve proof
- local/synthetic gate status: first-user release gate and logical load gates are green in current artifacts
- external-user proof status: **not proven yet**; verified external users remain `0`
- statistically significant agent-level lift: **not claimed** until a controlled external-user benchmark passes

## readiness status
- controlled first-10 PyPI beta infrastructure: **GO** — PyPI latest, fresh-install, stdio MCP, docs claim guard, and security gates are green
- supervised local first-user path: GO in current artifacts
- public self-serve launch: **NO-GO until first-10 row-derived external evidence passes**
- 100 real-user rollout: **NO-GO until 10 external users, >=8 installs, >=6 useful rescues, and 0 critical incidents**
- decision: controlled first-10 beta only; no broad self-serve or frontier-better-than claim

## evidence
- `eval/public_self_serve_launch_gate_snapshot.json`
- `eval/real_user_rollout_gate_snapshot.json`
- `eval/first_10_user_scoreboard.json`
- `eval/pypi_fresh_install_snapshot.json`
- `eval/first_user_release_gate_snapshot.json`
