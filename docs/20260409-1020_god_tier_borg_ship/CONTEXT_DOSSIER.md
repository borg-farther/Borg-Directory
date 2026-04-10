# Context Dossier — Borg v3.3.0 God-Tier Ship Plan + PRD

**Dossier ID:** 20260409-1020_god_tier_borg_ship / CONTEXT_DOSSIER
**Generated:** 2026-04-09 10:20 UTC
**Author:** Hermes Agent (orchestrator)
**Quality bar:** Google SWE-L6 / PhD committee / HN front page

---

## 1. Background — what is this, who's it for, why now

**Product:** `agent-borg` (PyPI: `agent-borg`, CLI: `borg`) — a federated knowledge exchange for AI agents. CLI + MCP server. Ships a pack/tip/workflow registry with local trace caching. v3.2.4 is the current PyPI release. v3.3.0 is the next release.

**What this pipeline produces (the deliverable):**
A full **SPEC.md + PRD** for agent-borg v3.3.0 — world-class quality. This means: formal architecture, complete data model, mathematical formulations where relevant, binary pass/fail success criteria per feature, explicit failure modes, test plan, and implementation roadmap. The spec is the contract; the PRD is the story.

**Why now:** v3.2.4 is not shippable as "ready for real users". Four concrete ship blockers block promotion. The cold-start gap (empty search on first install) is the rate-limiting step of adoption. This pipeline produces the v3.3.0 release plan, spec, and PRD that will pass a Google-level review.

**Current state of the codebase:**
- Repo: `https://github.com/bensargotest-sys/agent-borg` (PyPI name: `agent-borg`)
- Borg version: `3.2.4` (master at commit `decb281`)
- CLI: `borg` (subcommands: `search`, `setup-claude`, `observe`, `generate`, `debug`, `pull`, `feedback-v3`, `mcp`)
- MCP server: 17 tools, JSON-RPC 2.0
- Skills: `~/.hermes/skills/` (user-level, per-memory)
- Seeds data: `borg/seeds_data/` (17 frontmatter skill files, 104 KiB, shipped in wheel since pre-3.2.4, but NOT wired into `borg_search`)
- Traces DB: `~/.borg/traces.db` (SQLite, populated by `borg observe`)
- Pack store: `~/.hermes/guild/` (local index)
- Remote index: `guild-packs` GitHub repo (to be renamed `agent-borg` per SB-04)
- PyPI downloads: ~1,545/month, ~10.6% real interpreter runs (≈164/month)

**Ecosystem reality:** Competitors: `pip install pre-commit` (CLI + registry, works out of box), `copier` (CLI + template registry), `pipx` (CLI that interrogates registry). Ruff is a linter, not a comparable baseline. Borg competes on "does it make my agent smarter?" not on linting speed.

**Model routing in this session:**
- Orchestrator (this agent): Claude Opus 4.6 via Anthropic primary
- Subagents: MiniMax-M2.7 via MiniMax provider (M2.7 handles tool use, agent loops)
- Sonnet blocked: OAuth token `sk-ant-oat01...` refuses tool-use payloads (returns synthetic 429). See `docs/20260408-1118_borg_roadmap/P2_OAUTH_TOOLUSE_429_FINDING.md`. Sonnet experiment deferred.

---

## 2. The four ship blockers — verbatim from FIRST_USER_E2E_AUDIT_20260409.md

These are hard gates for v3.3.0. All four MUST pass before the release tag.

### SB-01 — `setup-claude` emits `"command": "python"`
- **File:** `borg/integrations/setup_claude.py` (grep for `"command": "python"`)
- **Bug:** Hardcodes `"command": "python"`. Ubuntu 24, macOS Python.org installer, pyenv — all ship only `python3`. Claude Code spawns `python`, gets ENOENT, silently fails — every `borg_*` tool is invisible.
- **Fix:** prefer `shutil.which("borg-mcp")`; fall back to `sys.executable`
- **Effort:** 30 min
- **Verification:** `borg setup-claude` → inspect config JSON → `"command"` is a path that exists
- **Reproducer captured:** This SAME failure broke our own VPS. Evidence: 120-second hang.

### SB-02 — `docs/EXTERNAL_TESTER_GUIDE.md` — 49 hits of stale `guildpacks` naming
- **File:** `docs/EXTERNAL_TESTER_GUIDE.md`
- **Bug:** Contains `guildpacks`, `guild-packs`, `guild-mcp`, `pip install guild-packs` (49 hits). Every command is wrong. Users follow the guide, get 404, conclude the project is dead.
- **Fix:** Delete the file. Add a 50-line `docs/TRYING_BORG.md` with the correct names.
- **Effort:** 1 hr
- **Verification:** `grep -ri 'guild-packs\|guildpacks\|guild-mcp' docs/` returns zero hits (outside internal audit artefacts and `borg/seeds_data/guild-autopilot/`)
- **Acceptance:** New doc has correct `pip install agent-borg` and `import borg` throughout.

