# SKEPTIC REVIEW — `borg debug` Classifier PRD

**Role:** Honest value auditor. Not a cheerleader.
**Read:** CONTEXT_DOSSIER, RED_TEAM_REVIEW, ARCHITECTURE_SPEC, DATA_ANALYSIS, error_corpus.jsonl, baseline_results.csv, README.md.
**Tone:** direct. If it's engineering-for-engineering's-sake, I say so.

---

## TL;DR — the honest call

- **The one-line fix is obviously worth doing.** Ship it today. (fix-worth 9/10)
- **Blue's 5–6 week spec is probably engineering-for-its-own-sake right now.** It is a beautiful classifier for a feature whose actual usage AB cannot quantify. Right architecture, wrong priority. (spec-worth 3/10)
- **AB should not write another line of classifier code until he has talked to three humans who have actually run `borg debug` in anger.** (talk-to-user 10/10)

The wedge is: **Phase 0 + a reposition of the README + 48 hours of user research.** That captures 80% of the value for ~2% of the effort, and unlocks the right decision on whether to then do Blue's full spec or redirect those 5–6 weeks to SWE-bench / MCP / agent-borg integrations.

---

## 1. THE CORE QUESTION — is `borg debug <error>` even the right surface?

### Who pastes an error into a CLI before ChatGPT / Cursor / Copilot Chat?

Honest answer, going through the realistic personas:

| Persona | What they actually do with an error today | Does `borg debug` win? |
|---|---|---|
| Solo Python dev on Django | Reads traceback. Googles first. Pastes into ChatGPT second. | No — ChatGPT has context of the whole file. |
| JS/TS dev with a hydration error | Pastes into Claude / Cursor Chat inline. | No — LLM gives contextual answer in 2 seconds. |
| Rust dev with E0382 | Reads rustc's own error, which is already excellent. Maybe Googles the error code. | No — rustc errors are already the gold standard. |
| Platform/DevOps with K8s `CrashLoopBackOff` | Runs `kubectl logs --previous`. Then Googles. | No — they need `kubectl`, not a CLI lecture. |
| AI coding agent (Claude Code / Cursor / Cline) | Calls an LLM. Potentially calls `borg-mcp` tool if wired in. | **Maybe** — this is the only persona where borg has a theoretical edge. |

The CLI surface `borg debug "paste error here"` is competing against tools that (a) already have file context, (b) are already open, (c) have no dependency to install, (d) handle every language. **A human pasting an error into a CLI is a path few humans take.**

The ONLY surface where borg plausibly wins is the **agent-callable** surface: an LLM agent inside Claude Code / Cursor / Cline hits an error mid-task, needs a deterministic, offline, cheap lookup, and calls borg via MCP. That is a real wedge. But it's a different product framing than "paste an error into a CLI."

### What's the differentiator vs just asking an LLM? (no hand-waving)

Honest list of things borg could in theory offer that an LLM doesn't:

1. **Deterministic, cached, zero-cost** — true. LLMs cost tokens, borg doesn't.
2. **Offline / air-gapped** — true and real for enterprise.
3. **Structured JSON contract for tool-chaining** — true, but not implemented (Red MEDIUM-5).
4. **"Refuses to answer when unsure"** — true aspiration, false today (53.8% FCR).
5. **Collective learning from real outcomes** — largely **false as shipped**. The "EVIDENCE: 47/52 successes (90%)" in the README is the Red team's MEDIUM-10 finding: it's a self-fulfilling vanity stat written into pack frontmatter by hand, not learned. Handing that number to PyPI users as a trust signal is misleading. Do not use "collective learning" as a differentiator until there is an actual feedback loop wired up.

What's left after honesty: **deterministic + offline + MCP-callable**. That's a real niche, but it's an **agent-tool** niche, not a human-pastes-errors niche.

### Does anyone use `borg debug` today?

Unknown. There is no telemetry (Red MEDIUM-10). The 2862 tests don't cover `classify_error` (Red CRITICAL-5). The only signal we have is three dogfood teams who came back with bugs — meaning at most three teams ran it, and 100% of that sample reported it broken. That's the highest-leverage data point in this entire PRD: **the only users we know about all hit the bug.**

Fixing a feature that may have no users is the definition of engineering-for-engineering's-sake. Fixing a feature that has three known users and all three hit bugs is worth the one-line fix but NOT worth 5–6 weeks until the denominator is known.

---

