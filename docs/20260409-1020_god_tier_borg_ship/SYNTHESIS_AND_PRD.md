# agent-borg v3.3.0 — Synthesis and PRD

| Field | Value |
|---|---|
| Spec ID | SYNTHESIS_AND_PRD_v3.3.0 |
| Author | Chief Architect (Hermes orchestrator) |
| Date | 2026-04-09 |
| Status | For AB approval |
| Quality bar | Google SWE-L6 / PhD committee / HN front page |

---

## Prefatory Note

This document merges findings from three parallel teams (RED adversarial review, BLUE architecture + PRD spec, GREEN empirical grounding) into a single action plan and Product Requirements Document for agent-borg v3.3.0. It resolves all known conflicts between team inputs, produces a revised roadmap with real estimates, and answers all 10 questions from the Context Dossier.

**Key corrections vs. prior drafts:**
- Day 2 is 28 hours (not 22h): wiring is 8h (not 6h), curation is 20-25h serial (not 12h)
- Day 3 is 67 hours of curation wave (serial, not parallelizable)
- SB-05 added: `borg autopilot` cli.py:973 has the same `"command": "python"` bug as SB-01
- `_load_seed_index()` is a greenfield subsystem: it must be built, not wired from existing code
- Existing `borg/seeds_data/*.md` are SKILL-format, not `workflow_pack` YAML — they cannot be used as-is for search
- K=500 is feasible: GREEN confirmed ~30% of the 5MiB budget is used at K=500

---

## 1. What is agent-borg?

agent-borg is a federated knowledge exchange for AI agents: a CLI and MCP server that ships a pack/tip/workflow registry with local trace caching, enabling agents to share and retrieve reproducible debugging workflows across a team.

---

## 2. What's broken in v3.2.4?

### Ship Blockers (4 + 1 confirmed)

**SB-01 — `setup-claude` emits `"command": "python"` (CRITICAL)**
`borg/integrations/setup_claude.py` hardcodes `"command": "python"`. Ubuntu 24, macOS Python.org installer, and pyenv ship only `python3`. Claude Code spawns `python`, gets ENOENT, and silently fails — every `borg_*` tool is invisible. The fix is to prefer `shutil.which("borg-mcp")` and fall back to `sys.executable`. Effort: 30 min.

**SB-02 — `docs/EXTERNAL_TESTER_GUIDE.md` has 49 stale `guildpacks` hits (CRITICAL)**
Every command in the file is wrong (`pip install guild-packs` → 404). Users conclude the project is dead. Fix: delete the file and add `docs/TRYING_BORG.md` with correct names. Effort: 1 hr.

**SB-03 — `borg generate --format claude` fails with `invalid choice` (CRITICAL)**
README documents `--format claude` and `--format cursor`. Argparse choices are `claude-md` and `cursorrules`. User copies README verbatim and gets an immediate failure. Fix: rename argparse choices to `{cursor, cline, claude, windsurf, all}` with backward-compatible aliases. Effort: 45 min.

**SB-04 — `pyproject.toml` URLs point at `guild-packs` (CRITICAL)**
Homepage/Repository/Documentation point at `https://github.com/bensargotest-sys/guild-packs`. PyPI homepage link leads to wrong repo. Fix: update all URLs to `agent-borg`, grep entire file for any remaining stale naming. Effort: 15 min.

**SB-05 — `borg autopilot` cli.py:973 has the same `"command": "python"` bug as SB-01 (CRITICAL, RED addition)**
`borg/cli.py` line 973 inside `_cmd_autopilot()` builds an MCP config entry with `"command": "python"`. This is the same failure mode as SB-01. Users who run `borg autopilot` get the identical 120-second hang. Fix: same one-line fix as SB-01. Effort: 5 min.

### Cold-Start Gap (HIGH, separate track)

`borg/seeds_data/` has 17 frontmatter skill files (104 KiB) shipped in the wheel since before 3.2.4, but `_load_seed_index()` does not exist — the integration path is unimplemented. `borg_search()` in `search.py` has no seed loading code. Existing seeds are SKILL-format (YAML frontmatter + markdown body), incompatible with `workflow_pack` YAML schema that `borg_search` consumes. Every cold install returns `No packs found.` on any query.

---

## 3. What does v3.3.0 ship?

Each feature has a binary pass/fail criterion:

