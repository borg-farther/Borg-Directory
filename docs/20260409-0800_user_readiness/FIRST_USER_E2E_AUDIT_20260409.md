# agent-borg v3.2.4 — First-User E2E Audit

**Author:** Claude Code on behalf of AB
**Date:** 2026-04-09 08:00 UTC
**Package under test:** `agent-borg==3.2.4` (PyPI)
**Environment:** Ubuntu 24.04 VPS (srv1353853), Python 3.12.3, fresh `/tmp` venv
**Report type:** Canonical ship-gate audit for v3.3.0
**Audit ceiling:** ≤60 min wall clock, $0.50 cost — both met
**Status:** SHIP GATE EVALUATION

---

## 1. Executive Summary

**Verdict: NOT READY to promote as "ready for real users" in v3.2.4. Ship-ready after the v3.3.0 fixes below land.**

The package **installs cleanly and quickly** (5.4s, 21 deps, no compilation),
the CLI **launches sub-100 ms** on every fast command, the **MCP server works
end-to-end** (17 tools enumerated, `borg_search` / `borg_observe` /
`borg_suggest` return real JSON), and the **observe → search roundtrip
introduced in v3.2.4 is in fact fixed** — the regression it was meant to patch
does not reproduce. These are genuine wins and should be stated plainly.

But the **first-user story has four concrete ship blockers** that a naive
`pip install agent-borg` user will walk into within five minutes, and every
one of them is recoverable with small, mechanical fixes:

| # | Ship blocker | Severity | Fix surface |
|---|---|---|---|
| **SB-01** | `borg setup-claude` emits `"command": "python"` in the MCP config. Ubuntu 24 (and macOS with the stock Python.org installer, and any pyenv user) ships **no `python` binary** — only `python3`. Claude Code will try to spawn `python`, fail with ENOENT, and every `borg_*` tool will be invisible. This is the *exact* 120-second hang we already documented on this same VPS. | **SHIP_BLOCKER** | 1 line: `borg/integrations/setup_claude.py` — use `sys.executable`. |
| **SB-02** | `docs/EXTERNAL_TESTER_GUIDE.md` is the file we ship external testers to, and it contains **49 hits for the old name** (`guildpacks`, `guild-packs`, `guild-mcp`, `pip install guild-packs`, `import guild`). Every single command in that guide is wrong. This is the literal "old name is a ship-blocker" clause from the audit spec. | **SHIP_BLOCKER** | Delete or rewrite `docs/EXTERNAL_TESTER_GUIDE.md`. |
| **SB-03** | `README.md` documents `borg generate ... --format claude` and `--format cursor`. Both fail with `argparse.ArgumentError: invalid choice`. The real values are `claude-md` and `cursorrules`. A user who copies the README verbatim is told they typed their own tool wrong. | **SHIP_BLOCKER** | Either rename the `--format` enum to `claude`/`cursor` (aliasing the old names) or fix the README. |
| **SB-04** | Project URLs in the wheel metadata still point at `https://github.com/bensargotest-sys/guild-packs` (three of them: Homepage, Repository, Documentation). A user who clicks "Homepage" on PyPI lands on a repository whose name contradicts the tool name — the single-most-common legitimacy signal is broken. | **SHIP_BLOCKER** | `pyproject.toml` `[project.urls]`. |

**Ship verdict:** agent-borg v3.2.4 is **fine as a CLI for a Python/Django
developer running `borg debug` on their own machine**, but **not fit** for the
two louder stories the README tells — *"plug into Claude Code/Cursor via MCP"*
and *"battle-tested by external testers"*. Fix SB-01..SB-04 and ship v3.3.0.

**Non-blocking but high:** `search debugging` on a freshly-installed box
returns **zero matches when `HERMES_HOME` doesn't exist** (the 4 packs the
second run showed are not shipped with the wheel — they come from
`~/.hermes/guild/` already present on this host). First-user cold-start is
still an empty DB. See HIGH-01. Installing the seed corpus on first run, or
shipping packs inside the wheel's `borg/seeds_data/`, would close the single
biggest cold-start gap.

**TL;DR:** Install works. CLI works. MCP works. **First-user MCP adoption
does not work on Ubuntu 24 / pyenv / macOS-without-python-shim**, the external
tester guide sends testers to a phantom tool called `guildpacks`, and the
README ships two wrong copy-paste commands. Four mechanical fixes unblock
v3.3.0.

---

## 2. Methodology

**"First user" definition (for this audit):** a developer who has never heard
of borg, has Python 3.12 on a clean Ubuntu 24 box (no pyenv, no conda, no
prior `.hermes` directory), and has 30 minutes to decide whether this tool
earns a permanent slot in their workflow. They will read the PyPI page, run
`pip install`, try two or three commands, and if any of them lie to them they
leave.

**Harness:**

- Host: `srv1353853` (Hostinger Ubuntu 24.04, Python 3.12.3 at `/usr/bin/python3.12`).
- Audit dir: `/tmp/borg-audit-1775738954` (fresh tmpdir, `$(date +%s)`-stamped).
- Venv: `python3.12 -m venv venv` → `source venv/bin/activate`.
- System `borg` is **not touched** — the production P2.1 Sonnet experiment is
  still running under `run_p2_sonnet.pid` and uses `/root/.hermes/borg/`. The
  audit venv is fully isolated.
- Fresh `HOME` pointed at `/tmp/fresh-*-<nanos>` to simulate a brand-new user
  whenever `HERMES_HOME` contamination was a risk.
- Every timing was captured with `/usr/bin/time -f "WALL=%e"`. Every "broken"
  claim has a captured stderr. Every "fine" claim has a wall-clock or
  output snapshot.
- Total audit wall clock: ≈35 minutes. Cost: well under $0.50.

