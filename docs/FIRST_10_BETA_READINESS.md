# Borg First-10 Beta Readiness Contract

**Status:** ready for controlled first-10 beta sharing. Public self-serve launch is still gated by real external-user evidence.

**Success metric:** At least 6 of the first 10 users get one relevant ACTION/STOP/VERIFY moment without maintainer handholding, and every miss is recorded as NO_CONFIDENT_MATCH or explicit negative feedback instead of being hidden.

## Product promise

Borg is a cache layer for agent reasoning. It should help an agent avoid a previously discovered dead end or reuse a proven next move. If Borg does not know, it must say so plainly.

A weak match is worse than no match.

## Agent priming paragraph

Put this in `CLAUDE.md`, the agent system prompt, or the first user message:

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and record the outcome with borg_rate(helpful=True/False).
```

## Clean-user smoke path

Run this before handing Borg to a tester:

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

## Supported first-user mixes

- Human only: CLI or Python API, no MCP required.
- Human chat UI plus agent host: Telegram/Discord/Slack/API sessions through Hermes, with Borg configured once in Hermes.
- MCP-native coding agents: Claude Code, Cursor, Cline, Continue, Goose, Codex-style CLIs, or custom runners with `borg-mcp` configured.
- Any model provider behind the host: ChatGPT/OpenAI, Claude, OpenRouter, local models, or other OpenAI-compatible endpoints.
- Chat app with no MCP/tool execution: run `borg rescue` / `borg search` outside the chat and paste the `ACTION / STOP / VERIFY` packet back, or route through an MCP-capable host.

For every mix, the invariant is the same: install Borg on the machine that executes tools, prime the agent/human to call Borg before technical fixes, and record helpful/not-helpful/no-match outcomes.

## The seven gates

### G1 — real-vs-synthetic confidence is visible

Pass criteria:

- Every rescue/observe path exposes confidence and evidence source.
- Synthetic-only guidance is labeled synthetic or inferred, never proven.
- Real trace count is visible before detailed guidance.

Proof:

- `borg rescue '<known error>' --json` includes evidence and confidence.
- `borg_observe` output includes `CONFIDENCE` with real/synthetic counts when available.

### G2 — retrieval fails closed

Pass criteria:

- Low-similarity hits are filtered before rendering.
- Content-free hits cannot become `ACTION` guidance.
- Unrelated matches return `NO_CONFIDENT_MATCH`, not random advice.

Proof:

- Confidence-gate tests reject weak, empty, or unrelated matches.

### G3 — day-one packet answers what to do, avoid, and verify

Pass criteria:

- `borg_rescue` returns `ACTION`, `STOP`, `VERIFY`, `human_receipt`, and `automation_policy`.
- `borg_observe` returns `ACTION`, `STOP`, `VERIFY`, and `CONFIDENCE`, or an explicit no-match packet.
- Agents are instructed not to blend weak retrieval into normal reasoning.

Proof:

- `borg/tests/test_rescue.py`
- `borg/tests/test_first_10_readiness.py`

### G4 — fresh-user install path is canonical

Pass criteria:

- One clean install command is documented.
- `doctor/version/rescue/search/MCP setup` are the public smoke path.
- MCP configs use absolute `BORG_HOME` paths, not `~`.

Proof:

- Root README evaluator smoke path.
- This document.

### G5 — claims are truthful for beta

Pass criteria:

- Docs describe Borg as a reasoning-cache/rescue-memory beta, not magic lift.
- Unproven network effects and broad non-Python coverage are listed as limitations.
- Success metric is user-observed `ACTION/STOP/VERIFY` value, not vanity test count.

Proof:

- README readiness/limitations section.
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

## G7 — 10-user beta is measured, not theatre

Pass criteria:

- Each tester gets the same install, priming, tasks, and feedback receipt.
- Outcomes are captured as helpful/not helpful/no match.
- GO/NO-GO after first 10 is binary against the useful-moment threshold.

Proof:

- `borg first-10 --json`
- This document.

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
