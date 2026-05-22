> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg final proof run — 2026-05-17

Generated: `2026-05-18T07:46:07.803035+00:00`

## Binary result

- Expected commands passed: `True`
- First-user release gate: `True`
- Synthetic/load gates through 1000 logical users: `True`
- Ready for 100 real external users: `False`
- Max recommended real users now: `10`

## Real-user blockers

- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

## Command evidence

- `targeted_readiness_and_store_tests`: passed=`True` rc=`0` expected=`[0]` duration_s=`1.507`
- `full_pytest_suite`: passed=`True` rc=`0` expected=`[0]` duration_s=`111.661`
- `security_gate_check`: passed=`True` rc=`0` expected=`[0]` duration_s=`0.068`
- `first_user_release_gate_fresh_venv`: passed=`True` rc=`0` expected=`[0]` duration_s=`12.316`
- `synthetic_load_readiness_gates`: passed=`True` rc=`0` expected=`[0]` duration_s=`93.217`
- `real_user_rollout_gate_expected_block`: passed=`True` rc=`1` expected=`[1]` duration_s=`0.04`
- `doc_and_whitespace_diff_check`: passed=`True` rc=`0` expected=`[0]` duration_s=`0.04`

Full raw stdout/stderr is captured in `eval/20260517_borg_final_proof_run.json`.
