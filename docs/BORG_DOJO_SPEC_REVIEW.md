# Borg + Dojo Specification Review

**Review Date:** 2026-03-29
**Reviewer:** Adversarial Analysis Sub-agent
**Spec Reference:** Based on research docs — DOJO_DEEP_ANALYSIS.md, HERMES_STATE_DB_SCHEMA.md, BORG_DOJO_INTEGRATION_MAP.md
**Spec Parts:** Not yet written — review based on integration map and source analysis

---

## Executive Summary

The Borg + Dojo integration pipes dojo's fine-grained session analysis (from `state.db`) into borg's pack ecosystem. The integration map is thoughtful and well-structured, but the underlying dojo implementation has significant security, reliability, and scalability gaps that will propagate into borg if not addressed. This review is adversarial — assume the worst-case scenario for every claim.

---

## 1. ARCHITECTURE REVIEW

### Module Decomposition

**Concerns:**

- **dojo monitor.py is a monolith** — 358 lines with 4 separate concerns (error detection, correction detection, skill gap detection, retry detection) tangled in a single `analyze_sessions()` function. This will be difficult to test, debug, and evolve independently. The 20 ERROR_PATTERNS, 20 CORRECTION_PATTERNS, and 12 REQUEST_PATTERNS are all global constants that could be extracted into a configurable rules engine but are hardcoded instead.

- **borg ↔ dojo coupling is bidirectional but asymmetric** — The integration map shows borg depending on dojo outputs (weakest_tools, skill_gaps, user_corrections) but dojo has no awareness of borg's pack ecosystem. If borg publishes a pack that fills a dojo-detected gap, dojo's skill_gaps will be stale until the next cron run. This creates a feedback loop that can oscillate.

- **6 of 7 integration points touch borg/core or borg/db directly** — aggregator.py, search.py, apply.py, reputation.py, analytics.py, and the hermes-plugin all import dojo. This is massive surface area. A breaking change in dojo's API (e.g., renaming a field in the monitor output dict) will silently break multiple borg modules.

- **dojo scripts are not packaged as a module** — They're loose Python files in `hermes-dojo/scripts/`. Importing `from hermes_dojo.scripts.monitor import analyze_sessions` works only if the skill is installed in the right place. The integration map uses lazy imports (`try/except ImportError`) as mitigation, but this masks import errors that should be explicit failures.

**Recommendations:**

- Define a **stable interface contract** between dojo and borg. The `analyze_sessions()` output dict shape should be versioned. Any field rename breaks borg silently unless there's a schema version check.
- Extract dojo's pattern sets (ERROR_PATTERNS, CORRECTION_PATTERNS, REQUEST_PATTERNS) into a rules YAML file so non-engineers can tune detection without editing Python.
- Add integration tests that verify borg modules fail gracefully when dojo is absent, rather than hiding behind lazy imports.

**Severity: P1** — Module boundaries exist but are not enforced. A breaking change in dojo will propagate silently into borg across 6+ integration points.

---

## 2. SECURITY REVIEW

### PII Exposure from state.db

**Critical Concern:**

The `sessions.user_id` column in `state.db` stores **platform-specific user IDs** (e.g., Telegram chat IDs). This is PII. The dojo monitor reads from `state.db` but does NOT filter or redact this field before passing data to borg. The integration map's session context data structure includes no redaction step:

```python
# Shared data structure from integration map — NO redaction:
{
    "overall_success_rate": float,
    "weakest_tools": [...],
    "user_corrections": int,   # ← count only, safe
    # But session_id itself could be linkable to user_id
}
```

However, the monitor.py reads `session_id` from `messages.session_id` which references `sessions.id` which can be joined with `sessions.user_id`. If dojo ever surfaces `session_id` in its output (it does — `retry_patterns[].session_id`), and borg logs or displays it, that's a PII leak.

**Additional PII vectors:**

- `sessions.system_prompt` — may contain user-specific instructions or context
- `sessions.model_config` — may contain user preferences or configuration
- `messages.content` — user text, fully stored and analyzed
- `messages.reasoning` — extended thinking text (schema v6+) could contain highly sensitive content

**The dojo analyzer and fixer write to disk** — `fixer.py` writes patches to `~/.hermes/skills/<skill>/SKILL.md`. If a system prompt from a privileged session is captured in an error message and written to a skill file that gets shared, that's a data exfiltration path.

### Credential Leakage in Tool Outputs

