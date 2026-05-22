# Borg production/day-one hardening plan

Generated: 2026-05-22T09:57:48Z
Branch: `production-readiness-hardening-20260522`
Repo path: `/root/hermes-workspace/borg-firewall-fix`

## Executive verdict

Borg's production nucleus is narrow and real:

> Install `agent-borg`, run `borg rescue "<error>"`, and get an `ACTION / STOP / VERIFY` rescue packet, or a fail-closed `NO_CONFIDENT_MATCH`.

That nucleus is the day-one value path. Everything else is gated by evidence.

## Release-state split

- Controlled supervised first-user path: **GO after local/fresh-install gates pass in this branch**.
- Controlled first-10 beta: **GO only with truthful evidence capture and consented users**.
- Public self-serve launch: **NO-GO until first-10 external-user scoreboard passes**.
- Served remote MCP: **NO-GO until live served runtime path and behavior match audited source**.
- 100 real users: **NO-GO until first-10 evidence passes the 8/6/0 threshold**.
- Real adoption / statistically significant lift: **unproven; count verified external users as zero**.

## What is already real

- Package identity: PyPI package `agent-borg`, import `borg`, CLI `borg`, stdio MCP `borg-mcp`.
- First-user value command: `borg rescue "<error>"`.
- Agent value shape: `ACTION / STOP / VERIFY`, `human_receipt`, automation policy, confidence evidence.
- Fail-closed behavior: unknown inputs return explicit no-match semantics instead of blended weak advice.
- Existing evidence gates distinguish local/synthetic readiness from real external-user rollout.

## P0 blockers that code cannot honestly fake

1. **External-user proof gap**
   - Current evidence rows: zero.
   - Required to unlock public self-serve: 10 consented external users, at least 8 install successes, at least 6 useful rescue moments, 0 critical privacy/security incidents.
   - Permanent rule: do not synthesize or backfill fake rows.

2. **Served MCP split-brain**
   - Audited source path: `/root/hermes-workspace/borg-firewall-fix`.
   - Served runtime reported a different path under `/root/hermes-workspace/borg`.
   - Permanent rule: source tests do not prove live served MCP readiness; live canary + runtime fingerprint must pass after operator-approved runtime cutover.

3. **Public launch claim discipline**
   - Docs may say controlled beta is allowed, but must not imply broad self-serve, 100-user, external lift, or served remote MCP readiness.

## P1 repo-fixable hardening now being delivered

1. **Version truth**
   - Failure mode: MCP `serverInfo.version` hardcoded to `1.0.0` while package/runtime version is `3.3.8`.
   - Fix: source MCP `SERVER_INFO.version` from `borg.__version__`.
   - Tests: initialize response, `SERVER_INFO`, `borg.__version__`, and `pyproject.toml` must all match.

2. **CLI security/static-scan hygiene**
   - Failure mode: first-user interactive CLI path used builtin `input()`, triggering Bandit B322.
   - Fix: read one stdin line via explicit `sys.stdin.readline()` helper; preserve prompts and EOF/interrupt behavior.
   - Tests: source-level no-`input(` regression and interactive rescue fallback smoke.

3. **Apply path safety**
   - Failure mode: `borg apply` auto-selected substring pack-name matches, which could execute the wrong local pack.
   - Fix: exact single-directory pack names only; reject path traversal; return similar suggestions without execution.
   - Tests: reject path-like names and fail closed on fuzzy substring names.

4. **Embedding/schema compatibility**
   - Existing tests already cover legacy trace DBs without `causal_intervention` and ensure no surprise model load on no cached index.
   - Gate remains in targeted proof run.

5. **Row-derived first-10 evidence gate**
   - Failure mode: aggregate counters could be edited without real rows.
   - Fix: `eval/first_10_evidence.py` derives counts only from consented row-level evidence, rejects duplicate/synthetic/internal rows, checks redaction, and verifies stored aggregate consistency.
   - Tests: forged aggregate counts with empty rows must fail; valid 10-row fixture must pass; duplicate/secret rows must fail.

6. **Public self-serve launch gate**
   - Failure mode: first-user/local/synthetic gates could be mistaken for broad public launch readiness.
   - Fix: `eval/public_self_serve_launch_gate.py` requires first-user gate, PyPI latest metadata, PyPI fresh-install + MCP stdio canary, docs claim guard, and first-10 external evidence.
   - Expected current result: controlled first-10 beta infrastructure can be green, but public self-serve remains NO-GO while real evidence rows are zero.

7. **Truthful docs/proof artifact**
   - This document records the hard-gated plan and non-fakeable blockers.
   - Final status must be updated only after fresh test/gate output exists.

## Verification plan

Targeted tests:

```bash
python -m pytest -q \
  tests/mcp/test_mcp_server.py::TestInitialize \
  tests/cli/test_cli.py::test_cli_source_does_not_use_builtin_input \
  tests/cli/test_cli.py::test_rescue_interactive_fallback_reads_one_stdin_line \
  tests/core/test_apply.py::TestActionStart::test_start_rejects_pack_name_paths \
  tests/core/test_apply.py::TestActionStart::test_start_does_not_execute_fuzzy_substring_match \
  tests/packaging/test_embeddings_schema_compat.py
```

Readiness/security gates:

```bash
python -m pytest -q \
  eval/tests/test_borg_day_one_readiness.py \
  eval/tests/test_real_user_rollout_gate.py \
  tests/readiness/test_public_self_serve_launch_gate.py
python scripts/security_gate_check.py
python eval/borg_day_one_readiness.py
python eval/real_user_rollout_gate.py  # expected nonzero while first-10 evidence is empty
python eval/run_pypi_fresh_install_canary.py
python eval/public_self_serve_launch_gate.py  # expected nonzero while first-10 evidence is empty
```

Representative/full proof:

```bash
python -m pytest -q --tb=short
```

Fresh install proof, local branch only and no publish:

```bash
python -m venv /tmp/borg-day-one-proof
PYTHONPATH= /tmp/borg-day-one-proof/bin/python -m pip install --no-cache-dir /root/hermes-workspace/borg-firewall-fix
cd /tmp
PYTHONPATH= /tmp/borg-day-one-proof/bin/borg --version
PYTHONPATH= /tmp/borg-day-one-proof/bin/borg rescue "ModuleNotFoundError: No module named flask" --short
PYTHONPATH= /tmp/borg-day-one-proof/bin/borg-doctor --json
```

Static/security verification:

```bash
python -m bandit -r borg -x tests,build,dist
```

If Bandit is unavailable, the source-level CLI regression still proves the B322 fix; installing tools is not done without explicit approval.

## Allowed claims after repo gates pass

- "Borg is ready for supervised first-user/beta use through the local CLI/PyPI-style rescue path."
- "Borg returns ACTION/STOP/VERIFY or fails closed with NO_CONFIDENT_MATCH."
- "Public self-serve and 100-user rollout remain blocked until real first-10 evidence passes."

## Disallowed claims until new evidence exists

- Broad production/public self-serve readiness.
- Served remote MCP readiness.
- Real adoption or network effects.
- Statistically significant agent-level lift.
- Any guarantee of safety or success.

## Final closeout requirement

This hardening is not complete until the final response records:

- exact changed files,
- exact command outputs/exit codes,
- generated readiness snapshots,
- fresh-install proof result,
- remaining NO-GO blockers with no hand-waving.
