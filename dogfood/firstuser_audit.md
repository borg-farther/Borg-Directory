# Borg First-User Experience Audit

**Date:** 2026-04-07
**Version:** agent-borg 3.1.0 (PyPI)
**Auditor:** Automated fresh-venv simulation
**Environment:** Python 3.11, clean venv at /tmp/borg-firstuser-audit/venv

---

## Step-by-Step Results

### Step 1: Create fresh venv
- **Command:** `python3 -m venv /tmp/borg-firstuser-audit/venv`
- **Exit code:** 0
- **Time:** 4.2s
- **Impression:** Clean, no issues.

### Step 2: pip install agent-borg
- **Command:** `pip install agent-borg`
- **Exit code:** 0
- **Time:** 5.1s
- **Impression:** Fast install. Only 4 runtime deps (pyyaml, fastapi, uvicorn, sse-starlette). Lightweight. Good.
- **Friction:** Package name is `agent-borg` but CLI is `borg` — minor discoverability gap but acceptable. PyPI summary is clear: "Proven workflows for AI agents."

### Step 3: borg --help
- **Command:** `borg --help`
- **Exit code:** 0
- **Time:** <0.5s
- **Impression:** GOOD. Clean help output. 16 subcommands listed with short descriptions. Tagline "Semantic reasoning cache for AI agents" is clear.
- **Friction:** None. This works perfectly.

### Step 4: borg version
- **Command:** `borg version`
- **Exit code:** 0
- **Time:** <0.1s
- **Output:** `borg 3.1.0`
- **Impression:** Clean. Works.

### Step 5: borg --version
- **Command:** `borg --version`
- **Exit code:** 0
- **Time:** <0.1s
- **Output:** `borg 3.1.0`
- **Impression:** Both `version` and `--version` work. Good.

### Step 6: PyPI page description
- **Summary:** "Proven workflows for AI agents — execution-proven, safety-scanned, feedback-improving"
- **Homepage:** https://github.com/bensargotest-sys/guild-packs
- **Impression:** Summary is clear but the GitHub URL looks like a test account ("bensargotest-sys"). This hurts credibility for a new user.
- **Friction:** No License field set. No long description visible via pip. A new user checking PyPI would want to see examples, quickstart, and what "packs" are.

### Step 7: borg search debugging
- **Command:** `borg search debugging`
- **Exit code:** 0
- **Time:** 0.55s
- **Output:** 6 packs found including `quick-debug`, `systematic-debugging`, `agent-a-debugging`
- **Impression:** GOOD. Results are relevant. Confidence tiers shown (tested/guessed/inferred). Problem class descriptions help.
- **Friction:** "my-pack" and "old-pack" show up in results — these look like test artifacts, not real packs. Pollutes the search results for new users. The `.rubric` entry is confusing — why is it a separate pack?

### Step 8: borg list
- **Command:** `borg list`
- **Exit code:** 0
- **Time:** 0.25s
- **Output:** 6 packs listed
- **Impression:** MODERATE. Shows local packs with IDs and confidence levels.
- **Friction:** `my-skill` and `test-scaffold-pack` appear as local packs — these are clearly dev artifacts. A fresh install should have ZERO local packs (these come from shared ~/.hermes). The guild:// prefix is unexplained — what is "guild"?

### Step 9: borg init my-first-pack
- **Command:** `borg init my-first-pack`
- **Exit code:** 0
- **Time:** 0.06s
- **Output:** Created scaffold at `/root/.hermes/guild/my-first-pack/pack.yaml`
- **Impression:** GOOD. Fast, clear output. Tells you exactly what to edit.
- **Friction:** Creates in `~/.hermes/guild/` — a new user might expect it in their current directory. No explanation of pack.yaml format or link to docs.

### Step 10: borg try systematic-debugging
- **Command:** `borg try systematic-debugging`
- **Exit code:** 0
- **Time:** 0.31s
- **Impression:** EXCELLENT. Shows pack name, problem class, confidence, phases, and safety verdict. Perfect preview.
- **Friction:** None. This is exactly what a user needs before committing.

### Step 11: borg debug 'TypeError: NoneType has no attribute get'
- **Command:** `borg debug 'TypeError: NoneType has no attribute get'`
- **Exit code:** 0
- **Time:** 0.11s
- **Impression:** EXCELLENT. This is the killer feature. Detailed root cause analysis, investigation trail with specific file paths, resolution sequence, anti-patterns to avoid, and evidence stats (47/52 successes, 90% rate, 3.1min avg resolve time). Extremely useful.
- **Friction:** The investigation trail references Django-specific files (django/contrib/admin/options.py) even though the user didn't mention Django. The guidance is generic but examples are Django-specific — could confuse users on other frameworks.

### Step 12: borg generate systematic-debugging --format all
- **Command:** `borg generate systematic-debugging --format all`
- **Exit code:** 0
- **Time:** 0.12s
- **Impression:** EXCELLENT. Generates .cursorrules, .clinerules, CLAUDE.md, and .windsurfrules all at once. Output is well-formatted and complete.
- **Friction:** Output goes to stdout only — no files created. A user might expect `--format all` to write files. Need `> file` or a `--output` flag.

