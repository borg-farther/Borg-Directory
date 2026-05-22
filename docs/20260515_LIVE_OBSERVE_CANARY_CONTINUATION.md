> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg live observe canary continuation — 2026-05-15

## Verdict

- READY_FOR_SUPERVISED_FIRST_USER: YES_WITH_DISCLOSED_LIVE_CAVEAT
- READY_FOR_PUBLIC_WAITLIST_OR_NARROW_BETA: YES_WITH_CAVEATS
- READY_FOR_SELF_SERVE_PUBLIC_LAUNCH: NO
- LIVE_MCP_OBSERVE_CANARY: FAILING_STALE_IN_MEMORY_PROCESS
- FIRST_10_REAL_USERS: BLOCKED_VERIFIED_EXTERNAL_USERS_0

## What changed in source

Patched `/root/hermes-workspace/borg/borg/core/confidence_gate.py` and regression tests in `/root/hermes-workspace/borg/borg/tests/test_confidence_gate.py`.

New source hardening:

1. `trace_match_is_confident()` now requires concrete non-meta lexical overlap when fallback trace hits do not include an explicit `similarity` score. This closes the path where actionable-looking Hermes/Borg runtime traces could bypass relevance checks.
2. `guidance_is_safe_to_inject()` now suppresses non-permission `PACK GUIDANCE (...)` unless the pack label has concrete overlap with the current task. This closes the observed case where a readiness/runtime prompt received unrelated `PACK GUIDANCE (python-type-error)`.
3. Regression coverage added for:
   - missing-similarity Hermes plugin/BORG_HOME trace rejected for Borg readiness prompt;
   - high-confidence but unrelated `PACK GUIDANCE (python-type-error)` suppressed;
   - relevant `PACK GUIDANCE (git-merge-conflict)` still allowed for an actual git merge conflict;
   - permission guidance remains allowed only for concrete permission-denied tasks.

## Live canary result

`mcp_borg_mcp_borg_runtime_fingerprint` reports the served process path and disk hashes:

- PID: `101562`
- executable: `/root/.hermes/hermes-agent/venv/bin/python3`
- cwd: `/root/.hermes/hermes-agent`
- `borg`: `/root/hermes-workspace/borg/borg/__init__.py`
- `borg.core.confidence_gate`: `/root/hermes-workspace/borg/borg/core/confidence_gate.py`
- confidence_gate.py disk sha after patch: `99df0ae36ff5c8e77dca4099698ff2f90b4628b3b99506cb5382bef12981f732`

But the live `mcp_borg_mcp_borg_observe` canary still returns irrelevant guidance for:

```text
continue Borg readiness/get it there: fix borg_observe irrelevant guidance/runtime mismatch and proceed toward first-user readiness
```

Observed failing live output includes:

```text
ACTION: Plugin directory ~/.hermes/plugins/ is NOT auto-discovered. Real plugin is in hermes_cli/plugins/ in source tree. BORG_HOME env var in service file wa
CONFIDENCE: Real traces: 22 | Synthetic: 0 | Most recent: 31d ago | BORG [HIGH CONFIDENCE]
PACK GUIDANCE (python-type-error)
```

Interpretation: disk/source is patched, but the currently served MCP process is still executing stale in-memory code/state. Trust the live behavior canary over disk hashes.

## Safety boundary

No gateway restart, kill, or signal was attempted. This environment has an explicit safety rule forbidding gateway process restarts/kills/signals. The approved next step is operator-supervised reload/cutover of the Borg MCP/Hermes service boundary only, followed by live canaries.

## Exact post-reload canaries

After safe reload/cutover, rerun:

1. `borg_runtime_fingerprint`
   - expected: served process reports `/root/hermes-workspace/borg` paths and current `confidence_gate.py` hash.

2. Unrelated readiness observe canary:

```text
borg_observe(task="continue Borg readiness/get it there: fix borg_observe irrelevant guidance/runtime mismatch and proceed toward first-user readiness", context="python borg mcp runtime readiness")
```

Expected:

- contains `NO_CONFIDENT_MATCH` or equivalent fail-closed response;
- does not contain `Plugin directory ~/.hermes/plugins/`;
- does not contain `BORG_HOME env var`;
- does not contain `PACK GUIDANCE (python-type-error)`;
- does not contain unrelated permission/django/git pack guidance.

3. Positive permission canary:

```text
borg_observe(task="Fix bash: ./deploy.sh: Permission denied", context="bash permission denied chmod")
```

Expected:

- permission guidance remains allowed;
- includes `Permission denied`, `chmod`, or `PACK GUIDANCE (bash-permission-denied)`;
- does not return `NO_CONFIDENT_MATCH` for the concrete permission task.

## First-10 / launch state

`eval/first_10_user_scoreboard.json` remains truthful:

- `verified_external_users`: 0
- `real_users`: 0
- `install_successes`: 0
- `useful_rescue_moments`: 0
- `public_self_serve_launch_gate`: BLOCKED

Therefore public self-serve launch remains NO. Public waitlist/narrow beta remains possible only with caveats and supervised onboarding; do not claim real adoption or unattended self-serve readiness until first-10 thresholds are met.