| Feature | Binary Pass/Fail | Measurement |
|---|---|---|
| **SB-01 fix** | `borg setup-claude` produces config with valid path that exists | Inspect config JSON, verify path exists |
| **SB-02 fix** | `grep -ri 'guild-packs\|guildpacks\|guild-mcp' docs/` returns 0 hits outside audit artifacts | Automated grep |
| **SB-03 fix** | All four `borg generate <pack> --format {cursor, cline, claude, windsurf}` exit 0 | CI test |
| **SB-04 fix** | `pip show agent-borg | grep -i url` shows zero `guild-packs` substrings | CI test |
| **SB-05 fix** | `borg autopilot` produces valid MCP config with existing interpreter path | Inspect config JSON |
| **G1 cold-start** | >= 40/50 queries on 50-query benchmark return >= 1 relevant result | `test_cold_start_benchmark_80_percent` |
| **G2 cold-start** | >= 47/50 queries on 50-query benchmark return >= 5 results | `test_cold_start_benchmark_5_hits_95_percent` |
| **G3 wheel size** | Seed corpus adds <= 5 MiB to wheel (uncompressed) | `test_wheel_size_under_budget` (bound tightened to 5 MiB, not 10 MiB) |
| **G4 regression** | `pytest borg/tests/` 100% pass | `pytest borg/tests/ --tb=short` |
| **G5 license** | Every `packs/*.yaml` has allowlist license + resolvable source_url + sibling `.license.json` | `test_license_audit_completeness` |
| **G6 opt-out** | `borg search x --no-seeds` AND `BORG_DISABLE_SEEDS=1 borg search x` both return 0 seed hits | `test_no_seeds_flag_disables_seeds` |
| **G7 C3 replay** | C3 replay (15 runs x MiniMax-M2.7) shows >= 12/15 runs returning >= 1 seed match | C3 replay JSONL + `test_c3_content_rate` |
| **HIGH-02 guild://** | All CLI help strings say `borg://`; `guild://` URIs still resolve | Grep + manual test |
| **HIGH-03 feedback-v3** | `borg feedback-v3 --success garbage` exits 1 with error | CLI test |
| **HIGH-04 debug exit** | `borg debug 'zzzzzzzzz'` exits 1 (not 0) | CLI test |
| **HIGH-05 borg_suggest** | `borg_suggest` with valid trigger returns non-empty OR is removed from tools/list | MCP test |
| **HIGH-06 rename** | `borg/seeds_data/guild-autopilot` → `borg-autopilot` with content updated | `git mv` + grep |

**All of the above are a conjunction gate: ALL must PASS for the v3.3.0 release tag.**

---

## 4. How do we know it worked? (Eval Plan)

### Instruments

| Instrument | What it measures | When |
|---|---|---|
| Ship-gate shell script | SB-01 through SB-05 acceptance | End of Day 1 |
| `borg/tests/test_seed_corpus.py` (10 pytest tests) | G1, G2, G3, G5, G6 compliance | After Phase 1 (seed infrastructure) |
| 50-query cold-start benchmark fixture | G1, G2 | Phase 4 acceptance testing |
| C3 replay JSONL logs | G7 | Within 2 hours of Phase 2.3 start |
| `pytest borg/tests/ --tb=short -q` | G4 regression gate | After every phase |
| `pip show agent-borg` | PyPI metadata cleanliness (SB-04) | After PyPI upload |
| Manual Ubuntu 24 test (no `python` symlink) | SB-01 effectiveness | After SB-01 fix |

### Who measures

- **Implementing engineer**: runs pytest suite, benchmark fixture, ship-gate script after each phase
- **Hermes orchestrator**: runs final ship-gate before PyPI upload
- **External reviewer (optional)**: manual Ubuntu 24 + macOS Python.org test for SB-01

### 50-query benchmark pre-registration

The benchmark fixture is committed to `borg/tests/fixtures/cold_start_queries.json` with external pre-registration as a GitHub gist before Phase 4. Query distribution: 12 Django errors, 15 Python stdlib errors, 8 Git/Docker/bash, 10 framework-specific, 5 edge cases. Pre-registration prevents post-hoc query selection bias.

### Statistical rigor

- No statistical claims from the 50-query benchmark: it is a binary acceptance test, not a hypothesis test
- G7 uses Clopper-Pearson 95% CIs for "borg returned content" rate (same method as P1.1)
- Pre-registered decision rule: `>= 12/15 runs return >= 1 match` is the primary threshold
- No p-hacking: queries are fixed before the test runs

---

## 5. What's NOT in scope?

Explicitly out of scope for v3.3.0:

