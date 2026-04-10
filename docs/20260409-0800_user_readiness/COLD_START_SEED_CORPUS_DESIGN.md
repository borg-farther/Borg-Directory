# Cold-Start Seed Corpus — Design Document

| Field | Value |
|---|---|
| Doc ID | 20260409-0800_user_readiness / COLD_START_SEED_CORPUS_DESIGN |
| Status | Proposed for review |
| Author | Hermes Agent (subagent, Claude Opus 4.6) |
| Target reviewer bar | Google SWE-L6 design review / PhD committee / HN front page |
| Target implementer | One senior engineer, no further questions |
| Supersedes | Nothing (first doc on this problem) |
| Related | `docs/20260408-1118_borg_roadmap/P1_MINIMAX_REPORT.md` (evidence), `docs/20260408-1118_borg_roadmap/BORG_TESTING_ROADMAP_20260408.md` (context) |
| Borg version at design time | `agent-borg 3.2.4` (master @ `decb281`) |
| Owner after acceptance | TBD |

---

## 1. Problem statement

On a clean install (`pip install agent-borg==3.2.4`) a first-time user or agent running `borg search <anything>` gets either an empty result set or, at best, whatever the remote `guild-packs` index happens to list on GitHub that day. The local pack store under `~/.hermes/guild/` is empty, the local trace database under `~/.borg/traces.db` is empty, and `borg/seeds_data/*.md` (17 skill-frontmatter files, 104 KiB, shipped in the wheel since before 3.2.4) is wired into the classifier but **not into `borg.core.search.borg_search`**. Until the user does work *and* that work is observed *and* promoted, Borg is a semantic cache with nothing cached.

This is not a hypothesis. It is the single loudest empirical result of the P1.1 MiniMax Path 1 experiment, 20260408:

> "`borg search 'django'` after seeding still returned 'No packs found' (borg 3.2.3 observes traces but does not promote them into the search index in this version), so C2 and C1 are effectively indistinguishable in what borg actually returned to the agent. This is a real-world limitation of the current borg release, not a bug in the experiment."
> — `P1_MINIMAX_REPORT.md` §10, "Threats to validity", item 6.

All 30 treatment runs returned `borg_searches == 1` exactly, then stopped on iteration 2 after a single `borg_search` call that returned nothing useful. The experiment cannot distinguish "Borg has no effect" from "Borg has an empty cache on first use", because the floor effect dominates (§10 item 1, §12 "honest interpretation"). Pass rates were C0=C1=C2=0.000 with identical Clopper-Pearson upper bounds of 0.218.

The v3.2.4 release closed one half of the bug — `borg_search` now joins against `traces.db` so `borg observe` → `borg search` is a round trip. It does not fix the other half: **three traces is not a corpus**, and 17 frontmatter skill files that never reach the search path is not either. A first-time user sees, in the measurable first 30 seconds: `pip install agent-borg` → `borg search 'flask error handling'` → `No packs found.` → tab closed. From `BORG_TESTING_ROADMAP_20260408` §2.1: 1,545 PyPI downloads/month, ~10.6% real interpreter runs (≈164/month), and of those an unknown small fraction make it to a second `borg` invocation. Cold-start failure is the rate-limiting step of adoption. No downstream metric — classifier accuracy, GLMM effect size, wiki depth — matters if the first search returns nothing.

---

## 2. Goals and non-goals

### 2.1 Goals (exit criteria are the definition of "solved")

| ID | Goal | Exit measurement |
|---|---|---|
| G1 | On a clean install, `borg search` returns ≥1 relevant result for 80% of a pre-registered query set | Automated test over a ≥50-query benchmark, described in §11 |
| G2 | On a clean install, `borg search` returns ≥5 results (any relevance) for 95% of the benchmark set | Same benchmark |
| G3 | Seed corpus adds ≤ 5 MiB to the wheel uncompressed, ≤ 2 MiB compressed on PyPI | `ls -la` on built wheel |
| G4 | Adding the seed corpus does not break any existing `borg/tests/` test | `pytest borg/tests` green on CI |
| G5 | Every seed pack has a traceable public source and an MIT/Apache-2.0/CC-BY/CC0-compatible license, audited | License manifest committed alongside the corpus |
| G6 | An opt-out flag (`--no-seeds` or `BORG_DISABLE_SEEDS=1`) exists for users who want a pristine cache | CLI help text + test |
| G7 | The fix is visible in a C3 condition replay of P1.1 MiniMax: the per-run "borg returned content" rate rises from 0/30 to ≥25/30 | Replay experiment, §7 |

