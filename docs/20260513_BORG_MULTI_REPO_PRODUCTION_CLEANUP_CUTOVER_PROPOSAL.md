# 20260513 Borg multi-repo production cleanup / cutover proposal

**rev:** 20260513-1535 rev A  
**status:** production cleanup proposal; evidence-backed; no service restart performed  
**decision:** Borg remains **CONTROLLED GO for supervised first-user beta only** and **NO-GO for broad unattended public launch**.

## Executive summary

Borg has real working product surfaces, but the current system is not yet world-class production clean because the ecosystem is split across multiple repos, mirrored runtime paths, duplicate CLI names, stale/live process ambiguity, and uneven test readiness.

The right move is not to delete or merge blindly. The safe move is a **no-loss consolidation**:

1. Freeze and inventory every repo/path before moving anything.
2. Declare one canonical ownership map.
3. Remove hand-maintained runtime forks from the production path.
4. Resolve CLI namespace collisions before public onboarding.
5. Keep source patches, proof artifacts, and first-user evidence in one authoritative repo/docs surface.
6. Gate any public launch on external-user transcripts and automated first-10 scoreboard evidence.

## Evidence collected

### Raw read-only audit job

Cron job: `8d61451c97d2` (`borg-multi-repo-production-readiness-raw-audit-20260513`) completed read-only.

Important results:

| Surface | Result | Evidence |
|---|---:|---|
| `/root/hermes-workspace/borg` | partial pass | git repo exists; branch `fix/borg-observe-wrapper-20260424`; HEAD `402d3f5`; remote `https://github.com/borg-farther/Borg-Directory.git`; **237 dirty/untracked entries** |
| canonical Borg confidence/readiness tests | pass | `19 passed in 5.94s` |
| Hermes Borg auto-trace plugin tests | pass | `6 passed in 1.44s` |
| Borg version consistency | pass | `pyproject_version=3.3.1`; `runtime_version=3.3.1` |
| proof artifacts | pass | `eval/first_user_release_gate_snapshot.json`, `eval/uat_scoreboard_snapshot.json`, `eval/gate_run_snapshot.json`, `eval/borg_proof_dashboard.json` all exist and parse |
| plugin direct safety probe | pass | `suppresses_unrelated=True`; `allows_permission=True` |
| `/root/hermes-workspace/borg-init` | test pass, git unknown | `43 passed`; path had no `.git` at audited location |
| `/root/hermes-workspace/borg-collective-v1` | fail in current env | Vitest/Wrangler remote-mode login required; invalid `--runInBand` for Vitest |
| `/root/hermes-workspace/borg-collective-py` | fail in current env | missing test deps: `respx`, `hypothesis`; no packages installed by design |
| `guild-v2`, `guild-packs`, `guild-benchmark`, `guild-mcp-package` | not production-auditable from path | requested paths reported `NO_GIT_OR_MISSING` |

### Important live-runtime finding

`mcp_borg_observe` still leaked weak synthetic `PACK GUIDANCE (bash-permission-denied)` into unrelated audit prompts during this session. That means the source/plugin patch is passing tests, but live MCP/runtime behavior is still not fully cut over or reloaded.

This is a trust blocker. Expected behavior for unrelated/weak matches is `NO_CONFIDENT_MATCH`, not confident-looking guidance.

## Current repo/product map

| Path | Intended role | Current production status |
|---|---|---|
| `/root/hermes-workspace/borg` | canonical local/offline MCP failure-memory product; package `agent-borg` | strongest surface; tests pass; repo dirty; controlled-go only |
| `/root/hermes-workspace/borg-collective-py` | Python federation SDK/CLI; package `borg-collective` | alpha; tests blocked by missing deps; CLI namespace conflicts with `agent-borg` |
| `/root/hermes-workspace/borg-collective-v1` | Cloudflare Worker/D1 hosted federation backend | backend exists; local test run blocked by Wrangler remote-mode auth/config |
| `/root/hermes-workspace/borg-init` | npm installer/onboarding package `@borg-collective/init` | tests pass; git/release cleanliness not provable at audited path |
| `/root/hermes-workspace/guild-v2` | older/mirror Borg runtime source | must not be hand-maintained production source; patched defensively only |
| `/home/user/guild-tools` | older active-candidate runtime path | must not be hand-maintained production source; patched defensively only |
| `/root/.hermes/hermes-agent/hermes_cli/plugins/borg_auto_trace` | real Hermes plugin path | tests pass; direct safety probe passes; live service may still need controlled reload |
| `/root/.hermes/hermes-agent/plugins/borg_auto_trace` | duplicate/defensive plugin path | not the primary auto-discovered plugin path; keep only if required by packaging, otherwise deprecate |