**Scope:** installation, CLI surface, zero-state happy path, MCP server path,
docs audit, error modes, performance, industry comparison, defect inventory,
remediation plan, adoption verdict. **Out of scope:** pack quality, retrieval
effectiveness (that's P1/P2 experiment territory, documented elsewhere),
Windows, macOS.

---

## 3. Installation Path

```bash
$ AUDIT_DIR=/tmp/borg-audit-$(date +%s)  # /tmp/borg-audit-1775738954
$ python3.12 -m venv $AUDIT_DIR/venv
$ source $AUDIT_DIR/venv/bin/activate
$ /usr/bin/time -f "WALL=%e MAX_RSS_KB=%M" pip install agent-borg
...
Successfully installed agent-borg-3.2.4 annotated-doc-0.0.4
  annotated-types-0.7.0 anyio-4.13.0 click-8.3.2 fastapi-0.135.3
  h11-0.16.0 httptools-0.7.1 idna-3.11 pydantic-2.12.5
  pydantic-core-2.41.5 python-dotenv-1.2.2 pyyaml-6.0.3
  sse-starlette-3.3.4 starlette-1.0.0 typing-extensions-4.15.0
  typing-inspection-0.4.2 uvicorn-0.44.0 uvloop-0.22.1
  watchfiles-1.1.1 websockets-16.0
WALL=5.40 MAX_RSS_KB=127012
```

**Result: install is clean and fast.** 5.4 seconds wall clock on a VPS with
a warm pip cache, **21 dependencies total**, **zero native compilation**,
**zero warnings**, **zero deprecation notices**, exit code 0.

### Entry points registered

```
EntryPoint(name='borg',      value='borg.cli:main',                     group='console_scripts')
EntryPoint(name='borg-defi', value='borg.defi.cli:main',                group='console_scripts')
EntryPoint(name='borg-http', value='borg.integrations.http_server:main',group='console_scripts')
EntryPoint(name='borg-mcp',  value='borg.integrations.mcp_server:main', group='console_scripts')
```

All four are importable and executable. No broken entry points.

### Wheel metadata

```
Name:            agent-borg
Version:         3.2.4
Summary:         Collective memory for AI coding agents — your agent learns from every session
Requires-Python: >=3.10
Project-URL:     Homepage,     https://github.com/bensargotest-sys/guild-packs   ← STALE (SB-04)
                 Repository,   https://github.com/bensargotest-sys/guild-packs   ← STALE (SB-04)
                 Documentation,https://github.com/bensargotest-sys/guild-packs#readme ← STALE (SB-04)
```

### Dependency tree (direct, from `Requires-Dist`)

```
pyyaml>=6.0
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
sse-starlette>=1.6.0
pynacl>=1.5.0                ; extra=="crypto"
sentence-transformers>=2.2.0 ; extra=="embeddings"
numpy>=1.24.0                ; extra=="embeddings"
aiohttp>=3.9.0               ; extra=="defi"
cryptography>=41.0.0         ; extra=="defi"
pytest>=7.0                  ; extra=="dev"
pytest-cov>=4.0              ; extra=="dev"
pytest-asyncio>=0.21.0       ; extra=="dev"
```

**Observation (MEDIUM-03):** the core install pulls in **FastAPI + uvicorn +
sse-starlette + uvloop + websockets** for what 99 % of first-users will use
as a read-only CLI. That is a ~6 MB dependency surface and ~1.2 s of import
overhead waiting to happen. uvicorn/fastapi should be moved under an
`agent-borg[server]` extra; a CLI user has no reason to install uvloop. Not a
ship blocker, but compare to `pip install ruff` (zero Python deps).

---

## 4. CLI Surface Inspection

`borg --help` returns **16 subcommands** in 0.05 s:

```
search pull try init apply publish feedback feedback-v3 debug
convert generate list observe version autopilot setup-claude
setup-cursor start
```

All 16 `borg <cmd> --help` invocations were captured into
`$AUDIT_DIR/subcmd_helps.log` (258 lines). Every subcommand exposes a
well-formed `--help`, every help message has an `Examples:` block, and every
argparse parser exits cleanly on missing args with exit code 2.

**Issues flagged during CLI surface inspection:**

| Finding | Subcommand | Severity |
|---|---|---|
| `setup-claude --help` has **no flags at all** — no `--force`, no `--python`, no `--dry-run`, no `--global` vs `--local`. A user who wants to regenerate the config to point at a different Python has to delete the JSON file by hand. | `setup-claude` | MEDIUM-04 |
| `pull` help text says `"Pack URI (guild://, https://, or local path)"` — "guild://" is the OLD URI scheme name. The tool still accepts it (for back-compat) but the user-facing docs should say `borg://`. Not a ship-blocker because it works; a branding ship-blocker because the README and tool name say "borg". | `pull` | HIGH-02 |
| `start` help text ends with the literal line `First time? Just run: pip install agent-borg && borg start` — this is cute, but a user who is *inside* `borg start` has already run `pip install`. Minor. | `start` | LOW-01 |
| `feedback-v3 --success` takes a string but the parser accepts literally anything (tested with `--success maybe`). No validation → silent wrong data written to feedback DB. | `feedback-v3` | HIGH-03 |
| `debug` with an empty string (`borg debug ''`) returns "No matching problem class found" but **exits 0** even though nothing was classified. `debug` should exit 1 (or 2) when it has no match — automation will treat "no match" as "fix applied". | `debug` | HIGH-04 |
| `observe`, `search --json`, `apply --json`, `try --json`, `feedback` — the JSON output is well-formed and consistent. **Positive finding.** | (multiple) | ✓ |

---

## 5. Zero-State Happy Path

### 5(a) `borg --version`

```
$ /usr/bin/time -f "WALL=%e" borg --version
borg 3.2.4
WALL=0.05
```

✅ Works, sub-100 ms.

### 5(b) `borg search` on a truly empty DB

**First run (accidentally using pre-existing `/root/.hermes/`):**

```
$ borg search debugging
Name                                Confidence   Tier     Problem Class
----------------------------------------------------------------------
quick-debug                         tested       COMMUNITY simple debugging
systematic-debugging                tested       COMMUNITY Agent stuck in circular debugging — ...
agent-a-debugging                   tested       COMMUNITY Use when encountering any bug, ...
systematic-debugging.rubric         inferred     COMMUNITY

Total: 4 pack(s)
WALL=0.58
```

This looks like a win, but it is a **false positive for the first-user
story** — those 4 packs are coming out of `/root/.hermes/guild/` which was
*already on this host* (leftover from the development machine). This is the
single biggest gotcha I found in the audit.

**Second run (fresh `HOME` with `HERMES_HOME` overridden to an empty dir):**

```
$ HOME=/tmp/fresh2-440715504 HERMES_HOME=/tmp/fresh2-440715504/.hermes \
    borg search debugging
No packs found.

$ HOME=/tmp/fresh2-440715504 HERMES_HOME=/tmp/fresh2-440715504/.hermes \
    borg search debugging --json
{
  "success": true,
  "matches": [],
  "query": "debugging",
  "total": 0,
  "mode": "text"
}
```

**This is HIGH-01.** A freshly-installed `agent-borg` on a clean machine
returns **zero matches** for `borg search debugging`. The wheel ships
`borg/seeds_data/*.md` (18 files including `systematic-debugging.md`,
`null-pointer-chain.md`, `missing-dependency.md`, etc.), but **these are
never seeded into the local pack directory on first run**. A first user runs
`borg search debugging`, sees "No packs found.", and concludes the tool is
broken.

**Empty-state message audit:**

```
$ borg search zzzzzzzzzz
No packs found.
```

That's it. Four words. **No hint that the user should run `borg pull` or
`borg init`. No link to the README. No "try `borg debug 'your error'`
instead".** This is exactly the "empty state is not actionable" flag the
audit spec asked me to look for. It is recoverable in 10 lines of code —
see HIGH-01 fix below.

### 5(c) `borg observe` → `borg search` roundtrip

```
$ HOME=/tmp/fresh2-440715504 /usr/bin/time -f "WALL=%e" \
    borg observe 'fix django auth bug in login flow'
Recorded trace 5410f519 for task: fix django auth bug in login flow
WALL=0.08

$ HOME=/tmp/fresh2-440715504 borg search 'django auth'
Name                                Confidence   Tier     Problem Class
----------------------------------------------------------------------
trace:5410f519                      observed     trace    fix django auth bug in login flow

Total: 1 pack(s)
```

✅ **The v3.2.4 roundtrip fix works.** This is genuinely the cleanest
improvement in this release — the P1.1 experiment (MiniMax) found this path
broken, v3.2.4 patched it, and the patch holds under a first-user reproducer.
Traces live in `~/.borg/traces.db` (SQLite), are discoverable by text search,
and surface with a visually distinct `trace:` prefix and `observed` confidence
tag so the user can tell them apart from community packs. This is well-done.

### 5(d) `borg setup-claude`

```
$ HOME=/tmp/fresh3-946869859 /usr/bin/time -f "WALL=%e" borg setup-claude
[setup-claude] Claude Code setup complete!
  • claude_desktop_config.json → /tmp/fresh3-946869859/.config/claude/claude_desktop_config.json
  • CLAUDE.md (created) → /tmp/CLAUDE.md

Next steps:
  1. Restart Claude Code (or reload the MCP server config)
  2. Borg MCP tools (borg_observe, borg_search, borg_suggest) will be available
  3. Run 'borg search <query>' to find relevant packs
WALL=0.06
```

**Looks great.** Here is the file it wrote:

```json
{
  "mcpServers": {
    "borg": {
      "enabled": true,
      "command": "python",                              ← ★ SHIP_BLOCKER SB-01
      "args": ["-m", "borg.integrations.mcp_server"],
      "env": {
        "PYTHONPATH": "/tmp/borg-audit-1775738954/venv/lib/python3.12/site-packages"
      }
    }
  }
}
```

**Proof that `python` does not exist on this host:**

```
$ ls /usr/bin/python
ls: cannot access '/usr/bin/python': No such file or directory

$ env -i PATH=/usr/bin:/bin python --version
env: 'python': No such file or directory
(exit 127)
```

Ubuntu 24.04 ships `python3` and `python3.12` and **no `python`**. This is
not a borg bug in the sense of "a developer forgot", it is a **deliberate
Debian/Ubuntu packaging decision** (PEP 394; `python-is-python3` is an
explicit opt-in package the user has to `apt install`). macOS with the
python.org installer has the same issue. **The generated MCP config is
broken on every major modern Python distribution.**

We already documented this same failure mode on this same host in a prior
note: *"borg-mcp + guild MCP DISABLED on this VPS because the default
`command: python` hangs the Telegram gateway for 120s"*. That is not a
theoretical concern — it already broke our own infrastructure.

**The fix is one line.** `borg/integrations/setup_claude.py` (or wherever
this config is emitted) should emit `sys.executable` instead of the string
`"python"`. This is what `mcp dev`, `claude mcp add`, and every other
well-written MCP setup script already does. See SB-01 fix below.

There is also a secondary issue: `CLAUDE.md` is written to `/tmp/CLAUDE.md`
— i.e. `os.getcwd()` at the time the user ran `borg setup-claude`. In this
case I happened to be `cd`'d to `/tmp`, so the file landed at `/tmp/CLAUDE.md`
and will be silently picked up by any other tool that reads `/tmp/CLAUDE.md`.
This is MEDIUM-01 — it should write to `$PWD/CLAUDE.md` but only if `$PWD`
looks like a project root (has a `.git/`, `pyproject.toml`, `package.json`,
etc.), and otherwise print a "please cd to your project first" message.

### Idempotency test (positive finding)

```
$ borg setup-claude   # first run: creates files
$ borg setup-claude   # second run:
[setup-claude] MCP server already configured in claude_desktop_config.json
[setup-claude] CLAUDE.md already contains borg instructions — skipping
[setup-claude] Everything already set up! Borg is ready.
```

✅ Idempotency handled correctly. No destructive overwrite.

---

## 6. MCP Path — Agent Adoption Story

I wrote a raw JSON-RPC stdio probe (`/tmp/mcp_probe.py`) that speaks the
MCP 2024-11-05 protocol, launches `borg-mcp` from the fresh venv, and calls
`initialize` + `tools/list` + three `tools/call`s. Full transcript:

```
INIT: {'jsonrpc': '2.0', 'id': 1, 'result':
        {'protocolVersion': '2024-11-05',
         'serverInfo': {'name': 'borg-mcp-server', 'version': '1.0.0'},
         'capabilities': {'tools': {}}}}

TOOL_COUNT: 17
  - borg_search
  - borg_pull
  - borg_try
  - borg_init
  - borg_apply
  - borg_publish
  - borg_feedback
  - borg_suggest
  - borg_observe
  - borg_convert
  - borg_generate
  - borg_context
  - borg_recall
  - borg_reputation
  - borg_analytics
  - borg_dashboard
  - borg_dojo

SEARCH:  {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text",
         "text":"{\"success\": true, \"matches\": [{\"name\": \"quick-debug\",
         ...systematic-debugging...]}"}], "isError": false}}

OBSERVE: {"jsonrpc":"2.0","id":4,"result":{"content":[{"type":"text",
         "text":"{\"success\": true, \"observed\": true,
         \"guidance\": \"🧠 Borg found a proven approach: **systematic-debugging**
         (confidence: tested)..."}], "isError": false}}

SUGGEST: {"jsonrpc":"2.0","id":5,"result":{"content":[{"type":"text",
         "text":"{}"}], "isError": false}}

---STDERR---
borg-mcp-server v3.2.4 ready (stdio transport)
```

**Results:**

| MCP check | Result |
|---|---|
| `borg-mcp` console script launches from `sys.executable` directly | ✅ works |
| MCP `initialize` handshake | ✅ correct protocol version, valid serverInfo |
| `tools/list` enumerates | ✅ **17 tools** |
| `borg_search` call returns structured JSON | ✅ |
| `borg_observe` call records trace + returns guidance | ✅ (genuinely impressive — it auto-suggests `systematic-debugging` for an auth task) |
| `borg_suggest` returns empty `{}` for the 2-failures case | ⚠️ HIGH-05 — see below |
| Server stderr is one single clean line `"borg-mcp-server v3.2.4 ready (stdio transport)"` | ✅ (good MCP citizen — no log spam) |

**`borg_suggest` returns `{}` for the documented trigger condition.**
The README says: *"borg_suggest — auto-suggest after 2+ consecutive failures"*.
I called it with two `TypeError`s and a task — it returned `{}`, not a
suggested pack, not a pattern hit, not an explanation of why. An agent that
adopted this tool and wired `borg_suggest` into its failure-retry loop would
see empty responses every time it tried to learn from failure. This is
HIGH-05.

**Core MCP story verdict:** `borg-mcp` itself is a well-behaved MCP server.
The **bottleneck is not the server, it is the `setup-claude` that configures
Claude Code to find it**. SB-01 alone gates the entire agent-adoption story;
everything downstream of a working MCP handshake works.

---

## 7. Docs Audit

**Files inspected:** `README.md`, `docs/EXTERNAL_TESTER_GUIDE.md`,
`docs/MCP_SETUP.md`, `docs/TESTER_MESSAGE.md`, `docs/ROADMAP.md`,
`dogfood/firstuser_audit.md`.

### Stale "guild" name references (ship-blocker bucket)

```
$ search_files pattern='guild://|guild-packs|guildpacks|guild-mcp|guild MCP' *.md
Total hits: 220 across 20 files
```

Top offenders:

| File | Hits | Ship-blocker? |
|---|---|---|
| `docs/EXTERNAL_TESTER_GUIDE.md` | **49** | **YES — SB-02** |
| `docs/MCP_SETUP.md` | 41 | YES if we ship testers there |
| `docs/UX_AUDIT_HERMES.md` | 26 | No (internal audit artefact) |
| `docs/DISTRIBUTION_INFRA_DESIGN.md` | 24 | No (design doc) |
| `borg/seeds_data/guild-autopilot/SKILL.md` | 16 | HIGH — shipped in the wheel |
| `skills/guild-autopilot/SKILL.md` | 16 | HIGH — shipped in the wheel |
| `docs/ROADMAP.md` | 9 | No (historical) |
| `README.md` | **0** | ✅ clean |

**The README itself is fully migrated to `borg` / `agent-borg`.** That is a
positive finding and it should be called out — whoever did the rename of the
top-level README did a competent job. The problem is everything *else* the
README links to.

### `docs/EXTERNAL_TESTER_GUIDE.md` — the worst case

```
Line 3: "This guide is for evaluating the guild-v2 system from an external
         tester perspective."
Line 5: "- **CLI**: `guildpacks` (renamed from `guild` to avoid conflicts)"
Line 6: "- **Python API**: `import guild`"
Line 7: "- **MCP Server**: `guild-mcp`"
Line 8: "- **Repo**: `bensargotest-sys/guild-packs`"
Line 19: "- [ ] `pip install guild-packs` installs without errors"
Line 22: "- [ ] `guildpacks version` shows a version number"
Line 23: "- [ ] `guildpacks search debugging` returns results"
Line 24: "- [ ] `guildpacks try guild://systematic-debugging` shows pack preview"
Line 25: "- [ ] `guildpacks pull guild://systematic-debugging` saves locally"
Line 26: "- [ ] `guildpacks apply systematic-debugging --task 'fix a bug'`"
Line 28: "### MCP Server (guild-mcp)"
Line 29: "- [ ] `guild-mcp` responds to `tools/list` with 9 tools"
Line 32: "- [ ] Agent can call `guild_search` via MCP"
Line 33: "- [ ] Agent can call `guild_try` via MCP"
...
```

A tester who follows this guide will:

1. Try `pip install guild-packs` → **404** (`No matching distribution found`).
2. If they figure out it's really `agent-borg`, try `guildpacks version` →
   **`command not found`**.
3. Try `guild-mcp tools/list` → **`command not found`**.
4. Conclude "this project is abandoned" and leave.

This is the textbook "old name is a ship-blocker" clause. **Delete this
file** (or rewrite it top-to-bottom; it is nine commits out of date). This
is SB-02.

### README example-command testing

I ran every example command from `README.md`:

| README line | Command | Result |
|---|---|---|
| L45–46 | `pip install agent-borg && borg start` | ✅ works |
| L58 | `borg debug "ModuleNotFoundError: No module named 'cv2'"` | ⚠️ routes to `missing_dependency` (correct) but the *output text* the README shows (`[dependency-resolution] ... 47/52 successes (90%) over 127 uses`) **does not match** what borg actually prints. The real classifier returns `[missing_dependency]` with different stats. The README is either showing aspirational output or an old format. MEDIUM-02. |
| L101 | `borg debug "your error message here"` | ✅ works (returns "no match" for a literal string, exits 0 — see HIGH-04) |
| L137–138 | `borg generate systematic-debugging --format claude` | ❌ **FAILS** — "invalid choice: 'claude' (choose from 'cursorrules', 'clinerules', 'claude-md', 'windsurfrules', 'all')". **SB-03.** |
| L143–144 | `borg generate systematic-debugging --format cursor` | ❌ **FAILS** — same error. **SB-03.** |
| L149–150 | `borg generate systematic-debugging --format cline` | ❌ **FAILS** — same error. **SB-03.** |
| L155–156 | `borg generate systematic-debugging --format windsurf` | ❌ **FAILS** — same error. **SB-03.** |
| L162 | `{"mcpServers":{"borg":{"command":"borg-mcp"}}}` | ✅ works (and is *correct* — better than what `setup-claude` generates) |
| L171 | `borg debug "django.db.utils.OperationalError: no such column: app_user.email"` | ✅ works, routes to `schema_drift` |
| L174 | `borg observe "refactor authentication to use JWT tokens"` | ✅ works |
| L177 | `borg search "docker networking"` | ✅ works (returns 0 matches — not a lie, just an empty corpus) |

**Four out of four `borg generate` examples in the README are wrong.** The
README documents `--format claude|cursor|cline|windsurf`; the actual CLI only
accepts `--format claude-md|cursorrules|clinerules|windsurfrules|all`.
*Every single platform-setup snippet in the README is broken.* This is
SB-03 and it is the single most embarrassing ship-gate finding in this audit,
because the README *leads with* "Platform Setup" as the hero feature.

The fix is a judgment call: either rename the argparse choices (and alias
the old ones for back-compat), or fix the four README lines. I recommend
**renaming the choices** because `--format claude` is the name a human would
guess, and `claude-md` is internal jargon.

### MCP docs

`README.md` L162 says:

```json
{ "mcpServers": { "borg": { "command": "borg-mcp" } } }
```

This is **correct** and would work on every host (because `borg-mcp` is the
console-script entry point and pip puts it on `$PATH`). But `borg setup-claude`
**does not generate this config** — it generates the broken `"command":
"python"` version. So the README is right, the tool is wrong, and a user who
copies the README will have a working setup while a user who trusts
`setup-claude` will have a broken one. Internal inconsistency.

---

## 8. Error Modes

I deliberately triggered six failure modes and graded each on "does the user
know what to do next?":

| Failure | Command | Output | Grade |
|---|---|---|---|
| Missing required arg | `borg search` | `borg search: error: the following arguments are required: query` + usage | ✅ argparse default, clear |
| Pack not found | `borg apply fake-pack-xyz --task 'test'` | `Error (pack not found): Pack not found: fake-pack-xyz. Pull it first with borg_pull.` + JSON error body | ⚠️ says `borg_pull` (the MCP tool name) but the user is on the CLI — should say `borg pull`. LOW-02 |
| Bad URI to pull | `borg pull not-a-real-uri` | `Error: Pack not found: not-a-real-uri` + hint: *"Expected URI format: guild://domain/pack-name"* | ⚠️ Hint text says `guild://` — stale naming inside the error body. LOW-03 |
| Empty error string to debug | `borg debug ''` | Long "ERROR: / no matching problem class" message with the 12 known classes listed | ✅ actionable and honest |
| Fake feedback session ID | `borg feedback fake-session-123` | `Error: Session not found: fake-session-123` — exit 1 | ✅ correct |
| Generate a missing pack | `borg generate nonexistent-pack` | `Error: Pack not found: nonexistent-pack` — exit 1 | ✅ correct |
| Network-blackhole `borg search` | `BORG_REMOTE_INDEX=https://blackhole.invalid.tld/index.json borg search debugging` | Returns local packs successfully, **silently ignores remote failure** | ⚠️ MEDIUM-05 — silent network failure. A user on a plane will never know the remote index wasn't fetched. Should emit a one-line `(remote index unavailable — showing local only)` hint. |
| Permission-denied init (tried `chmod 555 $CWD; borg init`) | `borg init new-pack` | Created pack at `$HOME/.hermes/guild/new-pack/pack.yaml` (writes to HOME, not CWD) | ✅ actually a positive finding — `init` is immune to cwd-permission issues |
| Missing API key | (N/A) — borg **has no API key** in the core path | — | ✅ positive finding — "no API keys, no config" really is true for the CLI. |

**Error-mode verdict:** borg's error messages are **honest and generally
actionable**, with three minor stale-name leaks (LOW-02, LOW-03) and one
silent-network-failure bug (MEDIUM-05). This is well above average for a
CLI at this maturity level — ruff is famously good at error messages and
borg is in the same zip code.

---

## 9. Performance

All timings measured with `/usr/bin/time -f "WALL=%e"` on this VPS, inside
the fresh `/tmp/borg-audit-1775738954` venv. Three runs per command:

```
help_run1_WALL=0.05
help_run2_WALL=0.09
help_run3_WALL=0.05

search_run1_WALL=0.60
search_run2_WALL=0.36
search_run3_WALL=0.50

observe_run1_WALL=0.08
observe_run2_WALL=0.08
observe_run3_WALL=0.08

list_run1_WALL=0.28
list_run2_WALL=0.30
list_run3_WALL=0.29

version_WALL=0.05
setup-claude_WALL=0.06
```

| Command | Min | Median | Max | 2 s ship-blocker threshold |
|---|---|---|---|---|
| `borg --help` | 0.05 s | 0.05 s | 0.09 s | ✅ pass |
| `borg --version` | 0.05 s | 0.05 s | 0.05 s | ✅ pass |
| `borg search debugging` | 0.36 s | 0.50 s | **0.60 s** | ✅ pass (but slow for a text search) |
| `borg observe <task>` | 0.08 s | 0.08 s | 0.08 s | ✅ pass |
| `borg list` | 0.28 s | 0.29 s | 0.30 s | ✅ pass |
| `borg setup-claude` | 0.06 s | — | — | ✅ pass |
| `pip install agent-borg` | 5.40 s | — | — | ✅ pass (one-time) |

**Nothing exceeds the 2-second cold-start ship-gate threshold.** This is a
clear positive. borg is genuinely snappy — the 0.6 s worst-case on
`borg search` is an outlier worth profiling (see MEDIUM-06) but is still
well inside CLI UX budgets.

**Context:** for comparison, `ruff check .` on an empty repo is ~0.005 s.
`uv --version` is ~0.003 s. Python-CLI-measured against Rust-CLIs this is
*expected* to be ~100× slower at the floor because of the interpreter start.
borg is pulling in FastAPI + pydantic on every invocation, and that is the
main reason `--help` is at 0.05 s rather than 0.01 s. Moving uvicorn/fastapi
under an extra (MEDIUM-03) would compress this further.

---

## 10. Comparison to Industry Baseline

I picked three famously-good `pip install` experiences as reference points:
`ruff`, `uv`, and `httpx`.

| Dimension | `pip install ruff` | `pip install uv` | `pip install httpx` | `pip install agent-borg` |
|---|---|---|---|---|
| Wall-clock install | ~2 s | ~3 s | ~3 s | **5.4 s** |
| Deps | 0 (Rust binary) | 0 (Rust binary) | 4 (httpcore, anyio, certifi, idna) | **21** |
| First command works with zero config | `ruff check .` — yes | `uv venv` — yes | `python -c "import httpx; httpx.get(...)"` — yes | `borg debug "..."` — **yes** ✅ |
| Home-page URL matches tool name | `astral-sh/ruff` ✅ | `astral-sh/uv` ✅ | `encode/httpx` ✅ | **`bensargotest-sys/guild-packs`** ❌ (SB-04) |
| README example commands work verbatim | ✅ | ✅ | ✅ | **❌ — 4 broken `--format` lines** (SB-03) |
| `--help` under 200 ms | ✅ (10 ms) | ✅ (3 ms) | N/A (library) | ✅ (50 ms) |
| Ships usable data on first install | N/A (ruff is a linter) | N/A (uv is a tool) | N/A (httpx is a library) | **❌ — empty-DB cold-start** (HIGH-01) |
| Agent-integration story | N/A | N/A | N/A | **❌ — broken `python` shim** (SB-01) |

**Honest takeaway:** on the **pure CLI axis**, borg is closer to ruff/uv
than you would expect — install is fast, help is fast, error messages are
good, there are no API keys. On the **agent-integration axis**, borg is
closer to an abandoned 2022 side project — the generated MCP config doesn't
work on the most common modern Linux distribution, and the external tester
guide sends people to a package name that no longer exists. The gap between
"CLI that works" and "agent integration that works" is the gap v3.3.0 has
to close.

---

## 11. Defect Inventory

Ranked strictly. No "everything is important" padding. SHIP_BLOCKER means
v3.3.0 **does not ship** until this is fixed. HIGH is "fix in v3.3.0 or I
will veto the release note that says 'ready for users'". MEDIUM is
"v3.3.x patch window is fine". LOW is "nice to have, no urgency".

| ID | Severity | Component | Reproducer (command) | Observed | Impact | Proposed fix | Effort |
|---|---|---|---|---|---|---|---|
| **SB-01** | SHIP_BLOCKER | `setup-claude` config emission | `borg setup-claude; cat ~/.config/claude/claude_desktop_config.json` | `"command": "python"` | Every Ubuntu 24 / pyenv / macOS-stock-installer user gets a broken MCP server that fails with ENOENT, agent integration is invisible | Replace hard-coded `"python"` with `sys.executable`. File: `borg/integrations/setup_claude.py` (or wherever the config dict is built — grep for the literal string `"command": "python"`). See fix below. | **30 min** |
| **SB-02** | SHIP_BLOCKER | `docs/EXTERNAL_TESTER_GUIDE.md` | `grep -c guild docs/EXTERNAL_TESTER_GUIDE.md` → 49; every example command is broken | Every external tester we hand this file to hits `pip install guild-packs` → 404, concludes project is dead | Delete the file, or rewrite it head-to-toe using the borg/agent-borg/borg-mcp names. Recommend delete + redirect link in README to a short new `docs/TRYING_BORG.md`. | **1 h** |
| **SB-03** | SHIP_BLOCKER | `borg generate --format` vs README | `borg generate systematic-debugging --format claude` → `argparse: invalid choice` | Every `Platform Setup` snippet in the README is a broken copy-paste | Rename argparse choices from `{cursorrules, clinerules, claude-md, windsurfrules}` to `{cursor, cline, claude, windsurf}` and alias the old ones for back-compat. Alternative: fix 4 lines in README.md (lines 138, 144, 150, 156). Recommend rename — `claude` is what a user will guess. | **45 min** |
| **SB-04** | SHIP_BLOCKER | `pyproject.toml` project URLs | `pip show agent-borg` → 3× `https://github.com/bensargotest-sys/guild-packs` | PyPI Homepage link leads to a repo whose name contradicts the tool name | Update `[project.urls]` in `pyproject.toml` to the real `agent-borg` repo URL, cut a 3.2.5 metadata-only release or roll into 3.3.0 | **15 min** |
| **HIGH-01** | HIGH | Cold-start seed corpus | `HOME=/tmp/x HERMES_HOME=/tmp/x/.hermes borg search debugging` → `No packs found.` | First-user cold-start returns empty results; the tool looks broken | On first run, copy `borg/seeds_data/*.md` (already shipped in wheel) into `$HERMES_HOME/guild/` as pack skeletons, OR make `borg search` fall back to `seeds_data` when `HERMES_HOME/guild` is empty. Emit an "initialized starter pack library (N packs)" one-liner on the first non-empty search. | **2 h** |
| **HIGH-02** | HIGH | Stale `guild://` URI scheme in user-facing text | `borg pull --help` → `"Pack URI (guild://, https://, or local path)"` | Users see the old product name in tool output every time they ask for help | Global search/replace in CLI help strings: `guild://` → `borg://`, keep accepting both schemes in the parser. File: `borg/cli.py` + any HelpFormatter strings. | **30 min** |
| **HIGH-03** | HIGH | `feedback-v3 --success` validation | `borg feedback-v3 --pack foo --success maybe` → accepted | Garbage data reaches the feedback DB | Change the argparse `type=` to a function that accepts only `{yes,no,y,n,true,false,1,0}`, rejects everything else with a clear error. File: `borg/cli.py` around the `feedback-v3` subparser. | **15 min** |
| **HIGH-04** | HIGH | `borg debug` exit code on no-match | `borg debug ''; echo $?` → `0` | Automation treats "no match found" as success | Return exit 2 when classifier returns "no match" so scripts can detect it. File: `borg/cli.py` near `cmd_debug`. | **15 min** |
| **HIGH-05** | HIGH | `borg_suggest` MCP tool returns `{}` for the documented trigger | MCP probe: `tools/call borg_suggest {"failures":[...],"task":"..."}` → `{}` | Documented auto-suggest-after-2-failures path is dead | Either remove the tool from the `tools/list` until it works, or fix its implementation to actually match failures against the pack catalogue. File: `borg/integrations/mcp_server.py` (grep for `borg_suggest`). | **2 h** |
| **HIGH-06** | HIGH | Stale "guild" references in shipped SKILL.md files | `borg/seeds_data/guild-autopilot/SKILL.md` has 16 hits; the wheel **ships** these | Agents loading the skill at runtime see the old product name | Rename directory `guild-autopilot/` → `borg-autopilot/`, update file contents, update packaging `include` list. | **45 min** |
| **MEDIUM-01** | MEDIUM | `setup-claude` writes `CLAUDE.md` to `os.getcwd()` | `cd /tmp; borg setup-claude` → `CLAUDE.md` lands in `/tmp` | User pollutes `/tmp` or `$HOME` with a CLAUDE.md that gets picked up by other tools | Require `$PWD` to look like a project root (has `.git/`, `pyproject.toml`, `package.json`, `Cargo.toml`, etc.) or print a `cd to your project first` warning and offer `--force` | **1 h** |
| **MEDIUM-02** | MEDIUM | README.md shows fabricated example output | README L60–90: `"EVIDENCE: 47/52 successes (90%) over 127 uses"` does not match real `borg debug` output | Users copy-paste the command, see different output, lose trust | Rerun `borg debug "ModuleNotFoundError..."` and paste the *actual* current output into README. Revisit quarterly. | **20 min** |
| **MEDIUM-03** | MEDIUM | FastAPI/uvicorn in core install | `pip show agent-borg` → 21 deps | 6 MB of dep surface for a read-only CLI user | Move `fastapi`, `uvicorn[standard]`, `sse-starlette` under `agent-borg[server]` extra. Dynamic-import in `borg/integrations/http_server.py` with a friendly "please install agent-borg[server]" fallback. | **1 h** |
| **MEDIUM-04** | MEDIUM | `setup-claude` has no flags | `borg setup-claude --help` → zero options | Can't regenerate, can't specify Python, can't dry-run | Add `--python PATH`, `--dry-run`, `--force`, `--claude-md-path PATH`. | **1 h** |
| **MEDIUM-05** | MEDIUM | Silent remote-index failure | `BORG_REMOTE_INDEX=https://blackhole.invalid.tld/index.json borg search debugging` → returns results, no warning | User on a plane never knows remote packs aren't being considered | Emit one-line stderr hint: `(remote index unreachable — showing local only)` when the fetch fails. Never block the search. | **30 min** |
| **MEDIUM-06** | MEDIUM | `borg search` takes 0.36–0.60 s | `time borg search debugging` | 10× slower than `borg observe` on the same startup budget | Profile with `python -X importtime -m borg.cli search debugging`. Likely candidates: sentence-transformers lazy-import not actually lazy, or a per-call YAML load. | **2 h** |
| **LOW-01** | LOW | `borg start` help text suggests `pip install agent-borg && borg start` to a user who is already inside `borg start` | `borg start --help` | Minor self-contradiction | One-line edit. | **5 min** |
| **LOW-02** | LOW | `borg apply` error says "pull it first with `borg_pull`" (MCP tool name) | `borg apply fake --task x` | Confusing — user is on the CLI | Detect context (CLI vs MCP) when formatting the error, say `borg pull` on CLI. | **15 min** |
| **LOW-03** | LOW | `borg pull` error hint mentions `guild://` URI format | `borg pull not-a-real-uri` | Stale naming in error body | Same global rename as HIGH-02. | **5 min** |
| **LOW-04** | LOW | `borg list` shows a pack named `systematic-debugging.rubric` with empty `problem_class` | `borg list` on this host | Cosmetic | Filter `.rubric` suffixes out of `borg list` default view or label them properly. | **15 min** |

**Severity breakdown:** 4 ship blockers, 6 high, 6 medium, 4 low. **Total
estimated effort for all 4 ship blockers: ~2.5 hours of engineering.**
Total for SB + HIGH: ~9 hours. That is not a hard release to ship.

---

## 12. Remediation Plan for v3.3.0

This is the minimum diff to land in v3.3.0 for the release note to honestly
say *"agent-borg is ready for real users"*.

### Fix SB-01 — `setup-claude` uses `sys.executable`

**File:** `borg/integrations/setup_claude.py` (or whichever module builds
the config dict — grep for the literal string `"command": "python"` inside
the `borg` package).

**Patch (conceptual):**

```python
# BEFORE
config = {
    "mcpServers": {
        "borg": {
            "enabled": True,
            "command": "python",
            "args": ["-m", "borg.integrations.mcp_server"],
            "env": {"PYTHONPATH": site_packages_path},
        }
    }
}

# AFTER
import sys, shutil
# Prefer the pip-installed console script if present — it's the cleanest option
borg_mcp = shutil.which("borg-mcp")
if borg_mcp:
    server_cfg = {"command": borg_mcp}
else:
    server_cfg = {
        "command": sys.executable,  # absolute path to THIS Python
        "args": ["-m", "borg.integrations.mcp_server"],
    }
config = {"mcpServers": {"borg": {"enabled": True, **server_cfg}}}
```

**Acceptance test:**

```bash
python3.12 -m venv /tmp/t && source /tmp/t/bin/activate
pip install agent-borg
HOME=/tmp/t-home borg setup-claude
python -c "
import json
cfg = json.load(open('/tmp/t-home/.config/claude/claude_desktop_config.json'))
cmd = cfg['mcpServers']['borg']['command']
assert cmd.endswith('borg-mcp') or cmd.endswith('python3') or cmd.endswith('python3.12'), cmd
import shutil; assert shutil.which(cmd) or cmd.startswith('/'), f'not resolvable: {cmd}'
print('PASS:', cmd)
"
```

### Fix SB-02 — Delete / rewrite `EXTERNAL_TESTER_GUIDE.md`

**Option A (recommended):** `git rm docs/EXTERNAL_TESTER_GUIDE.md` and add a
new short `docs/TRYING_BORG.md` (≤50 lines) that says:

```markdown
# Trying Borg

```bash
pip install agent-borg
borg start
# or paste an error:
borg debug "your error message"
```

## Adopt borg inside Claude Code

```bash
borg setup-claude
# Restart Claude Code. The `borg_*` tools will appear in the tool list.
```

Something broken? Open an issue at
https://github.com/<real-repo-name>/issues/new
```

**Option B:** rewrite in place. Acceptance: `grep -i 'guild' docs/TRYING_BORG.md`
returns zero lines.

### Fix SB-03 — Rename `--format` choices OR fix the README

**Recommended:** rename. Users type `claude`, not `claude-md`.

**File:** `borg/cli.py` — find the `generate` subparser.

```python
# BEFORE
parser_generate.add_argument(
    "--format",
    choices=["cursorrules", "clinerules", "claude-md", "windsurfrules", "all"],
    default="all",
)

# AFTER
FORMAT_ALIASES = {
    "cursor": "cursorrules", "cursorrules": "cursorrules",
    "cline": "clinerules", "clinerules": "clinerules",
    "claude": "claude-md", "claude-md": "claude-md",
    "windsurf": "windsurfrules", "windsurfrules": "windsurfrules",
    "all": "all",
}
parser_generate.add_argument(
    "--format",
    choices=sorted(FORMAT_ALIASES.keys()),
    default="all",
)
# Then in cmd_generate: format_key = FORMAT_ALIASES[args.format]
```

**Acceptance test:**

```bash
borg generate systematic-debugging --format claude  | head -1   # exit 0
borg generate systematic-debugging --format cursor  | head -1   # exit 0
borg generate systematic-debugging --format cline   | head -1   # exit 0
borg generate systematic-debugging --format windsurf| head -1   # exit 0
# Old names still work:
borg generate systematic-debugging --format claude-md | head -1 # exit 0
```

### Fix SB-04 — `pyproject.toml` project URLs

**File:** `pyproject.toml`

```toml
# BEFORE
[project.urls]
Homepage      = "https://github.com/bensargotest-sys/guild-packs"
Repository    = "https://github.com/bensargotest-sys/guild-packs"
Documentation = "https://github.com/bensargotest-sys/guild-packs#readme"

# AFTER
[project.urls]
Homepage      = "https://github.com/<real-agent-borg-repo>"
Repository    = "https://github.com/<real-agent-borg-repo>"
Documentation = "https://github.com/<real-agent-borg-repo>#readme"
Issues        = "https://github.com/<real-agent-borg-repo>/issues"
```

**Acceptance:** `pip show agent-borg | grep -i url` shows the real URL;
visiting the PyPI page links to a repo whose README matches the tool.

### Fix HIGH-01 — Seed corpus on first run

**File:** `borg/core/search.py` or a new `borg/core/bootstrap.py`.

```python
def ensure_seed_corpus(borg_dir: Path) -> int:
    """Idempotently seed $HERMES_HOME/guild/ from packaged seed files."""
    if borg_dir.exists() and any(borg_dir.glob("*/pack.yaml")):
        return 0
    seeds_root = Path(__file__).parent.parent / "seeds_data"
    borg_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for seed_md in seeds_root.glob("*.md"):
        pack_name = seed_md.stem
        pack_dir = borg_dir / pack_name
        pack_dir.mkdir(exist_ok=True)
        # convert .md → minimal pack.yaml (or copy wholesale)
        ...
        n += 1
    return n

# at the top of cmd_search:
seeded = ensure_seed_corpus(BORG_DIR)
if seeded:
    print(f"(initialized starter pack library: {seeded} packs)", file=sys.stderr)
```

**Acceptance test:**

```bash
HOME=/tmp/clean-$(date +%N) HERMES_HOME=$HOME/.hermes borg search debugging
# expect: stderr says "(initialized starter pack library: N packs)"
# expect: stdout shows at least 5 matches
```

### Fix HIGH-02 through HIGH-06

Batch these into a single "terminology + correctness" PR:

- **HIGH-02:** `sed -i 's|guild://|borg://|g' borg/cli.py` (plus the help
  strings for `pull`, `apply`, `publish`). Keep the parser accepting both.
- **HIGH-03:** Add `--success` validator function, reject `maybe`.
- **HIGH-04:** `cmd_debug` returns `1` if classifier result is `"unknown"`.
- **HIGH-05:** Either (a) implement `borg_suggest` properly against the trace
  matcher, or (b) remove it from `tools/list` and update the README.
- **HIGH-06:** `git mv borg/seeds_data/guild-autopilot borg/seeds_data/borg-autopilot`;
  update contents; confirm `MANIFEST.in` / pyproject `include` picks up the new path.

### Acceptance gate for v3.3.0

A new file `docs/20260409-0800_user_readiness/V330_SHIP_GATE.sh` should exist
with a shell script that:

1. Creates a fresh venv
2. `pip install agent-borg==3.3.0`
3. Runs all four ship-blocker reproducers from Section 11 and asserts they
   now pass
4. Runs the MCP JSON-RPC probe from Section 6 and asserts `tools/list` returns
   ≥ 17 tools AND that `borg_suggest` returns non-empty for the 2-failures case
5. Runs `grep -c guild docs/EXTERNAL_TESTER_GUIDE.md` — expects 0 or "no such
   file"
6. Runs all 4 `borg generate --format {claude,cursor,cline,windsurf}` and
   asserts exit 0 on each
7. Runs `pip show agent-borg | grep -i url` and asserts no `guild-packs`
   substring

**v3.3.0 does not ship until this script returns exit 0.**

---

## 13. Verdict by Adoption Path

### (a) Solo developer trying borg once

**YES, with caveats.** The install is fast, the CLI is snappy, `borg debug
"your error"` works out of the box for Python/Django errors, and `borg
observe → borg search` is an honest-to-god working feature. A Python/Django
developer with a real traceback will get real value in under 2 minutes.

**Caveats that gate a clean YES:**
- They must happen to be on `python3` alone and never touch `borg setup-claude`.
- They must not paste `--format claude` from the README.
- They must ignore the "No packs found." empty state the first time.

### (b) An agent (Claude Code / Cursor / Codex) adopting borg via MCP

**NO — not in v3.2.4.** The `borg setup-claude` command produces a config
that **does not work on Ubuntu 24 / Debian 12 / macOS python.org / pyenv** —
the four most common developer environments. An agent framework that runs
`borg setup-claude` as its adoption path will silently end up with an MCP
server the agent can't see. The MCP server itself (`borg-mcp`) works
beautifully when launched correctly (17 tools, clean handshake, structured
JSON responses). The bug is strictly in the "connect Claude to it" path.

**YES as soon as SB-01 lands.** (The other SBs don't gate agent-adoption
directly — only the broken Python shim does.)

### (c) Team adoption at a mid-sized company

**NO — not in v3.2.4.** A security-conscious engineering director who does
due diligence on a new tool will:

1. Click the PyPI homepage link → land on `bensargotest-sys/guild-packs` →
   name mismatch → ⚠️
2. Open `docs/EXTERNAL_TESTER_GUIDE.md` → every command is wrong → ❌
3. Try the README's `borg generate --format cursor` → error → ❌
4. See the install pulls in FastAPI and uvicorn → why does my CLI need an
   HTTP server? → ⚠️
5. Flag to leadership: "interesting tool, not ready for team rollout".

Zero of those five signals is about correctness of the packs — borg's actual
intellectual value is never even evaluated before the tool loses the
evaluation on presentation. These are cosmetic/packaging bugs with
engineering-leadership-visible consequences.

**YES in v3.3.0 if the ship gate in Section 12 passes**, because the same
due-diligence pass at that point finds a tool that installs cleanly,
points at the right repo, ships working example commands, and actually
boots up inside Claude Code on their engineers' Ubuntu laptops.

---

## Appendix A — Audit Artefacts

All reproduction files are under `/tmp/borg-audit-1775738954/`:

- `install.log` — full `pip install` output, 5.40 s wall clock
- `borg_help.log` — `borg --help` output
- `subcmd_helps.log` — 258 lines, every subcommand `--help`
- `entrypoints.log` — wheel entry points + metadata
- `search_empty.log` — contaminated-HOME search
- `fresh_hermes_search.log` — clean-HOME search (the `No packs found.` state)
- `observe1.log` — observe→search roundtrip proof
- `setup_claude.log` — `setup-claude` output + resulting config
- `/tmp/mcp_probe.py`, `/tmp/mcp_probe.log` — raw MCP JSON-RPC probe script + captured 17-tool list

**All artefacts are timestamped under `/tmp/borg-audit-1775738954/` and
will survive until `/tmp` is swept.**

## Appendix B — Positive Findings (do not regress)

In the interest of not turning the report into a hit-piece, here is a
ledger of what borg v3.2.4 does **well** and must not regress in v3.3.0:

1. **Install is fast and clean.** 5.4 s, zero warnings, zero native compilation.
2. **CLI is snappy.** Every fast command is under 100 ms.
3. **`borg observe → borg search` roundtrip works.** The v3.2.4 patch is
   real and it holds.
4. **`borg debug` language-guard works.** Non-Python errors get "no match"
   honestly instead of Django-migration garbage.
5. **MCP server is well-behaved.** Single clean stderr line, valid MCP
   2024-11-05 handshake, 17 tools enumerated, JSON-structured responses.
6. **Error messages are actionable.** Above-average for a CLI at this
   maturity level — comparable to ruff.
7. **`borg setup-claude` is idempotent.** Re-runs don't clobber existing
   configs; they print "already configured" instead.
8. **The README is fully migrated off the `guild` name.** Whoever did that
   pass did a competent job — it's only the downstream files that lag.
9. **JSON output is consistent.** `--json` on every subcommand returns a
   stable `{success, matches, total, mode, ...}` shape. Good for scripting.
10. **Exit codes are mostly correct** (except HIGH-04).

These are the load-bearing positives. If v3.3.0 trades any of them away to
ship SB-01..SB-04 faster, that's a net loss.

---

## Signoff

**Audit author:** Claude Code on behalf of AB
**Audit duration:** ~35 minutes wall clock (under the 60-min budget)
**Audit cost:** < $0.05 (under the $0.50 ceiling)
**Ship verdict:** NOT READY at v3.2.4 → 4 ship-blockers identified → ~2.5 h
engineering to unblock → **READY at v3.3.0 if the ship gate in Section 12
returns exit 0**.

This audit is canonical. Do not re-run it for v3.2.4; re-run it against
v3.3.0 as the release-gate check.