### SB-03 — `borg generate --format claude` fails with argparse `invalid choice`
- **File:** `borg/cli.py` near `generate` subparser
- **Bug:** README documents `--format claude` and `--format cursor`. Real argparse values are `claude-md` and `cursorrules`. User copies README verbatim → told they typed their own tool wrong.
- **Fix:** Rename argparse choices to `{cursor, cline, claude, windsurf, all}`. Alias old names for back-compat.
- **Effort:** 45 min
- **Verification:** All four `borg generate <pack> --format {cursor,cline,claude,windsurf}` exit 0.

### SB-04 — `pyproject.toml` URLs point at `guild-packs`
- **File:** `pyproject.toml` `[project.urls]`
- **Bug:** Homepage / Repository / Documentation point at `https://github.com/bensargotest-sys/guild-packs`. PyPI homepage link leads to wrong repo. Also: wheel `Author` / `Author-email` fields may still reference old name.
- **Fix:** Update all URLs to `agent-borg`. Grep entire file for any stale naming.
- **Effort:** 15 min
- **Verification:** `pip show agent-borg | grep -i url` shows zero `guild-packs` substrings.

**Total ship-blocker effort: ~2.5 hours of senior engineering.**

---

## 3. Cold-start seed corpus — verbatim from COLD_START_SEED_CORPUS_DESIGN.md

This is the single biggest first-user friction. Without this, every cold install returns `No packs found.`

**Problem:** On `pip install agent-borg` → `borg search <anything>` → empty result. `borg/seeds_data/` has 17 frontmatter skill files (104 KiB) shipped in the wheel since before 3.2.4, but they're NOT wired into `borg_search`. The P1.1 experiment (2026-04-08) confirmed: all 30 treatment runs got `borg_searches == 1`, then stopped on iteration 2 because the search returned nothing useful. C0=C1=C2=0.000.

**Recommended fix (Option A — bundle a curated seed corpus):**
- Ship `borg/seeds_data/packs/*.yaml` (200–500 packs, 0.5–2 MiB compressed) alongside existing skill files
- Add `_load_seed_index()` that merges seeds with remote index + traces at search time (never copies to user dir)
- Precompute `borg/seeds_data/index.json` — zero runtime LLM
- Re-curation cadence: quarterly (aligned to minor releases)

**Goals (must ALL pass):**
| ID | Goal | Exit measurement |
|---|---|---|
| G1 | Clean install: `borg search` returns ≥1 relevant result for 80% of 50-query benchmark | Automated test |
| G2 | Clean install: `borg search` returns ≥5 results for 95% of benchmark | Same benchmark |
| G3 | Seed corpus adds ≤ 5 MiB to wheel (uncompressed) | `ls -la` on built wheel |
| G4 | Existing `pytest borg/tests/` still green | CI |
| G5 | Every seed pack has traceable public source + MIT/Apache-2.0/CC0-compatible license | License manifest |
| G6 | `--no-seeds` opt-out flag exists | CLI help text + test |
| G7 | C3 replay: per-run "borg returned content" rate rises from 0/30 to ≥25/30 | Replay experiment |

**Verification approach for cold-start:**
- 50-query benchmark (pre-registered, diverse: Python errors, bash one-liners, git workflows, Docker configs, etc.)
- Run `borg search <query>` on each of 50 queries in a zero-state environment (fresh HOME dir)
- Count: queries with ≥1 result (G1), queries with ≥5 results (G2)
- Target: G1 ≥ 40/50, G2 ≥ 47/50

**Known issues with the design doc (red-team notes):**
- D2: MDN (CC-BY-SA 2.5) is listed as allowed source but CC-BY-SA is incompatible with MIT/Apache wheel → DROP MDN
- D7: No incident-response play for a bad seed pack already installed → ADD one paragraph
- D8: Prototype plan used MiniMax-Text-01, which floor-effected in P1.1 → REPLACE with MiniMax-M2.7
- D1: K=500 stated as back-of-envelope (correct), but §7 prototype must validate it empirically

**Prototype plan (§7 of design doc):**
- 50 SWE-bench gold patches → seed packs (one YAML pack per task, describing the bug class)
- `_load_seed_index` wiring into `borg.core.search.borg_search`
- C3 replay: 15 runs × 20 iters × MiniMax-M2.7
- Target: "borg returned content" rate ≥ 0.8

**Total cold-start effort: ~70 engineering hours** (dominated by curation). Prototype in ~6 hours.

---

## 4. Other HIGH items for v3.3.0

