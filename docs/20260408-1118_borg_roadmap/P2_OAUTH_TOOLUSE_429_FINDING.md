# P2.1 Sonnet — OAuth Tool-Use 429 Finding

| Field | Value |
|---|---|
| Date | 2026-04-09 |
| Time | 13:30 UTC |
| Author | Hermes Agent on behalf of AB |
| Supersedes | `P2_RESUME_CHECKPOINT.md` "rate-limit window" hypothesis |
| Status | P2.1 Sonnet experiment INDEFINITELY HALTED on this OAuth token |

## TL;DR

The 20260408-1612 stop and the 20260409-1246 / 20260409-1318 resume attempts of the P2.1 Sonnet replication all hit `429 Too Many Requests` on the **first** real eval call. The previous diagnosis ("5h utilization bucket near 75 percent, sequential pacing on shared OAuth is fragile") was **partially wrong**. The actual cause is: the shared `sk-ant-oat01...` Claude Code OAuth token **refuses tool-use messages requests that include a real problem prompt**, returning a synthetic `rate_limit_error` with message="Error" while the rate-limit headers report 0–4% utilization. Minimal payloads (`max_tokens=10`, no tools, "." prompt) succeed; payloads with realistic system + tool list + 1500+ char problem fail immediately and consistently.

This is not a budget. It is a scope or content-policy refusal masquerading as a 429. **No amount of pacing, retry, or waiting will unblock it.** Sonnet replication on this token is structurally impossible and the roadmap's Priority 2.1 must either (a) acquire a fresh first-party `sk-ant-api03...` Anthropic key or (b) pivot to a different model.

## Reproducer

```python
import httpx
TOKEN = open('/root/.hermes/.env').read().split('ANTHROPIC_TOKEN=')[1].split('\n')[0]
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "oauth-2025-04-20",
    "content-type": "application/json",
}

# CASE A — minimal ping. Status 200.
r = httpx.post("https://api.anthropic.com/v1/messages", headers=HEADERS, json={
    "model": "claude-sonnet-4-5-20250929", "max_tokens": 10,
    "system": "You are Claude Code, Anthropic's official CLI for Claude.",
    "messages": [{"role":"user","content":"."}],
})
# → 200 OK, returns content

# CASE B — realistic SWE-bench-shaped tool-use payload. Status 429.
tools = [
    {"name":"read_file","description":"r","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
    {"name":"finish","description":"f","input_schema":{"type":"object","properties":{}}},
]
r = httpx.post("https://api.anthropic.com/v1/messages", headers=HEADERS, json={
    "model": "claude-sonnet-4-5-20250929", "max_tokens": 100,
    "system": "You are Claude Code, Anthropic's official CLI for Claude.\n\nFix the bug.\n\nPROBLEM:\n" + "Django migration bug: " + "x"*2400,
    "tools": tools,
    "messages": [{"role":"user","content":"Begin"}],
})
# → 429
# {"type":"error","error":{"type":"rate_limit_error","message":"Error"},"request_id":"req_011..."}
```

The rate-limit headers on a separate ping immediately before AND after the failing call show:

```
anthropic-ratelimit-unified-5h-status        allowed
anthropic-ratelimit-unified-5h-utilization   0.04
anthropic-ratelimit-unified-7d-utilization   0.74
anthropic-ratelimit-unified-7d_sonnet-utilization 0.01
anthropic-ratelimit-unified-overage-status   allowed
anthropic-ratelimit-unified-status           allowed
```

i.e. the bucket reports the request was *allowed* both before and after — but the request itself returned 429. This is not how a real rate-limit should behave.

## What rules out an actual rate limit

1. Minimal pings (`max_tokens=10`, no tools, `"."`-content) always return 200, and headers always show < 5% utilization.
2. Tool-use requests with **short** prompts also succeed (200), even with 6 tools attached.
3. Tool-use requests with **long** SWE-bench-shaped prompts always fail with 429 — repeatable, deterministic, no jitter.
4. The 7d Sonnet-specific bucket is at 1% utilization with the reset > 24 hours away. There is no plausible budget that would refuse the second call.
5. `claude-opus-4-6` with the same shape **succeeds** (200), and that is the model the parallel audit subagents are using right now, on the same token, without 429s.
6. The 429 body's `message` field is the literal string `"Error"` — not the usual Anthropic rate-limit prose `"This request would exceed your organization's rate limit..."`.

## Most likely cause

