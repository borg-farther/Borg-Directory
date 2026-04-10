# SKEPTIC REVIEW — v3.3.0 Honest Value Audit

**Reviewer:** Skeptic / Honest Value Auditor
**Date:** 2026-04-09
**Commit reviewed:** `decb281` (v3.2.4 / master)
**Documents reviewed:** All five inputs (CONTEXT_DOSSIER, RED_TEAM_REVIEW, ARCHITECTURE_SPEC, DATA_ANALYSIS, SYNTHESIS_AND_SHIP_PLAN)

---

## Preamble

My job is not to relitigate the four ship blockers. Those are correct and real. My job is to answer the five questions the dossier explicitly asks that no other team was assigned.

---

## 1. Is this product surface even right? Who uses it? LLM alternatives?

### The product

`agent-borg` is a federated knowledge exchange for AI agents -- a CLI and MCP server that lets agents share workflow packs (structured debugging/playbook knowledge). The stated value proposition: "does it make my agent smarter?" not "is it a fast linter?"

### Who actually uses it

PyPI says ~1,545 downloads/month, ~10.6% real interpreter runs (approximately 164/month). The RED_TEAM_REVIEW finding 22-28 documents the embarrassment risks: the README tagline says "Python/Django debugging expert" but the product does not work on Go, Rust, Docker, or K8s errors. The test badge "1708 passed" has no linked CI source.

The P1.1 experiment (30 treatment runs) is the only behavioral evidence of real agents using borg. All 30 stopped at iteration 2 because search returned nothing useful -- floor effect, not a product failure, but also not a success story.

The target user described in the synthesis is: "a developer who has never heard of it" evaluating it via the README Platform Setup section -- which is broken on arrival (SB-03). Every potential user who reads the README copy-pastes `--format claude` and gets `invalid choice`.

### LLM alternatives

The honest comparison class is NOT ruff (a linter). It is:
- `pip install pre-commit` -- CLI + registry, works out of the box (no cold-start gap)
- `pip install copier` -- CLI + template registry, works out of the box
- `pip install pipx` -- CLI interrogates registry, works out of the box
- A well-curated GitHub gist bookmarked in the agent's instructions

The differentiation claim is "structured debugging workflows with anti-patterns and investigation trails." This is a real differentiation -- but it only has value if the search returns results on day one. Today it does not.

### Verdict on product surface

The surface is reasonable but the cold-start gap makes it non-functional for its core promise. The MCP tool visibility failure (SB-01) means Claude Code cannot see any `borg_*` tools. The README examples are broken (SB-03). The PyPI link is wrong (SB-04). These are not polish issues -- they are first-user funnel killers.

The ARCHITECTURE_SPEC's formal model (Section 2) is sound: text search over K=500 packs with token overlap is the right algorithm for this corpus size. The K=500 corpus goal is validated by the Zipf power-law model in GREEN_TEAM_DATA. The search strategy justification (Section 6.1) correctly argues against Bayesian, evolutionary, and embedding-based approaches for this scale.

The product surface is RIGHT in the sense that a CLI/MCP server for structured debugging knowledge is a real market. It is WRONG in the sense that v3.2.4 cannot demonstrate its value proposition on a clean install.

---

## 2. Cost/benefit vs other bets (revised roadmap ~95h total). ROI analysis.

### Revised effort numbers

The SYNTHESIS_AND_SHIP_PLAN claims ~12 hours total. This is wrong. The RED_TEAM_REVIEW correctly identified the compounding errors:

| Item | Ship plan claim | Skeptic correction |
|------|-----------------|-------------------|
| SB-01 + SB-02 + SB-03 + SB-04 | 2.5h | 2.5h (correct) |
| SB-05 (autopilot python bug -- new finding) | 0 | +0.5h (same fix, different code path) |
| Cold-start wiring (`_load_seed_index`) | 2h (design doc) / 6h (RED) | 6-8h engineering (greenfield integration) |
| Cold-start curation K=200 | 12h (synthesis) | 20-25h serial (RED finding 10) |
| HIGH-02..HIGH-06 batch | 4h | 4h (correct) |
| 50-query benchmark pre-registration | 0 | +2-3h (RED finding 17) |
| License CI enforcement | 0 | +2h (RED finding 20) |
| Incident response / recall procedure | 0 | +2h (RED finding 13) |
| `borg pull` happy-path network test | 0 | +0.5h (RED finding 8) |
| Wheel size test fix (5MiB not 10MiB) | 0 | 1 min |