"Solved" is the *conjunction* of G1 through G7. If any single goal fails, the rollout gate does not open.

### 2.2 Non-goals (explicit)

1. **Making Borg solve SWE-bench tasks.** This doc is about cold-start visibility. The P1.1 floor effect is a different problem (model/harness capability). Fixing cold-start is necessary but not sufficient for a positive agent-level effect.
2. **A recommendation engine.** Retrieval quality beyond "at least one relevant hit" is out of scope; ranking stays `text` mode for MVP.
3. **Replacing `borg observe`.** Auto-observation of the current user's own sessions (see `borg-auto-observe` skill) is *complementary*: seeds give you a floor, observation gives you personalization. Both ship.
4. **Replacing the Borg Wiki.** The wiki (`~/.hermes/guild/wiki/`) is an accumulating compounded knowledge layer; seeds are a cold-start prior. They share a store (§5) but serve different roles.
5. **Fine-tuning or LLM-in-the-loop curation.** Seeds are statically curated text. No runtime LLM calls to build them.
6. **A federated network.** §3(c) is considered and rejected below.
7. **Private data of any kind.** Nothing from `~/.hermes/sessions/`, `~/.claude/`, `~/halford4d/`, chatgpt-export, or any Ted- or Angus-specific content enters the corpus, ever.

---

## 3. Options considered

Ranked by expected value at shipping time (not by novelty).

### Option A — Bundle a curated seed corpus in the wheel

The wheel already ships 17 frontmatter-only skill files under `borg/seeds_data/` via `[tool.setuptools.package-data]` (`pyproject.toml` lines 58–59). Extend this mechanism: add a properly-structured `borg/seeds_data/packs/*.yaml` plus a precomputed `borg/seeds_data/index.json` that `borg.core.search.borg_search` reads on every query, merged with the remote index + local pulls + traces.

- **Pros:** zero network on first run; deterministic; reproducible; works offline; already-precedented by the classifier path in `borg/core/pack_taxonomy.py::_get_skills_dir`; easy to test.
- **Cons:** wheel size grows; seeds are versioned with the binary (update cadence tied to releases); corpus is static per install.
- **Sizing:** 200–500 pack corpus in YAML ≈ 0.5–2 MiB compressed. Well under G3.
- **License:** every source must be permissive (§6). Audit is one-time, replicable.
- **Maintainability:** medium. Re-curation cadence aligned to minor releases (quarterly).

### Option B — First-run wizard that auto-imports from local agent history

On first `borg` invocation, scan `~/.claude/`, `~/.hermes/sessions/`, `~/.codex/`, `~/.cursor/` and offer to import conversations as traces.

