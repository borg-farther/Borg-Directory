# Borg Auto-Trace System — Engineering Specification
## World-class contextual intelligence for AI agents
## Version 1.0 | 2026-04-01

---

## 1. SYSTEM OVERVIEW

When an agent solves a hard problem, Borg automatically captures what it learned.
When the next agent hits a similar problem, Borg serves that knowledge instantly.

```
Agent A hits Django QuerySet bug → struggles for 50 tool calls → finds fix in query.py
    ↓ AUTO-CAPTURE
Borg extracts: "QuerySet bug → files: query.py, compiler.py → root cause: alias mutation"
    ↓ STORED
Agent B hits similar QuerySet bug → borg_observe fires →
    "Prior agent found this type of issue in query.py and compiler.py.
     Root cause was alias mutation in change_aliases(). Check there first."
    ↓ Agent B solves in 11 tool calls instead of 50
```

## 2. DATA MODEL

### 2.1 Investigation Trace (SQLite)

```sql
CREATE TABLE traces (
    id TEXT PRIMARY KEY,                    -- uuid4
    
    -- WHAT happened
    task_description TEXT NOT NULL,         -- original task/bug description
    outcome TEXT NOT NULL,                  -- 'success' | 'failure' | 'partial'
    root_cause TEXT,                        -- what the actual issue was (if found)
    approach_summary TEXT,                  -- what approach worked (or didn't)
    
    -- WHERE in the codebase
    files_read TEXT,                        -- JSON array of file paths read
    files_modified TEXT,                    -- JSON array of file paths modified
    key_files TEXT,                         -- JSON array of most important files (top 3)
    
    -- HOW the agent worked
    tool_calls INTEGER,                    -- total tool calls used
    errors_encountered TEXT,               -- JSON array of error messages seen
    dead_ends TEXT,                         -- JSON array of approaches that didn't work
    
    -- MATCHING metadata
    keywords TEXT,                          -- extracted keywords for search
    technology TEXT,                        -- detected tech (django, flask, react, etc.)
    error_patterns TEXT,                    -- normalized error type patterns
    
    -- QUALITY tracking
    helpfulness_score REAL DEFAULT 0.5,    -- shown_and_helped / shown_count
    times_shown INTEGER DEFAULT 0,
    times_helped INTEGER DEFAULT 0,
    
    -- META
    agent_id TEXT,
    created_at TEXT NOT NULL,
    source TEXT DEFAULT 'auto'             -- 'auto' | 'manual' | 'imported'
);

CREATE INDEX idx_traces_keywords ON traces(keywords);
CREATE INDEX idx_traces_technology ON traces(technology);
CREATE INDEX idx_traces_outcome ON traces(outcome);
CREATE INDEX idx_traces_helpfulness ON traces(helpfulness_score DESC);

-- FTS5 for text search
CREATE VIRTUAL TABLE traces_fts USING fts5(
    task_description, root_cause, approach_summary, keywords, error_patterns,
    content=traces, content_rowid=rowid
);
```

### 2.2 Trace Matching Index

```sql
CREATE TABLE trace_file_index (
    trace_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    role TEXT NOT NULL,                     -- 'read' | 'modified' | 'key'
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);
CREATE INDEX idx_tfi_file ON trace_file_index(file_path);

CREATE TABLE trace_error_index (
    trace_id TEXT NOT NULL,
    error_type TEXT NOT NULL,               -- normalized: 'TypeError', 'ImportError', etc.
    error_context TEXT,                     -- first 200 chars of error message
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);
CREATE INDEX idx_tei_error ON trace_error_index(error_type);
```

## 3. AUTO-CAPTURE ENGINE

### 3.1 Capture Hook

Hooks into the MCP tool call stream. After each tool call, accumulates state.
On session end (or after N tool calls with no progress), extracts the trace.