## Highest-risk split-brain issues

### 1. CLI namespace collision

Both `agent-borg` and `borg-collective-py` expose `borg` and `borg-mcp` entrypoints.

That is not production-clean. A user can install both and get different code depending on install order, shell path, pipx environment, or venv state.

**Decision needed:**

- `agent-borg` keeps `borg`, `borg-mcp`, `borg-doctor`.
- `borg-collective-py` should rename public commands to `borg-collective` and `borg-collective-mcp`, or become a library consumed by `agent-borg`.
- Until this is fixed, do not claim clean unattended install.

### 2. Runtime mirror drift

Multiple copies of Borg MCP/runtime code exist. The observed live `borg_observe` behavior proved source-of-truth ambiguity is real.

**Production rule:** runtime mirrors are deployment artifacts, not source repos. Any hand-maintained mirror must be deprecated or generated from canonical source.

### 3. Live process stale after patch

Source tests now pass, but the running MCP/gateway path still returned synthetic unrelated guidance.

**Production rule:** a fix is not closed until the live loaded code path returns `NO_CONFIDENT_MATCH` for the known unrelated audit prompt.

### 4. Dirty canonical repo

Canonical `borg` has 237 dirty/untracked entries. This blocks clean release confidence.

**Production rule:** no release until every modified/untracked file is classified as one of:

- keep + commit,
- keep + document artifact,
- move to archive,
- ignore via explicit `.gitignore`,
- delete only after manifest review.

### 5. Worker test environment not reproducible

`borg-collective-v1` tests currently require Wrangler remote-mode login/config and failed locally.

**Production rule:** worker CI must have a local deterministic test mode that does not require interactive auth.

### 6. Python federation SDK tests not self-contained

`borg-collective-py` pytest collection failed due missing `respx` and `hypothesis`.

**Production rule:** test extras must be declared and CI/dev docs must install them through one command, e.g. `pip install -e '.[test]'` or `uv sync --extra test`.

## No-loss consolidation plan

### Phase 0 — freeze and manifest

Do not delete anything yet.

Create a manifest under canonical Borg:

`docs/repo-manifest/20260513_borg_ecosystem_manifest.json`

For each path capture:

- absolute path,
- git remote/branch/HEAD/status count if available,
- package name/version,
- entrypoints,
- docs role,
- last modified files,
- test command and result,
- secrets redaction status,
- keep/archive/deprecate recommendation.

### Phase 1 — assign source-of-truth boundaries

Recommended ownership:

1. **`agent-borg` / `/root/hermes-workspace/borg`**
   - canonical user-facing local product,
   - owns `borg`, `borg-mcp`, `borg-doctor`, `borg rescue`, `borg observe`, first-user docs, confidence gates.

2. **`borg-collective-v1`**
   - hosted federation backend only,
   - owns D1 schema, API endpoints, auth, deployment, worker tests.

3. **`borg-collective-py`**
   - federation SDK/library only, unless merged into `agent-borg`,
   - must not own `borg` or `borg-mcp` entrypoints in public install path.

4. **`borg-init`**
   - installer only,
   - must call/verify the canonical commands from `agent-borg`, not introduce a parallel Borg runtime.

5. **`guild-v2`, `/home/user/guild-tools`, build copies**
   - archive/deployment artifacts only,
   - no hand-maintained source-of-truth patches after cutover.

### Phase 2 — preserve key work before cleanup

Before removing or renaming anything:

1. Generate diffs for every dirty repo/path.
2. Copy non-git directories into an archive location with timestamp:
   - `archive/borg-ecosystem-precutover-20260513/<path-slug>/`
3. Produce a feature/doc inventory:
   - packages,
   - CLI commands,
   - MCP tools,
   - tests,
   - docs,
   - eval artifacts,
   - Cloudflare migration files,
   - installer flows.
4. Redact credentials as `[REDACTED]`.
5. Only then classify and move/merge.

### Phase 3 — fix hard blockers

#### Blocker A — live `borg_observe` confidence leak

Acceptance test:

- unrelated production audit prompt returns `NO_CONFIDENT_MATCH` or no injected Borg advice,
- `bash-permission-denied` prompt still returns permission guidance,
- plugin direct probe remains:
  - `suppresses_unrelated=True`,
  - `allows_permission=True`.

This likely requires operator-approved reload of the live Hermes/gateway/MCP process after confirming loaded path. Do not restart automatically.

#### Blocker B — CLI namespace collision

Acceptance test:

- clean venv install of `agent-borg` gives one `borg` and one `borg-mcp`,
- clean venv install of `borg-collective-py` does not shadow `borg`, or is explicitly installed only as a library/extra,
- `which borg`, `borg version`, and `python -c 'import borg; print(borg.__file__)'` all point to the canonical package.