### Step 13: borg setup-claude
- **Command:** `borg setup-claude`
- **Exit code:** 0
- **Time:** 0.06s
- **Impression:** GOOD. Creates config and CLAUDE.md. Clear next-steps output.
- **Friction:** Writes to `/root/.config/claude/claude_desktop_config.json` — this could overwrite existing Claude config. No backup made. No warning.

### Step 14: borg autopilot
- **Command:** `borg autopilot`
- **Exit code:** 0
- **Time:** 0.09s
- **Impression:** GOOD. Zero-config claim is accurate. Explains what was configured and what happens next.
- **Friction:** Says "Skill already installed — skipping SKILL.md" but this is the first time running it. Confusing message for a new user. References "SKILL.md" without explaining what it is.

### Step 15: Python import
- **Command:** `from borg.core.generator import generate_rules`
- **Exit code:** 0
- **Impression:** GOOD. API is importable. Module structure is clean.
- **Friction:** No documentation on what's importable. A user would have to guess module paths.

### Step 16: MCP server
- **Command:** `python -m borg.integrations.mcp_server`
- **Exit code:** 0 (exits immediately)
- **Impression:** CONFUSING. Server exits immediately with no output. A new user would think it's broken.
- **Friction:** No `--help` output. No startup banner. No "listening on stdio" message. The `borg-mcp` entry point also exists but isn't documented. Expected behavior (reads JSON-RPC from stdin) but zero user feedback about what's happening.

---

## Overall Rating: 7/10

The core CLI experience is surprisingly polished. Commands are fast, output is clear, and the `debug` command is genuinely impressive. The main issues are environmental pollution (test artifacts in search/list), missing documentation hooks, and the MCP server UX.

---

## Top 5 Friction Points (P0 Onboarding Blockers)

### 1. Test artifacts pollute search/list results (P0)
- `my-pack`, `old-pack`, `my-skill`, `test-scaffold-pack` appear in fresh install
- These come from shared `~/.hermes` state, not from the package
- **Fix:** Ship clean bundled packs only. Filter out non-published packs from search. Add a `--builtin-only` flag or separate user packs from curated packs.

### 2. MCP server gives zero feedback (P1)
- `python -m borg.integrations.mcp_server` exits silently
- `borg-mcp` entry point exists but undocumented
- No `--help`, no startup message, no error
- **Fix:** Print "Borg MCP server ready (JSON-RPC over stdio). Connect via Claude Code or Cursor." to stderr on startup. Add `--help` with usage instructions.

### 3. `borg generate` outputs to stdout only (P1)
- `--format all` dumps everything to terminal
- User expects files to be written
- **Fix:** Add `--output-dir` flag. When `--format all`, write .cursorrules, .clinerules, CLAUDE.md, .windsurfrules to CWD by default.

### 4. `borg debug` examples are Django-specific regardless of context (P2)
- Investigation trail always references Django files
- User didn't mention Django in their error
- **Fix:** Make investigation trail generic or detect framework from context. At minimum, label examples as "Example from Django codebase" rather than presenting as universal.

### 5. No quickstart / getting-started flow (P2)
- After `pip install`, user must guess what to do
- No `borg quickstart` or `borg tutorial` command
- `borg init` creates in ~/.hermes with no format docs
- PyPI description has no usage examples
- **Fix:** Add `borg quickstart` that walks through search → try → apply. Add usage examples to PyPI long_description.

---

## Minor Issues

| Issue | Severity | Notes |
|-------|----------|-------|
| GitHub URL uses "bensargotest-sys" | P2 | Looks like test account, hurts credibility |
| No License in metadata | P2 | pip show shows no license |
| `borg setup-claude` may overwrite existing config | P2 | No backup, no warning |
| `borg autopilot` says "Skill already installed" on first run | P3 | Confusing for new users |
| `guild://` prefix unexplained | P3 | What is "guild"? Naming confusion with "borg" |
| `.rubric` shows as separate pack in search | P3 | Internal artifact leaking |
| `borg init` creates in ~/.hermes not CWD | P3 | Unexpected for most CLI tools |

---

## What Works Well

1. **`borg debug` is the killer feature** — instant, structured, evidence-backed debugging guidance
2. **Fast CLI** — every command responds in <1s
3. **`borg try` is perfect** — preview before commit is exactly right
4. **`borg generate --format all`** — multi-tool export is great
5. **`borg setup-claude` / `borg setup-cursor`** — one-command IDE integration
6. **Lightweight deps** — only 4 runtime dependencies
7. **Clean --help** — all 16 commands have clear descriptions

---

## Recommendation

The product is ~80% ready for public promotion. Fix items #1 (test artifacts) and #2 (MCP silence) before any public launch — they make the product look unfinished. Item #5 (quickstart) should follow immediately after.