```python
class TraceCapture:
    """Accumulates agent activity and extracts investigation traces."""
    
    def __init__(self):
        self.files_read: list[str] = []
        self.files_modified: list[str] = []
        self.errors: list[str] = []
        self.tool_calls: int = 0
        self.task: str = ""
        self.started_at: float = 0
    
    def on_tool_call(self, tool_name: str, args: dict, result: str):
        """Called after every tool call the agent makes."""
        self.tool_calls += 1
        
        # Track file reads
        if tool_name in ("read_file", "search_files") and "path" in args:
            self.files_read.append(args["path"])
        
        # Track file modifications
        if tool_name in ("write_file", "patch") and "path" in args:
            self.files_modified.append(args["path"])
        
        # Track errors
        if "error" in result.lower() or "traceback" in result.lower():
            # Extract first line of error
            for line in result.split("\n"):
                if "Error" in line or "Exception" in line:
                    self.errors.append(line.strip()[:200])
                    break
    
    def extract_trace(self, outcome: str, task: str = "") -> dict:
        """Extract a structured trace from accumulated activity."""
        # Deduplicate and rank files by frequency
        from collections import Counter
        read_counts = Counter(self.files_read)
        mod_counts = Counter(self.files_modified)
        
        # Key files = most frequently accessed + all modified
        key_files = sorted(
            set(list(mod_counts.keys()) + [f for f, c in read_counts.most_common(3)]),
            key=lambda f: mod_counts.get(f, 0) * 10 + read_counts.get(f, 0),
            reverse=True
        )[:5]
        
        # Extract technology
        technology = self._detect_technology(key_files)
        
        # Extract keywords from task + errors
        keywords = self._extract_keywords(task, self.errors)
        
        # Normalize error patterns
        error_patterns = self._normalize_errors(self.errors)
        
        return {
            "task_description": task or self.task,
            "outcome": outcome,
            "files_read": list(set(self.files_read)),
            "files_modified": list(set(self.files_modified)),
            "key_files": key_files,
            "tool_calls": self.tool_calls,
            "errors_encountered": self.errors[:10],  # cap at 10
            "keywords": keywords,
            "technology": technology,
            "error_patterns": error_patterns,
        }
    
    def _detect_technology(self, files: list[str]) -> str:
        patterns = {
            "django": ["django/", "manage.py", "models.py", "views.py"],
            "flask": ["flask/", "app.py", "routes.py"],
            "react": [".jsx", ".tsx", "component"],
            "python": [".py"],
            "typescript": [".ts", ".tsx"],
            "docker": ["Dockerfile", "docker-compose"],
        }
        for tech, markers in patterns.items():
            if any(any(m in f for m in markers) for f in files):
                return tech
        return "unknown"
    
    def _extract_keywords(self, task: str, errors: list[str]) -> str:
        """Extract searchable keywords from task and errors."""
        text = f"{task} {' '.join(errors)}".lower()
        # Extract significant terms
        stopwords = {"the", "a", "an", "is", "was", "in", "on", "at", "to", "for", 
                     "of", "and", "or", "but", "not", "with", "this", "that", "it"}
        words = [w for w in text.split() if len(w) > 2 and w not in stopwords]
        return " ".join(sorted(set(words)))
    
    def _normalize_errors(self, errors: list[str]) -> str:
        """Extract error type patterns."""
        import re
        types = set()
        for err in errors:
            match = re.search(r'(\w+Error|\w+Exception|\w+Warning)', err)
            if match:
                types.add(match.group(1))
        return " ".join(sorted(types))
```

### 3.2 Integration with MCP Server

```python
# In mcp_server.py — wrap call_tool to capture traces

_active_captures: dict[str, TraceCapture] = {}  # session_id -> capture

def call_tool_with_capture(name: str, arguments: dict, session_id: str = "default") -> str:
    """Wrapper that captures tool activity for trace extraction."""
    result = call_tool(name, arguments)
    
    # Initialize capture for new sessions
    if session_id not in _active_captures:
        _active_captures[session_id] = TraceCapture()
    
    _active_captures[session_id].on_tool_call(name, arguments, result)
    
    # Auto-extract on borg_feedback or after many tool calls without progress
    capture = _active_captures[session_id]
    if name == "borg_feedback" or capture.tool_calls > 40:
        trace = capture.extract_trace(
            outcome="success" if name == "borg_feedback" else "unknown",
            task=arguments.get("task", "")
        )
        if trace["tool_calls"] > 5:  # Only save non-trivial traces
            save_trace(trace)
        del _active_captures[session_id]
    
    return result
```

## 4. TRACE MATCHING ENGINE

### 4.1 Multi-Signal Matcher

