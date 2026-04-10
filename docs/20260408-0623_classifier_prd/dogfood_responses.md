# Dogfood Responses — v3.2.2 / v3.2.3 feedback log

**Purpose.** Log real-user responses to the 5-question survey in
`DOGFOOD_TEAM_DM_DRAFT.md`. The `borg-v323-dogfood-followup` cron
(fires 20260410-0700) parses this file and summarises responses
against the 5 flip conditions in `SKEPTIC_REVIEW.md` Appendix B
to tell AB whether Phase 1–4 of the classifier roadmap should
start or stay deferred.

**How to use.** When a response comes in, paste it below using
the template block. Keep the yyyymmdd-HHmm prefix so the cron
can date-sort. One block per respondent. The cron looks for the
literal strings `## Respondent` to count responses.

**Flip conditions being tracked** (from SKEPTIC_REVIEW.md
Appendix B — Phase 1–4 starts when ≥2 of these flip):

1. ≥3 dogfood teams say they run `borg debug` weekly and would value multi-language
2. AB commits to shipping MCP-in-Claude-Code in the same quarter
3. External contributor volunteers to author a pack for JS or Rust
4. SWE-bench Phase A saturates at 10/10 and next win is non-Python
5. Opt-in telemetry shows non-trivial borg debug invocation rate per installed user

---

## SOURCES PUBLISHED (so far)

- **GitHub Discussion** (enabled 20260408-0923): see
  `docs/20260408-0623_classifier_prd/github_discussion_url.txt`
  after the publish step completes. Replies land as GitHub
  Discussion comments; this file must be updated manually
  (copy the reply bodies into `## Respondent` blocks below).
- **GitHub issue template** (enabled 20260408-0923): any new
  issue tagged `classifier-feedback` against
  `bensargotest-sys/guild-tools` counts as a response. The
  cron cross-references the issue body against the template
  and extracts the 5 answers automatically.
- **DM draft** at `DOGFOOD_TEAM_DM_DRAFT.md`: AB to send
  manually to whoever the three teams are (human-only step —
  agent has no out-of-band channel to them).

---

## RESPONSE TEMPLATE

Copy this block for each new response:

```
## Respondent <N> — <handle or anonymous-N> — <yyyymmdd-HHmm>
**Source:** <telegram | discord | github-discussion | github-issue | email>
**Language they hit the bug on:** <rust | docker | react | typescript | other>
**Q1 when did you last run borg debug / routine?**
<answer>

**Q2 what did you paste, what did you want back?**
<answer>

**Q3 would "I don't know" have kept you or uninstalled?**
<answer>

**Q4 CLI vs MCP-in-Claude-Code — more or less useful?**
<answer>

**Q5 would you actually use a pack for your language, or just ChatGPT?**
<answer>

**Flip conditions triggered (mark any that apply):**
- [ ] Condition 1: weekly + multi-lang
- [ ] Condition 3: volunteers to author a pack
- [ ] Other signal: <note>
```

---

## RESPONSES

*(Empty. First response will be appended below this line.)*

---

## CRON PARSER CONTRACT

The `borg-v323-dogfood-followup` cron at `cron_id=64c21258e38f`
reads this file on 20260410-0700 and does:

```
respondents = count of "## Respondent" blocks under "## RESPONSES"
for each respondent:
    parse Q1-Q5 by regex, tag flip conditions
aggregate flip conditions; if >= 2 → recommend Phase 1 START
                          if < 2  → recommend Phase 1 STAY DEFERRED
report adoption signal: pypistats recent agent-borg
report issue count: gh issue list --label classifier-feedback --state open
send Telegram briefing to AB with recommendation + evidence
```

If AB wants to change the threshold, edit the cron prompt at
`cron_id=64c21258e38f` via `cronjob action=update`.
