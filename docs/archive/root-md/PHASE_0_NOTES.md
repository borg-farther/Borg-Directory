# Phase 0 Notes — 2026-04-24

## Done (4 commits on public-live-dashboard-20260423-1245)
- 94d44c1: untrack 106 .pyc files
- d4b87d7: scrub VPS IP from STATUS.md, untrack egg-info, add to .gitignore
- 54a5f95: remove broken docs/agenti submodule gitlink
- (disk) rm -rf docs/agenti: reclaimed 1.1 GB

## Handoff corrections (things that were wrong in the 2026-04-24_handoff)
- Stray file `public-live-dashboard-20260423-1245` at repo root — never existed
- README VPS IP leak — IP was in STATUS.md, not README
- pyproject.toml borg-farther/Borg-Directory — decided to keep (mirrors are byte-identical)
- docs/agenti "35,746 files tracked" — only 1 gitlink tracked; 35,745 were disk-only
- docs/agenti c1435ea crypto.py — already merged to HEAD, no reconciliation needed

## Known bugs deferred (intentional — not touched this session)
### borg_observe wrapper at mcp_server.py:3087 (the "duplicate")
Not a duplicate. It's a monkey-patch wrapper on top of the real definition at line 1679.
Real problems:
1. `_HARD_STOPS` regex loop is UNREACHABLE dead code
   (the `if action: return ...` above it always returns when ACTION present,
   which is nearly always)
2. `return result[:200]` on line ~3115 is indented INSIDE the `for` loop —
   even if _HARD_STOPS ran, only first pattern would be checked
3. Wrapper calls `_borg_observe_orig(..., short=False)` unconditionally,
   ignoring the `short` param for the inner call (wasteful, not wrong)
4. No tests in borg/tests/ cover the wrapper — only the original is imported
5. `build/lib/borg/integrations/mcp_server.py` contains stale copy
   (build artifact should be gitignored separately)

Fix requires design decision on what _HARD_STOPS should do,
test coverage for the wrapper, and careful rewrite.
Estimated effort: 45-60 min of focused work.
Do NOT fix at the end of a long session.

## Remaining Phase 0 items (none critical)
- build/ directory gitignore (see stale copy above)

## Not started
- 6 open decisions (see 2026-04-24_handoff.md)
- c1435ea design docs review (11 docs, ~6350 lines, mostly at HEAD)
- P2.1 Sonnet 30min diagnosis
- OpenSpace comparison
- Classifier 173-row corpus audit (27%/67% claims)

## State at pause
- Branch: public-live-dashboard-20260423-1245
- HEAD: 54a5f95 (4 commits ahead of origin)
- origin/public-live-dashboard-20260423-1245: still 3739b5b (not pushed)
- Stashes: 4 (unchanged from session start)
- Tree: clean


---

## Additional work same day (2026-04-24)

Beyond Phase 0 cleanup, completed:

- **7217d2a** `docs: classifier audit` — reproduced baseline.py, found
  framing misleads (Python subset n=34 is honest denominator). See
  `CLASSIFIER_AUDIT.md`.
- **30fdc14** `docs: patch PRD classifier claims` — 5 PRD sites updated
  with audited framing.
- **this commit** CHANGELOG correction banner + P2.1 formal deferral.

**Session state at close:** tree clean, 8+ commits local, origin still at
3739b5b. Nothing pushed. Handoff to next session: read `CLASSIFIER_AUDIT.md`
first — it's the most important document produced today.
