# Borg first-10 evidence intake

This is the public intake contract for controlled first-10 beta evidence. It is intentionally stricter than a testimonial: public self-serve requires row-derived, consented, external-user evidence.

## Intake path

1. Tester uses the maintainer-approved channel for that cohort: the GitHub source-smoke path while PyPI proof is red, or the next immutable PyPI package only after its fresh-install/MCP/generated-rules/OpenClaw canary is green.
2. Tester runs one real redacted rescue: `borg rescue "<real redacted error>" --short`.
3. Tester optionally attempts local stdio MCP setup with `borg-mcp`.
4. Tester opens `.github/ISSUE_TEMPLATE/first-10-evidence.yml` and fills one row.
5. GitHub issue automation runs `eval/first_10_issue_import.py` to produce a validated candidate row artifact. The issue URL itself is used as `external_user_evidence_uri` when the form field is blank.
6. Maintainer validates redaction, consent, external-user actor, and row shape.
7. Maintainer appends the normalized row through the reviewed append path, not by hand-editing aggregates. Either run the manual workflow `.github/workflows/first-10-scoreboard-pr.yml` with the issue number, or run locally:
   ```bash
   python eval/first_10_reviewed_issue_append.py \
     --issue-body /path/to/issue-body.md \
     --issue-url https://github.com/borg-farther/Borg-Directory/issues/<n> \
     --github-actor <external-github-actor> \
     --reviewer <human-maintainer-reviewer> \
     --internal-actors "$BORG_INTERNAL_ACTORS" \
     --write
   ```
8. Maintainer runs:
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
- normalized/imported evidence URI is HTTPS and secret-free; the issue form may leave it blank only when `eval/first_10_issue_import.py` fills it from the canonical GitHub issue URL;
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