1. **Embedding-based / semantic search**: `sentence-transformers>=2.2.0` is only loaded under `agent-borg[embeddings]`. The text search path is the default and must work without embeddings. Vector similarity is an optional enhancement for v3.4.0+.
2. **Thompson sampling / learning-to-rank**: requires behavioral data from `feedback-v3` which is not yet producing sufficient signals.
3. **Cross-model evaluation (P2 Sonnet)**: structurally blocked on OAuth token (P2_OAUTH_TOOLUSE_429_FINDING.md). Deferred until fresh Anthropic key is provisioned or MiniMax-M2.7 pivot is authorized.
4. **Community pack curation via federated fetch**: Option C of the cold-start design. Requires network on first run, breaks CI/air-gapped installs, and has no signing key story.
5. **LLM-synthesized packs (Option D)**: fails the HN/PhD review bar, contested license status.
6. **Independent seed pack versioning**: tied to minor release cadence (quarterly). Independent versioning adds release management overhead.
7. **SWE-bench AGPL license audit for v3.3.0**: deferred to curation protocol (v3.4.0). Must add per-file license check before using SWE-bench tasks as seed sources.
8. **`tier="seed"` in reputation engine calculations**: seeds are excluded from reputation calculations (not authored by agents).
9. **`borg_suggest` full implementation**: investigate whether it requires `agent_context` param; fix or remove from `tools/list`.
10. **`borg pull` happy-path network test**: A6 in GREEN analysis, add to test suite but not a release gate.

---

## 6. What are the failure modes?

| ID | Feature | Failure Mode | Likelihood | Severity | Detection | Mitigation |
|---|---|---|---|---|---|---|
| F1 | Seed corpus | Corrupted `index.json` causes `_load_seed_index()` to return `{}`; all searches return empty | LOW | HIGH | Phase 1 test `test_seed_index_loads_from_wheel` | Function returns `{"packs": []}` on JSON parse error, never raises |
| F2 | Seed corpus | One seed pack has non-allowlist license (CC-BY-SA slipped through) | MEDIUM | CRITICAL | CI license audit (every pack requires `.license.json` on allowlist) | Allowlist CI gate; rejected packs not included in index.json |
| F3 | Seed corpus | Seed pack actively misleads agent (wrong resolution for real error class) | MEDIUM | HIGH | Phase 0 prototype + C3 replay; spot-check 10% of corpus | `tier="seed"` and `source="seed"` deprioritize in ranking; `--no-seeds` opt-out |
| F4 | Seed corpus | Wheel size exceeds 5 MiB (G3 violation) | LOW | HIGH | CI `test_wheel_size_under_budget` | Minify YAML whitespace; fall back to K=200 if budget exceeded |
| F5 | Seed corpus | PyPI yanked wheel after bad seed pack discovered | LOW | HIGH | PyPI page monitoring; user bug reports | Emergency v3.3.1 patch; `BORG_DISABLE_SEEDS=1` as temporary mitigation |
| F6 | Search integration | `_load_seed_index()` not called (exception in code path) | LOW | CRITICAL | Phase 1 test `test_borg_search_returns_seed_hits_on_empty_store` | Returns `{"packs": []}` on any exception |
| F7 | Search integration | Duplicate pack IDs between seed and local (local not preferred) | LOW | MEDIUM | Phase 1 test `test_local_pack_shadows_seed_pack` | Existing dedup logic prefers local; explicit test covers |
| F8 | CLI | `--no-seeds` flag plumbed incorrectly; seeds still appear | LOW | MEDIUM | Phase 1 test `test_no_seeds_flag_disables_seeds` | Explicit test covers both env var and flag |
| F9 | Ship blockers | SB-01/SB-05 fix still fails on some Python installs | MEDIUM | HIGH | Manual test on Ubuntu 24, macOS Python.org, pyenv | `shutil.which("borg-mcp")` first, then `sys.executable` as fallback |
| F10 | Ship blockers | SB-03 aliases don't cover all README examples | LOW | MEDIUM | README example commands tested in CI | Full coverage of README examples; backward-compatible aliases |
| F11 | C3 prototype | C3 prototype fails G7 (< 12/15 "borg returned content") | MEDIUM | HIGH | C3 replay metrics | Pause and redesign before full curation spend |
| F12 | Trace surfacing | TraceMatcher fails on malformed `traces.db` | LOW | LOW | Phase 1 test; try/except in search.py | Exception caught and logged; search still returns results |
| F13 | Reputation engine | ReputationEngine raises exception during re-ranking | LOW | LOW | `search.py` broad try/except | Reputation is optional; search continues with text-order ranking |
| F14 | MCP server | `borg-mcp` entry point broken on installs without `python` symlink | HIGH | CRITICAL | SB-01 | `borg-mcp` uses `sys.executable` directly, not `python` string |
| F15 | Cold-start wiring | `_load_seed_index()` silently returns empty when seeds dir missing | MEDIUM | HIGH | `_load_seed_index()` must raise if seeds dir missing but feature requested | Return empty only if `--no-seeds` set; raise explicitly otherwise |
| F16 | Seed corpus | Seed pack ID collision with future community pack | LOW | LOW | Dedup policy documented | Local > Remote > Seed priority; documented in ARCHITECTURE_SPEC |

