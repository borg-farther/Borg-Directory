# Hermes State DB Schema

**Location:** `~/.hermes/state.db`
**Source:** `SessionDB` class in `~/.hermes/hermes-agent/hermes_state.py`
**Schema Version:** 6

## Overview

The Hermes Agent stores all session and message data in a single SQLite database using WAL mode for concurrent readers. It replaces older per-session JSONL files with a unified store supporting full-text search via FTS5.

**Database stats (current):** 715 sessions, 22,349 messages

---

## Tables

### `sessions`

Primary table for session metadata. Session IDs are typically formatted as `{date}_{time}_{random_id}` (e.g., `20260320_144123_4d3e2612`).

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PRIMARY KEY | Unique session identifier |
| `source` | TEXT NOT NULL | Platform origin: `cli`, `telegram`, `discord`, `slack`, etc. |
| `user_id` | TEXT | Platform-specific user ID (e.g., Telegram chat ID) |
| `model` | TEXT | Model string (e.g., `anthropic/claude-opus-4.6`, `claude-opus-4-6`, `MiniMax-M2.7`) |
| `model_config` | TEXT | JSON blob with model config (max_iterations, reasoning_config, etc.) |
| `system_prompt` | TEXT | Full assembled system prompt snapshot |
| `parent_session_id` | TEXT | For compression-triggered splits; chains via FK to `sessions.id` |
| `started_at` | REAL NOT NULL | Unix timestamp (seconds) when session began |
| `ended_at` | REAL | Unix timestamp when session ended |
| `end_reason` | TEXT | Why session ended: `session_reset`, `cli_close`, `max_iterations`, `error`, etc. |
| `message_count` | INTEGER DEFAULT 0 | Total messages in session |
| `tool_call_count` | INTEGER DEFAULT 0 | Total tool calls made |
| `input_tokens` | INTEGER DEFAULT 0 | Cumulative input tokens |
| `output_tokens` | INTEGER DEFAULT 0 | Cumulative output tokens |
| `cache_read_tokens` | INTEGER DEFAULT 0 | Cache read tokens (Anthropic prompt caching) |
| `cache_write_tokens` | INTEGER DEFAULT 0 | Cache write tokens |
| `reasoning_tokens` | INTEGER DEFAULT 0 | Extended thinking tokens |
| `billing_provider` | TEXT | API provider: `anthropic`, `openai`, `openrouter`, etc. |
| `billing_base_url` | TEXT | API endpoint base URL |
| `billing_mode` | TEXT | Billing mode identifier |
| `estimated_cost_usd` | REAL | Pre-computed cost estimate |
| `actual_cost_usd` | REAL | Final computed cost |
| `cost_status` | TEXT | Cost calculation status |
| `cost_source` | TEXT | Source of pricing data |
| `pricing_version` | TEXT | Pricing version used |
| `title` | TEXT | Optional session title (unique when non-NULL) |

**Indexes:**
- `idx_sessions_source` on `source`
- `idx_sessions_parent` on `parent_session_id`
- `idx_sessions_started` on `started_at DESC`
- `idx_sessions_title_unique` UNIQUE on `title` WHERE `title IS NOT NULL`

---

### `messages`

All messages within a session, ordered by `timestamp` then `id`.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | Row ID |
| `session_id` | TEXT NOT NULL REFERENCES sessions(id) | Parent session |
| `role` | TEXT NOT NULL | `user`, `assistant`, `tool`, `system` |
| `content` | TEXT | Message text content (NULL when tool_calls present) |
| `tool_call_id` | TEXT | Tool call ID for linking tool results to calls |
| `tool_calls` | TEXT | JSON array of tool call objects (NULL for regular messages) |
| `tool_name` | TEXT | Name of tool that produced this result (role=tool only) |
| `timestamp` | REAL NOT NULL | Unix timestamp |
| `token_count` | INTEGER | Token count for this message |
| `finish_reason` | TEXT | Why assistant generation stopped: `stop`, `tool_use`, `max_tokens` |
| `reasoning` | TEXT | Extended thinking/reasoning text (schema v6+) |
| `reasoning_details` | TEXT | JSON structure for reasoning details (schema v6+) |
| `codex_reasoning_items` | TEXT | JSON array for Codex-style reasoning items (schema v6+) |

**Indexes:**
- `idx_messages_session` on `(session_id, timestamp)`

**FTS:** `messages_fts` virtual table using FTS5 with content sync to `messages` table. Auto-updated via triggers on INSERT/UPDATE/DELETE.