**Concerns:**

- **OPENROUTER_API_KEY** is read by `fixer.py`'s `_load_openrouter_key()` — but the method has a bug (checks for `"OPENROUTER_API_KEY=***"` which never matches real .env files). The key is also passed as a subprocess environment variable to the self-evolution CLI. Subprocess environment inheritance means the API key could appear in process listings or error traces.

- **fixer.py generates `tool_instruction` dicts** that are passed to the `skill_manage` tool. These dicts include `skill_addition` markdown content built from error text. If an error message contains API keys, tokens, or other secrets, they get embedded in skill content.

- **Evolution score parsing is naive** — `run_evolution()` parses `before_score` and `after_score` by searching for `"before" + "score"` in output lines. A malformed output containing `"The score before optimization was impressive"` would crash float extraction or return garbage.

- **No output sanitization** — error text from `state.db` is passed directly into `FIX_STRATEGIES` keyword matching, then into `generate_skill_patch()` output, then into skill files. If a tool error message contains a URL with an API key (e.g., `curl https://api.example.com?key=SECRET`), it gets embedded verbatim.

**Recommendations:**

- **Redact all PII before borg integration** — dojo should never pass `user_id`, `system_prompt`, or raw `session_id` values to borg. At minimum, hash or one-way-tokenize session IDs so they can't be linked back to users.
- **Never write error text to skill files verbatim** — sanitize all content before embedding in generated skills.
- **Fix the `_load_openrouter_key()` bug** — this is currently checking for `***` literally instead of the actual key value.
- **Never pass API keys as environment variables to subprocesses** — use a secrets manager or at minimum, pass as a sealed ephemeral argument rather than env-var inheritance.
- Add a regex-based secret scanner on all error text before it enters the fix pipeline.

**Severity: P0** — PII (user_id, system_prompt) flows from state.db through dojo to borg integration points with no redaction. API key is passed to subprocesses with potential for credential leakage.

---

## 3. RELIABILITY REVIEW

### Failure Modes

**Concerns:**

- **state.db locked or corrupted** — If the Hermes agent is running (WAL mode enables concurrent reads, but not concurrent writes from multiple readers), dojo's read could race with the agent's write. If the DB is locked, dojo crashes. If it's corrupted (e.g., a partial write from a crashed agent), dojo silently returns garbage or crashes on a malformed row.

- **WAL mode does NOT protect against all corruption** — WAL mode helps with concurrent reads, but if a write is interrupted (power loss, OOM kill), the WAL header can be left in an inconsistent state. SQLite's default journal mode (DELETE) would leave a rollback journal; WAL uses a -wal file and -shm file that can become orphaned.

- **No DB integrity check before reading** — monitor.py opens the DB with `sqlite3.connect()` and immediately queries. It does not run `PRAGMA integrity_check` or even `PRAGMA wal_checkpoint` to ensure the WAL has been merged.

- **Partial fix application** — `fixer.py`'s `apply_fixes()` iterates through patches and creations, writing each to disk immediately. If the 3rd of 5 patches fails (disk full, permissions), the first 2 are already written with no rollback. The skill file is now in an inconsistent half-patched state.

- **Append-only patching is a reliability anti-pattern** — Skills are never updated or versioned, only appended to. If a patch is wrong, the only fix is another patch on top. After 50 iterations of patching, the skill is unmaintainable. There's no diff, no backup, no undo.

- **Self-evolution timeout is 300s hardcoded** — If the evolution process takes longer (e.g., a complex skill with slow convergence), it gets killed and the status is `"timeout"` but no cleanup occurs. The evolution CLI may leave partial artifacts.

- **No lifecycle hooks wired** — The integration map shows `on_consecutive_failure` and `on_task_start` hooks are "informational only — not yet called by run_agent.py". If these hooks are the intended integration point but aren't called, the entire nudge engine integration is dead code.

**Recommendations:**

- Run `PRAGMA integrity_check` before reading state.db. If it fails, return an error rather than reading garbage.
- Add a WAL checkpoint before reading to ensure all writes are flushed.
- Wrap `apply_fixes()` in a transaction or at minimum, write to a staging directory and atomic-rename on success.
- Add version tracking and backup before patching skills. At minimum, copy the original to `.skill.md.bak` before appending.
- Make evolution timeout configurable and add cleanup for partial evolution artifacts.
- Verify that lifecycle hooks are actually called before building integration around them.

