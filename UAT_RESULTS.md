# UAT_RESULTS

Date: 2026-04-20T09:08:46.112248+00:00
Scope: latest readiness gate execution in `/root/hermes-workspace/borg`

## Run parameters
- soak_duration_seconds: 180
- experiment_id: auto-latest

## Step results
- feedback_loop_tests: PASS (rc=0)
- metrics_contract_tests: PASS (rc=0)
- load_10: PASS (rc=0)
- load_100: PASS (rc=0)
- experiment_packet: PASS (rc=0)
- scoreboard: PASS (rc=0)

## Canonical rollout status
Final GO/NO-GO is always sourced from canonical artifacts, not this summary:
- `GO_NO_GO_DECISION.md`
- `PROJECT_STATUS.md`
- `/root/hermes-workspace/borg/eval/gate_run_snapshot.json`

## Notes
- This file is regenerated on every `eval/run_readiness_gates.py` run.
- Any failed hard gate blocks rollout.
