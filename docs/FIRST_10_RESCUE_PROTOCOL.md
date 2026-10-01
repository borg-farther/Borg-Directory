# Borg Rescue First-10 Protocol

**Protocol ID:** `borg-rescue-first10-v1`
**Current state:** **PREREGISTERED — ENROLLMENT CLOSED**
**Authoritative machine state:** `eval/first_10_user_scoreboard.json`

This is a prospective field-validation study of one narrow proposition:

> For a real technical failure, the pinned Borg Rescue artifact can return relevant `ACTION` / `STOP` / `VERIFY` guidance that the user verifies successfully before maintainer help.

It is **not** an experiment proving generic AI-agent lift, population efficacy, network effects, or public self-serve readiness. The protocol makes **no causal lift** claim.

## Frozen artifact

Before the first invitation, the scoreboard must contain:

- exact `agent-borg==X.Y.Z` version;
- SHA-256 of the PyPI wheel tested by the clean-user canary;
- `protocol.status: enrollment_open`;
- `protocol.enrollment_open: true`.

Lifecycle is fail-closed: `enrollment_open` requires zero rows; after the first retained attempt set `status: in_progress`; after the tenth retained attempt set `status: complete` and `enrollment_open: false`. `complete` means data collection ended—it does not mean the outcome gates passed.

Every row must use that exact version. Artifact changes after the first participant invalidate continuation; start a new protocol instead.

## Participants

- Exactly 10 unique external users, assigned immutable `enrollment_index` slots 1–10 consecutively before each attempt.
- One primary real, current technical failure per user.
- Internal, maintainer, synthetic, simulated, or replacement users do not count.
- Failed installs and unsuccessful rescues remain in the denominator.
- A participant is never replaced because their outcome is inconvenient.

## Procedure

1. Confirm consent; assign a pseudonym and the next immutable enrollment index before installation.
2. Confirm the user already has a real current technical failure.
3. Install the exact locked artifact:

   ```bash
   pipx install agent-borg==X.Y.Z
   ```

4. Record install success and elapsed minutes. If installation fails, record the failure and stop; the row still counts toward the 10-user denominator.
5. Before maintainer debugging help, run:

   ```bash
   borg rescue "<redacted real current error>" --json
   ```

6. Follow relevant guidance only. Run the original failing command or smallest regression test and record the redacted result.
7. Run the frozen negative control exactly:

   ```bash
   borg rescue "BORGFIRST10_UNKNOWN_CONTROL_v1: ZXQ-9199 proprietary scheduler quantum flux fault" --json
   ```

   Expected result: `status: no_confident_match`. Confident guidance is a false-confident match and immediately pauses enrollment.
8. Record the outcome with `borg_record_outcome`, `borg feedback-v3`, or the evidence issue. Preserve the redacted receipt/intervention identifier when one exists.
9. Submit `.github/ISSUE_TEMPLATE/first-10-evidence.yml`. The submitted issue URL becomes `external_user_evidence_uri`; users are not asked to know their issue URL before submission.
10. A maintainer posts a redacted validation note, records its HTTPS URI, and transcribes the row without altering the reported result. A row does not count while validation is pending or rejected.

## Primary outcome

A **verified useful rescue** requires all of the following:

- exact locked artifact installed successfully;
- real current failure, not a supplied synthetic task;
- Borg returned `ACTION` / `STOP` / `VERIFY`;
- guidance was relevant;
- user reported it useful;
- original failure or regression test passed;
- verification evidence is present and redacted;
- no maintainer help occurred before first value;
- outcome evidence was recorded;
- no false-confident control response;
- no harmful guidance.

A subjective “looked useful” response without successful verification does not count.

## Binary completion gates

All must pass:

| Gate | Threshold |
|---|---:|
| Valid unique external-user rows | 10/10 |
| Successful installs | at least 8/10 |
| Verified useful rescues | at least 6/10 |
| Unknown-control safety passes | at least 8 and equal to successful installs |
| False-confident unknown-control matches | 0 |
| Harmful guidance events | 0 |
| Critical privacy/security incidents | 0 |

## Immediate pause and stop rules

Pause enrollment on the first:

- harmful guidance event;
- critical privacy/security incident;
- false-confident unknown-control response;
- evidence containing an unredacted secret.

Do not resume until the defect is fixed in a new immutable artifact and the protocol impact is documented. Do not silently mix artifacts.

Stop for mathematical futility when:

```text
verified_useful_rescues + remaining_slots < 6
```

At closure:

- **PASS:** every binary gate passes.
- **NO-GO:** any gate fails, a safety pause is unresolved, or futility is reached.

## Evidence integrity

The evaluator derives counts from row-level evidence. Editable aggregate counters never establish readiness. It rejects:

- duplicate pseudonyms or reused participant/maintainer evidence URIs;
- duplicate, skipped, reordered, or greater-than-10 enrollment slots;
- placeholder or non-HTTPS evidence URIs;
- missing maintainer validation or validation evidence URI;
- unpinned or mismatched artifact versions;
- missing verification evidence;
- useful claims made after maintainer help;
- inconsistent unknown-control fields;
- missing outcome evidence;
- secrets in any string field;
- forged aggregate totals.

Measured time/token savings are optional and require an explicit counterfactual basis. They are descriptive only and do not become a causal-lift claim.

## Commands

Validate without changing the scoreboard:

```bash
python eval/first_10_evidence.py --check
```

Synchronize aggregates after a maintainer adds a validated row:

```bash
python eval/first_10_evidence.py --write
```

Inspect the user-visible contract:

```bash
borg first-10 --json
```
