# 20260408 GEPA-on-Borg-classifier spike report

**Date:** 20260408
**Author:** Hermes subagent (GEPA spike)
**Status:** Complete — honest-negative result
**Related:** `../SKEPTIC_REVIEW.md`, `../HERMES_FORGE_INTEGRATION_PLAN.md`, `../SYNTHESIS_AND_ACTION_PLAN.md` (§Phase 3)

---

## 1. Summary

We ran a time-boxed spike to test the naive hypothesis:

> **H0:** Point GEPA (Genetic-Evolutionary Prompt Adaptation) at the Borg
> classifier's hand-authored keyword table, give it the 173-row labelled
> error corpus, and the False-Confident Rate (FCR) will drop below
> Phase 0's v3.2.2 baseline of 4.6%.

**Result: H0 is not supported by this spike.** After 31 GEPA iterations
against `gemini-2.0-flash` with a custom `BorgKeywordTableAdapter`, FCR
moved from 4.62% → 4.62%. Zero mutations were accepted. Precision, recall,
and exact-correct rate were all unchanged. The classifier binary rule
table at the end of the run is byte-identical to the seed.

The spike is valuable anyway: it disproved the cheap hypothesis, produced
a reusable ~600-LOC adapter, and identified three concrete, fixable
blockers that would need to be cleared before a second attempt is worth
the engineer-day.

**Bottom line verdict:** GEPA on the Borg classifier is *plausible but
NOT a drop-in win*. The three blockers below are fixable in roughly one
engineer-day plus <$5 of LLM spend. The spike disproves the naive
hypothesis "point GEPA at Borg and FCR drops."

---

## 2. Infrastructure built

Everything lives under
`docs/20260408-0623_classifier_prd/gepa_spike/` and in a throwaway venv
at `/tmp/gepa-spike-venv`.

| Component | Location | Notes |
|-----------|----------|-------|
| venv | `/tmp/gepa-spike-venv` | Python 3.11, `gepa==0.0.26`, `dspy-ai==3.1.3`, `litellm` (transitively) |
| Driver script | `borg_gepa_evolve.py` (~600 LOC) | Self-contained reproducer |
| Custom adapter | `BorgKeywordTableAdapter(GEPAAdapter)` inside the driver | Treats the keyword TAB-table as the single evolvable candidate text |
| Reflective dataset | Built in-memory from `error_corpus.jsonl` | Each row tagged `CORRECT` / `FALSE-CONFIDENT` / `HONEST-MISS` with the expected class and the observed classifier output for GEPA's reflection prompt |
| LLM cascade | Anthropic → OpenAI → Gemini → `MockReflectionLM` | First usable key wins; spike ran on `gemini-2.0-flash` |
| Budget guards | `max_metric_calls=800`, hard cost cap $5 | Script exits cleanly on either |
| Seed candidate | v3.2.2 keyword table verbatim (39 rules) | Matches the shipped classifier |
| Artifacts | `results.json`, `gepa_run/` | GEPA state + per-task best outputs, safe to commit |

The `BorgKeywordTableAdapter.evaluate()` method:

1. Parses the candidate string as a TAB-separated keyword table.
2. Runs every corpus row through a pure-Python re-implementation of
   `borg.core.pack_taxonomy.classify_error` using the parsed table.
3. Aggregates per-row feedback with FCR-weighted loss (confident-wrong
   rows penalised ~10× vs honest misses).
4. Emits a reflective trace per row so GEPA's reflection LM can see
   *why* a row was tagged correct/false-confident/honest-miss.

This adapter is the only piece of code in the repo today that knows how
to score a candidate *from text*; if we ever revisit GEPA it is the
reusable kernel.

---

## 3. Run details (the actual numbers)

```
label                      = gemini_2_flash
is_mock                    = False
elapsed_seconds            = 182.3
max_metric_calls           = 800
reflection_minibatch_size  = 8
iterations_completed       = 31
accepted_mutations         = 0
actual_spend               = < $0.05   (gemini-2.0-flash is cheap)
gepa_error                 = null
```

History tail from `results.json`:

```
iter 0 val_aggregate = 0.5173
iter 1 val_aggregate = 0.5000   ← first proposed candidate was WORSE
                                  (parser saw 0 valid rules), never
                                  revisited by any later iteration
```

All 31 subsequent iterations re-proposed variations on "You are a Borg
classifier…" English-prose system prompts, all of which the parser
rejected as containing 0 valid TAB-delimited rules, all of which scored
worse than parent, all of which were rejected by the acceptance
criterion.

