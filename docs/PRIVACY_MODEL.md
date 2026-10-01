# Borg Privacy Model

**Rev:** 20260930-1141

Borg is failure memory for AI coding agents. It does not upload raw agent conversations, raw traces, tool outputs, source files, screenshots, or environment variables by default. Any shared failure-memory path is opt-in and accepts only signed, sanitized, revocable learning atoms.

Its epistemic guardrail adds local decision controls for consequential work. It does not request or upload private chain-of-thought.

## Data zones

| Zone | Data | Default | Sharing |
|---|---|---|---|
| Local raw trace | task text, tool metadata, local paths, errors | local-only | never directly shared |
| Local epistemic packet/intervention | bounded task/context, claims, evidence summaries, assumptions, memory references, decision and verification plan | local-only | never direct shared proof |
| Local atom | sanitized lesson distilled from trace | local-only | opt-in export only |
| Org atom | signed sanitized atom scoped to tenant/org | off by default | opt-in |
| Global candidate | signed sanitized atom eligible for quorum | off by default | requires policy + quorum |

## Default mode

`borg.sharing.mode = local_only`

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

## Epistemic-packet minimization

`borg_deliberate` requests decision-relevant artifacts only: task/context, structured material claims, evidence references/summaries, assumptions, verification steps, and an optional draft. It never requests private chain-of-thought. The returned `packet_id` binds a SHA-256 digest of the draft rather than persisting the draft in the packet. Intervention recording passes bounded packet data through the existing privacy redactor; outcome promotion still requires the signed, sanitized learning-atom path.

Retrieved memory is untrusted advisory data. Prompt-injection findings suppress unsafe memory before packet emission, and priming surfaces forbid injecting retrieved text as system/developer instructions.

## Controls

- deterministic structured privacy scanner;
- prompt-injection scanner;
- schema minimization;
- signed envelopes;
- quarantine decisions;
- tombstone revocation;
- retrieval firewall that marks memory as untrusted historical advice.

## User risk posture

Local-only use is the safe default. Sharing is opt-in and must pass policy. Borg should not be marketed as proven external-user lift until real-user evidence passes.
