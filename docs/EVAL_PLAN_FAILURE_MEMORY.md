# Borg Failure Memory Evaluation Plan

**Rev:** 20260503-0846

## Hypothesis

Seeded Borg learning atoms improve agent outcomes compared with an empty Borg scaffold.

## Conditions

- C0: no Borg tools or memory.
- C1: Borg tools present, empty atom store.
- C2: Borg tools present, seeded atom store.

Primary product contrast:

```text
C2 - C1 = pure knowledge value
```

## Metrics

- solve rate;
- tool calls;
- tokens;
- time to solution;
- negative transfer;
- top-3 retrieval precision;
- user/helpfulness feedback.

## Minimum early gate

Go only if:

- C2 beats C1 by >=15pp solve rate; or
- C2 reduces tool calls by >=25% on tasks solved by both;
- zero critical negative-transfer cases.

## Design requirements

- held-out tasks;
- no post-hoc task inclusion;
- model/version logged;
- repeated runs;
- confidence intervals;
- negative-transfer report;
- compare C2 to C1, not only C2 to C0.

## Sample size

- directional run: >=30 tasks;
- release claim: >=50 tasks with paired analysis where possible.

## Reporting

Report all outcomes, including null/floor effects. Do not claim agent-level utility until this eval passes.