## 2. COST / BENEFIT REALITY

### Blue's 5–6 weeks vs other borg bets

Borg bets competing for AB's solo time:

| Bet | Status | Strategic value | Estimated time | ROI per week |
|---|---|---|---|---|
| **Phase 0 debug fix** | 1 line + language gate | Stops actively harmful output on 53.8% of a realistic corpus | 0.5 days | Enormous |
| **Blue's full classifier spec** | 5–6 weeks | Elegant architecture. Fixes a feature of unknown usage. | 5–6 weeks | Unknown denominator → unknown ROI |
| **SWE-bench Phase A polish** | 9/10, real traction | Builds the thing borg is already winning at | ? | Known-positive; compounds |
| **Pack adoption cron** | Infra work | Closes the real feedback loop → makes "collective learning" not-a-lie | 1–2 weeks | High; unlocks real evidence |
| **CI hooks (`borg check` in GitHub Actions)** | Distribution | Gets borg into user workflows where it stays resident | 1–2 weeks | High; real discovery |
| **Agent-borg SDK / MCP in Claude Code** | Distribution | Real wedge: agents calling borg at error time | 1–2 weeks | Very high if `borg debug` ends up being an agent tool, not a CLI |

**Honest call:** if AB has 5–6 weeks of solo capacity to spend, the classifier spec is probably the 3rd or 4th best use of it. SWE-bench polish compounds on existing momentum. MCP-in-Claude-Code puts borg in front of users who matter. Pack adoption cron makes the "collective learning" claim true. Any of those probably beats "classifier academic-grade rebuild."

The classifier spec is the right thing to do **conditional on `borg debug` being a feature people actually use**. Without that conditional, it's gold-plating a lawn ornament.

### Is there a smaller wedge that captures 80% with 20% effort?

**Yes. It's Phase 0 only + honest README.** From DATA_ANALYSIS section 10:

> **P0** | Delete the `("Error", "schema_drift")` fallback line + add language-match gate | 53.8% FCR → ~6% FCR on the corpus with zero new packs | **0.5 eng-days** | **∞ ROI**

Let that sink in. **One deleted line and one language gate drops false-confidence from 53.8% to ~6% without shipping a single new pack, a single calibration curve, a single dataclass.** Everything else in Blue's 5–6 weeks is the difference between 6% and ≤2% FCR, plus coverage of JS/Rust/Go/Docker/K8s — coverage for users who don't exist yet.

The 80/20 move is explicit:

- **Phase 0** (Blue day 1): delete the fallback, add a language-match gate, reword the CLI "no match" message to be actionable. **0.5 days.**
- **README reposition** (30 minutes): change the 10-Second Demo to use a Python error, rewrite the Features bullet to "Python/Django expert today; other languages return 'unknown'", remove the `TypeError: Cannot read properties of undefined` example (which currently demos the bug). **30 minutes.**
- **Ship v3.2.2 to PyPI** same day.
- **Talk to three users** (see §4). **2 days of calendar time, 2 hours of AB time.**
- **Decide** whether to do Blue's spec, or redirect to SWE-bench / MCP / pack cron.

Total: ~3 calendar days, ~6 hours of real work. That's the wedge.

---

## 3. THE HONESTY TEST — v3.2.2 release notes

If AB ships Phase 0 as v3.2.2 today, the PyPI release notes should read like this. Draft below. Three paragraphs, honest, no marketing.

---

> **agent-borg 3.2.2 — Honesty patch**
>
> This release fixes a serious bug in `borg debug`. In 3.2.1 and earlier, any error message containing the substring "Error" — which is to say, most error messages in most programming languages — would be routed to our Django `schema_drift` pack and the CLI would print Django migration advice with a confident `(python)` label. We reproduced this on Rust `error[E0382]`, Go `panic: runtime error`, Docker `ENOSPC`, Node `ReferenceError`, Kubernetes `CrashLoopBackOff`, and more. On a 173-error multi-language corpus we built for this release, the false-confident rate was 53.8%. That is worse than refusing to answer. We are sorry.
>
> What 3.2.2 changes: we deleted the `"Error" → schema_drift` fallback and added a language-match gate so that Python packs only fire on inputs where we detect Python. If you paste a non-Python error, `borg debug` will now print "No matching problem class found" instead of bad advice. This is a regression in *coverage* and an improvement in *honesty*. On the same corpus, false-confident rate drops from 53.8% to ~6%.
>
> What `borg debug` is and is not, honestly: **it is a Python/Django expert with 12 hand-authored packs, no confidence score, and no learned model.** It is not yet multi-language — JavaScript, TypeScript, Rust, Go, Docker and Kubernetes return "unknown" in 3.2.2 and that is by design until we can ship calibrated per-language packs with measured false-confident rates. The README has been updated to reflect this. If you are a Python/Django developer, `borg debug` should still help. If you are not, we would rather say "we don't know yet" than give you a confidently wrong answer. Follow the roadmap in `docs/20260408-0623_classifier_prd/` if you want to contribute a pack for your language.