```python
class TraceMatcher:
    """Match incoming problems to relevant traces using multiple signals."""
    
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
    
    def find_relevant(self, task: str, error: str = "", 
                      files: list[str] = None, top_k: int = 3) -> list[dict]:
        """Find traces relevant to the current problem.
        
        Scoring:
          - FTS5 text match on task description: base score
          - Error type match: +5 per matching error type
          - File path overlap: +3 per overlapping file
          - Technology match: +2
          - Helpfulness score: multiply by helpfulness
          - Recency: slight boost for newer traces
        """
        candidates = []
        
        # Signal 1: FTS5 text search
        keywords = self._extract_search_terms(task, error)
        if keywords:
            rows = self.db.execute(
                "SELECT rowid, rank FROM traces_fts WHERE traces_fts MATCH ? ORDER BY rank LIMIT 20",
                (keywords,)
            ).fetchall()
            for rowid, rank in rows:
                candidates.append({"rowid": rowid, "score": abs(rank)})
        
        # Signal 2: Error type matching
        if error:
            error_type = self._extract_error_type(error)
            if error_type:
                rows = self.db.execute(
                    "SELECT trace_id FROM trace_error_index WHERE error_type = ?",
                    (error_type,)
                ).fetchall()
                for (tid,) in rows:
                    self._boost_candidate(candidates, tid, 5.0)
        
        # Signal 3: File overlap
        if files:
            for f in files[:5]:
                rows = self.db.execute(
                    "SELECT trace_id FROM trace_file_index WHERE file_path = ?",
                    (f,)
                ).fetchall()
                for (tid,) in rows:
                    self._boost_candidate(candidates, tid, 3.0)
        
        # Fetch full trace data for top candidates
        candidates.sort(key=lambda x: x["score"], reverse=True)
        results = []
        for c in candidates[:top_k]:
            trace = self._load_trace(c.get("rowid") or c.get("trace_id"))
            if trace:
                trace["match_score"] = c["score"]
                # Apply helpfulness multiplier
                trace["match_score"] *= max(0.1, trace.get("helpfulness_score", 0.5))
                results.append(trace)
        
        return sorted(results, key=lambda x: x["match_score"], reverse=True)[:top_k]
    
    def format_trace_for_agent(self, trace: dict) -> str:
        """Format a trace as concise guidance for an agent."""
        parts = []
        
        if trace.get("root_cause"):
            parts.append(f"ROOT CAUSE: {trace['root_cause']}")
        
        if trace.get("key_files"):
            files = json.loads(trace["key_files"]) if isinstance(trace["key_files"], str) else trace["key_files"]
            parts.append(f"KEY FILES: {', '.join(files[:3])}")
        
        if trace.get("approach_summary"):
            parts.append(f"APPROACH: {trace['approach_summary']}")
        
        if trace.get("dead_ends"):
            ends = json.loads(trace["dead_ends"]) if isinstance(trace["dead_ends"], str) else trace["dead_ends"]
            if ends:
                parts.append(f"AVOID: {'; '.join(ends[:3])}")
        
        if trace.get("outcome") == "success":
            parts.append(f"(This approach solved a similar problem in {trace.get('tool_calls', '?')} steps)")
        elif trace.get("outcome") == "failure":
            parts.append(f"(A prior agent tried this but failed — learn from their investigation)")
        
        return "\n".join(parts)
```

### 4.2 Search Term Extraction

```python
def _extract_search_terms(self, task: str, error: str) -> str:
    """Extract FTS5-compatible search terms."""
    text = f"{task} {error}".lower()
    
    # Remove common noise
    noise = {"the", "a", "an", "is", "was", "in", "on", "at", "to", "for", "of",
             "and", "or", "but", "not", "with", "this", "that", "it", "i", "my",
             "fix", "bug", "error", "issue", "problem"}
    
    words = [w for w in re.findall(r'\w+', text) if len(w) > 2 and w not in noise]
    
    # Keep max 8 most specific terms
    return " OR ".join(words[:8])
```

## 5. CONTEXTUAL INJECTION

### 5.1 Enhanced borg_observe