---

## 7. What's the rollout plan?

### Phase 0 — Ship Blockers (Day 1, 2.5 hours)

| # | Task | Effort | Exit |
|---|---|---|---|
| 0.1 | SB-01: `setup-claude` uses `sys.executable`/`shutil.which("borg-mcp")` | 30 min | Config JSON has valid path |
| 0.2 | SB-05: `borg autopilot` cli.py:973 uses `sys.executable` (same fix) | 5 min | Config JSON has valid path |
| 0.3 | SB-04: `pyproject.toml` URLs + full-file grep | 30 min | `pip show agent-borg` clean |
| 0.4 | SB-03: `--format` aliases | 45 min | All 4 format commands exit 0 |
| 0.5 | SB-02: delete `EXTERNAL_TESTER_GUIDE.md`, create `TRYING_BORG.md` | 1 hr | Zero `guild` hits in `docs/` |
| 0.6 | Remove vestigial `SKILLS_DIR` from `search.py` | 5 min | Code cleanup |
| 0.7 | Link or remove README test badge "1708 passed" | 10 min | No stale badge |
| 0.8 | Run ship-gate script | 15 min | Exit 0 |

**Day 1 wall clock: ~3 hours**

### Phase 1 — Seed Infrastructure (Day 2, 8 hours)

| # | Task | Effort | Dependency | Exit |
|---|---|---|---|---|
| 1.1 | Create `borg/seeds_data/index.json` over 17 existing `.md` files; add `SEEDS_DIR` + `_load_seed_index()` to `borg/core/uri.py` | 3 hr | None | `_load_seed_index()` returns `pack_count >= 17`; memoized; `BORG_DISABLE_SEEDS=1` returns empty |
| 1.2 | Wire `_load_seed_index()` into `search.py` after `_fetch_index()`; extend dedup for `source="seed"` | 2 hr | 1.1 | Seed packs appear in search results on empty HOME |
| 1.3 | Add `--no-seeds` CLI flag + `BORG_DISABLE_SEEDS=1` env var | 1 hr | 1.2 | Both flag and env var return 0 seed hits |
| 1.4 | Add `(seed)` suffix to seed rows in output; update `borg list --seeds` | 1 hr | 1.2 | Seed vs local vs remote distinguished in output |
| 1.5 | Document dedup policy: local > remote > seed | 1 hr | 1.2 | Policy documented before cold-start ships |

**Day 2 seed infrastructure wall clock: ~8 hours**

### Phase 2 — C3 Prototype + Initial Curation (Day 2 continued + Day 3, 28 hours total)

| # | Task | Effort | Dependency | Exit |
|---|---|---|---|---|
| 2.1 | Extract 50 SWE-bench gold patches → 50 `workflow_pack` YAML files | 6 hr | 1.1 | 50 YAML files conforming to schema; every pack has valid `.license.json` |
| 2.2 | Build `index.json` over 50 packs; verify `pack_count=50` | 1 hr | 2.1 | `python -c "from borg.core.uri import _load_seed_index; print(_load_seed_index()['pack_count'])"` |
| 2.3 | C3 replay: 15 runs x 20 iterations, MiniMax-M2.7 | 2 hr, ~$0.30 | 2.2 | Primary: >= 12/15 runs return >= 1 seed match |
| 2.4a | If C3 passes: full curation to K=200 packs (6 public sources) | 20-25 hr | 2.3 | 200 packs; every pack has allowlist license + source_url + `.license.json`; corpus size <= 5 MiB |
| 2.4b | If C3 fails: pause, redesign, report findings | — | 2.3 | Architecture review before continuing |

**Day 2 total: 8h (Phase 1) + 6h (Phase 2 wiring) + ~6h (initial curation) = 20h**
**Day 3 curation wave: ~25-67h (K=200 to K=500, serial at 15-20 min/pack)**

### Phase 3 — HIGH items batch (Day 2, 4 hours, parallel with Phase 2)