---

That's the release note. It's honest, it's short, and it turns a reputational bleeding wound into a credibility deposit. **That is worth shipping this afternoon.**

### Is "multi-language" even the right marketing frame?

**No.** The marketing frame should be **"Python/Django expert, explicit about what it doesn't know."** Reasons:

1. It's currently true and provable. The other frame isn't.
2. Python/Django is where borg's SWE-bench momentum already lives (9/10). Align marketing with reality.
3. "Explicit about what it doesn't know" is a genuine differentiator vs LLMs, which are famously NOT explicit about what they don't know.
4. It sets up the future multi-language story as **earned coverage**, pack by pack, rather than as an aspirational claim the code can't back.
5. A narrow tool that is honest about its scope is respected. A broad tool that is silently wrong is mocked.

The README change: delete the `TypeError: Cannot read properties of undefined` example (which currently demonstrates the bug — actively embarrassing), replace it with a Python example, change the positioning line from "paste an error, get a fix" to "paste a Python error, get a fix; other languages coming with measured precision, not marketing."

---

## 4. "DOES ANYONE CARE?" TEST — cheapest 48h signal

AB has **775+ PyPI downloads** and **0 telemetry**. We cannot know the denominator of actual `borg debug` usage without asking. Before committing 5–6 weeks, here are signals ranked by cost, cheapest first:

### Tier 1 — free, one-hour calendar

1. **DM the three dogfood teams** who reported the bug. Ask: "How did you come to run `borg debug`? What were you expecting? If it had said 'unknown', would you have kept the tool installed?" — 30 minutes of AB's time, 100% signal from users we know exist.
2. **Post in r/programming, r/Python, HN "Show HN Who's using `borg debug`?"** with the v3.2.2 release note as the hook. Even 10 replies tell you whether the surface has pull. Cost: 20 minutes.

### Tier 2 — 1 day of work

3. **Ship v3.2.2 with a one-shot opt-in prompt** on first `borg debug` call: `"Help borg improve? Share anonymous classification outcomes? [y/N]"`. Writes `{ts, error_hash, detected_lang, confident}` to a local JSONL. Even if users say no, the prompt itself forces a binary signal: did they invoke `borg debug` at all? Cost: half a day of CLI work, 0 infrastructure — local file only.
4. **PyPI download-version split analysis.** Check if anyone is still on older versions or if the distribution is all latest-version — gives a crude "are people actually using this" signal. Cost: 10 minutes.

### Tier 3 — 2 days of work

5. **Add a voluntary `borg debug --feedback` flag** and embed a link to a GitHub discussion in every `debug` output. Any single reply there is worth more than another week of Blue's spec.
6. **Grep GitHub code search for `borg debug` in .sh, .yml, .md files.** If it's in anyone's install scripts or CI, that's real adoption. Cost: 30 minutes.

### The Actually Cheapest Answer

**Option 1 is free and unambiguous.** AB should spend 30 minutes tonight writing to the three dogfood teams with a structured question list:

- When did you last run `borg debug`? (date)
- What error did you paste?
- What did you want back?
- If `borg debug` said "I don't know, try ChatGPT", would you uninstall?
- If `borg debug` were only callable from Claude Code via MCP (not as a human CLI), would that be more useful or less?

Three answers is enough to decide whether to do Blue's 5–6 weeks. If zero of the three say "I paste errors into it regularly," Blue's spec is deferred and the effort goes to MCP-in-Claude-Code. If two or three say "yes, I use it weekly," Blue's spec is justified and gets prioritised.

**This is a 30-minute question that unlocks a 5–6 week decision.** Doing the 5–6 weeks without asking is a failure of the "verify before ship" non-negotiable applied to AB's own roadmap, not just the code.

---

## 5. VERDICT

### Scores (0–10)

