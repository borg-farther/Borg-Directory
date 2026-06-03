# Borg first-10 evidence intake

This is the public intake contract for controlled first-10 beta evidence. It is intentionally stricter than a testimonial: public self-serve requires row-derived, consented, external-user evidence.

## Intake path

1. Tester installs the exact current approved package: `pipx install agent-borg==3.3.17` after the PyPI fresh-install/MCP canary for that exact version is green.
2. Tester runs one real redacted rescue: `borg rescue "<real redacted error>" --short`.
3. Tester optionally attempts local stdio MCP setup with `borg-mcp`.
4. Tester opens `.github/ISSUE_TEMPLATE/first-10-evidence.yml` and fills one row.
5. Maintainer validates redaction, consent, and row shape.
6. Maintainer appends the normalized row to `eval/first_10_user_scoreboard.json`.
7. Maintainer runs:
   - `python eval/first_10_evidence.py --input eval/first_10_user_scoreboard.json --write`
   - `python eval/public_self_serve_launch_gate.py`
   - `python eval/real_user_rollout_gate.py`
   - `python scripts/build_borg_proof_dashboard.py`

## Required fields

The GitHub issue form must map to these row fields:

- `user_id_pseudonym`
- `external_user_evidence_uri`
- `consent_confirmed`
- `install_method`
- `install_success`
- `time_to_first_rescue_minutes`
- `rescue_input_redacted`
- `rescue_returned_action_stop_verify`
- `rescue_useful`
- `mcp_setup_attempted`
- `mcp_setup_success`
- `no_confident_match_when_unknown`
- `blocker_category`
- `blocker_notes_redacted`
- `privacy_security_incident`
- `repeat_use_within_7_days`
- `outcome_recorded`
- `baseline_minutes_without_borg`
- `actual_minutes_with_borg`
- `net_minutes_saved`
- `baseline_tokens_without_borg`
- `actual_tokens_with_borg`
- `net_tokens_saved`
- `savings_counterfactual_basis`
- `dead_end_avoided_confirmed`
- `user_confirmed_value`

## Counting rules

A row counts only when:

- the tester is external, not a maintainer/internal agent/synthetic load user;
- consent is confirmed;
- evidence URI is HTTPS and secret-free;
- the row is redacted and does not contain credentials;
- duplicate pseudonyms are rejected;
- aggregate counters in the scoreboard match row-derived counts.

## Thresholds

Public self-serve remains NO-GO until rows prove:

- 10 verified external users;
- at least 8 install successes;
- at least 6 useful rescue moments;
- 0 critical privacy/security incidents.

## Value/savings claims

Measured savings are not claimed until the same row-derived first-10 evidence includes before/after time or token fields. Maintainer estimates, synthetic load, and aggregate-only edits do not count.

## If a row reports a bad first answer

Open `.github/ISSUE_TEMPLATE/bad-answer.yml` and record the bad guidance. Agents should use the shipped MCP/CLI path `borg_record_failure(...)` or `borg feedback-v3 ...` for durable learning. Do not rely on nonexistent helper names.
