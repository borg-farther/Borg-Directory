> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# 20260513 Borg full audit + observe confidence-gate closure

## Executive decision

Borg remains **CONTROLLED GO for supervised first-user beta only**.

Borg is still **NO-GO for unattended Git onboarding** and **NO-GO for broad public launch** until real external-user evidence exists.

The immediate blocker found in this pass was not a missing feature. It was a trust bug: live Borg guidance could inject confident-looking weak/synthetic pack advice (`bash-permission-denied`, later `git-merge-conflict`) into unrelated readiness/beta prompts. That violates the first-10 beta contract: weak matches must fail closed as `NO_CONFIDENT_MATCH`.

## What was reviewed

### Canonical Borg package

- `/root/hermes-workspace/borg/README.md`
- `/root/hermes-workspace/borg/pyproject.toml`
- `/root/hermes-workspace/borg/borg/__init__.py`
- `/root/hermes-workspace/borg/borg/cli.py`
- `/root/hermes-workspace/borg/borg/integrations/mcp_server.py`
- `/root/hermes-workspace/borg/borg/core/first_user_readiness.py`
- `/root/hermes-workspace/borg/borg/core/search.py`
- `/root/hermes-workspace/borg/borg/core/trace_matcher.py`
- `/root/hermes-workspace/borg/borg/core/rescue.py`
- `/root/hermes-workspace/borg/borg/tests/test_borg_observe_confidence_gate.py`
- `/root/hermes-workspace/borg/borg/tests/test_first_10_readiness.py`
- `/root/hermes-workspace/borg/eval/run_first_user_release_gate.py`
- `/root/hermes-workspace/borg/eval/uat_scoreboard.py`
- `/root/hermes-workspace/borg/eval/run_readiness_gates.py`
- `/root/hermes-workspace/borg/scripts/build_borg_proof_dashboard.py`
- `/root/hermes-workspace/borg/scripts/borg_proof_dashboard_lint.py`

### Readiness / docs truth surfaces

- `/root/hermes-workspace/borg/docs/BORG_PROOF_DASHBOARD.md`
- `/root/hermes-workspace/borg/docs/FIRST_10_BETA_READINESS.md`
- `/root/hermes-workspace/borg/GO_NO_GO_DECISION.md`
- `/root/hermes-workspace/borg/PROJECT_STATUS.md`
- `/root/hermes-workspace/borg/UAT_RESULTS.md`
- `/root/hermes-workspace/borg/docs/README.md`
- `/root/hermes-workspace/borg/docs/SECURITY_HARDENING_BASELINE.md`
- `/root/hermes-workspace/borg/docs/PRIVACY_MODEL.md`
- `/root/hermes-workspace/borg/docs/PROMPT_INJECTION_THREAT_MODEL.md`
- `/root/hermes-workspace/borg/docs/REVOCATION_AND_DELETION.md`
- `/root/hermes-workspace/borg/docs/TRUST_AND_PROMOTION.md`
- `/root/hermes-workspace/borg/docs/LEARNING_ATOM_SCHEMA.md`

### Runtime/path-mismatch surfaces

- `/root/hermes-workspace/borg/borg/integrations/mcp_server.py` — canonical current code already had fail-closed helpers.
- `/root/hermes-workspace/borg/build/lib/borg/integrations/mcp_server.py` — build copy also had current fail-closed helpers.
- `/home/user/guild-tools/borg/integrations/mcp_server.py` — older active-candidate runtime path, missing confidence gate before this pass.
- `/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py` — older mirror, missing confidence gate before this pass.
- `/root/.hermes/hermes-agent/hermes_cli/plugins/borg_auto_trace/__init__.py` — real Hermes plugin path.
- `/root/.hermes/hermes-agent/plugins/borg_auto_trace/__init__.py` — duplicate plugin path; patched defensively but not assumed live.

## Findings

### F1 — Canonical source already had the right intent

