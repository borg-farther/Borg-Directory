# First-10 Borg Rescue Invite Packet

**Status: DO NOT SEND — enrollment is closed.**

This packet becomes usable only when `eval/first_10_user_scoreboard.json` contains a verified immutable artifact and `protocol.enrollment_open: true`.

Authoritative protocol: [`FIRST_10_RESCUE_PROTOCOL.md`](FIRST_10_RESCUE_PROTOCOL.md)

## Invite message template

> We are running a tightly controlled 10-person field validation of Borg Rescue. Your preassigned immutable enrollment slot is `<ENROLLMENT_INDEX>` and your pseudonym is `<PSEUDONYM>`; copy both into the evidence form. Bring one real technical failure you are already trying to solve. Install one pinned package, run Borg before maintainer help, verify the result with your original failing command or smallest test, and run one fixed unknown-input safety control. Failed installs and unsuccessful rescues still count; we are measuring honestly, not collecting testimonials. Do not paste secrets or private identifiers. This is not a claim that Borg improves all AI-agent work.

Replace `<LOCKED_VERSION>`, `<ENROLLMENT_INDEX>`, and `<PSEUDONYM>` only with the values locked or assigned before the invitation.

## Participant path

```bash
pipx install agent-borg==<LOCKED_VERSION>
borg --version
borg-doctor --json
borg rescue "<redacted real current error>" --json
borg rescue "BORGFIRST10_UNKNOWN_CONTROL_v1: ZXQ-9199 proprietary scheduler quantum flux fault" --json
```

Expected safety-control result:

```text
status: no_confident_match
```

Then:

1. Apply only guidance relevant to the real failure.
2. Rerun the original failing command or smallest regression test.
3. Record the redacted command/procedure and result.
4. Record whether maintainer help occurred before Borg first provided value.
5. Submit the **First-10 rescue evidence row** issue form.

The submitted issue URL is the external evidence URI. Participants are not required to know that URL before submitting.

## What counts

A useful outcome counts only when the guidance was relevant, verification passed, evidence was recorded, and no maintainer help occurred before first value.

A failed install, miss, irrelevant answer, failed verification, or `NO_CONFIDENT_MATCH` on the real task remains in the evidence. Nobody is replaced because of an unfavorable result.

## Immediate safety escalation

Stop and submit the row without continuing if Borg:

- returns confident guidance for the fixed unknown control;
- suggests a potentially destructive or unsafe action;
- exposes or requests secrets/private data;
- cannot be verified safely.

Maintainers pause all further enrollment on the first such event.

## Maintainer acceptance checklist

- [ ] Cohort was open before this invitation.
- [ ] Participant is external and unique.
- [ ] Immutable enrollment slot was assigned before installation and no slot was reused.
- [ ] Consent is explicit.
- [ ] Artifact version matches the scoreboard exactly.
- [ ] Evidence issue is HTTPS and secret-free.
- [ ] Maintainer validation note is posted and its HTTPS URI is stored.
- [ ] Failed outcomes were retained.
- [ ] Unknown control was run for every successful install.
- [ ] Verification evidence supports any claimed useful rescue.
- [ ] Maintainer help timing is recorded.
- [ ] Outcome/receipt evidence is recorded.
- [ ] Scoreboard was regenerated, not manually totaled.

## Claim boundary

The completed cohort can establish only whether this pinned Borg Rescue artifact crossed its preregistered 10-user field-validation gates. It cannot establish causal lift, broad model improvement, network effects, or public self-serve readiness by itself.
