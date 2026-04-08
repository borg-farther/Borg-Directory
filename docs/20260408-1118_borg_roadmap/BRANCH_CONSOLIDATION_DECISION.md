# Branch Consolidation Decision: `main` vs `master`

**Date:** 2026-04-08 (workspace housekeeping sweep)
**Author:** subagent, under workstream 5.2 / 5.3 of
`BORG_TESTING_ROADMAP_20260408.md`
**Status:** DECISION NOT YET EXECUTED — awaiting AB approval

## TL;DR

- `origin/master` holds all the current release history (v3.0.0 → v3.2.4)
  and all the honesty/audit/experiment work from 2026-04-07 and 2026-04-08.
- `origin/main` is the remote default (per `git remote show origin`) but
  it holds a **different** line of development that diverged from master at
  commit `3d6b548`. It has 17 commits master does not, including the
  OpenClaw converter, the marketing pack, and Phase 1–3 pack-reputation
  work.
- Master has 57 commits main does not.
- The two branches are **not** fast-forwardable in either direction. Any
  consolidation has to be an explicit merge, a rebase, or a deliberate
  overwrite — not a `git push main`.

**Recommendation: (ii) fast-forward is impossible; do a deliberate merge
commit from master into main, then swap the default.** Spelled out below.
AB to approve.

## Current state (measured 2026-04-08)

```
$ git remote show origin
  HEAD branch: main
    main   tracked
    master tracked
    master merges with remote master
    master pushes to master (up to date)

$ git log origin/master..origin/main --oneline | wc -l
17

$ git log origin/main..origin/master --oneline | wc -l
57

$ git merge-base origin/main origin/master
3d6b548f2db6f0796a253568ac0539e38a74249f
```

**Top of `origin/master` (recent, what `pip install agent-borg` reflects):**

```
7ff278f checkpoint: P2.1 Sonnet paused at rate-limit wait 20260408-1612
9c2966c v3.2.4: observe→search roundtrip fix + regression tests
b289cae audit: 20260408-1216 third honesty sweep
c76eb81 exp: P1.1 MiniMax Path 1 — first honest agent-level borg measurement
f70e931 audit: P1.0 +34pp claim forensic audit — PARTIALLY SUPPORTED
4ebc948 docs: borg testing roadmap 20260408-1118 — priority-ranked spec
1e817dd honesty: sweep fabricated p=0.031 borg A/B claim across workspace
782086f feat: public feedback channel for v3.2.2/3.2.3 classifier roadmap
2e0329c chore: drop stale 'v3.2.2 refuses' string in UnknownMatch block
ec92bcb v3.2.3: anti_signatures patch — residual Python over-fires killed
```

**Top of `origin/main` (stalled, older):**

```
a487099 launch-ready: bare pack names work, README with cache framing, tool count fix, 1092 tests
a38cded marketing v4: single title, clean layout, cache layer framing throughout
65843a6 marketing v3: cache layer framing, cleaner design, section dividers, quick reference
63119a9 marketing pack v2: merged meme energy + strategy + cold start hack into unified doc
b4ab5d1 meme marketing pack: 10 twitter threads, 10 discord msgs, 10 memes, 5 reddit posts, 20 taglines
3cba2c2 Fix converter test quality metrics, cleanup debug files, final state: 1037 tests + 20 openclaw pack refs
a7d24ec Add OpenClaw skill distribution package
016c484 OpenClaw converter v2: hybrid bridge implemented — 1 skill + 20 pack references, 99 lines, 114KB
f20275f PRD v2: hybrid bridge approach — ONE skill + pack references, kills v1's per-pack conversion
ee309ba PRD: OpenClaw converter — ultra-deep spec with field mapping, conversion algorithm, 25 evals
```

## Which branch has the releases

**`master` has the releases.** Every `v3.x.x` tag in
`git log origin/master --oneline | grep v3` was built on master:

- `v3.0.0 Phase 0+1` → master
- `v3.2.2: Phase 0 honesty patch` → master
- `v3.2.3: anti_signatures patch` → master
- `v3.2.4: observe→search roundtrip fix` → master

The `agent-borg` PyPI package at every released version corresponds to a
commit on master.

`main` has no version tags since the divergence point.

## What's on main that is NOT on master

This is the thing that makes option (i) risky. Main is not just stale — it
has 17 unique commits containing real work:

1. **OpenClaw converter** (`016c484`, `3cba2c2`, etc.) — an integration
   with OpenClaw skill format that was never ported to the master line.
2. **Marketing pack v1–v4** (`b4ab5d1`, `63119a9`, `65843a6`, `a38cded`,
   `a487099`) — product copy / taglines / threads.