The canonical current package already includes:

- `_no_confident_match_response()`
- `_trace_match_is_confident()`
- `_pack_match_is_confident()`
- regression tests for unrelated prompt → no `bash-permission-denied`
- first-10 readiness tests that require `NO_CONFIDENT_MATCH`

This means the product direction is correct: weak retrieval must fail closed.

### F2 — Live behavior still leaked stale guidance

Observed live `mcp_borg_observe` returned unrelated guidance for a first-user beta/readiness prompt:

- `PACK GUIDANCE (bash-permission-denied)` for a beta proof continuation prompt.
- Then `PACK GUIDANCE (git-merge-conflict)` for a docs/readiness proof prompt.

That means the running served path or preloaded module is not fully aligned with the canonical repo code.

### F3 — There are multiple Borg runtimes

The repo contains at least four relevant Borg/MCP codepaths:

1. canonical: `/root/hermes-workspace/borg/borg/integrations/mcp_server.py`
2. build copy: `/root/hermes-workspace/borg/build/lib/borg/integrations/mcp_server.py`
3. older active candidate: `/home/user/guild-tools/borg/integrations/mcp_server.py`
4. older mirror: `/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py`

The older active-candidate and mirror implementations used `classify_task()` + broad text search and had no fail-closed pack confidence gate. Those are exactly the paths that can turn broad search into unrelated guidance.

### F4 — The Hermes plugin needed its own safety belt

Even if Borg itself is fixed, the Hermes auto-trace pre-LLM plugin is the last place where bad guidance becomes prompt context. If an old Borg module is already loaded in memory, source patches do not change the current Python module object until reload/restart.

Therefore the plugin must independently suppress:

- `NO_CONFIDENT_MATCH` guidance,
- weak/no-match guidance,
- `BORG [SYNTHETIC ONLY]` pack guidance,
- any `Real traces: 0` + `PACK GUIDANCE` response,
- `PACK GUIDANCE (bash-permission-denied)` unless the user task actually contains a permission-denied signal,
- stale/pasted `=== BORG GUIDANCE ===` blocks before task classification or permission-signal detection.

A quoted old guidance block must be inert text, never evidence for a new `borg_observe` match.

## Changes made

### C1 — Patched older active-candidate MCP runtime

File:

- `/home/user/guild-tools/borg/integrations/mcp_server.py`

Added:

- `_no_confident_match_response()`
- `_pack_match_is_confident()`
- fail-closed filtering before choosing `best_match`

Effect:

- unrelated tasks no longer pick broad seed/generic packs in that path.
- permission packs only match concrete `permission denied`, `EACCES`, `chmod`, `operation not permitted`, `access denied`, or read-only filesystem wording.

### C2 — Patched older guild-v2 mirror

File:

- `/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py`

Added the same fail-closed helpers and filtering.

Effect:

- if any MCP config still points at the older mirror, it now fails closed instead of leaking unrelated pack guidance.

### C3 — Patched real Hermes Borg auto-trace plugin

File:

- `/root/.hermes/hermes-agent/hermes_cli/plugins/borg_auto_trace/__init__.py`

Added:

- `_permission_guidance_matches_task()`
- `_guidance_is_safe_to_inject()`
- `_strip_embedded_borg_guidance()`
- stricter `_is_observe_worthy()` that no longer treats long prose alone as a trigger
- suppression before returning `{"context": "=== BORG GUIDANCE ===..."}`

Effect:

- even if live Borg returns stale weak/synthetic guidance, the plugin will not inject it into the LLM prompt unless it is safely relevant.

### C4 — Patched duplicate plugin path defensively

File:

- `/root/.hermes/hermes-agent/plugins/borg_auto_trace/__init__.py`

Same safety-belt helpers and injection guard.

This path is not assumed live, but patching it removes future ambiguity.

### C5 — Added Hermes plugin regression tests

File:

