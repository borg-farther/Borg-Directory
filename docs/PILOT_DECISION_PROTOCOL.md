# Pilot Decision Protocol

**Status:** binding for the first local-first pilot. Changes to this protocol
after the pilot starts require a written amendment in the pilot log — never a
silent edit.

This protocol exists so the build/kill decision is made by a **pre-registered
rule on a pre-registered metric**, not by vibes, anecdotes, or the sunk cost
of having built the thing.

---

## 1. Primary metric: `counterfactual_rate`

**Definition.** Of the matched rescues recorded during the pilot, the fraction
where a pinned frontier model — replaying the same redacted failure blind,
with no Borg knowledge — **would NOT have recovered on its own**
(`VERDICT: WOULD_HAVE_BEEN_STUCK`).

That is: the share of Borg's "wins" that are *real* wins, not things any
frontier agent would have solved on the next attempt anyway. Match counts
(`borg status`) measure activity; `counterfactual_rate` measures value.

**Measurement procedure (pinned).**
- Tool: `scripts/counterfactual_replay.py` at the commit tagged for the pilot.
- Model: `MODEL_ID = claude-opus-4-8`, temperature 0.
- Prompts: `PROMPT_VERSION = cfr-1.0`. Any prompt or model change voids
  comparability and requires restarting the measurement window.
- Input: schema-v2 receipts (`replay_context`) from consenting pilot users
  only, exported by the user, replayed offline by the operator with
  `--attest-consent "<who, when>"` recorded in the report.
- Mock mode (`--mock`) is for CI only and is **never evidence**.

**Uncertainty.** Always report the Wilson 95% CI alongside the point estimate.
The decision rule below reads the *interval*, not the point.

## 2. Decision thresholds

| `counterfactual_rate` | Reading | Decision |
|---|---|---|
| **< 5%** | Borg's matches are things a frontier model solves alone — the local loop adds ~nothing on top of the model. | **KILL** the standalone product direction. Salvage: publish the seed corpus + findings. |
| **5% – 20%** | Signal, but not enough receipts or not enough margin to call it. | **EXTEND**: recruit to **N ≈ 30** users, run a second 14-day window, re-apply this same rule once the CI is decisive. One extension maximum. |
| **> 20%** | At least 1 in 5 rescues is value a frontier agent would not have produced alone. | **BUILD**: proceed to the federation-enabled beta per `docs/FEDERATION_DESIGN.md`, gates in PART 10 still applying. |

**Interval rule (conservative).** Call KILL only if the *upper* Wilson bound
is below 5%. Call BUILD only if the *lower* bound is above 20%. Anything else
— including a 0% point estimate at small N — is EXTEND. (`protocol_reading`
in the replay report implements exactly this.)

**Floor for validity.** A decision (other than EXTEND) requires ≥ 25 replayed
receipts across ≥ 5 distinct users. Below that, the answer is EXTEND
regardless of the rate.

## 2a. Diagnose before deciding — separate the signals (anti-false-negative)

The activation/retention success bar (`§3` secondary metrics, and the first-10
readiness bar) is **hit-rate-sensitive**: a user who mostly sees honest
`no_confident_match` never activates, and a user whose client never surfaces the
moment-line never *perceives* a hit — both look identical to "no value" in
activation/retention, even when Borg's mechanism is sound. The default matcher
is lexical (issue #9, `eval/recall_harness.py`: conversational recall ~0.14), so
this is a live risk, not a hypothetical.

**Therefore, before any low activation / retention / `counterfactual_rate` is
read as a value verdict, the operator MUST first read these separable signals
(all on disk, per user, from `borg status` / the receipt export):**

1. **hit-rate / miss-rate** (`value.hit_rate` / `value.miss_rate`). If hit-rate
   is low (Borg fired but mostly missed), low activation is a **recall**
   artifact, not a value verdict.
2. **per-client fires** (`value.fires_by_client` / `value.matched_by_client`).
   If a client (e.g. `cursor`) shows fires but the user reports not seeing the
   `🛟 Borg:` line, that is a **per-client visibility** artifact, not a value
   verdict. Reproduce what a given client receives with
   `python scripts/capture_client_visibility.py --client Cursor` (it shows
   whether the moment-line is in the model-visible tool result vs. only in
   `structuredContent`).

**Decision adjustment (binding):**

| Diagnosis | What it means | Decision |
|---|---|---|
| hit-rate low (e.g. < ~0.3 across users) | recall gap (issue #9) starved the funnel; activation reflects the matcher, not the product | **EXTEND** with a recall-remediation note — **never KILL** on this window |
| per-client fires present but user didn't perceive firing | relay/visibility gap on that client, not a value gap | **EXTEND** with a visibility-remediation note; fix the relay or the DAY1 note for that client |
| hit-rate adequate **and** moment-line demonstrably surfaced per client **and** `counterfactual_rate` interval is decisive | the signal is real | apply the `§2` rule (KILL / BUILD / EXTEND) |

A KILL is only valid when low value persists **with** an adequate hit-rate and
**with** confirmed per-client firing visibility. Killing on a starved funnel is
the exact false negative this protocol exists to prevent.

## 3. Pilot design

- **N = 10 users** (recruit spec below), each on their own machine, local-only
  mode (sharing defaults OFF; federation stays dark).
- **Duration: 14 days** of normal daily work — no synthetic tasks, no asking
  users to manufacture failures.
- **Day 0:** onboarding per `DAY1_USER_KIT.md` (install ≤ 10 minutes,
  `borg status` proof that receipts are flowing).
- **Days 1–14:** receipts accumulate locally. Operator does **not** look at
  any user's receipts mid-pilot (no peeking, no mid-course corrections to the
  matcher, no prompt edits).
- **Day 15: decide.** Users who consent export receipts; operator runs the
  pinned replay; the interval rule above produces KILL / EXTEND / BUILD.
  The decision and the full report are written to the pilot log the same day.

**Diagnostic gates** (read FIRST, per `§2a` — these can turn a would-be KILL into
EXTEND): `value.hit_rate` / `value.miss_rate`, and `value.fires_by_client` /
`value.matched_by_client` (per-client firing visibility).

**Secondary metrics** (reported, never deciding): `caught_after_stuck` count,
matched-by-coverage-class breadth, time-to-value at install, and per-user
"would you keep it installed?" (yes/no, day 14).

## 4. Recruit spec

Ten developers who ALL meet:
- **Stack:** Python — Django and/or Docker in their daily work (this is where
  the seed corpus is deepest; piloting off-corpus would measure the wrong thing).
- **Agent usage:** use **Claude Code or Cursor daily** as a primary workflow
  (the rescue/suggest loop fires through agent integrations; occasional users
  generate too few receipts in 14 days).
- **Consent:** signs the replay consent (local receipts, redacted, exported by
  them, replayed offline, deletable on request) **before** day 0.
- Not affiliated with the project (no maintainers, no friends-of testing
  politely).

## 5. Integrity rules

1. Thresholds, model, and prompts are frozen at pilot start (this document +
   the tagged commit). Amendments are logged, dated, and apply only to the
   *next* window.
2. Mock-mode output is never quoted as evidence anywhere.
3. A user's receipts enter the replay only with their consent attestation;
   "no consent" receipts count toward activity metrics only.
4. The replay report (JSON, including per-receipt verdicts and the consent
   attestations) is archived with the pilot log — the decision must be
   reproducible from it.
5. If the pilot produces fewer than 25 replayable receipts total, that is
   itself a finding (the trigger wiring or the corpus is too thin) and the
   decision is EXTEND with a remediation note — not BUILD on anecdotes.