**Severity: P0** — state.db corruption will crash dojo and corrupt borg's view of sessions. Partial fix application leaves skills in inconsistent states with no rollback.

---

## 4. SCALABILITY REVIEW

### What Happens with 10k Sessions? 100k Messages?

**Current Scale:** HERMES_STATE_DB_SCHEMA.md reports 715 sessions, 22,349 messages.

**Concerns:**

- **monitor.py loads ALL messages for analyzed sessions into memory** — `SELECT * FROM messages WHERE session_id IN (...) ORDER BY timestamp`. For 10k sessions with 20 messages each, that's 200k rows loaded at once. Each row's `tool_calls` JSON is deserialized with `json.loads()`. The `content` field (full user/assistant text) is stored in memory for regex matching against 20+ ERROR_PATTERNS and 20+ CORRECTION_PATTERNS per message.

- **No pagination** — `analyze_sessions()` fetches all messages in one query. There's no streaming, no batching, no cursor-based pagination.

- **O(n × m) regex matching** — n = number of messages, m = number of patterns (50+ total). Each pattern is a compiled regex but they're applied sequentially, not in a combined automaton. For 200k messages × 50 patterns = 10M regex operations per analysis run.

- **skill_gap detection is quadratic** — 12 REQUEST_PATTERNS × every user message = 12 regex operations per message, all loaded in memory first.

- **No caching between cron runs** — The integration map mentions "cache results for at least 5 minutes" but this is only for the borg→dojo integration (nudge engine polling). The dojo scripts themselves have no internal caching. If the cron job runs every hour, it re-analyzes the same data repeatedly.

- **tracker.py appends to metrics.json on every run** — No rotation, no size limit. Over time, this file grows unbounded. At 100k messages per day and daily snapshots, the JSON file will be megabytes within a year.

- **borg/analytics.py** cross-referencing dojo's metrics.json with pack_usage_stats means borg is reading a growing JSON file on every analytics query.

- **SQLite is not designed for 100k+ rows of message data with full-text search** — The FTS5 triggers fire on every INSERT/UPDATE/DELETE. Under heavy write load (100k messages/day), the FTS index rebuilds continuously. The integration map mentions WAL mode for concurrent reads, but WAL checkpointing under write load can cause reader starvation.

**At 10k sessions:**
- Memory: 200k messages × ~1KB average content = 200MB just for content strings, plus Python object overhead, plus regex state. This could exhaust a small server's RAM.
- Time: 10M regex ops could take 10-30 seconds on a fast machine, longer on a constrained one.
- Result: dojo analysis runs for 30+ seconds, cron pipeline becomes blocking, borg integration hangs.

**At 100k messages:**
- Memory: 2GB+ for message content alone.
- Time: Minutes-long analysis runs.
- DB: FTS index bloat — FTS5 tables are typically 2-3x the size of the content they index. 100k messages × 2KB average = 200MB content → 400-600MB FTS index.
- Result: state.db becomes unusable, Hermes agent slows to a crawl.

**Recommendations:**

- Add **streaming/pagination** to `analyze_sessions()` — use `LIMIT/OFFSET` or cursor-based fetching with yield.
- **Combine regex patterns** into a single compiled automaton using `regex` library's combined pattern mode, or use Aho-Corasick for multi-pattern matching.
- Add **result caching** to the dojo scripts themselves, not just the borg integration layer.
- Add **metrics.json rotation** — keep only last 90 days, archive older snapshots.
- Consider moving analytics to a dedicated read replica or using `PRAGMA query_only` to prevent dojo reads from blocking writes.
- Add an **index on `messages.timestamp`** if one doesn't exist (the schema shows an index on `(session_id, timestamp)` which helps, but a timestamp-only index would help with time-windowed queries).

**Severity: P1** — System works at current scale (715 sessions) but will degrade severely at 10k sessions and fail at 100k messages. No pagination, no caching, O(n×m) algorithm.

---

## 5. USABILITY REVIEW

### Is the Cron Pipeline Actually Useful?

**The cron pipeline described:**

```
state.db → monitor.py → analyzer.py → fixer.py → reporter.py → tracker.py → (borg)
```

**Concerns:**

- **Daily snapshots may miss intra-day patterns** — If a critical failure happens at 11am and is fixed by 2pm, the daily snapshot at midnight still shows the failure. A user who runs `borg report` at 9am sees yesterday's data. The sparkline shows "last 7 entries" which means 7 days of lag for trends to appear.