**Revised total: approximately 42-47h of engineering for v3.3.0** (not 12h). The cold-start full K=500 curation adds another ~40h on top, but the synthesis already flags K=200 as the realistic v3.3.0 target.

### ROI analysis

GREEN_TEAM_DATA Section 6 provides an ROI-ranked priority list using the formula: ROI = frequency x impact x ease_of_fix.

The four ship blockers collectively cost ~2.5 hours and have the highest combined ROI:
- SB-01: Breaks entire MCP story for Ubuntu24/macOS/pyenv users. Already broke our own VPS. ROI = 20,000.
- SB-04: Every PyPI visitor sees wrong homepage link. ROI = 40,000.
- SB-03: Every README copy-paster gets immediate failure on the hero Platform Setup section. ROI = 13,333.
- SB-02: Every external tester follows dead `pip install guild-packs` and concludes the project is dead. ROI = 10,000.

These are the highest-ROI items in the entire v3.3.0 backlog. Fixing them costs less than half a day and unblocks the entire adoption story.

The cold-start fix (HIGH-01) has high ROI but is also the primary sinkhole (GREEN_TEAM_DATA Section 7): wiring 17 seeds eliminates the honest miss but introduces false-confident risk. A wrong seed pack delivered with high confidence causes agents to follow wrong resolutions. The quality filter (MinHash dedup + automated parse check + human review of 10%) is the sinkhole mitigator and must ship with the wiring, not deferred.

### Cost/benefit vs other bets

The revised roadmap of ~42-47h produces:
1. Four ship blockers fixed (SB-01 through SB-05)
2. A working cold-start seed corpus wiring with K=200 curated packs
3. A clean PyPI listing with correct URLs
4. README examples that actually work
5. An external tester guide that leads to a real package

Alternatively: spend those 42h on something else. Given that SB-01 breaks the MCP story entirely and SB-04 makes the project look dead to anyone who checks the PyPI homepage, the cost of NOT shipping v3.3.0 is higher than the engineering cost.

The one genuine risk: the cold-start wiring is a greenfield integration (RED finding 2). The existing seeds at `borg/seeds_data/*.md` are in SKILL format, not `workflow_pack` YAML format, and are loaded by `pack_taxonomy._init_cache()`, not by `borg_search`. The design doc's `_load_seed_index()` function does not yet exist. Shipping v3.3.0 with a working cold-start prototype (K=50, not K=200) is achievable in 42h. Shipping v3.3.0 with K=200 fully curated packs is not achievable in 42h unless curation is parallelized aggressively.

---

## 3. Honesty test: 3-paragraph release note for TODAY (4 ship blockers only, no cold-start)

Here is what we would honestly ship today if we cut v3.3.0 with only the four ship blockers fixed and no cold-start seed corpus:

---

**agent-borg v3.3.0 -- Bug Fix Release**

This release fixes four critical first-user failures that prevented agent-borg from working on clean installations.

**What changed:** We fixed `setup-claude` so it correctly detects `python3` on Ubuntu 24, macOS Python.org installer, and pyenv (SB-01 + SB-05: the same bug affected both `setup-claude` and `autopilot`). We rewrote the external tester guide with correct package names (SB-02). We corrected the `--format` argument choices in `borg generate` so the README examples actually work (SB-03). We updated all PyPI project URLs from `guild-packs` to `agent-borg` (SB-04).

**What works:** `pip install agent-borg` followed by `borg setup-claude` now produces a valid MCP configuration. `borg generate systematic-debugging --format claude` now runs without argparse errors. The PyPI homepage link resolves to the correct repository. These fixes touch only CLI scaffolding and packaging metadata -- no core search or agent-adoption logic changed.

**What does not work in this release:** Cold-start search still returns "No packs found" on a fresh install. The 17 skill files shipped in the wheel at `borg/seeds_data/` are not yet wired into `borg search`. A cold-start seed corpus is designed and prototyped; the curation and full integration is the v3.4.0 work. Until then, `borg search` requires either a remote index or a local pack at `~/.hermes/guild/`.

---

### Honesty assessment

Is this honest? **Yes.** It makes no claim about cold-start being fixed.