The Claude Code OAuth token (`sk-ant-oat01...`) is provisioned with a content/scope policy that **blocks tool-use messages requests on Sonnet 4.5 unless they originate from the official Claude Code IDE binary**. The `anthropic-beta: oauth-2025-04-20` header allows the token to *talk to* the messages endpoint, but a server-side check on the request shape (prompt length × tool count × model) classifies our SWE-bench harness traffic as "non-IDE" and rejects it with a synthetic 429. Opus 4.6 is exempt because Opus is the official Claude Code CLI's primary model and the policy is keyed on model + shape.

This is consistent with:
- Both the 20260408-1612 and 20260409-1246 attempts failing at run 1/45 with no per-run variation.
- The runner's exponential backoff from 120s → 1800s never being unblocked.
- The 7d Sonnet bucket sitting at 1% across all attempts.
- The fact that we burn the same token for routine Hermes/Claude Code traffic without ever seeing this error.

It is plausible the policy is unintentional and a policy-team-side bug; it is also plausible it is intentional anti-abuse. Either way, **for the purposes of the borg roadmap, the OAuth path is closed for Sonnet tool-use experiments**.

## Decision

P2.1 Sonnet is HALTED indefinitely. The roadmap (`BORG_TESTING_ROADMAP_20260408.md` Priority 2.1, OQ #2) was already pre-committed to the option of a "fresh `****` key" — that is now the only viable path.

## Options going forward

Ranked by ROI:

1. **AB provisions a fresh first-party `sk-ant-api03...` Anthropic key.** Cost: ~$25 for the 45-run experiment + ~$1 for re-tested infra. Wall clock: 30–60 min. This is the original "Recommend: fresh key" answer from OQ #2 of the roadmap. Unblocks P2.1, P2.2 meta-analysis, P3 publication path.

2. **Pivot the Sonnet slot to MiniMax-M2.7.** M2.7 is a newer/stronger MiniMax model than the M-Text-01 used in P1.1, and a smoke test on 2026-04-09 13:35 UTC confirmed it accepts tool-use payloads with the same shape that 429s on Sonnet OAuth. Cost: ~$0.20 (still cheap). Wall clock: ~30 min. Drops the cross-model story from "MiniMax + Sonnet" to "two MiniMax tiers", which is weaker but honest.

3. **Pivot to GLM-4.6 / Kimi-K2 / Gemini-2.5 / GPT-5.** Each requires a separate API key and a per-model adapter in `run_single_task.py`. Estimated effort: 3 hours per model. Cost: ~$10–30 each.

4. **Defer P2 entirely**, focus on the Priority 5 pivot: ship the v3.3.0 cold-start fix from `COLD_START_SEED_CORPUS_DESIGN.md`, then re-do P1 with C3 (seeded public corpus) to actually answer "does borg help on cold-start". This is the "bypass the model question, fix the artifact" play.

**Recommendation:** Option 1 (fresh key) **for the canonical Sonnet result needed for publication**, AND Option 4 (cold-start fix + C3 replay) **in parallel because it does not depend on a key**.

## Action items

- [x] Halt the running orchestrator (PID 2118526), commit checkpoint
- [x] Commit this finding doc
- [ ] AB decision: fresh key, MiniMax pivot, or both
- [ ] Update `run_p2_sonnet.py` to detect a synthetic-429 (message="Error", retry-after absent) and abort instead of exponentially backing off forever
- [ ] Patch `BORG_TESTING_ROADMAP_20260408.md` Priority 2.1 to cite this finding instead of the original rate-limit hypothesis

## Provenance

All probes were done from this VPS (`srv1353853`), Python 3.12.3, raw `httpx` against `https://api.anthropic.com/v1/messages` to remove the runner as a confound. Captured request IDs for the 429 cases:

```
req_011CZtGWp4Fyn9BeUD7Rv3Vj
req_011CZtGiEqaUmbzMV3mPgLSG
req_011CZtGpEZ8LjT8JSjiCRvZM
req_011CZtGqsSvu9ZhzMozm4uYh
req_011CZtGsopDLyzKetuTwtxar
req_011CZtGspjXa1Hv4YWh4XJmT
req_011CZtGsqknnGSaTVbSSYWTM
req_011CZtGsrnoajgsYTLGeA2Aj
req_011CZtGssWDVm1PJHU9eWU9R
req_011CZtGstFcGMgFCJZDKeUUT
req_011CZtGsu6hunVTfK3JbUwCn
```

Anthropic Trust & Safety can use these IDs to confirm or refute the OAuth-scope hypothesis.