| ID | Title | Effort | Fix |
|---|---|---|---|
| HIGH-02 | `guild://` → `borg://` in CLI help strings (keep parser accepting both) | 30 min | Grep + patch |
| HIGH-03 | `feedback-v3 --success` validator | 15 min | Add `--success` validation |
| HIGH-04 | `borg debug` exit code on no-match | 15 min | Fix non-zero exit |
| HIGH-05 | Investigate `borg_suggest {}` — may need `agent_context` param | 2 hr | Fix or remove from `tools/list` |
| HIGH-06 | `git mv borg/seeds_data/guild-autopilot → borg-autopilot` + content update | 45 min | Rename + update refs |

---

## 5. Model routing context (for evals design)

**The core design constraint for this session:**
- Orchestrator: Claude Opus 4.6 (top-level, always)
- Subagents: MiniMax-M2.7 (all heavy lifting)
- Sonnet: BLOCKED (OAuth tool-use refusal, deferred)

**Why this matters for evals:**
Any eval that uses the orchestrator (Opus) for treatment runs will get ceiling-effect results (Opus solves everything regardless of borg). The experiment design must route treatment runs through M2.7, not Opus. This is a hard constraint — it comes from the P1.1 findings and the V3 skill's critical lesson: "Opus creates ceiling effects."

**Sonnet deferred note:**
P2.1 Sonnet is the cross-model story. It requires either:
(a) A fresh `sk-ant-api03...` Anthropic key (~$25), or
(b) A MiniMax-M2.7 pivot for the P2 slot (~$0.30)

For the v3.3.0 PRD, P2 is NOT in scope (cold-start is). The eval plan must account for P2's deferred status.

---

## 6. What the PRD must answer

The Chief Architect's PRD must explicitly cover ALL of the following — no section left blank:

1. **What is agent-borg?** One sentence. Target: developer who has never heard of it.
2. **What's broken in v3.2.4?** The four ship blockers + cold-start gap. Specific, not vague.
3. **What does v3.3.0 ship?** Each feature with its binary pass/fail criteria. Not "improve cold-start" — "G1 ≥ 40/50 on 50-query benchmark."
4. **How do we know it worked?** The eval plan. Who measures what, when, with what instruments.
5. **What's NOT in scope?** Explicit. This prevents the "but what about X?" questions.
6. **What are the failure modes?** Each feature's mode of failure. Not just "it might not work" — specific.
7. **What's the rollout plan?** Phased. No big-bang.
8. **What can go wrong AFTER launch?** Incident-response plays for bad seed packs, corrupted installs, PyPI yanked wheels.
9. **The release note.** 3 paragraphs. Honest. No marketing language. What changed, what works, what doesn't.
10. **The decision log.** Every design decision with its reason. Especially the controversial ones (Option A vs B vs C for cold-start, MiniMax routing, seed corpus licensing).

---

## 7. Files to read

