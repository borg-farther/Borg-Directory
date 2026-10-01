# First-10 Borg Rescue Adversarial Audit

**Verdict:** protocol implementation is structurally ready for release-candidate testing; cohort enrollment remains **CLOSED** until an immutable PyPI artifact is released, its wheel hash is locked, the production fresh-install canary passes, and the rollout gate authorizes enrollment.

## Audit scope

Three independent audit attempts were initiated through Hermes delegation, but none executed because the configured `gpt-5.4` child model is unsupported by the Codex ChatGPT backend. Three replacement Codex CLI reviews also failed before reading the repository because their access token could not refresh. No external-agent findings are claimed.

A manual adversarial review was completed across:

- `eval/first_10_evidence.py`
- `eval/real_user_rollout_gate.py`
- `eval/public_self_serve_launch_gate.py`
- `eval/run_pypi_fresh_install_canary.py`
- `eval/first_10_user_scoreboard.json`
- `borg/cli/doctor.py`
- `borg/core/first_user_readiness.py`
- the invite, intake, issue-form, and protocol surfaces
- readiness, CLI, packaging, and doctor regression tests

## Findings fixed

### 1. Diagnostic self-tests polluted real feedback state

`borg-doctor` exercised `borg_rate` against the operator’s live failure-memory store. The doctor now creates an isolated temporary Borg home and manager, then verifies that its synthetic feedback cannot appear in the real store.

### 2. Subjective usefulness could be counted without proof

A row now counts as a useful rescue only when the exact original failure or smallest regression test passes, redacted verification evidence exists, guidance was relevant, ACTION/STOP/VERIFY was returned, no maintainer helped before first value, and outcome evidence was recorded.

### 3. Failed installs could disappear from the denominator

Failed installs are valid cohort outcomes with explicit `not_reached` states. They remain in the 10-user denominator. Impossible downstream claims on a failed-install row are rejected.

### 4. Safety behavior was not a binary cohort gate

Every successful install must run one frozen unknown-input control. The exact control ID, input, and expected `no_confident_match` status are hard-coded and protocol-validated. One false-confident response, harmful-guidance event, critical privacy/security incident, or secret leak pauses enrollment.

### 5. Artifact drift could contaminate the cohort

The protocol now requires one exact `agent-borg` version and a 64-character PyPI wheel SHA-256. Every row must use a version-pinned install command matching that artifact. Artifact changes require a new protocol.

### 6. More than 10 users could enable outcome cherry-picking

Every participant receives an immutable consecutive `enrollment_index` from 1 through 10 before installation. Duplicate, skipped, reordered, or greater-than-10 slots fail closed. Readiness requires exactly 10 valid rows—not “at least 10.”

### 7. Self-reported rows lacked separate acceptance evidence

Each counted row now requires `maintainer_validation_status: verified` plus a separate HTTPS validation-evidence URI. Pending or rejected rows cannot count. This is a second review layer, not a claim of blinded or third-party independence.

### 8. The rollout gate paused only for privacy/security incidents

Controlled enrollment now also closes on harmful guidance, false-confident control responses, malformed evidence, aggregate drift, an unlocked protocol, exhausted slots, or the preregistered futility condition:

```text
verified_useful_rescues + remaining_slots < 6
```

### 9. The issue form asked users for a URL that did not exist yet

The participant no longer enters `external_user_evidence_uri`. The submitted issue URL becomes that field during maintainer transcription.

### 10. The production canary omitted the actual study controls

The fresh-PyPI canary now checks the installed `borg first-10 --json` protocol and executes the exact unknown control, requiring CLI exit code 1 plus `status: no_confident_match`.

## Methodology assessment

The study can answer only this narrow question:

> Did at least 6 of the first 10 consecutively enrolled external users obtain a relevant, verification-passed and separately maintainer-validated Borg Rescue result before maintainer help, while at least 8 installed successfully and every successful install passed the frozen unknown-input safety control?

It cannot establish causal lift, average population efficacy, model improvement, network effects, or broad public readiness. Time/token values remain optional descriptive measurements with explicit counterfactual labels.

The design deliberately favors false negatives over unsafe promotion: any malformed row, aggregate mismatch, artifact drift, safety event, or protocol mutation blocks the gate.

## Clean-user path assessment

The participant path is now internally coherent:

1. consent, pseudonym, and immutable enrollment slot;
2. exact pinned install;
3. `borg --version` and `borg-doctor --json`;
4. real current error through `borg rescue ... --json`;
5. original command or smallest regression-test verification;
6. exact frozen unknown control;
7. outcome receipt or evidence issue;
8. maintainer validation and row transcription;
9. row-derived scoreboard regeneration.

A local wheel rehearsal verified version reporting, doctor execution, known rescue behavior, frozen unknown-control fail-closed behavior, protocol output, and absence of doctor-generated feedback pollution. This is not production PyPI proof.

## Residual risks and hard blockers

- The changed code is not yet merged or released as a new immutable package version.
- The production PyPI wheel hash is therefore unavailable and cannot be locked honestly.
- Production fresh-install, MCP, and rollout gates must be rerun against the released artifact.
- External-agent audit coverage was unavailable due model/auth failures; this report does not represent independent third-party review.
- The one public frozen unknown-input control is a deterministic regression sentinel, not an estimate of specificity and not evidence against deliberate special-casing.
- Maintainer validation remains a human control. HTTPS evidence syntax and redaction are machine-checked, but semantic truth still requires review.
- There are zero real participant outcomes. Enrollment opening is not success evidence.

## Decision

Do not invite users until the release, hash lock, production canary, and rollout gate are green. After opening, obey the first safety event or futility result without replacing participants or moving thresholds.
