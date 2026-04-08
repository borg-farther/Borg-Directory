# Dogfood Team DM — 5 Questions Gate

**To:** the three dogfood teams who reported the v3.2.1 `borg debug` bug (Rust, Docker, React/TS)
**From:** AB
**When to send:** any time today after v3.2.2 ships (already live: https://pypi.org/project/agent-borg/3.2.2/)
**Why this matters:** Per the Skeptic gate in the PRD, these five answers determine whether AB invests 5–6 weeks on Phases 1–4 of the multi-language classifier or redirects that capacity to MCP-in-Claude-Code / SWE-bench polish / pack adoption cron.

---

## The DM

> Hey — quick note from the borg side. You found a real bug in v3.2.1 last week
> (`borg debug` matching Rust/Docker/React errors to a Django migration pack).
> Thank you for reporting it.
>
> v3.2.2 just shipped to PyPI with a fix: the bare `("Error", "schema_drift")`
> fallback is gone, and `borg debug` now detects 7 non-Python languages
> (Rust, Go, JS, TS, React, Docker, Kubernetes) and refuses to give a Python
> answer when the input doesn't match Python. On a 173-error multi-language
> corpus we built for the release, false-confident rate dropped from 53.8%
> to 4.6%. Try `pip install -U agent-borg && borg debug "<your error>"` —
> it should now say "Detected language: rust" and refuse rather than tell
> you to run `manage.py makemigrations`.
>
> The next question is whether to invest the next 5–6 weeks building actual
> per-language packs (Rust borrow-checker, Docker disk-full, TS type errors,
> React hydration, etc.) — vs spending those weeks on borg's other priorities
> (SWE-bench, Claude Code MCP integration, pack-feedback loop). Before I
> commit, I want to ask the people who actually hit the bug five questions:
>
> 1. **When did you last run `borg debug`?** (date) Was that the first time
>    or do you run it routinely?
>
> 2. **What error did you paste, and what did you actually want back?**
>    A diagnosis? An exact fix? A pointer to docs? Something else?
>
> 3. **If `borg debug` had said "I don't know — your error looks like Rust,
>    Borg only knows Python/Django right now"** (which is what v3.2.2 now
>    does), would you have kept the tool installed, or uninstalled?
>
> 4. **If `borg debug` were only callable from Claude Code / Cursor / Cline
>    via MCP** (so an AI agent inside your IDE invokes it on your behalf
>    when it hits an error mid-task) **rather than as a human CLI** —
>    would that be more useful or less? Be honest, even "less" is fine.
>
> 5. **For the language you reported the bug on (Rust / Docker / React),
>    would you actually use a Borg pack for that language if it existed?**
>    Or would you just paste the error into ChatGPT / Claude / Cursor like
>    you do today?
>
> Three answers from real users beats another week of architecture work.
> Reply when you have a minute, no rush.

---

## How AB should interpret the answers

Per `SKEPTIC_REVIEW.md` Appendix B:

**Flip to "do the 5–6 weeks" if any TWO of these are true:**
1. ≥ 3 of the dogfood teams say they run `borg debug` weekly and would value multi-language support.
2. AB commits to shipping MCP-in-Claude-Code in the same quarter (makes the dataclass + confidence API a shared dependency).
3. Anyone outside AB volunteers to author packs for JS or Rust.
4. SWE-bench saturates and the next strategic win is in non-Python territory.
5. Telemetry shows non-trivial `borg debug` invocation rate per installed user.

**Otherwise:** ship is Phase 0 only. Redirect the 5–6 weeks to MCP / SWE-bench / pack cron. Keep v3.2.2 as the honest-narrow-tool product.

## Logging the answers

Save responses verbatim to `docs/20260408-0623_classifier_prd/dogfood_responses.md`
with a timestamp prefix `[YYYYMMDD-HHMM]` per AB's filename convention. Then update
the OPEN QUESTION 1 in `SYNTHESIS_AND_ACTION_PLAN.md` with the verdict.
