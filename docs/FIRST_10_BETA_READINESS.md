# Borg First-10 Beta Readiness Contract

**Status:** pre-first-user beta contract. This is the standard Borg must satisfy before inviting the first 10 external users.

**Success metric:** at least 6 of the first 10 users get one relevant `ACTION / STOP / VERIFY` moment without maintainer handholding, and every miss is recorded as `NO_CONFIDENT_MATCH` or explicit negative feedback instead of being hidden.

## Non-negotiable product promise

Borg is a cache layer for agent reasoning. It should help an agent avoid a previously discovered dead end or reuse a proven next move. If Borg does not know, it must say so plainly.

That means first-user output must never look smarter than its evidence. A weak match is worse than no match.

## Agent priming paragraph

Put this in `CLAUDE.md`, the agent system prompt, or the first user message:

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and record the outcome with borg_rate(helpful=True/False).
```

## Clean-user smoke path

Run this from a clean environment before handing Borg to a tester:

```bash
python3 -m pip install agent-borg
borg version
borg-doctor --json
borg rescue 'ModuleNotFoundError: No module named flask' --json
borg search 'django migration table already exists'
borg setup-claude --scope user --verify --fix
borg first-10 --json
```

A passing smoke path proves the public package entrypoints exist, the rescue packet is machine-readable, seed search returns useful results, MCP setup has a binary verification path, and the first-10 contract is available to users.

## The seven gates

### G1 — real-vs-synthetic confidence is impossible to miss

Pass criteria:

- Every rescue/observe path exposes confidence and evidence source.
- Synthetic-only guidance is labeled synthetic or inferred, never proven.
- Real trace count is visible before detailed guidance.

Proof:

- `borg rescue '<known error>' --json` includes `evidence.source` and `confidence`.
- `borg_observe` output includes `CONFIDENCE` with `Real traces` and `Synthetic` counts.

### G2 — retrieval fails closed instead of hallucinating relevance

Pass criteria:

- Low-similarity trace hits are filtered before rendering.
- Content-free trace hits cannot become `ACTION` guidance.
- Unrelated pack matches return `NO_CONFIDENT_MATCH`, not random pack advice.

Proof:

- `_trace_match_is_confident()` rejects `similarity < 0.45` and empty causal traces.
- `_pack_match_is_confident()` requires domain/lexical overlap.
- Unknown observe output starts with `ACTION / STOP / VERIFY / CONFIDENCE` and includes `NO_CONFIDENT_MATCH`.

### G3 — day-one packet answers what to do, avoid, and verify

Pass criteria:

- `borg_rescue` returns `ACTION`, `STOP`, `VERIFY`, `human_receipt`, and `automation_policy`.
- `borg_observe` returns `ACTION`, `STOP` or explicit no-match `STOP`, `VERIFY`, and `CONFIDENCE`.
- Agents are instructed not to blend weak retrieval into normal reasoning.

Proof:

- `borg/tests/test_rescue.py`
- `borg/tests/test_first_10_readiness.py`

### G4 — fresh-user install gauntlet is canonical

Pass criteria:

- One clean install command is documented.
- `doctor/version/rescue/search/MCP setup` are the public smoke path.
- MCP configs use absolute `BORG_HOME` paths, not `~`.

Proof:

- README evaluator smoke path.
- This document.

### G5 — claims are truthful for a 10-user beta

Pass criteria:

- Docs describe Borg as a reasoning-cache/rescue-memory beta, not magic lift.
- Unproven network effects and non-Python breadth are listed as limitations.
- Success metric is user-observed `ACTION/STOP` value, not vanity test count.

Proof:

- README “What is proven right now” and “Honest limitations”.
- This document’s first-10 success metric.

### G6 — security and privacy baseline is linked into launch flow

Pass criteria:

- Security baseline exists and is referenced from README/docs index.
- Secret scan, dependency audit, static security scan, and policy check are CI gates.
- First users are told not to paste secrets into shared reports.

Proof:

- `docs/SECURITY_HARDENING_BASELINE.md`
- `scripts/security_gate_check.py`
- `.github/workflows/security-gates.yml`

Tester rule: do not paste API keys, private repo contents, passwords, tokens, cookies, customer data, or private stack traces into public issues. Use sanitized excerpts or private handoff.

### G7 — 10-user beta is instrumented as learning, not theatre

Pass criteria:

- Each tester gets the same install, priming, three tasks, and feedback receipt.
- Outcomes are captured as helpful/not helpful/no match.
- GO/NO-GO after first 10 is binary against the 6/10 useful-moment threshold.

Proof:

- `borg first-10 --json`
- This document.

## Runtime confidence-gate regression note — 2026-05-13

A first-user beta continuation prompt surfaced stale `PACK GUIDANCE (bash-permission-denied)` / generic pack guidance from live Borg paths even though the canonical package already had `NO_CONFIDENT_MATCH` confidence-gate logic.

Permanent rule: unrelated readiness, docs, audit, onboarding, or beta-proof prompts must never receive synthetic permission/git/debug pack advice. They must fail closed as `NO_CONFIDENT_MATCH` or be suppressed before prompt injection.

Patched safety layers:

- canonical Borg MCP confidence gate: `/root/hermes-workspace/borg/borg/integrations/mcp_server.py`
- installed live-runtime candidate: `/usr/local/lib/python3.12/dist-packages/borg/integrations/mcp_server.py`
- older active-candidate runtime: `/home/user/guild-tools/borg/integrations/mcp_server.py`
- older guild-v2 mirror: `/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py`
- Hermes plugin final injection guard: `/root/.hermes/hermes-agent/hermes_cli/plugins/borg_auto_trace/__init__.py`
- duplicate plugin guard: `/root/.hermes/hermes-agent/plugins/borg_auto_trace/__init__.py`

Additional permanent rule added 2026-05-14: strip any embedded/pasted `=== BORG GUIDANCE ===` block before task classification or permission-signal matching. A user quoting stale `PACK GUIDANCE (bash-permission-denied)` must not make the next turn look like a permission-denied task. Long operator prose alone is not observe-worthy; auto-injection requires an explicit technical/action keyword after stripping embedded Borg guidance.

Regression tests:

- `/root/hermes-workspace/borg/borg/tests/test_borg_observe_confidence_gate.py`
- `/root/hermes-workspace/borg/borg/tests/test_first_10_readiness.py`
- `/root/.hermes/hermes-agent/tests/test_borg_auto_trace_guidance_filter.py`

## First-10 tester packet

Send each tester this:

1. Install:
   ```bash
   python3 -m pip install agent-borg
   borg version
   borg-doctor --json
   ```
2. Add the priming paragraph above to their agent.
3. Try three tasks:
   - one real error they are currently debugging;
   - one install/config/deploy issue;
   - one test failure or failing command output piped into `borg rescue --json`.
4. After each task, record:
   - did Borg return `ACTION / STOP / VERIFY`?
   - was it relevant?
   - did it prevent a dead end?
   - did the fix work?
   - if no, what was the exact miss/no-match reason?
5. Record feedback:
   ```bash
   borg feedback-v3 --pack <pack-or-problem-class> --success yes
   # or
   borg feedback-v3 --pack <pack-or-problem-class> --success no
   ```

## GO / NO-GO after 10 users

GO only if:

- at least 6/10 testers record one relevant `ACTION / STOP / VERIFY` moment;
- no P0 install/MCP/security issue remains open;
- unrelated guidance is rare and classified as a bug with a regression test;
- every tester can explain what Borg did in one sentence.

NO-GO if:

- Borg frequently returns unrelated guidance;
- confidence is ambiguous;
- testers need maintainer explanation before the tool is useful;
- the docs overclaim what the product has proven.
