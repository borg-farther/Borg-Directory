# Borg v3.2.3 observe→search index bug — repro + diagnosis + fix

## TL;DR

**Bug**: `borg search <query>` did not find traces that were already present in
`~/.borg/traces.db`. In the P1.1 MiniMax experiment, after three Phase-A-lite
seeding runs the search index was still empty as far as the agent tool loop
could tell, so C2 (borg seeded) was indistinguishable from C1 (borg empty).

**Root causes (two, both required for the bug)**:

1. `borg search` in `borg/core/search.py::borg_search()` only queried the
   workflow *pack* index (remote `_fetch_index()` + local `~/.hermes/guild/*/pack.yaml`).
   It never touched `~/.borg/traces.db`, even though `TraceMatcher.find_relevant()`
   was available right next door.
2. `borg` CLI had no `observe` subcommand at all (only the MCP server exposes
   `borg_observe`). The seeding runs therefore never wrote traces via the CLI —
   they only called `borg search` / `borg debug`, neither of which records
   anything. So even if search had looked at traces, seeding would not have
   produced any fresh ones.

**Fix (v3.2.4)**: minimal, two-file change:

1. Add `borg observe <task> [--context ...]` CLI subcommand that records a
   trace via `borg.core.traces.save_trace()` — making observations CLI-reachable
   for the first time.
2. Extend `borg_search()` to append `TraceMatcher.find_relevant(query)` hits
   to its `matches` list (with `source="trace"` and a `trace:<id>` name
   prefix so existing callers can distinguish them).

Both changes together give the observe→search roundtrip the experiment needs.

## Step 1 — reproduce

```
$ borg --version
borg 3.2.3

$ borg observe 'fix django authentication bug' 2>&1 | head -20
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,
             convert,generate,list,version,autopilot,setup-claude,
             setup-cursor,start}
            ...
borg: error: argument command: invalid choice: 'observe' (...)
```

→ the observe subcommand does not exist in the CLI.

```
$ ls -la ~/.borg/
-rw-r--r-- 1 root root       40 Mar 31 10:30 borg.db
-rw-r--r-- 1 root root 14352384 Apr  8 17:00 borg_v3.db
-rw-r--r-- 1 root root    81920 Apr  6 18:48 traces.db

$ sqlite3 ~/.borg/traces.db 'SELECT COUNT(*) FROM traces'
36

$ sqlite3 ~/.borg/traces.db \
  "SELECT created_at, substr(task_description,1,60), source FROM traces
   ORDER BY created_at DESC LIMIT 8"
2026-04-06T18:48:04Z|Fix Django model field max_length mismatch in migration|auto
2026-04-06T18:48:03Z|Fix Django migration for model field change|auto
2026-04-06T18:42:53Z|Fix Django model field max_length mismatch in migration|auto
2026-04-06T18:42:52Z|Fix Django migration for model field change|auto
...
```

→ 36 traces exist, 29+ are explicitly Django, yet:

```
$ borg search django
No packs found.

$ borg search django --json
{
  "success": true,
  "matches": [],
  "query": "django",
  "total": 0,
  "mode": "text"
}
```

→ **BUG_REPRODUCED: yes**.

## Step 2 — find the code

- Search entry point: `borg/cli.py::_cmd_search()` (line 61) → calls
  `borg.core.search.borg_search()`.
- `borg/core/search.py::borg_search()` (line 82) loads packs from
  `_fetch_index()` and `BORG_DIR.glob("*/pack.yaml")`, runs a keyword scan,
  and returns the matches. It never imports `TraceMatcher` or touches
  `traces.db`.
- `borg/core/traces.py::save_trace()` (line 184) is the trace writer. It is
  only called from `borg/integrations/mcp_server.py::_feed_trace_capture()`
  (line 137) and `borg_apply` checkpoint handling (line 1197) — i.e. only
  from the MCP server path. The `borg` CLI never invokes it.
- `borg/core/trace_matcher.py::TraceMatcher.find_relevant()` (line 26) is the
  trace reader. It is only called from `borg_observe` in
  `borg/integrations/mcp_server.py` (line 1709) — again, only MCP-side.

So the CLI observe/search commands never touch traces. Two separate stores,
no bridge.

## Step 3 — diagnosis

Per the "most likely causes" list in the task spec:

- (a) "observe writes to one store, search reads from another" — **YES**, and
  it's worse than that: there is no CLI observe at all, so nothing writes.
- (b) "observe writes lazily" — no, `save_trace` is synchronous with
  `db.commit()` at line 236.
- (c) "search filters by metadata observe doesn't set" — no, pack search is
  pure substring match on pack metadata.
- (d) "minimum quality threshold" — no.
- (e) "index rebuilt only on separate command" — no such command exists;
  there is no rebuild pathway from traces → packs.

### Root cause locations (file:line)

- `borg/core/search.py:82` — `borg_search()` does not read from `traces.db`.
- `borg/cli.py:985` (subparser registration block) — no `observe` subparser
  exists; the CLI simply cannot write to `traces.db`.

## Step 4 — minimum fix

Two small edits, both in files already shipped by v3.2.3:

### Edit 1 — `borg/cli.py`

Add `_cmd_observe()` (≈25 LOC) and register the `observe` subparser
(≈10 LOC). The function instantiates a `TraceCapture`, calls
`extract_trace()`, and writes via `save_trace()`.

### Edit 2 — `borg/core/search.py`

After the text-search match loop, call `TraceMatcher().find_relevant(query,
top_k=10)` and append each result to `matches` as a normalized dict with
`source="trace"`, `name="trace:<id>"`, `tier="trace"`,
`confidence="observed"`, and the task description as `problem_class`. This
way:

- `_cmd_search()`'s existing `_test_filter` prefix list does not affect
  traces (it filters `"test-pack"`, `"guild:--"`, etc.).
- The existing pretty-print loop renders them as any other match row.
- `--json` callers see the full list including trace entries.

Wrapped in `try/except Exception: pass` so a broken trace DB can never
break search — matches the existing defensive style of the rest of
`borg_search()`.

## Step 5 — verify

See `test_observe_search_roundtrip.py` and the release notes below. After
the fix:

```
$ borg observe 'fix django authentication bug for the third time today'
Recorded trace <id> for task: fix django authentication bug ...

$ borg search django | head
Name                                Confidence   Tier     Problem Class
----------------------------------------------------------------------
trace:<id>                          observed     trace    fix django authentication bug ...
...
Total: N pack(s)
```

## Design note — why this is a fix, not a refactor

Packs and traces are architecturally separate by design: packs are
hand-crafted reusable workflows; traces are post-hoc investigation logs.
That separation is worth preserving. But the search UX should unify them,
because a user asking "has anyone dealt with X before?" wants both "here's a
pack for that class of problem" AND "here are traces of agents solving it".
The fix treats traces as a second search source, not as a pack replacement,
and marks them clearly with `source="trace"`.

A cleaner long-term story would be a dedicated `borg observe` +
`borg search --include-traces` flag split, but that's v3.3 work. For
v3.2.4 we need the roundtrip to work for the P1.2 experiment; surfacing
traces in the default search result set is the minimum viable bridge.