**For Red Team (adversarial review of the ship plan):**
- `docs/20260409-0800_user_readiness/SYNTHESIS_AND_SHIP_PLAN_20260409.md` — the current ship plan (this dossier's primary input)
- `docs/20260409-0800_user_readiness/FIRST_USER_E2E_AUDIT_20260409.md` — evidence for the four ship blockers
- `docs/20260409-0800_user_readiness/COLD_START_SEED_CORPUS_DESIGN.md` — cold-start design
- `docs/20260408-1118_borg_roadmap/P2_OAUTH_TOOLUSE_429_FINDING.md` — Sonnet OAuth finding (context for P2 deferral)
- `borg/cli.py` — CLI surface (ship blocker 3)
- `borg/core/pack_taxonomy.py` — classifier (cold-start wiring target)
- `borg/core/search.py` (or wherever `borg_search` lives) — search path for cold-start fix
- `borg/integrations/setup_claude.py` — ship blocker 1 target
- `pyproject.toml` — ship blocker 4 + wheel size budget
- `README.md` — ship blocker 3 verification source

**For Blue Team (architecture + PRD spec):**
All of the above + the P1.1 report (`docs/20260408-1118_borg_roadmap/P1_MINIMAX_REPORT.md`) for the experiment design context.

**For Green Team (empirical grounding):**
- `docs/20260409-0800_user_readiness/FIRST_USER_E2E_AUDIT_20260409.md` (defect inventory)
- `docs/20260409-0800_user_readiness/COLD_START_SEED_CORPUS_DESIGN.md` (cold-start G1-G7 metrics)
- `docs/20260408-1118_borg_roadmap/P1_MINIMAX_REPORT.md` (P1.1 raw data, floor-effect evidence)
- `borg/pyproject.toml` (dependency versions, wheel size budget)
- `borg/seeds_data/` (17 existing skill files — sample for size/content analysis)

**Ignore:** All of `docs/agenti/`, `docs/agent0/`, `docs/defi-trading-mcp/`, `docs/eliza_cloned/`, `docs/plugin-solana/`, `docs/ai-memecoin-trading-bot/`, `dogfood/` (experiment repos, not production code), `eval/` (experiment eval code, not product).

---

## 8. Constraints from AB (verbatim)

1. "claude just on the top level orchestrator agent and minimax 2.7 on the rest pls"
2. "do d, world-class Google quality" — "god tier / Google / PhD" = multi-agent adversarial, stats rigor
3. "plan it / spec / PRD" — produce a full spec + PRD, not just a ship plan
4. "deliver to a god tier google team" — the deliverable must pass Google SWE-L6 review
5. "clear evals, limits, success criteria, means of verification, testing" — every feature has all five
6. "approve" = go. Default if AB doesn't say otherwise: wait for explicit approval before PyPI release

---

## 9. Non-negotiable design rules (from the honesty invariants)

| ID | Rule | Why |
|---|---|---|
| N1 | No "proven" claim without raw data | Integrity |
| N2 | No treatment run counts if `borg_searches == 0` | Measurement validity |
| N3 | No statistical claim without pre-registered alpha + sample | No p-hacking |
| N4 | No marketing-style claims without experiment-log link | No theatre |
| N5 | Earlier wrong claims get a CORRECTION block | Self-correction > theatre |
| N6 | No LLM-on-hot-path for core borg ops without offline fallback | Cold-start must work offline |
| N7 | Opus is NOT on the eval treatment path | Ceiling effects invalidate results |

---

## 10. What each team is delivering

### Team RED — Adversarial Reviewers
**Deliverable:** `RED_TEAM_REVIEW.md`
Structured review with severity ratings (CRITICAL/HIGH/MEDIUM/LOW). Checklist:
- Ship plan flaws — are the four SBs actually the right four? What did we miss?
- Cold-start fix flaws — will Option A actually work? What can break it?
- Eval design flaws — does the 50-query benchmark actually test cold-start?
- Testing gaps — what's NOT tested?
- Failure modes we haven't listed
- Architecture smells
- "What did we skip that would embarrass us on HN?"

### Team BLUE — Architecture + PRD Spec
**Deliverable:** `ARCHITECTURE_SPEC.md`
Full PRD spec. Must include:
- Problem statement (one sentence)
- Formal model for cold-start seed corpus
- Data model (exact YAML schema for seed packs)
- `_load_seed_index()` interface contract
- Eval framework with metrics
- Binary pass/fail success criteria per feature (G1-G7 exactly)
- Failure modes matrix
- Implementation roadmap (ordered phases with dependencies)
- Design decision log

### Team GREEN — Empirical Analysis
**Deliverable:** `DATA_ANALYSIS.md` + `build_corpus.py` + `error_corpus.jsonl` + `run_baseline.py` + `baseline_results.csv`
Reproducible oracle pipeline. Must produce:
- Per-feature defect breakdown table
- Size analysis of existing `borg/seeds_data/` (sample from 17 files)
- Seed corpus sizing model (K=500 back-of-envelope validated or adjusted)
- Wheel size budget analysis (G3 ≤ 5 MiB)
- Recommended confidence thresholds per feature
- ROI-ranked priority list

### Chief Architect + Skeptic (parallel with teams)
**Deliverable:** `SYNTHESIS_AND_PRD.md`
Merged action plan + full PRD. Must include all 10 questions from §6 above. Runs in parallel with the three teams.

**Skeptic's required questions:**
1. Is this product surface even right? (who uses it, vs LLM alternatives?)
2. Cost/benefit vs other bets on the roadmap?
3. The honesty test: what does the draft release note look like if we ship the minimum patch today?
4. Does anyone care? cheapest 48h signal to find out?
5. The verdict: fix-worth / spec-worth / talk-to-user scored 0-10

---

## 11. Output directory

All deliverables go to: `docs/20260409-1020_god_tier_borg_ship/`

Required files:
1. `CONTEXT_DOSSIER.md` (this file)
2. `RED_TEAM_REVIEW.md`
3. `ARCHITECTURE_SPEC.md`
4. `DATA_ANALYSIS.md`
5. `GREEN_TEAM_DATA/` subdirectory with `build_corpus.py`, `error_corpus.jsonl`, `run_baseline.py`, `baseline_results.csv`
6. `SKEPTIC_REVIEW.md`
7. `SYNTHESIS_AND_PRD.md` (THE reference document — combines all findings)

---

## 12. Tone and format

- Numbers > vibes
- Severity tags: CRITICAL / HIGH / MEDIUM / LOW
- No emojis
- Markdown only
- Every finding: [SEVERITY] finding description + evidence + fix
- Every decision: stated reason, not just outcome
- Every metric: target number, not "improve"
- Commit to `master` when done, push

---

*This dossier was written to save each team ~30 minutes of re-discovery. Everything you need is here. Read it first.*