| Question | Score | Rationale |
|---|---:|---|
| (a) Is the **fix** worth doing? | **9/10** | 0.5 eng-days, drops FCR from 53.8% to ~6%, removes a real reputational bleed on 775+ downloads. Ship today. Not 10/10 only because even after the fix, we still don't know if anyone uses `borg debug`. |
| (b) Is the **5–6 week spec** worth doing? | **3/10** | The spec itself is excellent engineering — Red gives it real credit, Green gives it a measurable baseline, Blue's architecture is principled. But it's solving the wrong prioritisation problem. Without demand evidence, it is gold-plating a feature of unknown value at the expense of SWE-bench polish, pack adoption cron, and MCP-in-Claude-Code, any of which probably has higher ROI per week. Revisit score upwards to 7–8/10 **only** after §4's user research confirms real demand. |
| (c) Should AB **talk to a user** before investing further? | **10/10** | Literally the cheapest high-value action on the entire roadmap. 30 minutes of effort, gates a 5–6 week decision. If AB does one thing from this review, it's this. |

### Recommended next move (one sentence)

**Ship Phase 0 (delete the `"Error"` fallback + add a language-match gate + rewrite the README to "Python/Django expert, honest about the rest") as v3.2.2 this afternoon, then DM the three dogfood teams tonight with five questions, and defer the decision on Blue's 5–6 week classifier spec until those answers are in.**

---

## Appendix A — What I'd want AB to push back on in this review

Honest skeptic-of-the-skeptic:

1. **"The spec builds infrastructure you'd need anyway for the agent-MCP wedge."** Partly true. Match/UnknownMatch dataclasses, per-language calibration, structured JSON output — those help the MCP path too. If AB is going to build the MCP wedge, doing Blue's spec is a prerequisite for ~40% of that work. So spec-worth might be 5/10 not 3/10 if it's **explicitly scoped as "groundwork for agent-MCP, not for human CLI."**
2. **"Talking to three dogfood teams is cherry-picked."** True — they already self-selected as people who found bugs. Better sample: random PyPI downloader email via `pip`'s optional contact field (which doesn't exist). Best realistic: HN post.
3. **"Reputation risk is real regardless of usage."** Agreed. Even one screenshot on Twitter of Rust-on-Django ruins the trust AB is building via SWE-bench. This is the argument for Phase 0 being 9/10 rather than 6/10. The reputation leak is a forcing function that's independent of whether anyone uses the feature.
4. **"The 53.8% FCR number was measured on a corpus Green built; real user traffic might look different."** True. But a corpus built from Stack Overflow + docs IS the distribution of error strings users actually hit. If anything the real distribution is worse (users paste noisier things than curated corpora).
5. **"Blue's spec IS the verify-before-ship discipline AB preaches, applied to classification."** True. The spec is the correct academic-rigour response to the problem. The skeptic claim is not "the spec is wrong," it is "the spec is the right answer to the wrong question until we know the feature matters."

If AB disagrees with the headline call, the cheapest counter is: answer §4's questions honestly, then re-score.

---

## Appendix B — What would flip me to "yes, do the 5–6 weeks"

The spec becomes worth doing if **any two** of the following are true:

1. ≥ 3 of the dogfood teams (or any other real users) say they run `borg debug` weekly and would value multi-language support.
2. AB commits to shipping an MCP-in-Claude-Code integration in the same quarter, making the dataclass + confidence API a shared dependency with real downstream callers (not just a CLI).
3. A single external contributor volunteers to author packs for JS or Rust, proving the ecosystem wedge has pull (i.e., someone outside AB cares enough to contribute content).
4. The SWE-bench story saturates (Phase A hits 10/10 ceiling and the next win is in non-Python territory), making multi-language coverage strategically necessary for borg's next milestone.
5. Telemetry from v3.2.2's opt-in prompt (see §4 tier 2) shows a non-trivial denominator of actual `borg debug` invocations per installed user per week.

Until any two of those land, Blue's 5–6 weeks is an investment in elegance at the cost of momentum.

---

**Skeptic out.** If you want a 1-paragraph version to paste into Slack: *Delete the "Error" fallback line, ship v3.2.2 today as a Python/Django-only honesty patch, DM the three dogfood teams tonight, and defer Blue's 5–6 week spec until those three answers are in — right now it's gold-plating a feature of unknown usage while SWE-bench / MCP / pack cron are higher-ROI bets.*
