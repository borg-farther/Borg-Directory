# Borg first-10 user invite packet

Generated: 2026-05-14T18:25:05Z
Rev: 2026-06-03T19:10:00Z — controlled first-10 beta install path uses the published/canaried PyPI package `agent-borg==3.3.19`, but this packet is **not sendable right now**. Send only after the latest public gate confirms served-runtime freshness and first-10 evidence intake readiness; package/local runtime canaries are already green.

## Exact invite message

Hi — we are preparing a small consented Borg beta for the first 10 external users after served-runtime freshness and evidence-intake gates pass. Borg is an error/debugging assistant that returns ACTION / STOP / VERIFY guidance from local/public project traces. Would you be willing to try one install and one real debugging query when the gate opens, then send redacted feedback? Please do not paste secrets, tokens, proprietary code, private customer data, or confidential logs.

## Install commands

STOP gate: these commands are for the controlled first-10 beta only. Do **not** send them while the current cap is 0. Do **not** send them if served-runtime freshness fails, if `python eval/run_pypi_fresh_install_canary.py --version 3.3.19` regresses, or if more than 10 real external users would be invited before the first-10 evidence gate passes.

Preferred isolated install:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
pipx install agent-borg==3.3.19
borg --version
borg rescue "paste a REDACTED real error here"
```

Fallback if pipx is unavailable:

```bash
python -m venv /tmp/borg-beta-venv
/tmp/borg-beta-venv/bin/python -m pip install agent-borg==3.3.19
/tmp/borg-beta-venv/bin/borg --version
/tmp/borg-beta-venv/bin/borg rescue "paste a REDACTED real error here"
```

Source-branch install is only for maintainer-approved pre-release testing, not the default first-10 path.

## Consent and privacy warning

By participating, the user consents to have redacted outcome metadata recorded for launch readiness. Do not collect raw secrets, credentials, private keys, customer data, or unreduced proprietary logs. Store only pseudonymous user id, install outcome, redacted error category, whether advice was useful, and whether any privacy/security incident occurred.

## Feedback fields to collect

- user_id_pseudonym
- external_user_evidence_uri
- consent_confirmed
- install_method
- install_success
- time_to_first_rescue_minutes
- rescue_input_redacted
- rescue_returned_action_stop_verify
- rescue_useful
- mcp_setup_attempted
- mcp_setup_success
- no_confident_match_when_unknown
- blocker_category
- blocker_notes_redacted
- privacy_security_incident
- repeat_use_within_7_days
- outcome_recorded

## Scoreboard update instructions

Update `eval/first_10_user_scoreboard.json` only after a real external user provides consent and hard evidence. Keep `truth_policy.verified_external_users=0` until evidence exists. Never add fake rows. Public self-serve remains blocked until 10 real external users are verified with at least 8 install successes, at least 6 useful rescue moments, and 0 critical privacy/security failures.
