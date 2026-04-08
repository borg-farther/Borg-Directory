# P2.1 Sonnet Replication — Resume Checkpoint

**Stopped:** 20260408-1612 on AB's request
**Reason:** AB wanted to stop in a way that can be cleanly resumed
**State:** Phase A seeding complete. Zero eval runs executed. Clean stop point.

---

## Current state

### What HAS been done

1. **Infrastructure built and committed:**
   - `run_p2_sonnet.py` (~500 LOC) — paced orchestrator with Latin square condition cycling, 60s between-run pacing, exponential 429 backoff, budget tracking, honesty invariant enforcement, crash-to-JSONL logging.
   - `fit_p2_and_meta.py` — GLMM + meta-analysis script combining P1.1 MiniMax and P2.1 Sonnet results.
   - Both files were live-edited during the stop — see git status for final state.

2. **Preflight verified:**
   - v3.2.4 live: `borg --version` → 3.2.4 ✓
   - Observe→search roundtrip working: `borg observe` wrote traces, `borg search django` returned them ✓
   - All 15 pre-registered Docker images cached ✓
   - Anthropic API key resolved and working ✓
   - Sonnet smoke test passed ✓

3. **Phase A-lite seeding executed successfully:**
   - 3 non-eval Django tasks observed into traces.db:
     - `django__django-10973` — postgresql subprocess PGPASSWORD
     - `django__django-11087` — .delete() optimization
     - `django__django-11265` — exclude on annotated FilteredRelation
   - Verification: `borg search 'django'` returned 10 trace hits after seeding (v3.2.4 fix working in production)
   - Seeding traces are in `~/.borg/traces.db` on this VPS and in `p2_sonnet_results.jsonl` (3 rows with `condition=phase_a_seeding`)

### What has NOT been done

1. **Zero eval runs executed.** The runner started run 1/45 (`django__django-10554 / C0_no_borg`), hit the rate-limit probe, saw the 5h bucket at 75% utilization, and entered a 10,308-second safety sleep (~2h 52m) waiting for the rate-limit window to reset.

2. **No Sonnet API tokens have been spent.** Actual spend so far: $0.00 on the eval (Phase A seeding used no LLM calls — observe/search are local).

3. **No reports generated.** `P2_1_SONNET_REPORT.md` and `P2_2_META_ANALYSIS_REPORT.md` do not exist yet. They're blocked on the 45 runs completing.

### What the rate-limit signal means

The runner's probe hit `util_5h=0.75 overage=rejected` which means the **shared Anthropic OAuth token (sk-ant-oat01-*) is near its 5-hour usage limit from other sessions (Claude Code / your IDE)**. The runner's safety logic did the right thing: refused to start a large experiment that would push the bucket over the limit and crash the other sessions.

This confirms the concern flagged in the roadmap: sequential pacing on the shared OAuth is functional but fragile. **The rate limit is not a bug** — it's a hard constraint of running the experiment on a token that's being used concurrently by other things.

---

## Files in the working tree (uncommitted as of stop)

Run `git status --short` in `/root/hermes-workspace/borg/` to see current state. Expected:

```
 M docs/20260408-1118_borg_roadmap/run_p2_sonnet.py       (final version, paced orchestrator)
 M docs/20260408-1118_borg_roadmap/fit_p2_and_meta.py     (GLMM + meta-analysis)
?? docs/20260408-1118_borg_roadmap/p2_sonnet_results.jsonl (3 Phase A seeding rows only)
?? docs/20260408-1118_borg_roadmap/run_p2_sonnet.log     (seeding log + rate-limit probe)
?? docs/20260408-1118_borg_roadmap/P2_RESUME_CHECKPOINT.md (this file)
```

All of these should be committed before restart to preserve state.

---

## Resume instructions

When AB says "resume P2" or equivalent, the next agent needs to:

### Preflight (free, ~5 min)

