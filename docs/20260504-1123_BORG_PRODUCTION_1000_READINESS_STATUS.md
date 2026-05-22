> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# File rev 20260504-1123 rev B — Borg production / 1000-user readiness closure status

## Status

**STATUS: COMPLETE FOR THE CURRENT LOCAL FIRST-USER / 1000-LOGICAL-USER READINESS GATES.**

The earlier rev A blocker was execution proof only: `eval/load_soak.py` was executed as a script, so the repo root was not on `sys.path`, producing `ModuleNotFoundError: No module named 'borg.core.atom_retrieval'`.

That import-path blocker was patched and the second proof run completed green.

## Static blockers addressed

1. Version split-brain fixed:
   - `pyproject.toml`: `3.3.1`
   - `borg/__init__.py`: `3.3.1`
   - `build/lib/borg/__init__.py`: `3.3.1`

2. Root license added:
   - `LICENSE` with MIT license text.

3. Optional dependency groups fixed for documented install paths / CI:
   - `semantic`
   - `embeddings`
   - `crypto`
   - `dev`
   - `all`

4. Runtime doctor upgraded:
   - `borg/cli/doctor.py`
   - `build/lib/borg/cli/doctor.py`
   - emits runtime fingerprint with version, module path/hash, BORG_HOME, trace DB path, atom DB path, counts, PID, Python path.
   - restored `run_doctor()` entrypoint for `borg-doctor` console script.

5. Security gate tightened:
   - `scripts/security_gate_check.py` requires root `LICENSE`.
   - `docs/README.md` must reference `SECURITY_HARDENING_BASELINE.md` and `security_hardening_baseline.json`.

6. 1000-user readiness machinery added:
   - `eval/load_soak.py`
   - `eval/uat_scoreboard.py`
   - `eval/run_readiness_gates.py`
   - `eval/tests/test_readiness_1000.py`

7. Regression tests added:
   - `borg/tests/test_version_consistency.py`
   - `borg/tests/test_runtime_doctor.py`
   - `eval/tests/test_readiness_1000.py`

## Rev A first proof run result

Cron session: `/root/.hermes/sessions/session_cron_bf9198f66c42_20260504_111844.json`

Passing:

- version/distribution/runtime-doctor tests: `6 passed`
- atom/security/privacy tests: `87 passed`
- security gate: `PASS: Borg security hardening policy gate`
- atom fixture corpus: `success=true`, `total=10`
- readiness structure tests: `5 passed`
- targeted final tests: `9 passed`
- doctor: pass; trace DB showed `170 traces at /root/.borg/traces.db`

Failing:

- `load_10`: rc=1
- `load_100`: rc=1
- `load_1000`: rc=1
- `scoreboard_final`: rc=1
- `ready_for_1000`: false

Root cause from raw stderr:

```text
ModuleNotFoundError: No module named 'borg.core.atom_retrieval'
```

## Fix after first proof run

Patched `eval/load_soak.py`:

```python
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

## Rev B second proof run result

Cron session: `/root/.hermes/sessions/session_cron_bc36734123de_20260504_112218.json`

All required conditions passed:

- `GATE_RC:0`
- `SCOREBOARD_RC:0`
- `TARGETED_RC:0`
- `DOCTOR_RC:0`
- `eval/load_10_snapshot.json`: `passed=true`
- `eval/load_100_snapshot.json`: `passed=true`
- `eval/load_1000_snapshot.json`: `passed=true`
- `eval/uat_scoreboard_snapshot.json`: `ready_for_1000=true`
- `eval/gate_run_snapshot.json`: `ready_for_1000=true`

1000-logical-user soak snapshot:

```json
{
  "users": 1000,
  "operation": "learning_atom_retrieval_firewall_privacy_prompt_scan",
  "passed": true,
  "success_rate": 1.0,
  "failures": 0,
  "total_requests": 66838,
  "requests_per_second": 2227.9333333333334,
  "latency_ms": {
    "p50": 0.4074538592249155,
    "p95": 0.5817607045173645,
    "p99": 0.613755825906992,
    "max": 2.3157899267971516
  }
}
```

Canonical machine snapshots:

- `eval/gate_run_snapshot.json`
- `eval/load_10_snapshot.json`
- `eval/load_100_snapshot.json`
- `eval/load_1000_snapshot.json`
- `eval/uat_scoreboard_snapshot.json`
- `PROJECT_STATUS.md`
- `GO_NO_GO_DECISION.md`

## Honest boundary

This proves the current local runtime gates for first-user install surface, security/privacy/atom policy tests, and 10/100/1000 logical-user learning-atom retrieval/firewall/privacy/prompt-scan soak. It does **not** prove global network adoption, real external-user utility, or statistically significant agent-level outcome lift.

## Verdict

Code-side blocker closure: **complete for current gates**.  
Production/1000-logical-user readiness: **GO for controlled rollout**.  
External claims must remain scoped to the proof above.