---

## 4. Measured results (before vs after)

From `results.json`:

| Metric               | BEFORE (seed v3.2.2) | AFTER (31 GEPA iters) | Δ |
|---------------------:|:--------------------:|:---------------------:|:-:|
| n_total              | 173                  | 173                   | 0 |
| n_correct            | 14                   | 14                    | 0 |
| n_false_confident    | 8                    | 8                     | 0 |
| n_correct_no_match   | 151                  | 151                   | 0 |
| n_fired              | 22                   | 22                    | 0 |
| **FCR**              | **4.62%**            | **4.62%**             | **0.00pp** |
| Precision            | 63.6%                | 63.6%                 | 0.0pp |
| Recall               | 8.1%                 | 8.1%                  | 0.0pp |
| Exact-correct rate   | 8.1%                 | 8.1%                  | 0.0pp |
| n_rules in table     | 39                   | 39                    | 0 |

Zero movement on any axis. The `best_candidate_table` emitted by GEPA at
the end of the run is byte-identical to `seed_candidate_table`.

---

## 5. Blockers, in priority order

### Blocker 1 (primary): GEPA's default proposer rewrites candidates as English prose

GEPA's default `propose_new_texts` callback treats the candidate string
as a *system prompt* and hands it to the reflection LM with an instruction
along the lines of "improve this system prompt given these reflective
examples." The reflection LM (gemini-2.0-flash in our run) obligingly
produced paragraphs like:

> *"You are a Borg classifier. Your job is to map Python error messages
> to problem classes. Be careful about false positives on Rust/Go/JS
> locking errors…"*

…which is a perfectly sensible English prompt. It is not a
TAB-separated keyword table. Our parser saw 0 valid `<keyword>\t<class>`
lines, every metric collapsed to baseline-no-match (val_aggregate=0.5),
the acceptance criterion rejected it, and GEPA moved on — only to
propose another prose paragraph on the next iteration.

**Fix:** Supply a custom `propose_new_texts` callback (~80 LOC) that
instructs the reflection LM with an explicit format contract: "Here is a
TAB-separated keyword table. Propose edits as a patch: ADD `<kw>\t<cls>`,
REMOVE `<kw>`, or CHANGE `<kw>` to `<new_cls>`. Return the full table,
not prose." This is the single biggest lever and should be attempted
first on any GEPA-v2 spike.

### Blocker 2 (secondary): Phase 0 already harvested the easy wins

The v3.2.2 seed is not 2025-January-Borg; it is post-Phase-0. Corpus FCR
already fell from 53.8% → 4.6% via *hand-authored* deletion of bad
rules and addition of the non-Python language guard. Only **8 of 173
rows** remain false-confident, and inspection shows **most of those 8
require DELETION of an existing rule without losing recall on a
sibling row** — a surgical subtractive edit.