```python
def borg_observe_v2(task: str, context: str = "", files: list[str] = None) -> str:
    """Enhanced observe: check both packs AND traces."""
    
    guidance_parts = []
    
    # Check static packs (existing behavior)
    pack_guidance = borg_observe_original(task, context)
    if pack_guidance:
        guidance_parts.append(pack_guidance)
    
    # Check trace database
    matcher = TraceMatcher(TRACE_DB_PATH)
    traces = matcher.find_relevant(task=task, files=files or [], top_k=2)
    
    for trace in traces:
        if trace["match_score"] > 1.0:  # Only inject high-confidence matches
            formatted = matcher.format_trace_for_agent(trace)
            guidance_parts.append(f"\n📋 Prior investigation found:\n{formatted}")
            
            # Track that we showed this trace
            matcher.record_shown(trace["id"])
    
    return "\n".join(guidance_parts) if guidance_parts else ""
```

### 5.2 Enhanced borg_suggest

```python
def borg_suggest_v2(context: str, error: str = "", attempts: int = 0) -> str:
    """Enhanced suggest: include trace-based suggestions."""
    
    suggestions = []
    
    # Existing pack-based suggestions
    pack_suggestion = borg_suggest_original(context)
    if pack_suggestion:
        suggestions.append(pack_suggestion)
    
    # Trace-based suggestions (only after 2+ failures)
    if attempts >= 2 or "tried" in context.lower() or "failing" in context.lower():
        matcher = TraceMatcher(TRACE_DB_PATH)
        traces = matcher.find_relevant(task=context, error=error, top_k=1)
        
        if traces:
            trace = traces[0]
            formatted = matcher.format_trace_for_agent(trace)
            suggestions.append(
                f"🧠 A prior agent investigated a similar problem:\n{formatted}\n"
                f"Try their approach before starting from scratch."
            )
            matcher.record_shown(trace["id"])
    
    return json.dumps({"success": True, "suggestions": suggestions})
```

## 6. FEEDBACK LOOP

### 6.1 Helpfulness Tracking

```python
def record_trace_outcome(trace_id: str, agent_succeeded: bool):
    """Update trace helpfulness after it was shown to an agent."""
    db.execute("""
        UPDATE traces SET 
            times_shown = times_shown + 1,
            times_helped = times_helped + CASE WHEN ? THEN 1 ELSE 0 END,
            helpfulness_score = CAST(times_helped + CASE WHEN ? THEN 1 ELSE 0 END AS REAL) 
                              / (times_shown + 1)
        WHERE id = ?
    """, (agent_succeeded, agent_succeeded, trace_id))
    db.commit()
```

### 6.2 Decay and Promotion

```python
def maintenance():
    """Run periodically to decay unused traces and promote helpful ones."""
    # Decay traces that haven't been shown in 30 days
    db.execute("""
        UPDATE traces SET helpfulness_score = helpfulness_score * 0.9
        WHERE times_shown = 0 AND created_at < datetime('now', '-30 days')
    """)
    
    # Remove traces with consistently low helpfulness
    db.execute("""
        DELETE FROM traces 
        WHERE times_shown > 5 AND helpfulness_score < 0.1
    """)
    db.commit()
```

## 7. IMPLEMENTATION PLAN

### File Structure
```
borg/core/
  traces.py          -- TraceCapture + save_trace + TraceDB
  trace_matcher.py   -- TraceMatcher + format_trace_for_agent
  
borg/integrations/
  mcp_server.py      -- Enhanced borg_observe_v2, borg_suggest_v2
                     -- call_tool_with_capture wrapper
```

### Migration
```sql
-- Add to existing borg_v3.db
-- Run on first import of traces module
```

### Testing
```
test_trace_capture.py    -- unit tests for TraceCapture
test_trace_matcher.py    -- unit tests for matching
test_trace_integration.py -- end-to-end: capture → store → match → inject
```

## 8. SUCCESS CRITERIA

| Metric | Target | Measurement |
|--------|--------|-------------|
| Trace capture rate | >80% of sessions with >5 tool calls | count(traces) / count(sessions) |
| Match precision | >60% of shown traces are relevant | manual review of 20 traces |
| Agent success lift | >20pp vs no traces (on hard tasks) | A/B test |
| Latency overhead | <100ms per tool call | timing instrumentation |
| Storage growth | <1MB per 100 traces | db size monitoring |

## 9. WHAT THIS ENABLES

Day 1: Passive capture. Every agent session generates traces. Database grows.
Week 1: First matches. New agents get traces from the first week's sessions.
Month 1: Collective intelligence. Traces from 100+ sessions. Matching improves.
Month 3: Borg knows your codebase. Navigation shortcuts for every subsystem.

The more agents use Borg, the smarter Borg gets. This is the flywheel.