- **Error pattern matching is too generic** — `ERROR_PATTERNS` includes `(?i)could not` and `(?i)unable to`. These match benign text like "I could not find your file" (assistant saying it couldn't find something the user asked about, not a tool failure). This creates false positives in the error rate calculation. A 50% error rate could actually be 5% real failures + 45% regex false positives.

- **User correction detection is naive** — CORRECTION_PATTERNS includes `(?i)^no[,.]` and `(?i)wrong`. The word "no" at the start of a user message is a common conversational particle, not necessarily a correction. "No, I think that's actually fine" is not a correction. "No, wait — I meant the opposite" is. The pattern can't distinguish.

- **Skill gap detection only matches 12 hardcoded patterns** — `REQUEST_PATTERNS` is a fixed list. If a user asks for something not on the list, no gap is detected. The list is not extensible without code changes. A user asking for "kubernetes scaling" would not trigger a gap detection even if no Kubernetes skill exists.

- **Reports are CLI/Telegram-formatted but not actionable** — The reporter outputs weakness names and gap capabilities. But there's no **drill-down path**. A user sees "web-scraping: 8 failures, 23% success rate" and has to manually figure out which session, which URL, which error. The report is diagnostic, not actionable.

- **Improvements made are self-reported** — `improvements_made` in the tracker snapshot is whatever `apply_fixes()` returned. There's no verification that the improvement actually worked. If the patch was wrong and the next day's analysis shows MORE failures, there's no self-correction mechanism.

- **The sparkline is a 7-day rolling window** — If a user runs dojo weekly, they see 1 data point. The sparkline requires at least 2 data points to show a trend (otherwise it's just `█`). This assumes daily cron runs with actual data — a new user with 3 sessions sees no meaningful sparkline.

**Recommendations:**

- **Add intra-day snapshots** (hourly or on-demand) alongside daily, so recent failures aren't hidden.
- **Validate error patterns against tool_name context** — e.g., only flag "could not" as an error if `tool_name` indicates a tool was involved, not just any content match.
- **Use ML or longer context windows** for correction detection — a single regex on message start is insufficient. Consider looking at the previous message to determine if the current "no" is a correction.
- **Make REQUEST_PATTERNS extensible via YAML** and allow borg pack metadata to declare which capabilities they fulfill, so gap detection can cross-reference.
- **Add drill-down to reports** — include a session ID or timestamp for the worst failures so users can investigate.
- **Add a "verified improvement" step** — after applying a fix, re-run the analysis and compare. If failures increased, flag the fix as potentially harmful.

**Severity: P2** — The cron pipeline provides value at a high level (shows trends) but the underlying detection is too noisy to be reliably actionable. Reports lack drill-down and verification.

---

## Summary Table

| Angle | Severity | Critical Issues |
|-------|----------|-----------------|
| Architecture | P1 | Monolith monitor.py; no interface contract; 6+ borg modules couple to dojo |
| Security | P0 | PII (user_id, system_prompt) flows unreduced to borg; API key passed to subprocess; no output sanitization |
| Reliability | P0 | state.db corruption crashes dojo; partial fix application; no rollback; append-only patching anti-pattern |
| Scalability | P1 | No pagination; O(n×m) regex; no caching; unbounded metrics.json; FTS index bloat at 100k messages |
| Usability | P2 | Naive error/correction detection (high false positive rate); no drill-down; no improvement verification |

---

## Recommendations: Top 5 Priority Fixes

1. **[P0] Add PII redaction layer** — Before dojo outputs any data to borg, strip `user_id`, `system_prompt`, and any `session_id` that can be linked to a user. Hash or one-way-tokenize session IDs.

2. **[P0] Fix state.db reliability** — Add `PRAGMA integrity_check` before reading, WAL checkpoint, and a corruption-aware error path that returns empty data rather than crashing.

3. **[P0] Make `apply_fixes()` atomic** — Write to staging, atomic rename on success, rollback on failure. Add backup before patching. Track skill versions.

4. **[P1] Add pagination to `analyze_sessions()`** — Use cursor-based fetching or LIMIT/OFFSET to handle 100k+ messages without memory exhaustion.

5. **[P1] Add result caching** — Both within dojo (avoid re-analysis within 5 minutes) and within the borg integration layer. Cache the full `analyze_sessions()` output keyed by time window.

---

*End of Review*
