# Borg Privacy Model

**Rev:** 20260503-0846

Borg does not upload raw agent conversations, raw traces, tool outputs, source files, screenshots, or environment variables to shared collective memory. Shared collective memory accepts only signed, sanitized, revocable learning atoms.

## Data zones

| Zone | Data | Default | Sharing |
|---|---|---|---|
| Local raw trace | task text, tool metadata, local paths, errors | local-only | never directly shared |
| Local atom | sanitized lesson distilled from trace | local-only | opt-in export only |
| Org atom | signed sanitized atom scoped to tenant/org | off by default | opt-in |
| Global candidate | signed sanitized atom eligible for quorum | off by default | requires policy + quorum |

## Default mode

`borg.collective.mode = local_only`

Allowed values:

- `local_only` — no atom leaves the machine.
- `org_opt_in` — safe signed atoms may be shared to org memory.
- `global_opt_in` — safe signed atoms may enter global-candidate promotion.

## What shared memory accepts

Shared memory accepts only `LearningAtom` envelopes containing:

- error class / safe pattern;
- technology labels;
- worked approach;
- avoid/dead-end approaches;
- evidence strength;
- privacy/safety metadata;
- signature and lifecycle metadata.

## What shared memory rejects

- raw prompts;
- raw traces;
- full tool outputs;
- source files;
- env vars;
- secrets/tokens;
- private URLs;
- raw local paths in global scope;
- prompt-injection instructions;
- unsigned shared atoms;
- revoked atoms.

## Controls

- deterministic structured privacy scanner;
- prompt-injection scanner;
- schema minimization;
- signed envelopes;
- quarantine decisions;
- tombstone revocation;
- retrieval firewall that marks memory as untrusted historical advice.

## User risk posture

Local-only use is the safe default. Sharing is opt-in and must pass policy. Borg should not be marketed as proven global collective intelligence until the C0/C1/C2 utility eval passes.