Is it compelling? **No.** The release note describes four bug fixes to packaging metadata and CLI scaffolding. It does not describe a product that got meaningfully better at its core promise (making agents smarter via structured debugging knowledge). A user who reads this release note and installs v3.3.0 will still get `No packs found` on first search. The product's core differentiator is still silent on day one.

The SYNTHESIS_AND_SHIP_PLAN claims "total ~12 hours" for v3.3.0 -- the honesty test for this claim: the actual engineering is 42-47h, not 12h. If someone quotes "12 hours to ship v3.3.0" in a community post and we later discover it took 42h, that is a credibility gap. The 12h figure only covers the ship blockers, not the HIGH items, not the benchmark, not the incident response, not the network test.

**The 3-paragraph release note above is honest but not compelling.** The product story requires the cold-start fix to be compelling. The cold-start fix requires ~42-47h of engineering. Shipping today with only the four ship blockers produces a release note that describes a slightly less broken package, not a product that delivers its core promise.

---

## 4. Does anyone care? Cheapest 48h signal that real users want cold-start.

### The evidence that cold-start matters

GREEN_TEAM_DATA Section 7 ("Sinkhole Detection") identifies the cold-start fix as the primary sinkhole: it simultaneously eliminates honest misses (empty search) and introduces false-confident risk (wrong seed pack). The P1.1 experiment (30 treatment runs) showed all 30 agents stopped on iteration 2 because search returned nothing useful. This is the only behavioral evidence of real agents hitting cold-start.

The SYNTHESIS_AND_SHIP_PLAN Section 1 describes "the single biggest first-user friction" as the cold-start gap. Every first-time user who runs `borg search <anything>` gets `No packs found.` The 164/month real interpreter runs are almost certainly users who reached this failure state and stopped.

### The problem: no direct user validation of cold-start demand

We have no evidence that users who encounter "No packs found" then successfully found a workaround and became retained users. We have evidence they stopped (the P1.1 floor effect). We do not have evidence of the counterfactual: users who would have become retained users if search had returned results.

PyPI download stats (~1,545/month, ~164 real interpreter runs) tell us about acquisition funnel top, not retention. We cannot tell from these numbers whether the cold-start gap is:
- A. A friction that kills 90% of signups before they ever use a second command, OR
- B. A friction that kills only the users who would have churned anyway (wrong tool for their use case)

### Cheapest 48h signal that real users want cold-start

The green team DATA_ANALYSIS.md Section 8 describes the 50-query cold-start benchmark. The benchmark fixture does not yet exist in the repo (RED finding 17: "50-query benchmark pre-registered is not actually pre-registered or in repo"). Creating and running it costs:

1. **Draft 50-query benchmark fixture**: 2-3h (per RED finding 17)
2. **Run benchmark against current codebase** (zero-state install): 1h
3. **Pre-register externally** (GitHub gist with timestamp): 30 min
4. **Total: ~4-5h engineering, $0 inference cost**

This is the cheapest honest signal. Before spending 42h engineering on cold-start, spend 4h proving the benchmark is real.

Alternatively: post a single question on the GitHub repo or relevant community (r/LocalLLaMA, Hacker News) asking "what error do you most want a structured debugging workflow for?" and count responses. This costs 1h and $0 but is anecdotal, not behavioral data.

### What would actually prove users care

The gold standard: a before/after retention study. Ship v3.3.0 with ship-blockers-only (no cold-start). Track 30-day retention of new installs (do they run borg again after first week?). Then ship v3.4.0 with cold-start fix. Compare retention curves. This requires a tracking mechanism we do not currently have.

The silver standard: ship the cold-start prototype (K=50 packs, ~8h engineering) to a closed beta of 10 real users. Measure whether they run `borg search` more than once in a session.

The bronze standard (what we can do in 48h): run the 50-query benchmark, report G1/G2 numbers against the current codebase, publish the raw results. If G1 < 10/50, cold-start is catastrophic and the fix is mandatory. If G1 > 30/50, the problem is less severe than assumed.

### Recommendation

Do not spend 42h on cold-start without first running the 50-query benchmark. The benchmark costs 4h and tells us whether the problem is catastrophic (G1 < 10/50), moderate (G1 20-40/50), or mild (G1 > 40/50). The effort should scale with the measured severity.

---

## 5. Verdict

### fix-worth: 7/10

