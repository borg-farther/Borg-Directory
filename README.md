# Borg

**A Python/Django debugging expert that's honest about what it doesn't know.**

[![PyPI](https://img.shields.io/pypi/v/agent-borg)](https://pypi.org/project/agent-borg/)
[![Version](https://img.shields.io/badge/version-3.2.4-blue)]()
[![Tests](https://img.shields.io/badge/tests-1708%20passed-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)]()

> **v3.2.4 patch.** Fixes a broken `borg observe → borg search` roundtrip:
> earlier versions of `observe` could emit task-guidance query strings that
> `search` was unable to index, so the second hop silently returned nothing.
> v3.2.4 aligns the tokenizer on both sides and adds a regression test so
> the path stays honest. No new features, no new claims — this is a
> correctness fix.

> **v3.2.2 honesty patch (still in force).** Earlier versions of `borg debug`
> would route any error containing the substring "Error" to a Django migration
> pack — including Rust, Go, Docker, and JavaScript errors. v3.2.2 deleted
> that fallback and added a non-Python language guard. Borg refuses to give a
> Python answer to a non-Python error and tells you so explicitly. JS/TS,
> Rust, Go, Docker, and Kubernetes pack coverage is on the roadmap (see
> `docs/20260408-0623_classifier_prd/`). If you are a Python/Django developer
> `borg debug` should still help; if you are not, we would rather say
> "we don't know yet" than give you a confidently wrong answer.

> **What borg has been measured on.** Honest snapshot at v3.2.4:
> - **Classifier, 173-row Python/Django error corpus:** FCR 53.8% → 0.58%,
>   precision 13.1% → 93.8%. Reproducible via the test suite.
> - **Agent-level retrieval effect, 1 model:** MiniMax (P1.1) — floor-effect
>   null (0/10 both arms on Django SWE-bench easy). One model only; not
>   evidence for or against the mechanism.
> - **Agent-level retrieval effect, Sonnet replication:** in progress. Will
>   be published whichever way it lands.
> - **Not measured:** cross-language (non-Python), cross-vertical, and any
>   claim about collective learning across agents in production.
> See `BORG_PRD_FINAL.md` for the full audit trail (two correction blocks
> preserved as forensic evidence).

---

## Get Started in 30 Seconds

```bash
pip install agent-borg
borg start
```

That's it. Paste an error, get structured debugging guidance. No config, no API keys, works offline.

---

## 10-Second Demo

Paste an error. Get a structured fix.

```bash
$ borg debug "ModuleNotFoundError: No module named 'cv2'"

============================================================
ERROR: ModuleNotFoundError: No module named 'cv2'
============================================================
[dependency-resolution] (Python)
Problem: Missing system-level dependency masquerading as pip issue

ROOT CAUSE:
  Category: environment-mismatch
  opencv-python requires system libs that pip can't install alone

INVESTIGATION TRAIL:
  1. [first] requirements.txt
     → Check if opencv-python or opencv-python-headless is listed
     grep: opencv
  2. [then] Dockerfile or system packages
     → Confirm libgl1-mesa-glx is installed for GUI builds

RESOLUTION SEQUENCE:
  1. Install headless variant (no system deps needed)
     Command: pip install opencv-python-headless
     Why: Avoids libGL dependency entirely
  2. If GUI needed, install system deps first
     Command: apt-get install -y libgl1-mesa-glx

ANTI-PATTERNS (don't do these):
  ✗ pip install opencv-python without system deps
    Fails because: ImportError at runtime even though pip succeeds

EVIDENCE: 47/52 successes (90%) over 127 uses
         Avg resolve time: 2.3 min
============================================================
```

That's not a template. That's learned from real agent sessions.

---

## 30-Second Setup

```bash
pip install agent-borg
borg debug "your error message here"
```

That's it. No API keys. No config. No account.

---

## Why

Every AI coding agent — Claude Code, Cursor, Cline, Windsurf — starts from scratch every session. It doesn't know what worked last time. It doesn't know what failed.

Borg is collective memory. When one agent solves a problem, every agent learns. When one agent fails, nobody repeats the mistake.

- Agent hits an error → `borg debug` returns the fix
- Agent starts a task → `borg observe` returns how to approach it
- Agent needs patterns → `borg search` finds what worked before
- Export to your platform → `borg generate` writes the rules file

---

## Features

- **Python/Django expert** — 12 hand-authored packs covering migrations, schema drift, imports, types, permissions, timeouts, and more
- **Honest about scope** — non-Python errors return "no match" rather than wrong advice
- **Works offline** — no API calls, no cloud, runs locally
- **Platform export** — one command to generate .cursorrules, .clinerules, CLAUDE.md, or .windsurfrules
- **17 MCP tools** — plug into any MCP-compatible agent
- **Task guidance** — get step-by-step approaches before you start coding
- **Pattern search** — find what worked across all sessions
- **Failure memory** — tracks what didn't work so agents stop repeating mistakes

---

## Platform Setup

### Claude Code
```bash
borg generate systematic-debugging --format claude
# Creates CLAUDE.md in your project
```

### Cursor
```bash
borg generate systematic-debugging --format cursor
# Creates .cursorrules in your project
```

### Cline
```bash
borg generate systematic-debugging --format cline
# Creates .clinerules in your project
```

### Windsurf
```bash
borg generate systematic-debugging --format windsurf
# Creates .windsurfrules in your project
```

### MCP (any compatible agent)
```json
{ "mcpServers": { "borg": { "command": "borg-mcp" } } }
```

---

## Quick Start

```bash
# 1. Debug a Python/Django error
borg debug "django.db.utils.OperationalError: no such column: app_user.email"

# 2. Get task guidance before you start
borg observe "refactor authentication to use JWT tokens"

# 3. Search for patterns that worked
borg search "docker networking"

# 4. Export rules to your editor
borg generate systematic-debugging --format cursor

# 5. Classify an error without full guidance
borg debug --classify "django.db.utils.OperationalError: no such column"
```

---

## How It Works

Borg ships with packs — structured knowledge extracted from real debugging sessions. Each pack contains:

- **Problem signature** — what the error looks like
- **Root cause** — why it actually happens
- **Investigation trail** — where to look, in order
- **Resolution sequence** — exact commands to fix it
- **Anti-patterns** — what not to do (and why it fails)
- **Evidence** — success rate from real usage

Packs improve over time. When agents report outcomes via `borg feedback`, success rates update and better approaches surface.

---

## Install

```bash
pip install agent-borg          # core
pip install agent-borg[crypto]  # with signing support
pip install agent-borg[all]     # everything
```

Requires Python 3.10+.

---

## License

MIT
