# Hermes Dojo — Deep Technical Analysis

**Repository:** `~/hermes-workspace/hermes-dojo`
**Lines of Code:** ~2,444 across 7 Python files, 3 Markdown files, 1 shell script
**Purpose:** Self-improvement system for Hermes Agent that watches agent performance, identifies weakest skills, fixes them with self-evolution, and reports results.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [File-by-File Analysis](#2-file-by-file-analysis)
   - [monitor.py](#21-monitorpy)
   - [analyzer.py](#22-analyzerpy)
   - [fixer.py](#23-fixerpy)
   - [reporter.py](#24-reporterpy)
   - [tracker.py](#25-trackerpy)
   - [seed_demo_data.py](#26-seed_demo_datapy)
   - [demo.py](#27-demopy)
3. [Hermes Integration Details](#3-hermes-integration-details)
4. [Data Flow](#4-data-flow)
5. [Strengths](#5-strengths)
6. [Weaknesses and Gaps](#6-weaknesses-and-gaps)
7. [Edge Cases: Handled vs. Missed](#7-edge-cases-handled-vs-missed)
8. [Reimplementation Guide](#8-reimplementation-guide)

---

## 1. Architecture Overview

### High-Level Pipeline

```
state.db (SQLite)
    ↓
monitor.py → raw metrics (tool success/failures, corrections, gaps, retries)
    ↓
analyzer.py → prioritized recommendations (patch/create/evolve/investigate)
    ↓
fixer.py → patch instructions OR new skill content OR GEPA evolution commands
    ↓
reporter.py → human-readable or Telegram-formatted report
    ↓
tracker.py → persisted JSON metrics history for learning curve
```

### Directory Structure

```
hermes-dojo/
├── SKILL.md                      # Main orchestrator (Hermes skill format)
├── install.sh                     # Installs skill into ~/.hermes/skills/hermes-dojo/
├── scripts/
│   ├── monitor.py                 # Reads state.db, computes metrics (358 lines)
│   ├── analyzer.py                # Categorizes failures, ranks weaknesses (220 lines)
│   ├── fixer.py                   # Patches/creates skills, runs evolution (709 lines)
│   ├── reporter.py                # Generates CLI/Telegram reports (206 lines)
│   ├── tracker.py                 # Stores/retrieves learning curve (150 lines)
│   ├── seed_demo_data.py         # Demo data generator (282 lines)
│   └── demo.py                    # Full pipeline demo runner (225 lines)
├── references/
│   └── failure_patterns.md        # Error pattern reference (42 lines)
└── data/
    └── metrics.json               # Historical performance data (created at runtime)
```

### Hermes Integration Points

- **Skills System:** Dojo IS a skill; it creates/patches other skills via `skill_manage` tool
- **Self-Evolution (GEPA):** Invokes `hermes-agent-self-evolution` CLI via subprocess
- **Session Storage:** Reads from `~/.hermes/state.db` (SQLite)
- **Skill Storage:** Reads/writes to `~/.hermes/skills/`
- **Metrics Storage:** `~/.hermes/skills/hermes-dojo/data/metrics.json`
- **Environment:** Reads `OPENROUTER_API_KEY` from `~/.hermes/.env`

---

## 2. File-by-File Analysis

### 2.1 monitor.py (358 lines)

**Location:** `scripts/monitor.py`
**Purpose:** Performance Monitor — reads `state.db`, identifies failures, corrections, retry patterns, skill gaps.

#### Classes and Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `classify_tool_result` | `(content: str) → tuple[bool, str]` | `(is_error: bool, error_type: str)` |
| `detect_retry_patterns` | `(messages: list[dict]) → list[dict]` | List of retry loop descriptors |
| `analyze_sessions` | `(days: int = 7, session_id: str = None) → dict[str, Any]` | Full analysis dict |
| `print_dashboard` | `(data: dict) → None` | Prints human-readable dashboard |

#### Global Constants

**`ERROR_PATTERNS`** — List of 20 regex patterns for detecting tool failures:
```
(?i)error[:\s], (?i)traceback, (?i)exception[:\s], (?i)failed to,
(?i)command not found, (?i)permission denied, (?i)no such file,
(?i)timeout, (?i)connection refused, (?i)404 not found,
(?i)500 internal, (?i)rate limit, (?i)unauthorized, (?i)access denied,
(?i)ENOENT, (?i)EACCES, (?i)ETIMEDOUT, (?i)could not, (?i)unable to,
(?i)syntax error
```

**`CORRECTION_PATTERNS`** — 20 regex patterns for user dissatisfaction signals:
```
(?i)^no[,.], (?i)wrong, (?i)not what I, (?i)I meant, (?i)that's not,
(?i)please don't, (?i)stop, (?i)undo, (?i)revert, (?i)you misunderstood,
(?i)incorrect, (?i)fix (this|that|it), (?i)try again, (?i)that broke,
(?i)doesn't work, (?i)not working, (?i)why did you
```

**`REQUEST_PATTERNS`** — 12 tuples of (regex, capability_name) for skill gap detection:
```
(parse.*csv, csv-parsing), (format.*json, json-formatting),
(convert.*pdf, pdf-conversion), (send.*email, email-sending),
(create.*chart, chart-creation), (scrape.*web, web-scraping),
(deploy, deployment), (docker, docker-management),
(git.*commit, git-operations), (test.*unit|unit.*test, unit-testing),
(database|sql|query, database-operations), (api.*call|fetch.*api|rest.*api, api-integration)
```

#### Data Structures

- **Tool Stats:** `defaultdict(lambda: {"total": int, "errors": int, "error_types": Counter})`
- **Session Data:** `dict` with keys: `id`, `source`, `model`, `started_at`, `tool_call_count`, `message_count`
- **Message Data:** `dict` with keys: `role`, `content`, `tool_calls` (JSON string), `tool_name`, `timestamp`, `session_id`
- **Result Dict Keys:** `timestamp`, `days_analyzed`, `sessions_analyzed`, `total_tool_calls`, `total_errors`, `overall_success_rate`, `weakest_tools[]`, `user_corrections`, `correction_samples[]`, `retry_patterns[]`, `skill_gaps[]`, `total_messages`, `sessions[]`

#### External Dependencies

```python
import json, os, re, sqlite3, sys, time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
```

#### Hermes Interaction

- **Reads:** `~/.hermes/state.db` (or `$HERMES_HOME/state.db`)
- **Schema assumption:** Tables `sessions` and `messages`:
  - `sessions`: `id TEXT PRIMARY KEY, source TEXT, model TEXT, started_at REAL, ended_at REAL, end_reason TEXT, message_count INTEGER, tool_call_count INTEGER`
  - `messages`: `id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, tool_calls TEXT, tool_name TEXT, timestamp REAL`
- **No writes** — purely read-only

#### Algorithmic Approach

1. **Session Fetch:** Query `sessions` table with time cutoff (`time.time() - days * 86400`) or by specific `session_id`
2. **Message Fetch:** Load all messages for those sessions in one query with `ORDER BY timestamp`
3. **Tool Analysis:** Iterate messages where `role == "tool"`, apply each `ERROR_PATTERNS` regex against `content`; first match wins, extracts 10 chars before + 50 chars after match
4. **User Correction Detection:** Iterate `role == "user"` messages, apply each `CORRECTION_PATTERNS` regex
5. **Skill Gap Detection:** Iterate `role == "user"` messages, apply each `REQUEST_PATTERNS` regex; counts occurrences via `Counter`
6. **Retry Loop Detection:** Track consecutive same-tool calls within 30 seconds; flag when same tool appears 2+ times
7. **Ranking:** Sort `weakest_tools` by `errors/total` descending

#### Edge Cases

**Handled:**
- Database file not found → returns `{"error": "..."}` dict
- No sessions in time range → returns `{"sessions_analyzed": 0, "message": "..."}`
- Empty tool content → `classify_tool_result` returns `(False, "")` immediately
- `tool_calls` stored as JSON string or list → tries `json.loads` then falls back to treating as dict
- `Counter` objects in JSON output → `default=str` serializes them

**Missed:**
- No validation of `state.db` schema — assumes columns exist without checking
- Timezone-agnostic — `time.time()` is UTC but `started_at` could be local
- Sessions with no messages are included but contribute nothing
- Retry detection only catches "immediate" retries (same tool within 30s); misses longer retry loops
- Error pattern matching is case-insensitive but `ERROR_PATTERNS` list is ordered — earlier patterns take precedence even if later ones are more specific

---

### 2.2 analyzer.py (220 lines)

**Location:** `scripts/analyzer.py`
**Purpose:** Weakness Analyzer — takes monitor output, produces prioritized improvement recommendations.

#### Classes and Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `find_existing_skills` | `() → dict[str, Path]` | `{"skill_name": skill_dir_path}` |
| `map_tool_to_skill` | `(tool_name: str, existing_skills: dict[str, Path]) → str \| None` | Skill name or None |
| `generate_recommendations` | `(monitor_data: dict) → list[dict[str, Any]]` | Prioritized recommendation list |
| `_priority_score` | `(tool: dict) → float` | Priority score for a tool |
| `_tool_to_skill_name` | `(tool_name: str) → str` | Converted skill name |
| `_suggest_fix` | `(tool: dict) → str` | Suggested fix description |
| `print_recommendations` | `(recs: list[dict]) → None` | Prints formatted recommendations |

#### Global Constants

None — purely algorithmic, no hardcoded data.

#### Data Structures

- **Recommendations:** List of dicts with keys: `action` (str), `priority` (float), `target` (str), `skill_path` (str|None), `reason` (str), `top_error` (str|None), `suggested_fix` (str|None)
- **Actions:** `"patch"`, `"create"`, `"evolve"`, `"investigate"`

#### External Dependencies

```python
import json, os, sys
from pathlib import Path
from typing import Any
```

#### Hermes Interaction

- **Reads:** `~/.hermes/skills/*/SKILL.md` (discover installed skills)
- **Writes:** None
- **Skill Discovery Algorithm:**
  1. Iterate `SKILLS_DIR.iterdir()` — each subdirectory is a potential skill
  2. Check if `skill_md = item / "SKILL.md"` exists
  3. Also check nested subdirectories (one level deep) for `SKILL.md`
  4. Returns `{"directory_name": Path}` mapping

#### Algorithmic Approach

1. **Skill Discovery:** Scan `~/.hermes/skills/` for directories containing `SKILL.md`
2. **Tool-to-Skill Mapping (fuzzy):**
   - Direct name match: `tool_name == skill_name`
   - Fuzzy match: `skill_name in tool_name.lower().replace("_", "-")` OR vice versa
3. **Recommendation Generation:**
   - **PATCH:** For each `weakest_tool` with `errors >= 2`; if tool maps to existing skill → recommend patch
   - **CREATE:** If `errors >= 2` but no skill found → recommend creating a skill; also for each `skill_gap` with no fuzzy-matched existing skill
   - **EVOLVE:** For each `weakest_tool` with `success_rate < 90` AND `total >= 5`; if tool maps to existing skill → recommend GEPA evolution
   - **INVESTIGATE:** For each `retry_pattern` → flag for investigation
4. **Priority Scoring:**
   - `patch`: `error_rate * total * 10` where `error_rate = 1 - (success_rate/100)`
   - `create` (from skill_gap): `requests * 10`
   - `evolve`: `(100 - success_rate) * total / 10`
   - `investigate`: `count * 5`
5. **Deduplication:** Sort by priority descending, keep first occurrence per `target`

#### `_suggest_fix` Logic

Maps error text keywords to fix suggestions:

| Keyword(s) | Suggestion |
|------------|------------|
| "not found", "no such file" | Add path validation and existence checks before operations |
| "timeout" | Add retry logic with exponential backoff and configurable timeout |
| "permission", "access denied" | Add permission checks and suggest user fix with clear instructions |
| "command not found" | Add command existence check (which/command -v) before execution |
| "syntax error" | Add input validation and proper escaping |
| "rate limit" | Add rate limiting awareness and backoff strategy |
| (default) | Review failure patterns and add error handling for the most common case |

#### Edge Cases

**Handled:**
- Empty `SKILLS_DIR` → returns empty dict
- Malformed `SKILL.md` → still added to skill list (doesn't validate YAML)
- Tools with only 1 error → skipped for patch recommendation
- Skills with success_rate >= 90 or total < 5 → skipped for evolve
- Duplicate targets → first-seen (higher priority) recommendation kept

**Missed:**
- No cycle detection — could recommend patch + evolve for same skill
- No conflict detection between recommendations
- Fuzzy matching is very loose — `"git"` skill would match any tool containing "git" or vice versa
- `skill_gap` recommendations don't verify the gap actually lacks a skill under a different naming scheme
- Nested skill directories beyond 1 level not scanned

---

### 2.3 fixer.py (709 lines)

**Location:** `scripts/fixer.py`
**Purpose:** Auto-Fixer — generates and optionally applies fix instructions for patches, new skills, and GEPA evolution.

#### Classes and Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `classify_error` | `(error_text: str) → str` | Strategy category name |
| `generate_skill_patch` | `(rec: dict) → dict` | Patch instruction dict |
| `generate_skill_creation` | `(rec: dict) → dict` | Skill creation instruction dict |
| `_build_skill_content` | `(skill_name, error_type, top_error, reason) → str` | Full SKILL.md content |
| `_load_openrouter_key` | `() → str` | API key string |
| `run_evolution` | `(skill_name, iterations: int = 5, dry_run: bool = False) → dict` | Evolution result |
| `generate_fix_plan` | `(recommendations, evolve: bool = False, dry_run: bool = True) → dict` | Complete fix plan |
| `apply_fixes` | `(plan: dict) → list[dict]` | List of applied improvements |
| `print_fix_plan` | `(plan: dict) → None` | Prints formatted plan |

#### Global Constants

**`FIX_STRATEGIES`** — Dict mapping error category → fix dict:

```python
{
    "path_not_found": {
        "patch": "Add path validation: check if file/directory exists before operations...",
        "skill_addition": "## Pre-flight Checks\n- Before ANY file operation..."
    },
    "timeout": {
        "patch": "Add retry logic with exponential backoff...",
        "skill_addition": "## Timeout Handling\n- Set initial timeout to 10 seconds\n..."
    },
    "permission_denied": {...},
    "command_not_found": {...},
    "rate_limit": {...},
    "wrong_context": {...},
    "missing_dependency": {...},
    "generic": {...}
}
```

**`SKILL_TEMPLATES`** — Pre-built `SKILL.md` content for 4 specific skills:
- `web-extract` — Web scraping with timeout/retry/fallback strategy
- `terminal-run` — Shell commands with pre-flight checks (path, git context, tool existence)
- `execute-code` — Code execution with dependency management and iterative fixing
- `deployment` — Multi-target deployment (SSH, Docker, platform) with safety confirmations

**`DEFAULT_EVOLUTION_MODEL`** — `"openrouter/nousresearch/hermes-3-llama-3.1-70b"`

#### Data Structures

- **Fix Plan:** `{"patches": [], "creations": [], "evolutions": [], "summary": {...}}`
- **Patch Dict:** `{"action", "target", "skill_path", "error_type", "patch_description", "skill_addition", "tool_instruction"}`
- **Creation Dict:** `{"action", "target", "skill_content", "tool_instruction"}`
- **Evolution Result:** `{"skill", "iterations", "status", "before_score", "after_score", "command"|"output"|"error"}`
- **Improvement:** `{"action", "target", "description", "error_type"|"before_score"|"after_score"}`

#### External Dependencies

```python
import json, os, subprocess, sys, time
from pathlib import Path
from typing import Any
```

Plus environment access for `OPENROUTER_API_KEY`.

#### Hermes Interaction

- **Reads:** `~/.hermes/skills/<skill>/SKILL.md` (when applying patches), `~/.hermes/.env` (for API key)
- **Writes:** `~/.hermes/skills/<skill>/SKILL.md` (appends patch content via `apply_fixes`), `~/.hermes/skills/<skill_name>/SKILL.md` (new skill creation)
- **Subprocess:** Runs `hermes-agent-self-evolution` via `.venv/bin/python3 -m evolution.skills.evolve_skill`
- **Paths:** `HERMES_HOME / "skills"`, `HERMES_HOME / "hermes-agent-self-evolution"`, `EVOLUTION_DIR / ".venv" / "bin" / "python3"`

#### Algorithmic Approach

1. **Error Classification (`classify_error`):**
   - Iterates through `FIX_STRATEGIES` keys, checking if any keyword is in `error_text.lower()`
   - Priority order: `path_not_found` → `timeout` → `permission_denied` → `command_not_found` → `rate_limit` → `wrong_context` → `missing_dependency` → `generic`
   - Keywords checked via `any(p in error_lower for p in [...])` pattern

2. **Patch Generation:**
   - Classifies the error type
   - Retrieves strategy dict
   - Returns structured dict with `tool_instruction` for `skill_manage` with action `"patch"`

3. **Skill Creation:**
   - Checks `SKILL_TEMPLATES` first (exact key match on `skill_name`)
   - If found, returns that template
   - If not, generates dynamic content using `_build_skill_content` with error-specific strategy

4. **Skill Content Generation (`_build_skill_content`):**
   - Uses template if available
   - Otherwise builds YAML frontmatter + structured markdown with Context, Workflow, error-specific strategy section, and "When Things Go Wrong"
   - `safe_reason` sanitizes quotes and newlines for YAML embedding

5. **Evolution (`run_evolution`):**
   - Checks for `.venv` existence at `EVOLUTION_DIR`
   - Loads `OPENROUTER_API_KEY` from env or `~/.hermes/.env`
   - **Env file parsing bug:** Line `if line.startswith("OPENROUTER_API_KEY=***` — this will NEVER match a real `.env` file (which would have the actual key value, not `***`). The check seems inverted/confused.
   - Runs subprocess with 300s timeout, `capture_output=True`
   - Parses `before_score` and `after_score` by searching for `"before"` + `"score"` or `"after"` + `"score"` in output lines, extracting after `:`, stripping `%`

6. **Apply Fixes:**
   - **Patches:** Appends `skill_addition` text to existing `SKILL.md` via `open(path, "a")`
   - **Creations:** Creates `SKILLS_DIR / target / SKILL.md`, writes content
   - **Evolutions:** Only records if `status == "completed"`

#### Edge Cases

**Handled:**
- Evolution venv not found → returns `{"status": "error", "error": "..."}`
- Missing API key → returns `{"status": "error", "error": "..."}`
- Evolution timeout (300s) → returns `{"status": "timeout"}`
- Dry run mode → generates command string without executing
- Target skill directory doesn't exist → `skill_dir.mkdir(parents=True, exist_ok=True)`
- Patch to non-existent `SKILL.md` → skipped silently

**Missed:**
- **BUG:** `_load_openrouter_key()` checks `line.startswith("OPENROUTER_API_KEY=***")` — this will never match because the actual key value would be after `=`, not `***`. The real key is masked in the .env file? Actually looking more carefully: the check seems to be trying to match a masked value but the logic is backwards.
- **BUG:** Evolution score parsing uses naive string search — `if "before" in line.lower() and "score" in line.lower()` — could match "The score before optimization was impressive" and crash on float extraction
- No validation that patched skill is valid YAML/frontmatter
- No backup of original `SKILL.md` before patching
- No version tracking for skills
- Patches are always append-only — never removes or updates existing content
- If `apply_fixes` fails midway (e.g., 2nd creation fails), first creation is already written
- No rollback mechanism
- Skills with hyphens vs underscores in name — inconsistent handling

---

### 2.4 reporter.py (206 lines)

**Location:** `scripts/reporter.py`
**Purpose:** Generates formatted reports for CLI or Telegram delivery.

#### Classes and Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `generate_report` | `(monitor_data, improvements: list = None, previous_data: dict = None, fmt: str = "cli") → str` | Formatted report string |
| `_telegram_report` | `(sessions, tool_calls, success_rate, delta, corrections, weakest, gaps, improvements) → str` | Telegram markdown string |
| `_cli_report` | `(sessions, tool_calls, success_rate, delta, corrections, weakest, gaps, improvements) → str` | CLI-formatted string |

#### Data Structures

- **Input:** `monitor_data` dict (same structure as monitor.py output), `improvements` list (same as `apply_fixes` output), `previous_data` dict (previous snapshot from tracker)
- **Output:** Multi-line string formatted for CLI or Telegram

#### External Dependencies

```python
import json, os, sys, time
from datetime import datetime
from pathlib import Path
```

#### Hermes Interaction

- **Reads:** `~/.hermes/skills/hermes-dojo/data/metrics.json` (via `tracker.load_metrics()`)
- **Writes:** None

#### Algorithmic Approach

1. **Delta Calculation:** If `previous_data` provided, `delta = success_rate - prev_rate`
2. **Telegram Format:**
   - Header with emoji: `🥋 *Hermes Dojo — Report*`
   - Sessions/tool_calls line
   - Delta with direction emoji (`📈`/`📉`/`➡️`)
   - User corrections warning
   - Improvements grouped by action (patched/created/evolved)
   - Top weaknesses
   - Skill gaps
   - **Sparkline:** Loads history via `load_metrics()`, takes last 7 entries, computes `blocks = " ▁▂▃▄▅▆▇█"`, maps rates to block characters, renders as `▁▂▃▄▅▆▇█` scale
3. **CLI Format:**
   - Box-drawing with `=` headers
   - Same data, no emoji, tabular

#### Sparkline Algorithm

```python
rates = [h.get("overall_success_rate", 0) for h in history[-7:]]
blocks = " ▁▂▃▄▅▆▇█"
min_r, max_r = min(rates), max(rates)
span = max_r - min_r
if span == 0:
    sparkline = "█" * len(rates)
else:
    sparkline = "".join(
        blocks[min(8, int((r - min_r) / span * 8))] for r in rates
    )
```

#### Edge Cases

**Handled:**
- No `improvements` passed → shows weaknesses and gaps instead
- `delta` is None (no previous data) → shows absolute rate without arrow
- `load_metrics()` fails (file missing, JSON decode error) → silently skipped, no sparkline
- Empty `weakest` or `gaps` → those sections omitted
- Rate could be 0 → `span = 0` case handled (all `█`)

**Missed:**
- No validation that `success_rate - delta` doesn't go negative
- Sparkline only uses 8-char block scale — if all rates identical, all `█`
- Telegram output uses markdown (`*bold*`) — not validated for Telegram API compliance
- No handling of very long skill names or descriptions in output

---

### 2.5 tracker.py (150 lines)

**Location:** `scripts/tracker.py`
**Purpose:** Learning Curve Tracker — persists daily metrics snapshots to JSON.

#### Classes and Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `load_metrics` | `() → list[dict]` | Historical metrics list |
| `save_snapshot` | `(monitor_data: dict, improvements: list = None) → dict` | The saved snapshot |
| `print_history` | `() → None` | Prints learning curve |

#### Data Structures

- **Metrics File:** `~/.hermes/skills/hermes-dojo/data/metrics.json`
- **Snapshot Dict:** `{"timestamp": float, "date": str, "sessions_analyzed": int, "total_tool_calls": int, "overall_success_rate": float, "total_errors": int, "user_corrections": int, "skill_gaps": int, "retry_patterns": int, "weakest_tools": [...], "improvements_made": [...]?}`
- **Atomic Write:** Writes to `.tmp` file, then `replace()` to target ( POSIX atomic rename)

#### External Dependencies

```python
import json, os, sys, time
from datetime import datetime
from pathlib import Path
```

#### Hermes Interaction

- **Reads:** Nothing (only writes/reads metrics.json)
- **Writes:** `~/.hermes/skills/hermes-dojo/data/metrics.json`

#### Algorithmic Approach

1. **Load:** `json.load()` the file, returns empty list on `JSONDecodeError` or `ValueError`
2. **Save Snapshot:**
   - Creates `DATA_DIR` if needed
   - Loads existing history
   - Appends new snapshot with extracted fields
   - Filters to last 90 days (`timestamp > time.time() - 90*86400`)
   - Atomic write via temp file + rename
3. **Print History:**
   - Shows last 30 entries as a table
   - Computes trend: `first_rate → last_rate (delta)`
   - Sparkline: same 8-char block algorithm as reporter.py, but uses last 10 entries

#### Edge Cases

**Handled:**
- File doesn't exist → `load_metrics` returns `[]`
- JSON decode error → returns `[]`
- Interrupt during write → atomic rename prevents partial file corruption
- Very old entries → filtered out at 90-day cutoff

**Missed:**
- Concurrent writes from multiple processes → could race (no file locking)
- If file is corrupted (partial write before rename), the `.tmp` isn't cleaned up
- No validation of snapshot structure before saving
- No validation that `date` string is valid ISO format

---

### 2.6 seed_demo_data.py (282 lines)

**Location:** `scripts/seed_demo_data.py`
**Purpose:** Demo data generator — creates realistic session data in `state.db` for testing Dojo.

#### Classes and Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `seed_data` | `(days: int = 5, clear: bool = False, deterministic: bool = True) → None` | None (writes to DB) |

#### Global Constants

**`SCENARIOS`** — 10 realistic session scenarios with deliberate failures:

| # | Description | Failure Type |
|---|-------------|--------------|
| 1 | CSV file path wrong | `Error: No such file` → user correction → correct path |
| 2 | JSON validation | `JSONDecodeError` on bad JSON |
| 3 | Web scraping timeout | `Error: Request timeout after 30 seconds` → retry → web_search fallback |
| 4 | Git commit to wrong branch | Commits to `main` instead of `feature` → user correction → undo + redo |
| 5 | Successful fibonacci code | No failure — baseline success |
| 6 | SQL table not found | `Error: no such table: users` → discover correct table name |
| 7 | GitHub API rate limit | `Error: 403 Forbidden - API rate limit exceeded` → retry → web_search fallback |
| 8 | Memory update | No failure — baseline success |
| 9 | CSV parsing with pandas | `ModuleNotFoundError: No module named 'pandas'` → pip install → success |
| 10 | Deploy to wrong target | Docker push denied → user says SSH → rsync fallback |

#### Data Structures

- **Scenario:** `{"description": str, "messages": list[dict]}`
- **Message:** `{"role": str, "content": str|None, "tool_calls": list|None, "tool_name": str|None}`

#### External Dependencies

```python
import json, os, random, sqlite3, time, uuid
from pathlib import Path
```

#### Hermes Interaction

- **Reads:** Nothing
- **Writes:** `~/.hermes/state.db` — creates `sessions` and `messages` tables (via `CREATE TABLE IF NOT EXISTS`), inserts demo records with `source = 'dojo-seed'`

#### Algorithmic Approach

1. **Schema Creation:** Creates `sessions` and `messages` tables with `IF NOT EXISTS`
2. **Clear (optional):** Deletes rows where `source = 'dojo-seed'` before seeding
3. **Per-Day Seeding:**
   - `random.randint(3, 5)` sessions per day
   - Sessions distributed within first 12 hours of each day (`+ random(0, 43200)`)
   - Random scenario selection via `random.choice(SCENARIOS)`
   - Messages timestamped with `session_start + random.uniform(1, 10)`
4. **Tool Calls:** Serialized to JSON string via `json.dumps()` if present
5. **FTS Index:** Attempts `INSERT INTO messages_fts(messages_fts) VALUES('rebuild')` — silently skipped if FTS table doesn't exist

#### Schema (Hardcoded)

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT,
    model TEXT,
    started_at REAL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0
)

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,
    content TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL
)
```

#### Edge Cases

**Handled:**
- Database doesn't exist → `sqlite3.connect()` creates it
- FTS table missing → try/except silently ignores
- Deterministic mode (`random.seed(42)`) for reproducible demo output
- Clearing only `dojo-seed` records — preserves real user data

**Missed:**
- No validation that schema columns match Hermes Agent's actual `state.db` schema
- `random.choice` weights all scenarios equally — some failure types overrepresented
- Scenarios don't cover all error patterns (e.g., no `EACCES`, no `EISDIR`)
- `tool_call_count` computed as `sum(1 for m in messages if m.get("tool_calls"))` but `message_count` includes ALL messages
- No `message_id` in tool result messages to link to the originating tool call
- Timestamps go forward in time from `now - days*86400` but the last day's sessions may be in the future if `now` is near midnight

---

### 2.7 demo.py (225 lines)

**Location:** `scripts/demo.py`
**Purpose:** Full pipeline demo runner — runs monitor → analyzer → fixer → reporter → tracker in sequence.

#### Classes and Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `seed_learning_curve` | `() → None` | Pre-populates 4 days of metrics history |
| `run_demo` | `(reset: bool = False, telegram: bool = False) → None` | Runs full pipeline |

#### Data Structures

- **Pre-seeded History:** 4-entry list simulating Dojo running for 4 days with improving metrics:
  - Day 1: 34.2% success (10 sessions, 38 calls, 25 errors)
  - Day 2: 41.7% success (14 sessions, 48 calls, 28 errors)
  - Day 3: 47.3% success (18 sessions, 55 calls, 29 errors)
  - Day 4: 53.2% success (22 sessions, 62 calls, 29 errors)

#### Algorithmic Approach

**`seed_learning_curve`:** Writes 4 pre-made snapshot dicts to `metrics.json`, simulating a Dojo that has been running for 4 days with progressive improvement. Values chosen so today's seed data (57.1% with new batch of sessions) fits as continuation of trend.

**`run_demo` 6-step pipeline:**

1. **Optional Reset:** Calls `seed_data(days=7, clear=True)` then `seed_learning_curve()`
2. **Analyze:** `analyze_sessions()` → prints summary
3. **Recommend:** `generate_recommendations(data)` → counts patches/creates/evolves
4. **Apply Fixes:** `generate_fix_plan(recs, evolve=False, dry_run=False)` → `apply_fixes(plan)` → creates skills in `~/.hermes/skills/`
5. **Save Snapshot:** `save_snapshot(data, improvements)`
6. **Report:** `generate_report(data, improvements=improvements, previous_data=prev, fmt=telegram?)` → print
7. **History:** `print_history()` → show sparkline

**Sample Skill Display:** After applying fixes, reads and prints first 20 lines of one of the created skill files (`terminal-run`, `web-extract`, or `execute-code`) to prove the skills have real content.

#### Edge Cases

**Handled:**
- `--reset` clears demo data and reseeds
- `--telegram` shows Telegram-formatted report
- `--multi-day` seeds the learning curve without running full demo
- If no sample skill file exists, silently skips the sample display
- Previous snapshot loaded for delta calculation — handles case of only 1 history entry

**Missed:**
- `seed_learning_curve` always overwrites `metrics.json` completely (even if it already exists)
- No check that `hermes-agent-self-evolution` is installed before `run_demo`
- Skills created by demo go into `~/.hermes/skills/` but nothing cleans them up
- Demo calls `apply_fixes` with `dry_run=False` — actually writes skills during demo

---

## 3. Hermes Integration Details

### state.db Schema (Assumed)

Dojo assumes the following schema in `~/.hermes/state.db`:

```sql
-- sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,           -- UUID
    source TEXT,                    -- e.g., "telegram", "cli", "dojo-seed"
    model TEXT,                     -- e.g., "hermes-3-llama-3.1-70b"
    started_at REAL,                -- Unix timestamp
    ended_at REAL,                  -- Unix timestamp
    end_reason TEXT,                -- e.g., "completed", "error"
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0
)

-- messages table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,                -- FK to sessions.id
    role TEXT,                      -- "user", "assistant", "tool"
    content TEXT,                   -- message text
    tool_calls TEXT,                -- JSON string of tool call array (assistant only)
    tool_name TEXT,                 -- tool name (tool role only)
    timestamp REAL                  -- Unix timestamp
)
```

**Important:** Dojo does NOT create these tables. It assumes they exist from Hermes Agent's normal operation. `seed_demo_data.py` creates them with `CREATE TABLE IF NOT EXISTS`.

### skill_manage Tool Instructions

When `fixer.py` generates a patch or creation, it outputs a `tool_instruction` dict meant for Hermes Agent's `skill_manage` tool:

**Patch instruction:**
```python
{
    "tool": "skill_manage",
    "action": "patch",
    "name": "skill-name",
    "patch": "## Pre-flight Checks\n- Before ANY file operation...",
    "reason": "terminal_run fails 6/12 times (50% success)"
}
```

**Create instruction:**
```python
{
    "tool": "skill_manage",
    "action": "create",
    "name": "new-skill-name",
    "content": "---\nname: new-skill-name\n...\n# New Skill\n...",
    "reason": "Users requested 'csv-parsing' 4 times but no skill exists"
}
```

### Self-Evolution (GEPA) Integration

**Path:** `~/.hermes/hermes-agent-self-evolution`
**Venv:** `~/.hermes/hermes-agent-self-evolution/.venv/bin/python3`
**Module:** `evolution.skills.evolve_skill`

**CLI Command:**
```bash
cd ~/.hermes/hermes-agent-self-evolution
OPENROUTER_API_KEY=<key> .venv/bin/python3 -m evolution.skills.evolve_skill \
    --skill <skill_name> \
    --hermes-repo ~/.hermes \
    --iterations 5 \
    --optimizer-model openrouter/nousresearch/hermes-3-llama-3.1-70b \
    --eval-model openrouter/nousresearch/hermes-3-llama-3.1-70b
```

**Score Parsing:** Extracts `before_score` and `after_score` by searching stdout lines for patterns `(?i).*before.*score:.*` and `(?i).*after.*score:.*`, taking the substring after `:` and stripping `%`.

---

## 4. Data Flow

### Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER / CRON TRIGGER                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  SKILL.md (Hermes Skill Orchestrator)                           │
│  - Parses /dojo commands                                         │
│  - Delegates to Python scripts                                   │
│  - Uses: terminal, skill_manage, session_search, memory, delegate │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  monitor.py                                                      │
│  Input:  ~/.hermes/state.db (SQLite)                            │
│  Output: {sessions_analyzed, total_tool_calls, overall_success_  │
│          rate, weakest_tools[], user_corrections, skill_gaps[],  │
│          retry_patterns[], ...}                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  analyzer.py                                                     │
│  Input:  monitor.py output + ~/.hermes/skills/*/SKILL.md        │
│  Output: [{action: "patch"|"create"|"evolve"|"investigate",       │
│           target, priority, reason, suggested_fix, ...}, ...]    │
│  Key logic: fuzzy tool→skill mapping, priority scoring           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  fixer.py                                                        │
│  Input:  recommendations list                                    │
│  Output: fix plan {patches[], creations[], evolutions[]}        │
│          Applied to: ~/.hermes/skills/<skill>/SKILL.md          │
│          Evolution: ~/.hermes/hermes-agent-self-evolution CLI    │
│  Key logic: error classification → fix strategy → skill content │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
   ┌─────────────┐    ┌─────────────┐   ┌─────────────┐
   │   PATCH     │    │   CREATE    │   │   EVOLVE    │
   │ append to   │    │ new skill   │   │ GEPA CLI    │
   │ SKILL.md    │    │ dir + file  │   │ subprocess  │
   └─────────────┘    └─────────────┘   └─────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  reporter.py                                                    │
│  Input:  monitor data + improvements + previous snapshot        │
│  Output: CLI string OR Telegram markdown string                 │
│  Sparkline: loads tracker history, maps rates to ▁▂▃▄▅▆▇█      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  tracker.py                                                     │
│  Input:  monitor data + improvements                             │
│  Output: ~/.hermes/skills/hermes-dojo/data/metrics.json        │
│  (appends snapshot, retains last 90 days, atomic write)         │
└─────────────────────────────────────────────────────────────────┘
```

### metrics.json Schema

```json
[
  {
    "timestamp": 1743273600.0,
    "date": "2026-03-29 19:30",
    "sessions_analyzed": 23,
    "total_tool_calls": 156,
    "overall_success_rate": 78.0,
    "total_errors": 34,
    "user_corrections": 7,
    "skill_gaps": 3,
    "retry_patterns": 2,
    "weakest_tools": [
      {"tool": "web_extract", "success_rate": 72.0, "errors": 7}
    ],
    "improvements_made": [
      {"action": "patch", "target": "web-extract", "description": "..."}
    ]
  }
]
```

---

## 5. Strengths

1. **Comprehensive Error Detection:** 20 regex patterns for error detection, 20 for user corrections, 12 for skill gap detection — covers most common failure modes
2. **Multi-Strategy Fix Generation:** Not just patching — creates new skills, runs GEPA evolution, flags for investigation
3. **Pre-built Skill Templates:** 4 detailed skill templates (web-extract, terminal-run, execute-code, deployment) with actual bash commands, not just boilerplate
4. **Learning Curve Persistence:** 90-day history with sparklines and trend lines gives longitudinal insight
5. **Atomic Writes:** tracker.py uses temp file + rename to prevent corruption
6. **Deterministic Demo Data:** `random.seed(42)` ensures reproducible demo runs
7. **Fuzzy Tool-to-Skill Mapping:** Handles naming mismatches (underscores vs hyphens)
8. **CLI + Telegram Output:** Both human-readable CLI and Telegram markdown formatting
9. **No Hermes Source Modification:** Only touches `~/.hermes/skills/`, leaves agent source untouched
10. **Reference Patterns:** `failure_patterns.md` provides documented fix strategies

---

## 6. Weaknesses and Gaps

### Critical Bugs

1. **`_load_openrouter_key()` has inverted logic:** Checks for `line.startswith("OPENROUTER_API_KEY=***")` which will never match a real `.env` file. The `***` appears to be a masked placeholder, but the code checks if the line STARTS with that, not if it CONTAINS the masked value.

2. **Evolution score parsing is fragile:** Searches stdout for `if "before" in line.lower() and "score" in line.lower()` — could match arbitrary text, then `float(line.split(":")[-1].strip().rstrip("%"))` could crash on non-numeric content.

3. **Append-only patching:** Patches always append to `SKILL.md`. If a fix needs to MODIFY existing content (not just add), it's impossible. No version tracking for skill changes.

4. **No rollback:** If `apply_fixes` fails midway, already-applied changes aren't undone.

### Design Gaps

5. **Assumed schema not validated:** No check that `state.db` has the expected columns. Different Hermes Agent versions could have different schemas.

6. **skill_manage tool assumed to exist:** The SKILL.md lists `skill_manage` as an allowed tool, but the fixer outputs instructions for it rather than calling it directly. Hermes Agent must implement this tool for actual skill modification.

7. **Only reads bundled sessions:** `source = 'dojo-seed'` is how demo data is identified, but the monitor doesn't filter by source — it processes all sessions. Real user sessions mixed with demo data would skew results.

8. **No confidence scoring:** All recommendations treated equally despite varying evidence quality. A tool that failed 2/3 times vs 20/100 times should be weighted differently.

9. **Single-user focus:** No multi-user or multi-session aggregation. All metrics are aggregate totals, not per-user or per-session breakdowns.

10. **No feedback loop verification:** After applying fixes, there's no automated verification that the fix actually improved the metric. The 5% threshold mentioned in SKILL.md ("if improvement < 5%, flag for manual review") is never implemented in code.

11. **GEPA evolution is fire-and-forget:** `run_evolution` captures stdout/stderr but the improvement score is parsed from text output, not a structured result. If GEPA changes its output format, parsing breaks silently.

12. **No skill dependency graph:** If skill A depends on skill B, patching A might break B. No dependency tracking.

13. **Skill gap detection is purely regex:** Doesn't use LLM or semantic similarity. Pattern `r"parse.*csv"` won't catch "I need to analyze this spreadsheet data".

14. **No dark-launch mechanism:** New/changed skills go directly into production. No A/B testing or canary deployment.

15. **Metrics storage is single-file JSON:** No database, no compression, no incremental updates. At 90 days × multiple entries/day, could grow large.

---

## 7. Edge Cases: Handled vs. Missed

### Handled

| Edge Case | Where Handled |
|-----------|---------------|
| `state.db` not found | `monitor.py:146-147` — returns error dict |
| No sessions in time range | `monitor.py:165-170` — returns zero-count result |
| Empty tool content | `classify_tool_result` — returns `(False, "")` immediately |
| `tool_calls` as string or list | `detect_retry_patterns:118` — tries `json.loads` then dict access |
| `Counter` in JSON serialization | `monitor.py:356` — `default=str` |
| Empty `SKILLS_DIR` | `analyzer.py:27-28` — returns `{}` |
| Duplicate recommendation targets | `analyzer.py:133-138` — keeps first (highest priority) |
| Evolution venv missing | `fixer.py:496-499` — returns error status |
| API key missing | `fixer.py:501-505` — returns error status |
| Evolution timeout | `fixer.py:549-551` — returns timeout status |
| Metrics file missing | `tracker.py:28-34` — returns `[]` |
| JSON decode error on metrics | `tracker.py:32` — returns `[]` |
| Atomic write to prevent corruption | `tracker.py:68-72` — temp file + rename |
| Concurrent write race | Not handled (no file locking) |
| FTS index rebuild failure | `seed_demo_data.py:261-265` — silently skipped |

### Missed

| Edge Case | Impact |
|-----------|--------|
| Different `state.db` schema | `monitor.py` crashes on column access |
| Tool name with non-ASCII characters | Regex matching may fail |
| Very long error messages (>50 chars context window in classify) | Context extraction may truncate |
| Session with 0 messages | Included in session list but contributes nothing |
| Skill name collision (hyphen vs underscore) | Inconsistent matching in `map_tool_to_skill` |
| New session added while analysis running | Query may get inconsistent snapshot |
| GEPA output format change | Score parsing silently fails |
| Very large `metrics.json` (>1MB) | Loads entire file into memory |
| Interrupted atomic write | `.tmp` file left behind orphaned |
| Skills directory permissions | `apply_fixes` silently fails to write |
| Empty skill gap recommendation | Could create empty/useless skills |
| Self-referential skill patch | Skill that patches itself could enter infinite loop |
| Tool that is both skill name and tool name | Double-counting in metrics |

---

## 8. Reimplementation Guide

This section is intended to allow someone to reimplement Hermes Dojo from scratch using only this document as reference.

### Core Data Flow to Reimplement

1. **Monitor:** Connect to `~/.hermes/state.db`, query sessions within time window, load all their messages, iterate to compute error rates, correction counts, retry patterns, skill gaps.

2. **Analyzer:** Scan `~/.hermes/skills/*/SKILL.md` to discover skills. For each weak tool, attempt fuzzy name match. Generate 4 action types: patch (skill exists), create (no skill), evolve (success < 90% + total >= 5), investigate (retry loops).

3. **Fixer:** Map error text to fix strategy (path → validation, timeout → retry, permission → checks, etc.). For patches, append structured markdown to skill. For creates, generate YAML frontmatter + markdown body from template or strategy. For evolution, subprocess call to GEPA CLI.

4. **Reporter:** Format data as CLI box-drawing or Telegram markdown. Compute delta from previous snapshot. Generate sparkline from historical rates.

5. **Tracker:** JSON file at `~/.hermes/skills/hermes-dojo/data/metrics.json`. Append snapshots, filter >90 days, atomic write.

### Key Constants to Preserve

**Error patterns (20):** The full list in `monitor.py` lines 29-50
**Correction patterns (20):** The full list in `monitor.py` lines 53-71
**Skill gap patterns (12):** The full list in `monitor.py` lines 74-87
**Fix strategies (7 categories):** The full `FIX_STRATEGIES` dict in `fixer.py` lines 36-89
**Skill templates (4):** The full `SKILL_TEMPLATES` dict in `fixer.py` lines 166-395
**Evolution model:** `openrouter/nousresearch/hermes-3-llama-3.1-70b`

### Schema Contracts

**state.db sessions table:** `id TEXT PRIMARY KEY, source TEXT, model TEXT, started_at REAL, ended_at REAL, end_reason TEXT, message_count INTEGER, tool_call_count INTEGER`

**state.db messages table:** `id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, tool_calls TEXT, tool_name TEXT, timestamp REAL`

**metrics.json snapshot:** `{"timestamp": float, "date": str, "sessions_analyzed": int, "total_tool_calls": int, "overall_success_rate": float, "total_errors": int, "user_corrections": int, "skill_gaps": int, "retry_patterns": int, "weakest_tools": [...], "improvements_made": [...]?}`

### Critical Implementation Notes

1. **tool_calls column** can be JSON string OR a Python list (if Hermes writes raw Python objects). Always try `json.loads` first.

2. **skill_to_tool mapping** should handle both underscore and hyphen separators, case-insensitively.

3. **Atomic writes** are mandatory for tracker.py. Use `Path.with_suffix(".tmp")` + `replace()`.

4. **ERROR_PATTERNS order matters** — earlier patterns take precedence. "error:" will match before more specific patterns.

5. **GEPA evolution** requires both the `hermes-agent-self-evolution` repo cloned at `~/.hermes/hermes-agent-self-evolution` AND a virtualenv at `.venv/bin/python3`. Check both exist before attempting.

6. **OPENROUTER_API_KEY** must be loaded from `~/.hermes/.env` (not from environment exclusively, as the evolution CLI needs it).

7. **Skill gaps need >= 2 occurrences** to trigger a create recommendation. Single occurrences are noise.

8. **Patch recommendation threshold** is `errors >= 2`. Single errors are skipped.

9. **Evolve recommendation threshold** is `success_rate < 90 AND total >= 5`. Below-90% but rare tools aren't evolved (not enough data).

### File Output Locations

| File | Location |
|------|----------|
| Installed skill | `~/.hermes/skills/hermes-dojo/` |
| Created skills | `~/.hermes/skills/<skill-name>/SKILL.md` |
| Metrics history | `~/.hermes/skills/hermes-dojo/data/metrics.json` |
| Evolution repo | `~/.hermes/hermes-agent-self-evolution/` |
| Evolution venv | `~/.hermes/hermes-agent-self-evolution/.venv/bin/python3` |
| Hermes config | `~/.hermes/.env` |

---

*Document generated: 2026-03-29*
*Source: hermes-dojo repository, all 2,444 lines across 7 Python files read and analyzed*