| # | Task | Effort | Exit |
|---|---|---|---|
| 3.1 | HIGH-02: `guild://` → `borg://` in CLI help strings | 30 min | Help strings say `borg://` |
| 3.2 | HIGH-03: `feedback-v3 --success` validator | 15 min | `feedback-v3 --success garbage` exits 1 |
| 3.3 | HIGH-04: `borg debug` exit 1 on no-match | 15 min | `borg debug 'zzzzzzzzz'` exits 1 |
| 3.4 | HIGH-05: investigate `borg_suggest {}` — fix or remove | 2 hr | Non-empty or removed |
| 3.5 | HIGH-06: `git mv borg/seeds_data/guild-autopilot borg-autopilot` + content update | 45 min | All `guild` refs replaced |
| 3.6 | `borg/seeds_data/borg/SKILL.md` fix wrong repo URL | 5 min | Correct repo URL |
| 3.7 | Run full pytest suite; fix failures | 2 hr | 100% pass |

### Phase 4 — Acceptance Testing (Day 3-4, 4 hours)

| # | Task | Effort | Dependency | Exit |
|---|---|---|---|---|
| 4.1 | Run 50-query cold-start benchmark on fresh HOME | 2 hr | K=200 minimum | G1 >= 40/50, G2 >= 47/50 |
| 4.2 | Verify wheel size | 15 min | Phase 2 complete | Delta <= 5 MiB |
| 4.3 | Run G4 (existing tests green) | 30 min | Phase 3.7 | 100% pass |
| 4.4 | Run ship-gate; promote to PyPI | 30 min | All above | PyPI page clean |

**Day 4 wall clock: ~4 hours**

### Phase 5 — Release (Day 4 continued, 2 hours)

| # | Task | Effort | Dependency | Exit |
|---|---|---|---|---|
| 5.1 | Cut `3.3.0` tag; upload to TestPyPI | 30 min | Phase 4 complete | Wheel on TestPyPI |
| 5.2 | Verify TestPyPI install: `pip install --index-url https://test.pypi.org/simple/ agent-borg==3.3.0` | 15 min | 5.1 | Installs cleanly; `borg search django` returns >= 1 seed hit |
| 5.3 | Promote to PyPI as `3.3.0` | 15 min | 5.2 | PyPI page clean |
| 5.4 | Update README.md to advertise cold-start fix + new MCP setup | 30 min | 5.3 | README reflects v3.3.0 |

---

## 8. What can go wrong AFTER launch?

### Incident Response Plays

**Bad seed pack already installed (F3 / F5)**
If a seed pack is found to be misleading or wrong after install:
1. File a finding in the issue tracker with evidence
2. Cut v3.3.1 with corrected pack removed from `index.json` and source YAML fixed
3. Publish a `BORG_DISABLE_SEEDS=1` mitigation note (users can opt out temporarily)
4. Users must `pip install --force-reinstall agent-borg==3.3.1` to get corrected seeds (PyPI wheel yank does not reach installed packages)
5. Add a `borg doctor` command (2h engineering) that verifies seed pack integrity against SHA256 manifest

**Wheel size exceeds G3 after curation (F4)**
1. Minify YAML whitespace in all seed packs (remove unnecessary newlines, use compact YAML)
2. If still over 5 MiB: reduce pack count from K=500 to K=200, document as "beta corpus"
3. If still over 5 MiB: defer K=500 to v3.4.0

**Corrupted `index.json` in shipped wheel (F1)**
1. `_load_seed_index()` catches JSON parse errors and returns `{"packs": []}` — search proceeds without seeds
2. CI tests in `test_seed_corpus.py` catch malformed index before release
3. Emergency: yank wheel, hotfix `index.json`, cut patch release

**SWT-bench AGPL taint discovered after ship (MEDIUM-22 RED finding)**
1. Identify which seed packs were derived from AGPL-licensed SWE-bench tasks
2. Remove those packs from `index.json` in a patch release
3. Update curation protocol: add per-file license check before using any SWE-bench task as seed source
4. Target v3.3.1

**SB-01/SB-05 regression (F9)**
New Python distributions ship without `python` symlink. `shutil.which("borg-mcp")` handles most cases. If `borg-mcp` is also unavailable:
1. Fall back to `sys.executable`
2. Document in error message: "failed to find borg-mcp in PATH; please report this bug"
3. Patch release if fallback also fails

---

## 9. The Release Note

**v3.3.0: The cold-start release**

agent-borg v3.3.0 fixes five ship blockers that broke the first-user experience on Ubuntu 24, macOS with Python.org installer, and pyenv. Most critically, `borg setup-claude` and `borg autopilot` now correctly locate the Python interpreter on systems where only `python3` exists in PATH — every MCP tool is now visible on first run. This was the primary failure mode preventing agents from using the borg MCP server at all.

