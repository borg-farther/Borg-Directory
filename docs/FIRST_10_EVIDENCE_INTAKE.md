# First-10 Evidence Intake

Authoritative protocol: [`FIRST_10_RESCUE_PROTOCOL.md`](FIRST_10_RESCUE_PROTOCOL.md)

Machine scoreboard: `eval/first_10_user_scoreboard.json`

Issue form: `.github/ISSUE_TEMPLATE/first-10-evidence.yml`

## Enrollment rule

Do not recruit or accept participants while the scoreboard says `protocol.enrollment_open: false`. Before opening, lock one PyPI version and its wheel SHA-256.

## Intake sequence

1. Before installation, assign the consenting participant the next immutable `enrollment_index` slot (1–10) and pseudonym. Never reuse a slot.
2. Participant submits the issue form after attempting the frozen protocol.
3. Use the submitted issue URL as `external_user_evidence_uri`; never ask a participant to predict their own issue URL.
4. Verify consent, external-user status, uniqueness, artifact version, redaction, command evidence, and field completeness. Post a redacted maintainer validation note and retain its HTTPS URI.
5. Transcribe one row without changing the participant’s reported outcome. Set `maintainer_validation_status` to `verified` only after step 4; rejected/pending rows cannot count.
6. Keep lifecycle state synchronized before writing derived counts: after slot 1 set `protocol.status: in_progress`; after slot 10 set `protocol.status: complete` and `protocol.enrollment_open: false`. `complete` records cohort closure, not a passing verdict.
7. Run:

   ```bash
   python eval/first_10_evidence.py --write
   python eval/first_10_evidence.py --check
   ```

8. Review derived blockers. Editable totals are not evidence.
9. Pause enrollment immediately if any row reports a false-confident unknown control, harmful guidance, a critical privacy/security incident, or an unredacted secret.

## Required row fields

### Identity and consent

- `user_id_pseudonym`
- `enrollment_index`
- `external_user_evidence_uri`
- `maintainer_validation_status`
- `maintainer_validation_evidence_uri`
- `consent_confirmed`
- `task_was_real_current_failure`

### Immutable artifact and install

- `artifact_version`
- `install_method` containing `agent-borg==<artifact_version>`
- `install_success`
- `time_to_first_rescue_minutes`

Failed installs remain valid rows and remain in the denominator.

### Real rescue result

- `rescue_input_redacted`
- `rescue_returned_action_stop_verify`
- `rescue_useful`
- `guidance_relevant`
- `verification_status`: `passed`, `failed`, or `not_reached`
- `verification_evidence_redacted`
- `maintainer_help_before_first_value`

A useful rescue counts only when verification passed and no maintainer help occurred before value.

### Safety control

- `unknown_control_input_id`: `unknown-control-v1`
- `unknown_control_status`: `no_confident_match`, `false_confident_match`, or `not_run_install_failed`
- `no_confident_match_when_unknown`
- `false_confident_match`
- `harmful_guidance`
- `privacy_security_incident`

Every successful install must run the control. The explicit boolean fields must agree with `unknown_control_status`.

### Outcome evidence

- `outcome_recorded`
- `outcome_capture_method`: `borg_record_outcome`, `borg_feedback_v3`, `github_evidence_issue`, or `not_reached`
- `outcome_evidence_id`
- `blocker_category`
- `blocker_notes_redacted`
- `repeat_use_within_7_days`

### Optional descriptive value measurement

- before/after minutes and/or tokens;
- `savings_counterfactual_basis`;
- `dead_end_avoided_confirmed`;
- `user_confirmed_value`.

Savings do not count without a stated counterfactual basis and paired before/after values. Descriptive savings are not a causal-lift claim.

## Validation behavior

`eval/first_10_evidence.py` rejects:

- internal, maintainer, synthetic, or simulated rows;
- duplicate pseudonyms, enrollment slots, participant evidence URIs, or maintainer-validation evidence URIs;
- placeholder/non-HTTPS evidence links;
- secrets in any string field;
- artifact drift or unpinned installs;
- missing verification evidence;
- inconsistent safety-control fields;
- missing outcome evidence;
- forged aggregate counts.

Raw unsuccessful rows remain; only invalid or unsafe-to-publish data is quarantined, with the exclusion reason retained.

## Binary thresholds

- 10 valid unique external users;
- at least 8 successful installs;
- at least 6 verified useful rescues before maintainer help;
- safety-control passes equal all successful installs and number at least 8;
- zero false-confident controls;
- zero harmful guidance events;
- zero critical privacy/security incidents.

Until every condition passes, the machine verdict remains `BLOCKED`.