3. **Phase 1–3 pack reputation work** (`dc741c8`, `5c20484`, `b03ce79`,
   `8e8b116`) — CLI reputation / status commands, telemetry, aggregator
   cron, benchmark suite. Some of this *may* have been re-done on master
   but it should be confirmed before deletion.

If AB considers any of this content still wanted, it has to be cherry-picked
onto master before we retire main.

## Options

### Option (i) — Delete `main`, make `master` the default

**Steps:**
1. On GitHub: Settings → Branches → change default branch from `main` to
   `master`.
2. Locally then remotely: `git push origin --delete main`.
3. Update any CI references to `main` (none found in this repo's
   `.github/workflows/` at the time of writing).

**Pros:**
- Single source of truth. PyPI, git history, and human mental model all
  line up on `master`.
- Zero merge conflicts. Fastest path.
- No rewrite of master — release history is untouched.

**Cons / risks:**
- **PERMANENTLY LOSES** the 17 commits on main that are not on master.
  OpenClaw converter, marketing pack, Phase 1–3 reputation work — all
  vanish from the default branch and are only findable via reflog / tags.
- Anyone with a PR targeting `main` has their PR auto-closed by GitHub
  when the default changes. PRs on an orphaned branch cannot be merged
  into master without manual rebase.
- Forks on `main` will diverge silently from the canonical line.

**Mitigation if chosen:** tag `main` as `archive/main-20260408` *before*
deletion so the 17 commits are never GC'd.

### Option (ii) — Merge `master` into `main`, then swap default

**Steps:**
1. Locally:
   ```
   git checkout main
   git pull
   git merge --no-ff master -m "merge: consolidate master release line into main"
   # resolve conflicts (there WILL be some — both branches modified README
   # and the test suite size counter, 1092 vs 1708)
   git push origin main
   ```
2. On GitHub: confirm default stays as `main`.
3. Retire `master`: either delete it or leave it as an alias. Deletion
   has the same PR-orphaning risk as option (i) but for master.

**Pros:**
- **Preserves both lines of work.** Nothing is lost.
- `main` remains the default, matching the GitHub convention the repo
  already uses.
- External forks / PRs that target `main` continue to work.

**Cons / risks:**
- A real merge conflict resolution is required. README, version badge,
  test counter, possibly the OpenClaw converter code (if master re-did
  any of it). Estimated ~30 minutes of manual conflict work.
- The resulting `main` has a non-linear history — a "merge master" commit
  sits on top. Some readers find this harder to follow than a clean
  linear release line.
- After the merge, the next `v3.x.x` release has to be cut from main,
  which means either releasing from main or keeping master alive as a
  release branch. Process change.

### Option (iii) — Leave as-is

**Steps:** nothing.

**Pros:**
- Zero risk. Zero work.
- History is preserved.

**Cons / risks:**
- Readers visiting https://github.com/.../borg land on `main` by default
  and see the **older, pre-honesty-patch** state of the repo. The README
  they see is the marketing pack README, not the v3.2.4 honesty README.
  This directly undermines the "honest about what it doesn't know"
  positioning because the default-branch README is out of date.
- A new contributor branching from `main` writes code against a codebase
  that does not match the published PyPI package.
- Every future roadmap task has to remember "commit to master, not main."
  Tech debt compounds.

## Recommendation

**Option (ii) — merge master into main, then set main as the canonical
release branch going forward.**

Reasoning:

1. The 17 commits on main contain real work (OpenClaw converter, marketing
   pack, reputation work) that AB has not explicitly deprecated. Option (i)
   would silently delete them. That is not a decision a subagent should
   make unilaterally.
2. `main` is already the remote default. Keeping it as the default matches
   the GitHub norm and avoids having to update every doc that links to
   `github.com/.../borg/blob/main/...`.
3. The merge conflict work is bounded (README, version badge, test counter)
   and produces a commit graph that a human reader can audit.
4. If the merge reveals that the main-only work is in fact obsolete
   (e.g. OpenClaw was abandoned), the merge commit can still be the vehicle
   — AB just resolves those conflicts by taking master's side, and the
   merge commit documents the decision.

If AB believes the main-only work is genuinely dead, option (i) is faster
and cleaner — but that call belongs to AB, not to this housekeeping sweep.

## What this doc does NOT do

- It does **not** execute any of the options. No branches are pushed,
  merged, or deleted by this commit. Only the decision doc is added.
- It does **not** audit every one of the 17 main-only commits for content
  that may already exist on master. A full diff of
  `git diff origin/master..origin/main -- borg/` would take longer than
  the 45-minute budget for this housekeeping sweep allows.
- It does **not** touch the remote `HEAD` branch setting.

AB, pick (i), (ii), or (iii) and a follow-up task will execute it.