This release also ships a seed corpus of K=200-500 workflow packs that ship inside the wheel, enabling `borg search` to return results on a completely cold install. Previously, every query returned `No packs found.` on a first-time install because the 17 skill files bundled in the wheel were never merged into the search index. The seed corpus is read-only, never copied to user directories, and can be disabled with `--no-seeds`. All seed packs have been audited for license compliance (MIT/Apache-2.0/BSD/CC0 only) and provenance.

**What works**: Clean install now returns results for >= 80% of a 50-query benchmark covering Django errors, Python stdlib errors, git/Docker/bash workflows, and framework-specific issues. The CLI surface is consistent (`guild://` references replaced with `borg://` throughout). `borg generate --format claude` now works as documented in the README. PyPI homepage and repository links now correctly point to the agent-borg project.

**What doesn't**: The seed corpus is a beta launch (K=200 at launch, K=500 target for v3.4.0). Community pack federation (federated fetch from signed repo) is deferred. Semantic search via embeddings requires `agent-borg[embeddings]` and is not on the critical path. The cross-model evaluation (P2 Sonnet) remains blocked pending a fresh Anthropic API key; MiniMax-M2.7 results are available as an alternative. Users who installed v3.2.4 or earlier must `pip install --force-reinstall agent-borg==3.3.0` to receive the corrected seed corpus and MCP configuration.

---

## 10. Decision Log

### D1 — Cold-start fix strategy: Option A (wheel-bundled seed corpus)

**Decision**: Ship a curated seed corpus inside the wheel at `borg/seeds_data/packs/`, read-only, merged into search at query time via `_load_seed_index()`.

**Reason**: The only option that ships a working product to an offline, cold, headless VM on the first `borg search` call. Option B requires a human to grant consent. Option C requires network on first run. Option D fails the HN/PhD review bar.

**Controversy resolved**: The design doc's §5.4 describes wiring changes that require building `_load_seed_index()` from scratch. RED team confirmed that the existing `borg/seeds_data/*.md` files are SKILL-format, not `workflow_pack` YAML, and feed a different code path (`pack_taxonomy._get_skills_dir()`, not `borg_search`). The cold-start fix requires a greenfield integration shim + curation of new YAML files.

### D2 — K = 500 packs (starting target)

**Decision**: Target K=500 packs for v3.3.0 as a Zipf back-of-envelope estimate, validated empirically by the Phase 2 prototype.

**Reason**: G1 (K >= 161 at p_cov=0.01) and G2 (K >= 299) imply K=500 is conservative. GREEN confirmed K=500 uses ~30% of the 5 MiB budget, leaving buffer.

**Controversy resolved**: GREEN analysis shows K=500 is feasible. The 50-query benchmark at K=50 will calibrate p_cov empirically. If K=50 shows 40/50 on G1, p_cov is ~0.03-0.05 and K=200 suffices. The prototype must validate before full curation.

### D3 — Day 2 is 28h, not 22h

**Decision**: Phase 2 wiring takes 8h (not 6h). Full curation takes 20-25h serial (not 12h). Day 2 total = 28h.

**Reason**: RED team confirmed `_load_seed_index()` is a greenfield subsystem. The 6h estimate in the ship plan assumed wiring was a known pattern — it is not. Curation at 15-20 min/pack for 200 packs = 50-67h serial; at 3x parallelism = 17-22 wall-hours, not "12h" which assumed pure mechanical extraction.

**Controversy resolved**: The ship plan's "22h subagent compute in one wall day" was impossible for curation tasks. Revised Day 2 = 8h wiring + 6h initial curation. Day 3 = 67h curation wave (serial, not parallelizable).

### D4 — `_load_seed_index()` goes in `uri.py`

**Decision**: Implement `_load_seed_index()` in `borg/core/uri.py`, not a new file.

**Reason**: RED confirmed `borg/core/uri.py` exists and already handles index loading (`_fetch_index`, `resolve_guild_uri`). Adding seed loading to this module follows the existing pattern. The module is the correct home for all index-loading operations.

**Controversy resolved**: BLUE architecture spec calls for `_load_seed_index()` in `uri.py`. GREEN confirms the module exists. Implementation follows.

### D5 — Dedup priority: local > remote > seed

**Decision**: When a pack ID appears in multiple sources (seed, remote index, local), local wins, then remote, then seed.

**Reason**: This is the existing dedup logic in `search.py` lines 151-182. Extending it to handle `source="seed"` packs is straightforward. Seeds are a cold-start floor, not a ceiling — they should not overwrite user-authored or community-validated packs.

**Controversy resolved**: The dedup policy was implicit in the architecture. This decision makes it explicit and documents it in the spec.

### D6 — K=500 is feasible