- `/root/.hermes/hermes-agent/tests/test_borg_auto_trace_guidance_filter.py`

Tests added:

- permission guidance requires concrete permission signal.
- embedded/pasted `=== BORG GUIDANCE ===` blocks are stripped before permission detection.
- long nontechnical operator instructions do not trigger auto-observe just because they are long.
- stale embedded Borg guidance does not make a meta request observe-worthy.
- unrelated first-user beta prompt suppresses synthetic `bash-permission-denied` guidance.
- `NO_CONFIDENT_MATCH` guidance is not injected.
- `Real traces: 0` pack guidance is suppressed even if it is not labeled synthetic-only.
- real permission-denied task can still inject permission guidance.
- real high-confidence guidance is still allowed.

## Existing tests found

Canonical Borg already had:

- `/root/hermes-workspace/borg/borg/tests/test_borg_observe_confidence_gate.py`
- `/root/hermes-workspace/borg/borg/tests/test_first_10_readiness.py`

These lock the intended product behavior for the canonical package.

## Verification status

Static patch validation passed via the patch tool lint checks for modified Python files.

2026-05-14 source-level verification:

- needle scan confirms `_strip_embedded_borg_guidance`, `task_clean = _strip_embedded_borg_guidance`, and `real traces: 0` pack-guidance suppression exist in both Hermes plugin paths;
- needle scan confirms the same guard exists in canonical Borg, guild-v2, guild-tools, and installed `/usr/local/lib/python3.12/dist-packages/borg` runtime candidate;
- regression tests now cover the exact failure mode: a user message that includes pasted `=== BORG GUIDANCE === ... PACK GUIDANCE (bash-permission-denied)` must not create a permission-denied signal or auto-observe trigger.

Live probe status 2026-05-14: direct `mcp_borg_observe` still returned unrelated `rust_lifetime_error` plus `PACK GUIDANCE (bash-permission-denied)` for the pasted-guidance meta prompt. This confirms a stale in-memory served MCP module remains active until reload. Source/runtime/plugin files are patched; live served behavior is not claimed until a permitted reload/fresh process proves it.

A one-shot verification job was scheduled to run exact pytest/import-smoke commands with terminal access because this session toolset does not include a terminal executor. Job:

- `a582ef63406d` — `borg-observe-confidence-gate-verification-20260513`

Commands scheduled:

```bash
cd /root/hermes-workspace/borg && python -m pytest borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_first_10_readiness.py -q
cd /root/.hermes/hermes-agent && python -m pytest tests/test_borg_auto_trace_guidance_filter.py -q
```

Plus import-level smokes for canonical `_pack_match_is_confident()` and plugin `_guidance_is_safe_to_inject()`.

## What is still not claimed

This pass does **not** claim:

- the currently running gateway process has reloaded patched plugin source,
- the currently served MCP process has reloaded patched Borg source,
- broad public production readiness,
- unattended Git onboarding readiness,
- external-user adoption or retention,
- statistically significant success-rate lift.

Those require executable runtime evidence after reload / fresh process invocation and real first-user outcomes.

## Permanent standard from this audit

1. Borg must never inject weak synthetic pack guidance into unrelated prompts.
2. If Borg cannot prove relevance, output or treat as `NO_CONFIDENT_MATCH`.
3. Readiness docs remain controlled-go only until real external-user evidence exists.
4. Multiple runtime copies are a release risk; future fixes must patch/verify the actually loaded path, not only the canonical repo.
5. The plugin must fail closed because it is the final prompt-injection boundary.

## Next action after verification

If the verification job passes:

1. reload the relevant served runtime only with explicit operator approval,
2. rerun the exact live `mcp_borg_observe` probe,
3. confirm no unrelated `PACK GUIDANCE` appears,
4. continue first-user beta proof package.

If the verification job fails:

1. fix the failed test directly,
2. rerun the same targeted commands,
3. keep first-user onboarding blocked until green.