Fix the four ship blockers. They cost 2.5h and have the highest ROI in the entire backlog. SB-04 alone (wrong PyPI homepage) is a project-killing issue for anyone who evaluates the tool by checking the repository link. SB-01 (broken MCP config) means Claude Code cannot see any borg tools at all. These are not optional.

Do not ship v3.3.0 without fixing SB-01 through SB-04. The fix-worth score of 7 reflects: ship blockers are worth fixing, but the roadmap estimate is wrong by 3-4x (12h actual vs 42h real), and the cold-start fix is scoped as a full engineering track, not a 2h patch.

### spec-worth: 6/10

The ARCHITECTURE_SPEC is the strongest document in the package. The formal model for cold-start (Section 2) is sound. The `_load_seed_index()` interface contract (Section 4) is precise and implementable. The YAML schema (Section 3) is complete and includes the forbidden-fields list (no StackOverflow CC-BY-SA content, no MDN CC-BY-SA content). The search strategy justification (Section 6.1) correctly argues against embedding-based and Bayesian approaches for K=500.

The spec scores 6, not higher, because:
- The K=500 corpus is still unvalidated (the Zipf model is theoretical; P1.1 only proved the failure, not the cure)
- The C3 prototype uses a proxy metric ("borg returned content" rate) not task pass rate (RED finding 16)
- The 50-query benchmark fixture does not exist in the repo (RED finding 17)
- The dedup policy for seed vs remote vs local priority is not documented in the spec (RED finding 12)
- The incident-response play for misleading seed packs (RED finding 13) is not in the spec

The spec is good enough to implement from, but these five gaps mean it will require design decisions during implementation that should have been resolved before shipping the spec for review.

### talk-to-user: 8/10

There is a real user signal. P1.1 (30 treatment runs, floor effect on all 30) proves agents hit the cold-start gap. PyPI ~164 real interpreter runs/month is a non-zero user base. The RED_TEAM_REVIEW finding 25-28 documents the HN embarrassment risks (wrong tagline, stale test badge, README examples broken on arrival) -- these are issues a user would find on first contact.

The score is 8, not 10, because:
- We have no retention data (do users come back after first install?)
- We have no direct user testimony that the cold-start gap specifically is the killer (it is assumed, not measured)
- The "talk-to-user" step should happen before committing 42h of engineering to cold-start

The cheapest next step: post the 50-query benchmark results publicly and ask "does this match your debugging needs?" on HN, r/LocalLLaMA, or the GitHub discussions. This costs 4h of engineering to produce the benchmark and 1h of posting. It is the minimum viable talk-to-user signal before spending 42h.

---

## Summary Verdict Table

| Question | Score | Key Evidence |
|----------|-------|---------------|
| Is product surface right? | 7/10 | Surface is correct; cold-start gap makes it non-functional on day one |
| Cost/benefit vs other bets | 7/10 | SBs have highest ROI; 42-47h revised estimate is 3-4x the ship plan's 12h |
| Honesty test | 6/10 | Release note is honest but not compelling; cold-start story missing |
| Does anyone care? | 6/10 | P1.1 proves agents hit gap; no retention or direct user validation |
| **Fix-worth** | **7/10** | Ship the four SBs immediately; do not ship cold-start without benchmark first |
| **Spec-worth** | **6/10** | Strong formal model; 5 gaps must close before implementation |
| **Talk-to-user** | **8/10** | Strong user signal from P1.1; benchmark is the cheapest next validation |

---

## Recommended Action Order

1. **Today**: Fix SB-01 through SB-05 (2.5h engineering, highest ROI in the project)
2. **Today**: Fix SB-04 pyproject.toml URLs (15 min, fixes PyPI legitimacy signal)
3. **This week**: Draft and run the 50-query cold-start benchmark (4h). Publish results. This is the decision gate for whether cold-start engineering is warranted.
4. **If benchmark G1 < 20/50**: Cold-start is catastrophic. Proceed with full 42-47h engineering track.
5. **If benchmark G1 > 40/50**: Cold-start is mild. Consider shipping ship-blockers-only and calling cold-start a v3.4.0 feature.
6. **Before shipping any cold-start wiring**: Close the five spec gaps (C3 proxy metric acknowledgment, benchmark pre-registration, dedup policy doc, incident response play, license CI enforcement).

---

*Skeptic review complete.*