- **Pros:** corpus is immediately relevant to *this* user; complementary to `borg-auto-observe`.
- **Cons:** privacy nightmare (those directories contain API keys, private source, client names, NDA'd code); requires a consent dialog, which agent-initiated installs on headless VMs cannot answer; **zero coverage for the cold user this doc exists to solve**; legal exposure if Borg silently ingests NDA'd content; the `borg-auto-observe` skill already covers the warm-user case in the agent's own process, which is the correct privacy boundary.

Worst-of-both-worlds: zero cold-user coverage *and* warm-user privacy risk.

### Option C — Federated fetch on first run from a public `agent-borg-seeds` repo

On first run, `borg` downloads a signed pack bundle from `github.com/bensargotest-sys/agent-borg-seeds/releases/latest/seeds.tar.zst`, verifies a minisign signature, unpacks to `~/.hermes/guild/seeds/`.

- **Pros:** seeds decouple from binary release cadence; updatable without re-releasing `agent-borg`; lower wheel size.
- **Cons:** requires network on first run (CI sandboxes and air-gapped laptops break); introduces a signing key management + rotation story with no current owner; supply-chain dependency (the seeds repo becomes a CDN that must stay up); adds latency to first `borg search`; PyPI's offline-install guarantee is gone; we do not know which bundle a given user actually has.

### Option D — LLM-synthesized cold-start packs from a curated prompt corpus

Generate 500 packs by prompting an LLM against a curated prompt list. Commit the output.

- **Pros:** fast to prototype; covers long-tail problem classes cheaply.
- **Cons:** synthetic packs lie confidently — every wrong pack misleads a downstream agent (negative EV); license status of LLM output is contested; fails the HN/PhD/SWE-L6 review bar because critics will correctly call it slop; costs real money per re-curation ($10–$100 per batch).

### Option E — Do nothing, document the issue

- **Pros:** zero engineering cost; honest.
- **Cons:** zero effect on adoption. The P1.1 report already documents the issue honestly and that did not fix anything.

### Option Z — Hybrid: (A) now, (C) as an optional update channel later

Ship bundled seeds in the wheel for offline determinism. Add an opt-in `borg seeds update` command that can pull newer bundles from a signed repo, *after* the bundled baseline is proven.

---

## 4. Recommendation

**Option A, with a reserved upgrade path to Option Z.**

Reasoning (devil's-advocate passed):

1. **Option A is the only option that ships a working product to an offline, cold, headless install on the first `borg search` call.** B needs a human; C needs network; D needs a leap of faith; E is the status quo failure.
2. **The infrastructure already exists.** `pyproject.toml` declares `borg/seeds_data/**` as package-data; `pack_taxonomy._get_skills_dir()` resolves seed files from an installed wheel (`borg/core/pack_taxonomy.py` lines 302–326); the classifier has consumed seeds from that location since v3.2.3. The *gap* is that `borg.core.search.borg_search` does not read from it. Closing that gap is a one-function change, not a new subsystem.
3. **Option Z is the correct evolution.** Ship A first; add the federated update channel (C) as a second-phase enhancement behind an explicit `borg seeds update` command, once A is proven and a signing story exists.
4. **Accepted trade-off:** wheel size grows by ≤ 5 MiB; seed freshness is tied to release cadence (quarterly). Both are cheap prices for determinism and offline install.

Devil's advocate: "Why not rely on the remote `bensargotest-sys/guild-packs/index.json`?" — Because `_fetch_index()` silently returns `{"packs": []}` on any network error, and the index as of 2026-04-09 contains fewer than 30 packs, many test-scaffolded. The remote index is a manifest, not a corpus.

---

## 5. Detailed design (Option A)

### 5.1 Data sources and storage format

Seed packs are authored from the sources in §6. Every seed pack is a small YAML file of the existing `workflow_pack` schema (`borg/core/schema.py::parse_workflow_pack`). One pack = one problem class + 3–7 phases. No new schema.

Storage: **YAML files under `borg/seeds_data/packs/` plus a precomputed `borg/seeds_data/index.json`** mirroring the shape of the remote `guild-packs` index. Human-diffable, grep-able, trivially tested. Size for 500 packs: ~1.5 MiB. A SQLite FTS5 bundle was considered and rejected: the existing search path is an in-memory scan over `all_packs` (`borg/core/search.py` lines 270–280), and a 500-item scan is sub-millisecond. Revisit SQLite at N > 2,000.

### 5.3 Sizing — how many seed packs is enough?

Model: assume the user's first query is drawn from a Zipf-distributed vocabulary of common software-engineering query tokens (Django, Flask, pytest, ImportError, TypeError, migration, async, test, …). Empirically, the top 200 query tokens cover the bulk of common dev-stack vocabulary (StackOverflow tag frequencies follow a power law with α ≈ 1.0–1.2 in the software-engineering subsample; any StackOverflow data-dump report confirms the shape).

Let *K* be the number of seed packs and let each pack cover a disjoint problem class mapped to ~5 query tokens (name, problem_class, 3 phase names). Under a conservative independent-coverage model:

- P(query ∈ covered_tokens) ≈ 1 − (1 − p_cov)^K where p_cov is the per-pack coverage of the query vocabulary.
- Targeting 80% coverage (G1) at p_cov ≈ 0.01 (1% per pack) requires K ≈ 160.
- Targeting 95% coverage (G2) at the same p_cov requires K ≈ 300.
- Rounding up to account for correlated overlap (redundant packs on "null pointer"), target **K = 500 seed packs** for the first release.

This is a power-style analysis, not a power analysis in the Neyman-Pearson sense — there is no hypothesis test. It is a back-of-envelope upper bound on the corpus size needed to make G1/G2 plausible. The real validation happens in §7 (prototype) and §11 (acceptance tests).

**Budget gate:** if curating 500 packs would cost > 40 engineer-hours, fall back to K = 200 for v1 and re-curate in v2. See §12.

### 5.4 Integration with `borg.storage` and `borg.core.search`

Exact files to modify (all under `/root/hermes-workspace/borg/`):

1. **`borg/core/uri.py`** — add `SEEDS_DIR = Path(borg.__file__).parent / "seeds_data" / "packs"` and a helper `_load_seed_index() -> dict` that returns the same shape as `_fetch_index()` but reads from `borg/seeds_data/index.json`. Memoize at import; no TTL (seeds are immutable per install). Every returned pack gets `source="seed"`, `tier="seed"`.
2. **`borg/core/search.py`** — in `borg_search()`, after `all_packs = list(index.get("packs", []))`, extend with `_load_seed_index().get("packs", [])`. The existing dedup at lines 151–182 already handles overlap between remote, local, and (now) seed sources.
3. **`borg/db/store.py`** — **no change**. `AgentStore` is for user-observed data; seeds are read-only and must not pollute `guild.db`. Deliberate non-change.
4. **`borg/cli.py`** — in `_cmd_search()` (line 61), add a `(seed)` suffix on seed rows. Accept `--no-seeds` on the `search` subparser at line 1043; plumb through.
5. **`pyproject.toml`** — **no change**. The existing `package-data` glob `"seeds_data/**"` (line 59) already captures the new `packs/` subdirectory.

### 5.5 CLI UX

- `borg search <query>` transparently includes seed hits, merged with remote/local/trace via the existing dedup path. Default behavior.
- `borg search <query> --no-seeds` excludes them. Also honored via `BORG_DISABLE_SEEDS=1`.
- `borg list --seeds` — lists only seed packs (reuse `_cmd_search` with empty query + `source="seed"` filter).
- `borg pull` on a seed URI copies it into `~/.hermes/guild/<pack-name>/pack.yaml`; the dedup path then prefers the local copy. Clear "promote and edit" story.
- The `search` output gains a `(seed)` suffix on seed rows so users can distinguish.

### 5.6 Privacy, versioning, deletion

- **Privacy:** seeds are public and author-independent by construction. No user data ever enters them. They are read-only under `site-packages/borg/seeds_data/`, never under `~/.hermes/`.
- **Versioning:** seeds ship with the wheel. `borg/seeds_data/VERSION` is a line of the form `seeds-1.0.0-2026-04-09` which `borg --version` (`cli.py` line 1039) prints alongside the package version. Release cadence matches `agent-borg` (quarterly). Upgrade path to Option Z (deferred): a future `borg seeds update` subcommand fetches a signed bundle from `github.com/bensargotest-sys/agent-borg-seeds/releases/latest`, unpacks to `~/.hermes/guild/seeds-update/`, which `_load_seed_index()` prefers over wheel seeds. Not in scope for v1.
- **Deletion / overwrite:** seeds cannot be deleted via CLI (they live in the wheel); use `--no-seeds`. If a user pulls or authors a pack with the same ID as a seed, the existing dedup in `borg/core/search.py` lines 151–182 prefers the local copy; no behavioral change.

### 5.7 Relationship to the Borg Wiki and to `borg-auto-observe`

Three layers, three purposes, one storage root (`~/.hermes/guild/` for the user-accumulated layers; `site-packages/borg/seeds_data/` for the immutable prior):

| Layer | Lifetime | Source | Example |
|---|---|---|---|
| Seed corpus (this doc) | Baked into wheel, upgraded quarterly | Public curation (§6) | `null-pointer-chain.md` |
| Auto-observed traces | User-local, per-session | The running agent's own work (`borg-auto-observe` skill) | `trace:abc123` |
| Borg Wiki | User-local, auto-compounded | Structured extraction from pack executions (`borg-wiki-usage` skill) | `packs/systematic-debugging` article |

`borg_search` already queries layers 2 and 3 (v3.2.4) via `TraceMatcher` and wiki FTS. This design adds layer 1. All three merge at the same result list. The wiki and the seed corpus do *not* share a SQLite database: the wiki lives at `~/.hermes/guild/wiki/` with its own FTS5 index; seeds stay in the wheel as static files. Sharing a DB would complicate the read-only / read-write boundary and is not worth the coupling.

---

## 6. Seed corpus curation plan

### 6.1 Candidate sources (PUBLIC, permissive only)

| Source | License | Usable for | Estimated yield |
|---|---|---|---|
| SWE-bench Verified gold patches (princeton-nlp/SWE-bench_Verified) | MIT (per dataset README) | Problem-class → phases extraction | ~200 candidate packs, watch task-selection bias |
| GitHub Advisories DB (github/advisory-database) | CC0 (per repo LICENSE) | Security-issue packs | ~50–100 packs |
| CPython issues labeled "type-bug" with merged fixes (github.com/python/cpython) | PSF-2.0 (permissive) | Core language bug packs | ~50 packs |
| Django release notes (djangoproject.com/weblog) | BSD-3-Clause | Framework-upgrade packs | ~30 packs |
| Flask changelog (github.com/pallets/flask/blob/main/CHANGES.rst) | BSD-3-Clause | Framework-upgrade packs | ~20 packs |
| SQLAlchemy changelog (github.com/sqlalchemy/sqlalchemy/tree/main/doc/build/changelog) | MIT | Query/session-management packs | ~30 packs |
| MDN error references (developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors) | CC-BY-SA 2.5 | JS error packs (attribution required) | ~40 packs |
| Python docs error index (docs.python.org/3/library/exceptions.html) | PSF-2.0 | Python exception packs | ~30 packs |

**Explicitly forbidden sources** (from the task directive and from privacy audit):
- `/root/hermes-workspace/halford4d/` — H4D-private
- `/root/.hermes/sessions/` — private user sessions
- `chatgpt-export/` conversations — private
- Any Angus- or Ted-specific content
- StackOverflow question/answer bodies — CC-BY-SA 4.0 is share-alike; bundling would force the entire wheel into CC-BY-SA. Use SO **only** for tag-frequency statistics in §5.3, not for pack text.

### 6.2 Deduplication strategy

1. Normalize pack names and problem classes to `kebab-case`.
2. Compute a MinHash signature over the full YAML text per pack.
3. Drop any pack whose Jaccard similarity to an already-accepted pack exceeds 0.8.
4. Manual review on any pair with similarity in [0.6, 0.8].

Target: ≤ 5% redundancy after dedup.

### 6.3 Quality filter

Two-pass:

1. **Automated pass:** every pack must (a) parse via `borg.core.schema.parse_workflow_pack`, (b) have ≥ 3 phases, (c) have non-empty `problem_class`, (d) pass `borg.core.safety.scan_pack_safety`. Packs failing any check are dropped.
2. **Human review pass:** one engineer spot-checks 10% of the corpus (50 of 500) for "would this actually help a junior engineer?". If the spot-check rejection rate exceeds 20%, the whole batch is reclassified as draft and re-curated before release.

No LLM is used in the loop. Seeds are authored from public text; the pipeline is deterministic.

### 6.4 License audit

Every pack in `borg/seeds_data/packs/` has a sibling `.license.json`:

```
{"source_url": "...", "license": "BSD-3-Clause", "attribution": "Django Software Foundation",
 "retrieved_at": "2026-04-15", "sha256_of_source": "..."}
```

A single `borg/seeds_data/LICENSE_AUDIT.md` lists the full table. CI checks that every `packs/*.yaml` has a matching `.license.json` and that the license is on an allowlist (`MIT, Apache-2.0, BSD-3-Clause, BSD-2-Clause, CC0-1.0, CC-BY-4.0, PSF-2.0`). Any CC-BY-SA source is rejected outright.

---

## 7. Prototype plan (smallest possible test)

**Goal:** answer in ≤ 2 days whether cold-start really is the dominant factor by running a single new condition C3 against the P1.1 baseline.

| Step | Scope | Exit criterion | Budget |
|---|---|---|---|
| 1 | Pick one source: **SWE-bench Verified gold patches**, Django subset | 50 seed packs extracted and committed to a branch `seeds/v0-prototype` | 4 eng-hours, $0 |
| 2 | Wire the minimal `_load_seed_index` path from §5.4 behind an env var `BORG_ENABLE_SEEDS=1` | `pytest borg/tests` green with and without the env var | 2 eng-hours, $0 |
| 3 | Replay P1.1 MiniMax with a new **C3_borg_seeded_public** condition, 15 tasks × 1 run = 15 runs | JSONL + per-run "borg_search returned ≥ 1 match" rate | 1 wall-hour, $1.50 (15 × $0.001 × 100 tokens × ~20 iter) |
| 4 | Compare C3's "borg returned content" rate against C1/C2's 0/30 | Primary: ≥ 12/15 runs return ≥ 1 match. Secondary: task pass rate on C3 ≥ C1 within Clopper-Pearson bounds (likely still 0 due to floor effect, that is acceptable for this prototype) | $0 |

Total prototype cost: **≤ $5** and **< 1 day**. If C3 fails to show ≥ 12/15 runs with content, the design is wrong and this doc is revised before any full curation spend.

Exit criteria for prototype success → proceed to full curation: "borg returned content rate" climbs from 0/30 (C1+C2 combined in P1.1) to ≥ 0.8 in C3.

---

## 8. Rollout plan

| Phase | Gate | Action | User impact |
|---|---|---|---|
| 0 | Prototype ✓ (§7) | Merge `seeds/v0-prototype` behind `BORG_ENABLE_SEEDS=1`, tag `3.2.5-alpha1` on PyPI TestPyPI only | None (alpha-only) |
| 1 | Full curation to K=500 complete, license audit ✓ | Flip default to `BORG_ENABLE_SEEDS=1`, release `3.3.0` to PyPI | First-time users see seed hits |
| 2 | 2 weeks of production telemetry (download count delta, GitHub issue volume) | Decide: keep, roll back, or iterate | — |
| 3 | If stable, deprecate `BORG_DISABLE_SEEDS` as the non-default and leave it as an opt-out only | — | Seeds become implicit, indistinguishable from the rest of the index |

Migration path: existing users who already have a `~/.hermes/guild/` directory keep it. The dedup path prefers local over seed (§5.8), so their existing work is never hidden. No database migration. No file-format change. The old `seeds_data/*.md` classifier files stay where they are; this design *adds* a `seeds_data/packs/*.yaml` + `index.json` sibling directory.

Feature flag: `BORG_DISABLE_SEEDS=1` (env) and `--no-seeds` (CLI) remain supported indefinitely.

---

## 9. Risks and mitigations

| Risk | Sev | Mitigation |
|---|---|---|
| R1. A bundled pack is wrong and misleads agents | High | Two-pass quality filter (§6.3); every seed tagged `tier="seed"`, `confidence="community"` so ranking deprioritizes vs. user-validated local packs |
| R2. License audit misses an SA source, poisoning the wheel | High | Allowlist-only CI check (§6.4); unrecognized license fails the build |
| R3. Wheel size balloons past 5 MiB | Med | Minify YAML whitespace; hard CI gate on wheel size |
| R4. Seeds become stale (Django 6 lands) | Med | Quarterly refresh; defer >1-release freshness to Option Z |
| R5. User trust: "this is generic advice" | Med | `(seed)` suffix visible in `borg search`; README explains the three layers (§5.7) |
| R6. Curation exceeds 40-hour budget | Med | Fallback to K=200 for v1, iterate in v2 (§5.3) |
| R7. Someone slips a synthetic LLM-generated pack into seeds | Med | CI: every pack must have a `.license.json` with a `source_url` that resolves |
| R8. Search path latency regresses | Low | `_load_seed_index()` memoized at import; 500-item scan is sub-ms |
| R9. Adoption rises but quality per trace drops | Low | Orthogonal; handled by wiki + reputation layers |

---

## 10. Alternatives rejected (explicit)

1. **Option B (first-run wizard scanning local histories):** rejected for privacy and for zero coverage on the cold-user case that this doc exists to solve.
2. **Option C alone (federated fetch only):** rejected because it breaks offline install, adds a signing key management story with no current owner, and removes PyPI's reproducibility guarantee. Kept as a phase-2 optional upgrade path under Option Z.
3. **Option D (LLM-synthesized seed packs):** rejected because synthetic packs lie confidently, the license status of LLM output is contested, and it fails the HN/PhD/SWE-L6 review bar.
4. **Option E (do nothing):** rejected because P1.1 already documented the problem honestly and that did not fix adoption.
5. **Writing seeds directly into `~/.hermes/guild/guild.db` on first run:** rejected because it mixes a read-only prior with a read-write user store, complicates deletion semantics, and turns seed updates into database migrations.
6. **Putting seeds on PyPI as a separate `agent-borg-seeds` package:** rejected for the prototype because it doubles the release cadence and complicates offline install. Revisit at K > 2,000 if wheel size becomes a problem.

---

## 11. Acceptance tests (pytest specs)

All tests live under `borg/tests/test_seed_corpus.py` (new file). Named specs — pseudocode, not implementation:

1. `test_seed_index_loads_from_wheel` — given clean `~/.hermes/guild`, `borg.core.uri._load_seed_index()` returns a dict with `packs >= 200`, every pack has `source=="seed"` and `tier=="seed"`.
2. `test_borg_search_returns_seed_hits_on_empty_store` — given `HOME=tmp_home` (empty) and no network, `borg_search("django migration")` returns `success=True` with ≥ 1 match, at least one has `source=="seed"`.
3. `test_cold_start_benchmark_80_percent` — over a pre-registered 50-query fixture, ≥ 40/50 queries return ≥ 1 relevant match (token overlap with name+problem_class).
4. `test_cold_start_benchmark_5_hits_95_percent` — same fixture, `len(matches) >= 5` for ≥ 47/50.
5. `test_no_seeds_flag_disables_seeds` — with `BORG_DISABLE_SEEDS=1`, no match has `source=="seed"`.
6. `test_license_audit_completeness` — every `packs/*.yaml` has a matching `*.license.json`, every license is on the allowlist.
7. `test_local_pack_shadows_seed_pack` — given a seed pack and a local pack with the same ID, the local pack appears first and the seed does not duplicate.
8. `test_wheel_size_under_budget` — `python -m build --wheel` then assert `size < 10 * 1024 * 1024`.
9. `test_seed_packs_parse` — every seed YAML passes `borg.core.schema.parse_workflow_pack` and `borg.core.safety.scan_pack_safety`.
10. `test_seed_trace_wiki_merge` — seeds loaded + 1 trace + 1 wiki article on the same topic: all three appear with distinct `source` values.

These tests are the definition of G1, G2, G4, G6, and the license portion of G5.

---

## 12. Estimated effort and cost

| Item | Effort (eng-hours) | Dollars | Notes |
|---|---|---|---|
| Prototype: 50-pack SWE-bench slice + wiring + C3 replay | 8 | $5 | §7 |
| Full curation: 500 packs across 6 sources, with license audit | 32 | $0 | Mechanical extraction; no LLM |
| Integration code: `_load_seed_index`, search path merge, CLI flags | 6 | $0 | §5.4 |
| Test suite: 10 pytest tests + benchmark fixture | 6 | $0 | §11 |
| Release mechanics: changelog, README, version bump | 2 | $0 | — |
| C3 replay + statistics + writeup | 4 | $2 | Optional second pass |
| Contingency (20%) | 12 | $2 | — |
| **Total** | **~70 eng-hours** | **~$10** | Well under any reasonable budget |

Optional phase 2 (Option Z federated update channel): estimated 40 additional eng-hours + one signing key story. Out of scope for this doc.

---

## 13. Open questions (resolve in review)

1. Ship seeds in v3.3.0 or back-port to v3.2.5? Recommend v3.3.0 — a 500-pack corpus is a minor-version event.
2. `borg/seeds_data/packs/` or top-level `seeds/`? Recommend `borg/seeds_data/packs/` — the classifier path already resolves that root.
3. Should `tier="seed"` rank above or below `tier="community"`? Recommend below community, above nothing. Seeds are a floor, not a ceiling.

---

## 14. TL;DR

Borg's cold-start failure is a packaging problem, not an algorithmic one. The infrastructure to ship seed data in the wheel already exists (`borg/seeds_data/` is declared in `pyproject.toml` and resolved by `pack_taxonomy._get_skills_dir`); the bug is that `borg.core.search.borg_search` never reads from it. This doc proposes a 500-pack curated corpus from six public, permissively-licensed sources, stored as YAML under `borg/seeds_data/packs/` with a precomputed `index.json`, merged into the existing search path, preferred below local packs via existing dedup, opt-out via `--no-seeds`, complementary to `borg-auto-observe` and the Borg Wiki. A 50-pack prototype proves the hypothesis in under a day for under $5; full rollout is ~70 eng-hours and ~$10. Federated updates deferred to phase 2 behind a signing story. Local-history scan, LLM synthesis, and do-nothing are explicitly rejected. Acceptance gate: 80% of a 50-query benchmark returns ≥1 relevant hit; 95% returns ≥5 hits.