#### Blocker C — dirty repo cleanup

Acceptance test:

- canonical repo `git status --short` is zero or only explicitly allowed generated artifacts,
- all retained audit/docs/test files are committed or staged for review,
- no secrets in diff.

#### Blocker D — federation SDK test deps

Acceptance test:

- `borg-collective-py` declares test deps,
- fresh environment runs pytest without collection errors,
- missing `respx` / `hypothesis` resolved through declared extras, not ad hoc install instructions.

#### Blocker E — worker deterministic tests

Acceptance test:

- `npm test` has a local/no-auth mode,
- no generic remote migration command can accidentally apply seed-test-key migration,
- CI uses explicit safe migration scripts only.

## Production readiness gates

### G0 — repo clarity

Pass criteria:

- one product map exists,
- no ambiguous public CLI ownership,
- runtime mirrors are deprecated/generated,
- README install path is singular.

### G1 — clean install / first-user smoke

Pass criteria from current beta doc:

```bash
python3 -m pip install agent-borg
borg version
borg-doctor --json
borg rescue 'ModuleNotFoundError: No module named flask' --json
borg search 'django migration table already exists'
borg setup-claude --scope user --verify --fix
borg first-10 --json
```

### G2 — confidence fail-closed

Pass criteria:

- weak/unrelated matches return `NO_CONFIDENT_MATCH`,
- no synthetic-only advice is injected as confident operational guidance,
- regression tests cover `bash-permission-denied`, `django-circular-dependency`, and random audit prompts.

### G3 — security/privacy/anti-copy hardening

Pass criteria:

- no secrets in repo or generated docs,
- prompt-injection neutralization tests pass,
- signed/validated learning atoms where claims say so,
- public docs avoid overclaiming cryptographic trust.

### G4 — first-10 supervised beta

Pass criteria:

- at least 6/10 users get one relevant `ACTION / STOP / VERIFY` moment without maintainer handholding,
- every miss is recorded as `NO_CONFIDENT_MATCH` or explicit negative feedback,
- transcript/log evidence captured.

### G5 — federation backend reliability

Pass criteria:

- worker tests pass locally and in CI,
- D1 migration path safe and repeatable,
- API auth/error behavior documented and tested,
- no remote-only hidden dependency for basic test suite.

### G6 — release packaging

Pass criteria:

- no CLI collisions,
- `agent-borg` wheel/sdist install in clean env,
- version consistency tested,
- docs and package metadata point to the same repo/home.

### G7 — claims discipline

Allowed claims now:

- “Borg is a local/offline collective-memory aid for agents.”
- “The current local confidence/readiness gates pass in the audited source tree.”
- “Borg is controlled-go for supervised first-user beta.”

Not allowed yet:

- “Borg improves agent success rate by X%.”
- “Borg global collective network is production-proven.”
- “All packs are cryptographically trusted.”
- “Ready for broad unattended public launch.”

## Proposed target architecture

```text
user / agent
  ↓
agent-borg package
  ├─ borg CLI
  ├─ borg-mcp
  ├─ local trace/failure memory
  ├─ confidence gate / NO_CONFIDENT_MATCH
  └─ optional federation client boundary
        ↓
   borg-collective-py library only
        ↓
   borg-collective-v1 worker/D1 backend

borg-init
  └─ installer/orchestrator that installs/verifies agent-borg and configures MCP clients
```

## Immediate next actions

1. Produce `repo-manifest/20260513_borg_ecosystem_manifest.json` from raw audit data.
2. Clean/classify the 237 dirty/untracked entries in canonical `borg`.
3. Resolve `agent-borg` vs `borg-collective-py` CLI collisions.
4. Add declared test extras for `borg-collective-py` and re-run tests.
5. Add local/no-auth test mode for `borg-collective-v1`; remove invalid `--runInBand` usage from audit command docs.
6. Perform operator-approved runtime reload only after confirming exact loaded MCP/plugin path.
7. Verify live `mcp_borg_observe` returns `NO_CONFIDENT_MATCH` for unrelated prompt.
8. Resume first-10 supervised beta evidence capture.

## Final verdict

Borg is **not done** and not broad-production ready.

Borg is, however, close to a strong supervised beta if the cleanup is executed in this order:

1. close live confidence-gate/runtime mismatch,
2. clean canonical repo state,
3. fix CLI namespace ambiguity,
4. make federation/worker tests reproducible,
5. run first-10 beta with transcript-backed evidence.

Until those are complete, Borg should be described as:

> controlled-go local/offline agent memory product with passing canonical confidence/readiness tests, not yet proven as a broad public collective-intelligence network.