**Decision**: K=500 seed packs is within the G3 (5 MiB) wheel size budget.

**Reason**: GREEN analysis: existing 17 files = 46.8 KiB uncompressed, ~15 KiB compressed. K=500 at average 2.8 KiB/pack = ~1.4 MiB uncompressed. GREEN confirms this uses <30% of the 5 MiB budget. Even a 2,000-pack corpus would stay under 5 MiB with minified YAML.

**Controversy resolved**: GREEN contradicts no prior estimate — K=500 was always the target, but this confirms the budget is not binding.

### D7 — SB-05 added as ship blocker

**Decision**: Add `borg autopilot` cli.py:973 as SB-05 (CRITICAL).

**Reason**: RED team identified that `borg autopilot` has the same `"command": "python"` bug as SB-01, in a different code path. The E2E audit did not test `borg autopilot`. The fix is the same one-line change. This is a genuine first-user entry point with the identical failure mode.

**Controversy resolved**: The ship plan had 4 blockers. This makes 5. Total ship blocker effort: ~3 hours (not 2.5h).

### D8 — C3 prototype uses MiniMax-M2.7, not MiniMax-Text-01

**Decision**: C3 replay uses MiniMax-M2.7 for agent loops.

**Reason**: P1.1 confirmed MiniMax-Text-01 floor-effected on every task (stopped after 1-2 iterations, never called `read_file` or `write_file`). Replaying with that model would reproduce the floor effect regardless of corpus. MiniMax-M2.7 has longer agent loops.

**Controversy resolved**: The design doc §7 prototype plan used MiniMax-Text-01. D8 in RED team review correctly identifies this must be replaced with M2.7.

### D9 — MDN (CC-BY-SA 2.5) excluded from seed sources

**Decision**: MDN Web JavaScript error references are explicitly excluded as a seed source.

**Reason**: CC-BY-SA at any version is incompatible with bundling into an MIT/Apache-licensed wheel. The wheel would need to be CC-BY-SA to distribute MDN content.

**Controversy resolved**: D2 in RED review confirms the design doc's original MDN row contradicts its own §6.1 forbidden list.

### D10 — `test_wheel_size_under_budget` bound tightened to 5 MiB

**Decision**: Change the test assertion from `< 10 * 1024 * 1024` to `< 5 * 1024 * 1024`.

**Reason**: G3 states "Seed corpus adds <= 5 MiB to the wheel uncompressed." The 10 MiB bound was 2x too permissive — an 8 MiB corpus (over G3) would pass the test.

**Controversy resolved**: MEDIUM-19 in RED review. Fix is 1 minute.

---

## Disposition Table: CRITICAL + HIGH Findings

| Finding | Severity | Disposition | Owner | Effort | Target |
|---|---|---|---|---|---|
| SB-05: `borg autopilot` same python bug | CRITICAL | FIX | SB-01 subagent | 5 min | Day 1 |
| `_load_seed_index()` greenfield | CRITICAL | FIX — build integration shim | Cold-start subagent | 8h | Day 2 |
| Day 2 estimate: 22h → 28h | CRITICAL | FIX — revise schedule | Hermes | 0 | Before AB approval |
| Seed format incompatibility | CRITICAL | ACKNOWLEDGE — curate new YAML packs | Curation team | ~67h | Day 3 |
| SB-03 format mismatch | CRITICAL | FIX — add aliases | SB-03 subagent | 45 min | Day 1 |
| pyproject.toml full audit | CRITICAL | FIX — grep entire file | SB-04 subagent | 30 min | Day 1 |
| `borg pull` happy path untested | HIGH | FIX — add network test | Test author | 30 min | Day 2 |
| `--no-seeds` CLI flag no test | HIGH | FIX — add flag + test | Cold-start subagent | 1h | Day 2 |
| Day 2 curation (12h → 20-25h serial) | HIGH | FIX — revise to 20-25h + 5h review | Hermes | 0 | Before AB approval |
| Task #9 wiring (6h → 8h) | HIGH | FIX — give 8h allocation | Hermes | 0 | Before AB approval |
| Dedup policy documentation | HIGH | FIX — document dedup policy | Architecture | 1h | Before cold-start merge |
| Incident response for bad seed packs | HIGH | FIX — add recall + `borg doctor` to PRD | Chief Architect | 0 | v3.3.0 PRD |
| `guild://` in CLI help strings | HIGH | FIX — rename help strings | HIGH-02 subagent | 30 min | Day 2 |
| `borg/seeds_data/borg/SKILL.md` wrong URL | HIGH | FIX — update URL | HIGH-06 subagent | 5 min | Day 2 |
| C3 prototype proxy metric | HIGH | ACKNOWLEDGE — add behavioral secondary metric | Eval design | 0 | v3.3.0 |
| `test_wheel_size_under_budget` 2x too permissive | HIGH | FIX — tighten to 5 MiB | Cold-start test author | 1 min | Day 2 |
| Seeds license audit CI | HIGH | FIX — add CI check script | Cold-start subagent | 2h | Day 2 |
| Silent `_load_seed_index()` failure | HIGH | FIX — fail explicitly unless `--no-seeds` | Cold-start subagent | 1h | Day 2 |
| SWE-bench AGPL taint | HIGH | FIX — add per-file license check | Curation protocol | 4h | Before Day 2 |
| `SKILLS_DIR` vestigial | HIGH | FIX — remove from `search.py` | Code cleanup | 5 min | Day 1 |
| README badge freshness | HIGH | FIX — link badge to CI or remove | Hermes | 10 min | Day 1 |
| `lru_cache` memoization | HIGH | FIX — add to `_load_seed_index` | Cold-start subagent | 30 min | Day 2 |
| `borg_suggest {}` investigation | HIGH | INVESTIGATE — fix or remove | HIGH-05 owner | 2h | Day 2 |
| 50-query benchmark pre-registration | HIGH | FIX — commit fixture + external pre-reg | Eval author | 2-3h | Day 2 |
| G1 "relevant" token overlap | MEDIUM | ACKNOWLEDGE — add calibration sample | Eval author | 1h | Day 2 |