1. **Re-check the rate-limit bucket:**
   ```bash
   cd /root/hermes-workspace/borg/docs/20260408-1118_borg_roadmap
   /usr/bin/python3.12 <<'PY'
   from anthropic import Anthropic
   c = Anthropic()
   # Issue a single tiny call, check rate-limit headers in the response
   r = c.messages.create(model="claude-sonnet-4-5-20250929", max_tokens=10,
       messages=[{"role":"user","content":"preflight"}])
   print("OK tokens:", r.usage.input_tokens, r.usage.output_tokens)
   PY
   ```
   If it succeeds without a 429, the bucket has reset.

2. **Verify v3.2.4 is still active:**
   ```bash
   borg --version  # must show 3.2.4
   borg observe 'resume preflight' && borg search 'resume' | head -3
   ```

3. **Verify Phase A seeding is still in the DB:**
   ```bash
   borg search 'django' | head -15
   # Expect trace:* entries for django__django-10973, 11087, 11265
   ```

4. **Verify the JSONL file state:**
   ```bash
   wc -l /root/hermes-workspace/borg/docs/20260408-1118_borg_roadmap/p2_sonnet_results.jsonl
   # Expected: 3 (the Phase A seeding records)
   grep -c '"condition": "phase_a_seeding"' p2_sonnet_results.jsonl
   # Expected: 3
   ```

### Resume options for AB

**Option R1 — Full resume as originally planned** (recommended default)
- Skip Phase A re-seeding (it's already done)
- Skip task 0 rate-limit sleep (just check the bucket is clear)
- Run 45 eval runs with 60s pacing
- Fit GLMM + meta-analyze + commit + halt
- Budget: $18-25
- Wall clock: 2-6 hours depending on rate-limit conditions

**Option R2 — Degraded run on 8 tasks only**
- Cuts the run to 8 tasks × 3 conditions = 24 runs
- Stats plan is explicitly underpowered but still catches large effects
- Saves ~50% wall clock and budget
- Useful if AB wants a faster signal

**Option R3 — Swap to dedicated Anthropic key if AB provisions one**
- Same 45-run plan
- Parallel instead of sequential pacing
- Full budget ~$25
- Wall clock: 30-60 min
- Best option IF AB gets a fresh `sk-ant-api03-*` key

**Option R4 — Pivot to Priority 5 instead**
- Pack adoption cron OR knowledge-wiki dogfood at scale OR cross-model classifier benchmark
- None of these need cross-condition agent runs on a rate-limited token
- AB decides

### Resume command (for Option R1)

Restart the orchestrator, skipping seeding:

```bash
cd /root/hermes-workspace/borg/docs/20260408-1118_borg_roadmap
# Edit run_p2_sonnet.py to add a --skip-seeding flag IF not already present
# Then launch:
nohup /usr/bin/python3.12 run_p2_sonnet.py --skip-seeding > run_p2_sonnet_resume.log 2>&1 &
echo $! > run_p2_sonnet.pid
```

Or if `--skip-seeding` is not implemented, comment out the `phase_a_lite_seeding()` call in `main()` before launching.

Monitor with:
```bash
watch -n 60 'wc -l p2_sonnet_results.jsonl; tail -5 run_p2_sonnet_resume.log'
```

When complete:
```bash
/usr/bin/python3.12 fit_p2_and_meta.py
# Writes P2_1_SONNET_REPORT.md and P2_2_META_ANALYSIS_REPORT.md
git add . && git commit -m 'exp: P2.1 Sonnet resume + P2.2 meta-analysis'
git push origin master
```

---

## Honesty invariant status

- **H2 (borg_searches == 0 halts treatment runs):** still armed, will fire if violated during resume
- **Budget cap:** still $25, reset to full on resume
- **Pre-registered tasks:** still locked to the 15 in the roadmap Appendix A
- **Model:** still `claude-sonnet-4-5-20250929`
- **Latin square condition order:** preserved in `run_p2_sonnet.py`
- **Phase A seeding tasks:** 3 non-eval tasks already in traces.db, no need to re-seed

No state was corrupted by the stop. Resume is idempotent from here.

---

## Decision for AB at resume time

Pick one:
- **R1** (full resume, original plan) — default recommendation
- **R2** (degraded to 8 tasks) — if time is short
- **R3** (needs new Anthropic key) — if AB provisions
- **R4** (pivot to Priority 5) — if direction has changed

Or specify something different. This checkpoint file is the hand-off.
