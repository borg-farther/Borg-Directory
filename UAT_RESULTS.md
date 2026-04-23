# UAT Results

- timestamp (utc): `2026-04-23T11:52:29+00:00`
- overall status: **PASS**
- decision: **GO**

## Checks

| check | severity | status | detail |
|---|---|---|---|
| `git-home-cutover` | `critical` | **PASS** | origin_ok=True, legacy_remote_present=False, legacy_push_disabled=False |
| `governance-enforcement` | `critical` | **PASS** | success=True |
| `readiness-contract` | `critical` | **PASS** | overall_status=pass, operational_ready=True, sync_status=pass |
| `test-gate` | `critical` | **PASS** | status=pass, pytest_rc=0, summary=18 passed in 0.09s |
| `scale-gates` | `critical` | **PASS** | ready_for_10=True, ready_for_100=True, ready_for_1000=True, all_pass=True |
| `utility-and-savings` | `critical` | **PASS** | success_lift=0.6500, control_completion=0.3500, treatment_completion=1.0000, control_tokens_mean=2475.00, treatment_tokens_mean=1200.00 |
| `anti-theater-artifacts` | `high` | **PASS** | all required artifacts exist, are non-empty, and contain no placeholder markers |
| `legacy-access-warning` | `warning` | **PASS** | no legacy access warning reported |