GEPA's reflective mutation is empirically much better at
**additive expansion** ("I see you missed this kind of error; here is a
new rule to catch it") than at **subtractive pruning** ("this rule is
firing on a sibling; delete it and accept the recall loss, because the
recall was noise anyway"). The reflection prompt structure nudges
strongly toward "add a keyword," and even a correctly-formatted proposer
would fight the grain of the task.

**Fix:** Either (a) reframe the reflective dataset so DELETE is a
first-class proposed action, or (b) redirect GEPA to Phase 1+ where the
problem is *coverage* not *precision* — i.e. only revisit once we have a
real generative coverage problem, not a subtractive one.

### Blocker 3 (tertiary): Acceptance criterion too strict on tiny minibatches

We ran with `reflection_minibatch_size=8`. The base rate of
false-confident rows is 8/173 ≈ 4.6%, so the expected number of
false-confident rows in a random 8-row minibatch is **0.37**. In practice
most minibatches contained 0 false-confident rows, which means the parent
and any proposed candidate scored identically on that minibatch (both
classify the easy rows the same way). GEPA's default acceptance criterion
requires *strict improvement*, and ties are rejected.

Combined with blocker 1, this meant that even the (rare) minibatch where
the proposed candidate might have been structurally valid would have been
rejected on a tie.

**Fix:** Set `acceptance_criterion='improvement_or_equal'` and raise
`reflection_minibatch_size=24` so each minibatch contains a statistically
meaningful number of false-confident rows (expected ~1.1). This is a
one-line config change with no extra cost.

---

## 6. Honest verdict

> **GEPA on the Borg classifier is plausible but NOT a drop-in win.
> Blockers are fixable in ~1 engineer-day + <$5 LLM spend. The spike
> disproves the naive hypothesis: "point GEPA at Borg and FCR drops."**

We learned three concrete, cheap-to-test things (blockers 1/2/3), we
produced a reusable adapter, and we spent under $0.05 doing it. That is
a successful spike in the Popperian sense: an operational falsification
of a cheap hypothesis at the cost of a few hundred LLM calls and two
engineer-hours.

What we did **not** learn is anything about whether a *correctly-configured*
GEPA run could beat hand-authored rules. The spike was stopped at the
"default config doesn't work" stage before we started spending engineer
time on the custom proposer. That is the right stopping point given the
Skeptic gate's recommendation to defer Phase 1-4 entirely.

---

## 7. Recommended next step

**NOT RECOMMENDED (for now).**

Rationale:

1. **v3.2.3 (hand-written `anti_signatures`) is faster and more surgical
   for the residual 8 false-confident rows.** A human engineer can
   inspect 8 rows in ~20 minutes and write 8 anti-signatures. GEPA
   cannot currently do better than that.
2. **Phase 0 was the big win.** 53.8% → 4.6% FCR came from manual rule
   hygiene, not from search. The remaining 4.6% is in the long-tail
   regime where GEPA's advantages (exploring a large prompt space)
   don't apply.
3. **The Skeptic gate already recommends deferring Phases 1-4**
   (see `../SKEPTIC_REVIEW.md` Appendix B). Spending a day fixing the
   GEPA blockers would contradict that recommendation.

**Revisit GEPA if and only if** pack schema migration happens
*and* there is a *generative coverage* problem (e.g. "the new pack schema
introduces 40 new problem classes and we need to seed rules for them
from a labelled corpus"). That is an *additive* task, which plays to
GEPA's strengths, and would warrant clearing blocker 1 (custom proposer)
as the first step of that future spike.

Until then: shelve, do not delete. The reproducer is cheap to re-run.

---

## 8. Files created

All paths relative to `docs/20260408-0623_classifier_prd/gepa_spike/`:

| File / dir | Purpose |
|------------|---------|
| `borg_gepa_evolve.py` | Self-contained reproducer (~613 LOC). Creates adapter, builds reflective dataset, runs GEPA, writes `results.json`. |
| `results.json` | Full before/after metrics, history, gepa_error, seed and best candidate tables. The canonical artifact of this spike. |
| `gepa_run/` | GEPA's own state directory (`gepa_state.bin`, `generated_best_outputs_valset/task_*/`). Not strictly needed to reproduce but cheap to keep and useful for post-mortem inspection. |
| `SPIKE_REPORT.md` | This file. |

The `/tmp/gepa-spike-venv/` venv is **not** committed; it is trivially
recreated by the reproducer command below.

---

## 9. Reproducibility

To re-run the spike with a different LLM key (e.g. swap gemini for
Anthropic once rate limits normalise):

```bash
# 1. Recreate the venv
python3.11 -m venv /tmp/gepa-spike-venv
source /tmp/gepa-spike-venv/bin/activate
pip install 'gepa==0.0.26' 'dspy-ai==3.1.3'

# 2. Provide at least one LLM key (priority: ANTHROPIC > OPENAI > GEMINI)
export ANTHROPIC_API_KEY=sk-ant-...
#   or
export OPENAI_API_KEY=sk-...
#   or
export GEMINI_API_KEY=...

# 3. Run the reproducer from the repo root
cd /root/hermes-workspace/borg
python docs/20260408-0623_classifier_prd/gepa_spike/borg_gepa_evolve.py \
    --corpus docs/20260408-0623_classifier_prd/error_corpus.jsonl \
    --out docs/20260408-0623_classifier_prd/gepa_spike/results.json \
    --gepa-run-dir docs/20260408-0623_classifier_prd/gepa_spike/gepa_run \
    --max-metric-calls 800 \
    --cost-cap-usd 5.0
```

Expected wall clock: 3–10 minutes depending on LLM latency. Expected
cost: <$0.10 on gemini-2.0-flash, <$2 on claude-haiku, <$5 on
claude-sonnet. Expected outcome *without* the custom proposer fix:
identical to this run (0 accepted mutations, FCR unchanged).

To test blocker-1 fix, edit `BorgKeywordTableAdapter` in
`borg_gepa_evolve.py` and supply a custom `propose_new_texts` callback
that enforces the TAB-table format contract; that is the ~80 LOC change
referenced in §5 blocker 1.

---

*End of SPIKE_REPORT.md.*
