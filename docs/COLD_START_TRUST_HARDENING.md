# Borg cold-start trust hardening

Generated: `2026-05-25T16:30:12.581344+00:00`
Gate: **PASS**

## Why this gate exists

One irrelevant first Borg answer can destroy trust. Cold-start prompts must therefore fail closed instead of forcing a weak pack or random framework fix.

## Hard policy

Borg must fail closed with NO_CONFIDENT_MATCH for meta/product/readiness prompts, must not inject unrelated framework guidance, and must preserve concrete error guidance for exact failures.

## Scope and runtime boundary

This gate proves fresh source/stdio behavior from this checkout. It does not prove that a long-lived served Hermes/MCP runtime has reloaded this code. Served runtime GO additionally requires `borg_runtime_fingerprint` with `version_matches_source=true`, `observe_behavior_canary.passed=true`, and `reload_status=loaded_code_matches_source_behavior`.

## Checks

- `meta_permission_mentions_are_not_permission_tasks`: `PASS`
- `meta_django_mentions_do_not_set_django_tech`: `PASS`
- `high_similarity_meta_only_trace_rejected`: `PASS`
- `irrelevant_real_trace_only_guidance_not_injectable`: `PASS`
- `concrete_permission_signal_still_allowed`: `PASS`
- `stdio_meta_trust_prompt_fails_closed`: `PASS`
- `stdio_concrete_permission_prompt_gets_specific_guidance`: `PASS`

## Bad-answer feedback path

- Agent fast path: `call borg_rate(helpful=False) immediately after a bad suggestion`
- Durable memory path: `call borg_record_failure(error_pattern, pack_id, phase, approach, outcome='failure') when the bad path is concrete`
- Human path: open a GitHub issue using the bad-answer report template or paste the redacted transcript into first-10 evidence intake

## Public rollout boundary

This gate is required for controlled beta and public self-serve, but it is not sufficient for public self-serve. Broad public launch still requires row-derived first-10 external-user evidence.

## Evidence artifacts

- `eval/cold_start_trust_gate_snapshot.json`
- `tests/readiness/test_confidence_gate.py`
- `tests/mcp/test_borg_observe_confidence_gate.py`
- `tests/mcp/test_stdio_transport.py`