**tool_calls JSON structure** (OpenAI/Anthropic format):
```json
[
  {
    "id": "toolu_01B9QPYerEHXidjySzRdgyNL",
    "call_id": "toolu_01B9QPYerEHXidjySzRdgyNL",
    "response_item_id": "fc_toolu_01B9QPYerEHXidjySzRdgyNL",
    "type": "function",
    "function": {
      "name": "session_search",
      "arguments": "{\"query\": \"hermes setup\", \"limit\": 3}"
    }
  }
]
```

---

### `schema_version`

Single-row table tracking migrations.

| Column | Type |
|--------|------|
| `version` | INTEGER NOT NULL |

Current version: **6**

Migration history:
- v2: Added `finish_reason` to messages
- v3: Added `title` to sessions
- v4: Added unique index on `title`
- v5: Added token/billing columns to sessions
- v6: Added `reasoning`, `reasoning_details`, `codex_reasoning_items` to messages

---

## Data Flow

### Session Creation
1. Gateway/CLI calls `SessionDB.create_session()` with session_id, source, model, config
2. Session row inserted with `started_at = time.time()`, counters at 0

### Message Appending
1. Each message calls `SessionDB.append_message()`
2. `tool_calls` list serialized to JSON for storage
3. `message_count` incremented; `tool_call_count` incremented by `len(tool_calls)` if present
4. FTS trigger automatically indexes `content` field

### Tool Call Pattern
- **Assistant** messages with `tool_calls` JSON array represent tool invocations
- **Tool** messages with `tool_name` and `content` represent results
- `tool_call_id` on tool messages links to the original `tool_calls[].id`

### Session End
1. Gateway calls `SessionDB.end_session(session_id, end_reason)`
2. `ended_at` and `end_reason` fields populated
3. Final token counts via `update_token_counts()`

---

## Example Queries

### Get recent sessions with message counts
```sql
SELECT id, source, model, message_count, tool_call_count, started_at, end_reason
FROM sessions
ORDER BY started_at DESC
LIMIT 10;
```

### Get all messages for a session (with tool calls parsed)
```sql
SELECT id, role, content, tool_calls, tool_name, timestamp
FROM messages
WHERE session_id = '20260320_145932_7bb347'
ORDER BY timestamp, id;
```

### Find tool failures (error patterns in tool content)
```sql
SELECT m.session_id, m.tool_name, m.content
FROM messages m
WHERE m.role = 'tool'
  AND m.content LIKE '%error%'
LIMIT 20;
```

### Full-text search across messages
```sql
SELECT m.id, m.session_id, snippet(messages_fts, 0, '>>>', '<<<', '...', 40) as snippet
FROM messages_fts
JOIN messages m ON m.id = messages_fts.rowid
WHERE messages_fts MATCH 'docker OR deployment'
LIMIT 20;
```

### Count sessions by source
```sql
SELECT source, COUNT(*) as count FROM sessions GROUP BY source;
```

---

## Integration Points

### hermes-dojo monitor.py
The `analyze_sessions()` function in `hermes-dojo/scripts/monitor.py` reads from this database:
- Queries sessions within a time window
- Joins with messages to analyze tool call success/failure
- Detects retry patterns, user corrections, skill gaps
- Key query pattern: `SELECT * FROM sessions WHERE started_at > ?` + `SELECT * FROM messages WHERE session_id IN (...)`

### hermes-dojo seed_demo_data.py
Creates test sessions with realistic failure scenarios:
- Sessions tagged with `source = 'dojo-seed'`
- Tool call failures embedded as `role=tool` messages with error content
- User corrections detected via regex patterns

### SessionDB API (hermes_state.py)
```python
from hermes_state import SessionDB

db = SessionDB()  # Uses ~/.hermes/state.db

# Sessions
db.create_session(session_id, source, model, model_config, user_id, parent_session_id)
db.end_session(session_id, end_reason)
db.get_session(session_id)
db.list_sessions_rich(source=None, limit=20, offset=0)
db.search_sessions(source, limit, offset)

# Messages
db.append_message(session_id, role, content, tool_name, tool_calls, tool_call_id, ...)
db.get_messages(session_id)
db.get_messages_as_conversation(session_id)  # Returns OpenAI-format dicts

# Search
db.search_messages(query, source_filter, role_filter, limit, offset)

# Utility
db.session_count(source)
db.message_count(session_id)
db.export_session(session_id)
db.export_all(source)
```

---

## Key Design Notes

1. **WAL mode** enables concurrent reads from gateway's multiple platform handlers
2. **FTS5 triggers** keep full-text index in sync automatically on INSERT/UPDATE/DELETE
3. **JSON serialization** for `tool_calls`, `reasoning_details`, `codex_reasoning_items`, `model_config`
4. **Schema migrations** are additive only (safe for existing data)
5. **Unique title constraint** allows sessions to be looked up by title; `NULL` titles are excluded from uniqueness check
6. **Parent session chaining** enables long conversations to be split when context windows fill