---

## WHAT WE'RE NOT DOING

This list prevents scope creep and sets clear boundaries for v3.3.0:

1. **No embedding-based search in the default path**: `sentence-transformers` is optional. Text search is the primary path.
2. **No federated/community pack fetch on first run**: Option C deferred. Requires network, signing key story.
3. **No LLM-synthesized packs**: Option D rejected. Lying-confidently risk.
4. **No cross-model evaluation (P2 Sonnet)**: Blocked on OAuth token. MiniMax-M2.7 pivot available.
5. **No Thompson sampling or learning-to-rank**: Requires `feedback-v3` behavioral data not yet sufficient.
6. **No independent seed pack versioning**: Tied to minor release cadence.
7. **No `tier="seed"` in reputation engine calculations**: Seeds excluded from reputation.
8. **No community pack federation**: Federated fetch from signed repo deferred to v3.4.0+.
9. **No SWE-bench AGPL license audit for v3.3.0**: Deferred to curation protocol (v3.4.0).
10. **No `borg-mcp` as a standalone server**: MCP server is accessed via `borg setup-claude` or `borg autopilot`.

---

## Conflict Resolution Audit Trail

| Conflict | Resolution | Evidence |
|---|---|---|
| `_load_seed_index()` does not exist | Treat as greenfield subsystem requiring 8h engineering | RED CRITICAL finding 2: "this is a greenfield subsystem" |
| Existing seeds are SKILL-format not workflow_pack YAML | Curate new YAML files; old seeds stay for `classify_error` | RED CRITICAL finding 4: "existing `.md` are incompatible with `borg_search` path" |
| Day 2 wiring is 6h (not 6h), curation is 50-67h (not 12h) | Day 2 = 28h total: 8h wiring + 6h proto + 14h initial curation | RED HIGH findings 10+11; GREEN §7 confirms curation is not parallelizable |
| `borg autopilot` cli.py:973 has same SB-01 bug | Add as SB-05, same fix, 5 min | RED CRITICAL finding 1 |
| K=500 is feasible | GREEN confirms ~30% of 5MiB budget used | GREEN §2: "G3 is not binding at K=500" |
| `_load_seed_index` in uri.py | BLUE architecture spec + GREEN confirms uri.py exists | ARCHITECTURE_SPEC §4; GREEN DATA_ANALYSIS |
| Dedup priority: local > remote > seed | Explicit policy in architecture spec §5.5 | ARCHITECTURE_SPEC §5.5 |
| MDN excluded from seed sources | D2 in RED review; CC-BY-SA incompatible with MIT wheel | RED finding + ARCHITECTURE_SPEC §6.1 |
| C3 uses MiniMax-M2.7 not Text-01 | P1.1 floor effect on Text-01; M2.7 has longer loops | ARCHITECTURE_SPEC D7 |
| `test_wheel_size_under_budget` 10MiB → 5MiB | G3 states 5 MiB; test bound was 2x too permissive | RED MEDIUM finding 19 |

---

*Chief Architect synthesis complete.*
*Commit: `chief architect synthesis + PRD v3.3.0`*
*Status: Awaiting AB approval before PyPI release.*
