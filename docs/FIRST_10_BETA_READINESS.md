# Borg First-10 Beta Readiness Contract

**Status:** controlled first-10 public-package beta is **NO-GO right now / cap 0**. GitHub source exact-commit install is **GO** for source commit `4d829c50b82179bd0afca6f0f7cc03bb79fa983f` with CLI, Python API, rescue/doctor, and local stdio MCP canaries green. PyPI `agent-borg==3.3.18` remains the published metadata-correct package, but current-source PyPI/package proof is NO-GO until a new immutable package release includes the bundled-pack clean-install fix and the PyPI fresh-install/OpenClaw canary is green. Invite **0** controlled testers until source/package/release/ops/docs gates are green and evidence intake captures consented external-user rows. Public self-serve stays NO-GO until row-derived first-10 external evidence passes.

**Success metric:** At least 6 of the first 10 users get one relevant ACTION/STOP/VERIFY moment without maintainer handholding, and every miss is recorded as NO_CONFIDENT_MATCH or explicit negative feedback instead of being hidden.

## Product promise

Borg is a cache layer for agent reasoning. It should help an agent avoid a previously discovered dead end or reuse a proven next move. If Borg does not know, it must say so plainly.

A weak match is worse than no match.

## Agent priming paragraph

Put this in `CLAUDE.md`, the agent system prompt, or the first user message:

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. For a concrete failure in MCP, call error_lookup(input="<exact error or failing command output>"); it is the plain-English alias for borg_rescue(input="<exact error or failing command output>") and returns the same ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue "<exact error>". Use borg_observe(task="<exact task or error>", context="<tech stack>") for broader task-start guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and verify with the exact failing command or smallest regression test. After the outcome, record it with borg_record_outcome when Borg returned an intervention_id, borg_feedback if you used a pack session, or borg_record_failure if you are recording a concrete error-pattern success/failure.
```

## Clean-user smoke path

Run this before handing Borg to a tester, after the current release version is published and proof dashboards are green:

Install package `agent-borg`; it provides `borg`, `borg-mcp`, and `borg-doctor`. Do **not** use `pip install borg`, `brew install borgbackup`, `apt install borgbackup`, `apt-get install borgbackup`, `dnf install borgbackup`, or `pacman -S borg`; those are unrelated.

```bash
python3 -m pip install agent-borg
borg version
borg-doctor --json
borg rescue 'ModuleNotFoundError: No module named flask' --json
borg search 'django migration table already exists'
borg setup-claude --scope user --verify --fix
borg first-10 --json
borg collective summary --json
```

After `borg setup-claude --scope user --verify --fix`, fully restart Claude Code and verify Claude lists Borg tools such as `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_search`.

MCP first call for a concrete failure:

```text
error_lookup(input="ModuleNotFoundError: No module named flask", show_guidance=False)
# same rescue contract as:
borg_rescue(input="ModuleNotFoundError: No module named flask", show_guidance=False)
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

- `error_lookup` and `borg_rescue` return the same `ACTION`, `STOP`, `VERIFY`, `human_receipt`, `automation_policy`, and no-hype `value_receipt`.
- `borg_observe` returns `ACTION`, `STOP`, `VERIFY`, and `CONFIDENCE`, or an explicit no-match packet.
- Agents are instructed not to blend weak retrieval into normal reasoning.

Proof:

- `tests/core/test_rescue.py`
- `tests/readiness/test_first_10_readiness.py`

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
- Outcomes are captured as helpful/not helpful/no match plus optional before/after minutes or tokens.
- Borg interventions with `intervention_id` are closed with signed `borg_record_outcome` receipts and visible through `borg collective summary --json`.
- Measured savings are row-derived only: consented external-user rows in `eval/first_10_user_scoreboard.json` must supply before/after fields before dashboards may show minutes or tokens saved.
- Rescue packets never claim savings at call time; they expose a `value_receipt` saying measurement is pending until outcome rows exist.
- GO/NO-GO after first 10 is binary against the useful-moment threshold.

Proof:

- `borg first-10 --json`
- `borg collective summary --json`
- This document.

## First-10 tester packet

Send each tester this:

1. Install:
   
   Package name is `agent-borg`; command after install is `borg`. Do **not** install `borg` or `borgbackup`.
   
   ```bash
   python3 -m pip install agent-borg
   borg version
   borg-doctor --json
   ```
2. Add the priming paragraph above to their agent. For a concrete MCP failure, the first call is `error_lookup(input="<exact error>")`; if the host only shows canonical Borg names, use `borg_rescue(input="<exact error>")`.
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
   - intervention_id, outcome_receipt_id, and contribution_event_id when Borg returned an intervention.
   - optional measured value fields: baseline minutes without Borg, actual minutes with Borg, net minutes saved, baseline tokens without Borg, actual tokens with Borg, net tokens saved, savings counterfactual basis, dead-end avoided confirmed, and user-confirmed value.
5. Record feedback:
   - If MCP returned an `intervention_id`, close it with signed outcome evidence:
     ```text
     borg_record_outcome(
       intervention_id="<intervention_id>",
       outcome="success|failure|partial",
       helpful=true|false,
       verified=true,
       verification_command="<command or check that proves the outcome>"
     )
     ```
   - If this was a pack-session/CLI-only run with no intervention id, use legacy pack feedback only after VERIFY, and set the outcome truthfully:
     ```bash
     borg feedback-v3 --pack <pack-or-problem-class> --success no
     # set --success to yes only after the verification command/check proves the fix worked
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
