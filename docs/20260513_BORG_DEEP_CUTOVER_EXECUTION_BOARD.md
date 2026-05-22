> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# 20260513 Borg deeper production cutover execution board

**rev:** 20260513-1848 rev A  
**status:** execution board; deeper raw audit pending job `986868297ce9`  
**launch truth:** controlled-go supervised beta only; public launch no-go.

## What changed in this deeper pass

Created a preliminary no-loss manifest:

`docs/repo-manifest/20260513_borg_ecosystem_manifest.prelim.json`

Queued deeper read-only audit:

`986868297ce9` — `borg-deep-dirty-namespace-runtime-audit-20260513`

This audit is designed to classify:

- all 237 canonical `borg` dirty/untracked entries,
- exact git state and recent commits,
- entrypoint collisions from package metadata,
- MCP/runtime mirror locations,
- unsafe guidance literals and confidence-gate helper presence,
- diff stats for patched source/plugin areas,
- truth-source status across readiness docs.

## Current hard blocker stack

### P0 — live runtime trust blocker

`mcp_borg_observe` still returned unrelated guidance during this session, including `PACK GUIDANCE (django-circular-dependency)` / synthetic guidance patterns. Source tests pass, but live served behavior is not proven fixed.

**Close condition:**

- served/live `borg_observe` returns `NO_CONFIDENT_MATCH` or no injected guidance for unrelated audit prompts,
- permission-denied prompts still return permission guidance,
- plugin file path is proven to be the loaded path,
- reload only with operator approval.

### P1 — dirty canonical repo blocker

First raw audit showed canonical `borg` repo has `237` dirty/untracked entries.

**Close condition:** every entry is classified:

- commit,
- archive,
- ignore,
- generated artifact,
- delete later after explicit approval.

No deletion before archive/manifest.

### P2 — CLI namespace blocker

Known collision:

- `agent-borg` exposes `borg`, `borg-mcp`.
- `borg-collective-py` exposes `borg`, `borg-mcp`.

**Close condition:** one owner for `borg` and `borg-mcp`. Recommended:

- `agent-borg` keeps `borg`, `borg-mcp`, `borg-doctor`.
- `borg-collective-py` becomes SDK/library or exposes namespaced `borg-collective`, `borg-collective-mcp` only.

### P3 — federation tests not deterministic

`borg-collective-py` pytest fails collection due missing `respx`, `hypothesis`.

`borg-collective-v1` npm test fails because Wrangler remote-mode login/config is required.

**Close condition:** fresh clone/dev setup runs tests without manual hidden state.

### P4 — external-user proof blocker

No broad production claim until first-10 supervised beta evidence exists.

**Close condition:** 6/10 first users get one relevant `ACTION / STOP / VERIFY` moment without maintainer handholding; all misses recorded.

## Execution lanes

### Lane A — dirty-tree triage

Pending raw audit job will output exact path categories. After that:

1. group by top-level directory,
2. separate docs/eval/test/source/build/cache,
3. preserve unique work,
4. commit or archive,
5. regenerate status docs from machine snapshots.

### Lane B — runtime split-brain closure

1. fingerprint loaded MCP/module path,
2. verify plugin path from `hermes_cli/plugins`, not `~/.hermes/plugins`,
3. verify BORG_HOME / DB path,
4. operator-approved reload only after scope is explicit,
5. rerun live `mcp_borg_observe` canary.

### Lane C — namespace cleanup

1. inspect package metadata,
2. decide command ownership,
3. update docs/install paths,
4. add CI test detecting duplicate console scripts across Borg packages,
5. fresh venv install both packages and prove no shadowing.

### Lane D — federation reproducibility

1. add test extras for `borg-collective-py`,
2. create local/no-auth worker test mode for `borg-collective-v1`,
3. preserve remote migration warning,
4. rerun CI-equivalent tests.

### Lane E — first-10 beta proof

Only after P0-P3 close:

1. clean user path,
2. exact transcript capture,
3. scoreboard update,
4. classify each user outcome,
5. keep claims bounded.

## Next acceptance artifact

After job `986868297ce9` completes, create:

`docs/20260513_BORG_DEEP_DIRTY_TREE_AND_NAMESPACE_AUDIT.md`

It must include:

- raw dirty-tree summary,
- exact collision table,
- unique runtime mirror findings,
- doc truth-source contradictions if any,
- final next patch sequence.
