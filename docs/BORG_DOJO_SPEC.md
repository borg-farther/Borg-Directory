# Borg + Dojo Integration Specification

**Document Type:** Google-Level Engineering Design Document
**Status:** DRAFT v1.0
**Date:** 2026-03-29
**Authors:** Hermes Agent (multi-agent deep research)
**Reviewers:** Adversarial Review Sub-agent (see BORG_DOJO_SPEC_REVIEW.md)

---

## 1. Executive Summary

This specification defines the integration of hermes-dojo's session analysis capabilities into agent-borg's collective intelligence architecture. The result is a closed-loop self-improvement system: borg reads Hermes's session history, classifies failures, detects skill gaps, auto-fixes weak skills, tracks improvement over time, and propagates successful fixes across the collective. Unlike dojo (single-agent, no tests, security gaps), this integration is built to Google engineering standards: PII-redacted, paginated, rollback-safe, versioned interfaces, and 75+ tests.

---

## 2. Background

### 2.1 Agent-Borg (Current State)

| Component | Status | LOC |
|-----------|--------|-----|
| `aggregator.py` | Pack-level metrics from telemetry.jsonl | 355 |
| `nudge.py` | NudgeEngine with background thread, signal aggregation | 388 |
| `search.py` | Pack search with keyword classification (20+ categories) | ~600 |
| `apply.py` | Multi-phase pack execution with checkpoints | ~1100 |
| `reputation.py` | Agent trust scoring (contribution, access tiers, free-rider detection) | ~460 |
| `analytics.py` | Ecosystem health metrics, time-series | ~300 |
| `mcp_server.py` | 14 MCP tools (JSON-RPC 2.0) | ~1200 |
| `hermes-plugin` | Hooks into agent loop, starts NudgeEngine | ~340 |
| Tests | 1083 passing | ~5000 |

**Key gap:** Borg has no way to read Hermes's actual session data. The aggregator reads its own telemetry logs, not the agent's real performance history.

### 2.2 Hermes-Dojo (Current State)

| Component | LOC | What It Does |
|-----------|-----|-------------|
| `monitor.py` | 358 | Reads `~/.hermes/state.db`, classifies tool failures, detects corrections |
| `analyzer.py` | 220 | Ranks weaknesses, maps tools→skills, generates recommendations |
| `fixer.py` | 709 | Generates fix plans, applies patches, runs GEPA evolution |
| `reporter.py` | 206 | CLI + Telegram formatted reports |
| `tracker.py` | 150 | Daily metric snapshots, learning curve with sparklines |
| `demo.py` | 225 | Full pipeline runner with demo data seeding |
| `failure_patterns.md` | 42 | Error→fix reference table |
| Tests | 0 | None |

**Key strengths:** Reads real session data, practical error classification, concrete fix strategies.
**Key weaknesses (from adversarial review):**
- P0: PII flows unreduced (user_id = Telegram chat IDs)
- P0: No credential scrubbing in error text
- P0: No state.db corruption handling
- P0: No rollback on partial fix application
- P1: No pagination (loads all messages into memory)
- P1: O(n×m) regex on every message
- P1: No interface versioning

### 2.3 The Database

```
~/.hermes/state.db (SQLite, WAL mode, schema v6)
├── sessions (715 rows)
│   ├── id TEXT PRIMARY KEY
│   ├── source TEXT (cli|telegram|discord|slack|...)
│   ├── user_id TEXT (PII! Telegram chat ID)
│   ├── model TEXT
│   ├── system_prompt TEXT (PII! may contain user context)
│   ├── started_at REAL (unix timestamp)
│   ├── ended_at REAL
│   ├── tool_call_count INTEGER
│   ├── estimated_cost_usd REAL
│   └── title TEXT
└── messages (22,349 rows)
    ├── id INTEGER PRIMARY KEY
    ├── session_id TEXT → sessions.id
    ├── role TEXT (user|assistant|tool|system)
    ├── content TEXT (PII! raw conversation)
    ├── tool_calls TEXT (JSON array)
    ├── tool_call_id TEXT
    └── timestamp REAL
```

---

## 3. Goals and Non-Goals

### Goals

| ID | Goal | Measurable Criterion |
|----|------|---------------------|
| G1 | Read Hermes session data safely | state.db reads without corruption, PII-redacted |
| G2 | Classify tool failures accurately | >90% precision on known error categories |
| G3 | Detect user corrections | >85% recall on correction signals |
| G4 | Identify skill gaps | Flag capabilities requested 3+ times with no skill |
| G5 | Auto-fix weak skills | Generate valid patches/new skills for top 3 weaknesses |
| G6 | Track improvement over time | Daily metric snapshots with trend analysis |
| G7 | Deliver actionable reports | CLI + Telegram + Discord formatted output |
| G8 | Integrate with borg's collective | Session insights feed into reputation, nudge, search |
| G9 | Run as overnight cron pipeline | analyze→fix→report in single scheduled run |
| G10 | 75+ tests | Unit, integration, E2E coverage |

### Non-Goals

- **N1:** Modifying hermes core (`run_agent.py`) — we read state.db, we don't hook into the agent loop
- **N2:** Running GEPA/DSPy self-evolution — too complex, requires separate install. Defer to Phase 4.
- **N3:** Cross-agent session sharing — collective intelligence is for packs, not raw sessions
- **N4:** Real-time session interception — we analyze after-the-fact, not during execution
- **N5:** Replacing borg's existing aggregator — we augment it, not replace it

---

## 4. Detailed Design

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    BORG DOJO INTEGRATION                         │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ SessionReader │───▶│ FailureClassifier│───▶│ SkillGapDetect│  │
│  │ (state.db)   │    │ (error+correction│    │ (request freq) │  │
│  └──────┬───────┘    │  patterns)       │    └───────┬───────┘  │
│         │            └────────┬─────────┘            │          │
│         │                     │                       │          │
│         ▼                     ▼                       ▼          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              SessionAnalysis (dataclass)                  │   │
│  │  tool_metrics, failure_reports, corrections,              │   │
│  │  skill_gaps, retry_patterns, summary_stats                │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│         ┌───────────────┼───────────────┐                       │
│         ▼               ▼               ▼                       │
│  ┌─────────────┐ ┌────────────┐ ┌─────────────────┐            │
│  │  AutoFixer  │ │ LearningCrv│ │ ReportGenerator  │            │
│  │ (patch/crt) │ │ (snapshots)│ │ (CLI/TG/Discord) │            │
│  └──────┬──────┘ └─────┬──────┘ └────────┬─────────┘            │
│         │              │                  │                      │
│         ▼              ▼                  ▼                      │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         EXISTING BORG MODULES                         │       │
│  │  aggregator │ nudge │ search │ reputation │ analytics │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              CronPipeline                             │       │
│  │  analyze_sessions() → classify → detect_gaps →        │       │
│  │  auto_fix() → snapshot() → report() → deliver()      │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Module: `borg/dojo/session_reader.py`

Reads `~/.hermes/state.db` safely with PII redaction, pagination, and WAL-safe access.

```python
@dataclass
class ToolCallRecord:
    """A single tool invocation extracted from messages."""
    session_id: str
    tool_name: str
    arguments_hash: str  # SHA256 of args, never raw args (PII safety)
    result_snippet: str  # first 200 chars, PII-redacted
    is_error: bool
    error_type: str      # classified error category
    timestamp: float
    turn_index: int

@dataclass
class SessionSummary:
    """Aggregated session metadata, PII-free."""
    session_id: str
    source: str           # cli|telegram|discord
    model: str
    started_at: float
    ended_at: Optional[float]
    tool_call_count: int
    message_count: int
    estimated_cost_usd: Optional[float]
    # PII fields intentionally omitted: user_id, system_prompt
```

**Key design decisions:**
- **Read-only, WAL-safe:** Open with `?mode=ro&nolock=1` URI. Set `PRAGMA query_only = ON`.
- **Pagination:** Process 100 sessions at a time, yielding results. Never load all messages.
- **PII pipeline:** `user_id` → HMAC-SHA256 (anonymized). `system_prompt` → never read. `content` → passed through `privacy.redact_pii()` before storage.

```python
class SessionReader:
    """Safe, paginated reader for ~/.hermes/state.db."""

    def __init__(self, db_path: Path = None, days: int = 7, page_size: int = 100):
        self.db_path = db_path or Path.home() / ".hermes" / "state.db"
        self.days = days
        self.page_size = page_size
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> None:
        """Open read-only connection with integrity check."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"state.db not found: {self.db_path}")
        uri = f"file:{self.db_path}?mode=ro&nolock=1"
        self._conn = sqlite3.connect(uri, uri=True)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA query_only = ON")
        # Integrity check (fast — checks freelist only)
        result = self._conn.execute("PRAGMA quick_check").fetchone()
        if result[0] != "ok":
            raise RuntimeError(f"state.db integrity check failed: {result[0]}")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self): self.open(); return self
    def __exit__(self, *a): self.close()

    def iter_sessions(self) -> Iterator[SessionSummary]:
        """Yield sessions from the last N days, paginated."""
        cutoff = time.time() - (self.days * 86400)
        offset = 0
        while True:
            rows = self._conn.execute(
                """SELECT id, source, model, started_at, ended_at,
                          tool_call_count, message_count, estimated_cost_usd
                   FROM sessions
                   WHERE started_at > ?
                   ORDER BY started_at DESC
                   LIMIT ? OFFSET ?""",
                (cutoff, self.page_size, offset)
            ).fetchall()
            if not rows:
                break
            for row in rows:
                yield SessionSummary(
                    session_id=row["id"],
                    source=row["source"] or "unknown",
                    model=row["model"] or "unknown",
                    started_at=row["started_at"],
                    ended_at=row["ended_at"],
                    tool_call_count=row["tool_call_count"] or 0,
                    message_count=row["message_count"] or 0,
                    estimated_cost_usd=row["estimated_cost_usd"],
                )
            offset += self.page_size

    def get_tool_calls(self, session_id: str) -> List[ToolCallRecord]:
        """Extract tool calls from a session's messages."""
        rows = self._conn.execute(
            """SELECT m1.session_id, m1.content AS assistant_content,
                      m1.tool_calls, m2.content AS tool_result,
                      m2.tool_call_id, m2.timestamp
               FROM messages m1
               JOIN messages m2 ON m2.session_id = m1.session_id
                                AND m2.tool_call_id IS NOT NULL
               WHERE m1.session_id = ? AND m1.role = 'assistant'
                     AND m1.tool_calls IS NOT NULL
               ORDER BY m2.timestamp""",
            (session_id,)
        ).fetchall()
        # ... parse tool_calls JSON, classify results, redact PII ...

    def get_user_messages(self, session_id: str) -> List[Tuple[str, float]]:
        """Get PII-redacted user messages for correction detection."""
        rows = self._conn.execute(
            "SELECT content, timestamp FROM messages WHERE session_id = ? AND role = 'user' ORDER BY timestamp",
            (session_id,)
        ).fetchall()
        return [(redact_pii(row["content"]), row["timestamp"]) for row in rows]
```

### 4.3 Module: `borg/dojo/failure_classifier.py`

Classifies tool call results into error categories. Addresses the adversarial review's concerns about false positives.

```python
@dataclass
class FailureReport:
    """A classified tool failure."""
    tool_name: str
    error_category: str     # path_not_found|timeout|permission|command_not_found|rate_limit|syntax|network|generic
    error_snippet: str      # PII-redacted, max 200 chars
    session_id: str
    timestamp: float
    confidence: float       # 0.0-1.0, how certain the classification is

# Error categories with patterns and context requirements
ERROR_CATEGORIES: Dict[str, ErrorCategory] = {
    "path_not_found": ErrorCategory(
        patterns=[r"(?i)no such file", r"(?i)ENOENT", r"(?i)FileNotFoundError"],
        # ONLY match in tool role messages (not assistant reasoning)
        role_filter="tool",
        min_confidence=0.9,
    ),
    "timeout": ErrorCategory(
        patterns=[r"(?i)ETIMEDOUT", r"(?i)timed?\s*out", r"(?i)deadline exceeded"],
        role_filter="tool",
        min_confidence=0.85,
    ),
    "permission_denied": ErrorCategory(
        patterns=[r"(?i)EACCES", r"(?i)permission denied", r"(?i)403 forbidden"],
        role_filter="tool",
        min_confidence=0.9,
    ),
    "command_not_found": ErrorCategory(
        patterns=[r"(?i)command not found", r"(?i)not recognized"],
        role_filter="tool",
        min_confidence=0.95,
    ),
    "rate_limit": ErrorCategory(
        patterns=[r"(?i)429", r"(?i)rate limit", r"(?i)too many requests"],
        role_filter="tool",
        min_confidence=0.9,
    ),
    "syntax_error": ErrorCategory(
        patterns=[r"(?i)SyntaxError", r"(?i)IndentationError", r"(?i)unexpected token"],
        role_filter="tool",
        min_confidence=0.95,
    ),
    "network": ErrorCategory(
        patterns=[r"(?i)connection refused", r"(?i)ECONNREFUSED", r"(?i)network unreachable"],
        role_filter="tool",
        min_confidence=0.85,
    ),
}

# FALSE POSITIVE MITIGATION:
# Pattern: (?i)could not → matches assistant text "I could not find..."
# Fix: Only match patterns in `role='tool'` messages, never in assistant/user.
# Pattern: (?i)error → matches "no errors found"
# Fix: Require error pattern + non-success exit code or explicit error structure.
```

**Correction detection** — user correction patterns applied ONLY to `role='user'` messages:

```python
CORRECTION_PATTERNS = [
    # High confidence (explicit correction)
    (r"(?i)^no[,.\s]", 0.9),
    (r"(?i)wrong\s+(file|path|dir)", 0.95),
    (r"(?i)I meant", 0.9),
    (r"(?i)that's not (right|correct|what)", 0.9),
    # Medium confidence (possible correction)
    (r"(?i)try again", 0.7),
    (r"(?i)doesn't work", 0.7),
    (r"(?i)not working", 0.7),
    # Low confidence (may be unrelated)
    (r"(?i)stop", 0.5),  # could be "stop the server" not a correction
    (r"(?i)undo", 0.6),
]
```

### 4.4 Module: `borg/dojo/skill_gap_detector.py`

```python
@dataclass
class SkillGap:
    """A detected missing capability."""
    capability: str         # normalized name (e.g., "csv-parsing")
    request_count: int      # how many times user asked
    session_ids: List[str]  # which sessions
    confidence: float
    existing_skill: Optional[str]  # if a skill exists but user still struggles

REQUEST_PATTERNS: List[Tuple[str, str]] = [
    (r"(?i)parse.*csv|csv.*parse", "csv-parsing"),
    (r"(?i)convert.*pdf|pdf.*convert", "pdf-conversion"),
    (r"(?i)send.*email|email.*send", "email-sending"),
    (r"(?i)create.*chart|plot.*graph", "chart-creation"),
    (r"(?i)docker.*compose|compose.*up", "docker-management"),
    (r"(?i)deploy.*to|push.*prod", "deployment"),
    (r"(?i)scrape.*web|crawl.*site", "web-scraping"),
    (r"(?i)unit.*test|test.*unit", "unit-testing"),
    (r"(?i)database.*query|sql.*query", "database-operations"),
    (r"(?i)api.*call|fetch.*api|rest.*api", "api-integration"),
    (r"(?i)resize.*image|crop.*image", "image-processing"),
    (r"(?i)merge.*pdf|split.*pdf", "pdf-manipulation"),
]

# Threshold: report as gap only if requested 3+ times
SKILL_GAP_THRESHOLD = 3
```

### 4.5 Module: `borg/dojo/auto_fixer.py`

**Decision tree:**

```
For each weakness (ranked by priority score):
  1. Is there an existing skill for this tool?
     ├─ YES: Is success rate > 60%?
     │   ├─ YES → ACTION: patch (add error handling for specific failure)
     │   └─ NO  → ACTION: evolve (skill needs deeper rework) [deferred to Phase 4]
     └─ NO: Has user requested this capability 3+ times?
         ├─ YES → ACTION: create (new skill from session patterns)
         └─ NO  → ACTION: log (note for future, don't auto-create)
```

**Rollback safety** (addresses P0 from review):

```python
@dataclass
class FixAction:
    """A proposed fix with rollback capability."""
    action: str              # "patch" | "create" | "evolve" | "log"
    target_skill: str
    priority: float
    reason: str
    fix_content: str         # the patch text or new skill content
    backup_content: Optional[str]  # original content before patch (for rollback)
    applied: bool = False
    success: bool = False
    rollback_path: Optional[str] = None  # path to backup file

class AutoFixer:
    """Applies fixes with atomic rollback support."""

    BACKUP_DIR = Path.home() / ".hermes" / "borg" / "dojo_backups"

    def apply_fix(self, fix: FixAction) -> FixAction:
        """Apply a single fix with backup."""
        if fix.action == "patch":
            skill_path = self._find_skill(fix.target_skill)
            if not skill_path:
                fix.success = False
                return fix
            # Backup original
            backup_path = self.BACKUP_DIR / f"{fix.target_skill}_{int(time.time())}.md"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_path / "SKILL.md", backup_path)
            fix.backup_content = (skill_path / "SKILL.md").read_text()
            fix.rollback_path = str(backup_path)
            # Apply patch
            try:
                self._apply_patch(skill_path / "SKILL.md", fix.fix_content)
                fix.applied = True
                fix.success = True
            except Exception as e:
                # Rollback
                shutil.copy2(backup_path, skill_path / "SKILL.md")
                fix.applied = False
                fix.success = False
            return fix

    def rollback_fix(self, fix: FixAction) -> bool:
        """Rollback a previously applied fix."""
        if not fix.rollback_path or not Path(fix.rollback_path).exists():
            return False
        skill_path = self._find_skill(fix.target_skill)
        shutil.copy2(fix.rollback_path, skill_path / "SKILL.md")
        return True
```

**Fix strategies** (8 categories from dojo, improved):

```python
FIX_STRATEGIES: Dict[str, FixStrategy] = {
    "path_not_found": FixStrategy(
        patch_instruction="Add path validation before file operations. "
                         "Check `os.path.exists()` first. Search common alternatives.",
        skill_addition="## Pre-flight Checks\n- Verify path exists before ANY file operation\n"
                       "- Search ~/Documents/, ./, ~/ if not found\n- Ask user if ambiguous",
    ),
    "timeout": FixStrategy(
        patch_instruction="Add retry with exponential backoff (5s, 10s, 20s). "
                         "Fall back to alternative method after 3 failures.",
        skill_addition="## Timeout Handling\n- Set initial timeout to 10s\n"
                       "- Retry 3x with 2x backoff\n- Fall back to alternative approach",
    ),
    "permission_denied": FixStrategy(
        patch_instruction="Check permissions before operations. "
                         "Suggest chmod/sudo with explanation.",
        skill_addition="## Permission Checks\n- Verify file permissions before read/write\n"
                       "- Explain the permission issue clearly\n- Never auto-sudo without confirmation",
    ),
    "command_not_found": FixStrategy(
        patch_instruction="Verify command exists with `which` before execution. "
                         "Suggest install if missing.",
        skill_addition="## Command Verification\n- Run `which <command>` before use\n"
                       "- Suggest installation if missing\n- Try alternatives (python3 vs python)",
    ),
    "rate_limit": FixStrategy(
        patch_instruction="Parse retry-after header. Use exponential backoff. "
                         "Fall back to alternative data source.",
        skill_addition="## Rate Limiting\n- Check for 429 + retry-after header\n"
                       "- Wait before retrying\n- Fall back to alternative source",
    ),
    "syntax_error": FixStrategy(
        patch_instruction="Validate syntax before execution. "
                         "Use ast.parse() for Python, shellcheck for bash.",
        skill_addition="## Syntax Validation\n- Pre-validate code before execution\n"
                       "- Show specific error location with context",
    ),
    "network": FixStrategy(
        patch_instruction="Check connectivity before network operations. "
                         "Add timeout and retry logic.",
        skill_addition="## Network Resilience\n- Verify connectivity first\n"
                       "- Set explicit timeouts\n- Retry with backoff on transient failures",
    ),
    "generic": FixStrategy(
        patch_instruction="Add try/except with clear error messages and user guidance.",
        skill_addition="## Error Handling\n- Wrap operations in try/except\n"
                       "- Log clear error messages\n- Suggest actionable next steps",
    ),
}
```

### 4.6 Module: `borg/dojo/learning_curve.py`

```python
@dataclass
class MetricSnapshot:
    """A point-in-time measurement of agent performance."""
    timestamp: float
    date: str                      # YYYY-MM-DD HH:MM
    sessions_analyzed: int
    total_tool_calls: int
    overall_success_rate: float    # 0.0-100.0
    total_errors: int
    user_corrections: int
    skill_gaps_count: int
    retry_pattern_count: int
    weakest_tools: List[Dict]      # top 5 by error count
    improvements_made: List[Dict]  # fixes applied this cycle
    schema_version: int = 1

class LearningCurveTracker:
    """Tracks agent performance over time."""

    METRICS_FILE = Path.home() / ".hermes" / "borg" / "dojo_metrics.json"
    MAX_SNAPSHOTS = 365  # 1 year of daily snapshots

    def save_snapshot(self, analysis: SessionAnalysis, fixes: List[FixAction]) -> MetricSnapshot: ...
    def load_history(self) -> List[MetricSnapshot]: ...
    def get_trend(self, metric: str = "overall_success_rate", days: int = 30) -> Dict: ...
    def sparkline(self, metric: str = "overall_success_rate", width: int = 10) -> str: ...
```

### 4.7 Module: `borg/dojo/report_generator.py`

Three output formats:

```python
class ReportGenerator:
    def generate(self, analysis: SessionAnalysis, fixes: List[FixAction],
                 history: List[MetricSnapshot], fmt: str = "cli") -> str:
        if fmt == "telegram":
            return self._telegram_report(analysis, fixes, history)
        elif fmt == "discord":
            return self._discord_report(analysis, fixes, history)
        else:
            return self._cli_report(analysis, fixes, history)
```

### 4.8 CronPipeline

```python
class DojoPipeline:
    """Full analyze→fix→report pipeline for cron execution."""

    def run(self, days: int = 7, auto_fix: bool = True,
            report_fmt: str = "telegram", deliver_to: str = None) -> str:
        """Execute the full pipeline.

        Returns: formatted report string.
        """
        # Step 1: Read sessions
        with SessionReader(days=days) as reader:
            analysis = self.analyze(reader)

        # Step 2: Auto-fix (if enabled)
        fixes = []
        if auto_fix:
            fixer = AutoFixer()
            recommendations = fixer.recommend(analysis)
            fixes = [fixer.apply_fix(r) for r in recommendations[:3]]  # top 3 only

        # Step 3: Snapshot
        tracker = LearningCurveTracker()
        tracker.save_snapshot(analysis, fixes)
        history = tracker.load_history()

        # Step 4: Generate report
        reporter = ReportGenerator()
        report = reporter.generate(analysis, fixes, history, fmt=report_fmt)

        # Step 5: Feed into borg modules
        self._feed_aggregator(analysis)
        self._feed_nudge(analysis)
        self._feed_reputation(analysis)

        return report
```

### 4.9 Integration with Existing Borg Modules

| Borg Module | Integration Point | Data Flow |
|-------------|-------------------|-----------|
| `aggregator.py` | New `ingest_session_analysis()` | SessionAnalysis → per-pack metrics enrichment |
| `nudge.py` | New signal types `correction`, `skill_gap` | weakest_tools → confidence weighting |
| `search.py` | Extended `classify_task()` keyword map | skill_gaps → dynamic keyword additions |
| `apply.py` | Fix strategies in `action_checkpoint()` | error_category → specific guidance |
| `reputation.py` | `apply_session_feedback()` | per-session success rate → contribution_score |
| `analytics.py` | `timeseries_dojo_metrics()` | learning curve → ecosystem health |
| `hermes-plugin` | Periodic `analyze_sessions()` call | cached dojo context for nudge engine |

---

## 5. Data Model

### 5.1 Core Dataclasses

```python
@dataclass
class SessionAnalysis:
    """Complete analysis result. The single interface contract between dojo and borg."""
    schema_version: int = 1  # MUST increment on any field change
    analyzed_at: float = 0.0
    days_covered: int = 7
    sessions_analyzed: int = 0
    total_tool_calls: int = 0
    total_errors: int = 0
    overall_success_rate: float = 0.0
    user_corrections: int = 0
    tool_metrics: Dict[str, ToolMetric] = field(default_factory=dict)
    failure_reports: List[FailureReport] = field(default_factory=list)
    skill_gaps: List[SkillGap] = field(default_factory=list)
    retry_patterns: List[RetryPattern] = field(default_factory=list)
    weakest_tools: List[ToolMetric] = field(default_factory=list)  # sorted by error count desc

@dataclass
class ToolMetric:
    tool_name: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    top_error_category: str
    top_error_snippet: str

@dataclass
class RetryPattern:
    tool_name: str
    consecutive_count: int
    session_id: str
    time_window_seconds: float
```

### 5.2 Interface Versioning

**All borg modules MUST check `schema_version` before accessing fields:**

```python
def ingest_session_analysis(self, analysis: SessionAnalysis) -> None:
    if analysis.schema_version > SUPPORTED_SCHEMA_VERSION:
        logger.warning("Unsupported dojo schema version %d, skipping", analysis.schema_version)
        return
    # ... process analysis ...
```

---

## 6. API Design

### Public Functions

```python
# --- session_reader.py ---
def analyze_recent_sessions(days: int = 7, db_path: Path = None) -> SessionAnalysis:
    """One-shot analysis of recent sessions. Main entry point.

    Args:
        days: Number of days to look back (default: 7)
        db_path: Override path to state.db (default: ~/.hermes/state.db)

    Returns:
        SessionAnalysis with all metrics, failures, gaps, and patterns.

    Raises:
        FileNotFoundError: state.db doesn't exist
        RuntimeError: state.db integrity check failed
    """

# --- failure_classifier.py ---
def classify_tool_result(content: str, role: str = "tool") -> Tuple[bool, str, float]:
    """Classify a tool result as success or failure.

    Args:
        content: The tool result text (PII-redacted)
        role: Message role (only 'tool' messages are classified)

    Returns:
        (is_error, error_category, confidence)
    """

def detect_corrections(messages: List[Tuple[str, float]]) -> List[CorrectionSignal]:
    """Detect user correction signals in a conversation.

    Args:
        messages: List of (content, timestamp) tuples for user messages

    Returns:
        List of CorrectionSignal with pattern, confidence, timestamp
    """

# --- skill_gap_detector.py ---
def detect_skill_gaps(user_messages: List[str], existing_skills: Dict[str, Path]) -> List[SkillGap]:
    """Detect missing capabilities from user request patterns."""

# --- auto_fixer.py ---
def recommend_fixes(analysis: SessionAnalysis) -> List[FixAction]:
    """Generate ranked fix recommendations from analysis."""

def apply_fix(fix: FixAction) -> FixAction:
    """Apply a fix with backup. Returns updated FixAction with success/rollback info."""

def rollback_fix(fix: FixAction) -> bool:
    """Rollback a previously applied fix. Returns True if successful."""

# --- learning_curve.py ---
def save_snapshot(analysis: SessionAnalysis, fixes: List[FixAction] = None) -> MetricSnapshot:
    """Save a metric snapshot to the learning curve."""

def get_learning_curve(days: int = 30) -> List[MetricSnapshot]:
    """Get metric history for the last N days."""

# --- report_generator.py ---
def generate_report(analysis: SessionAnalysis, fixes: List[FixAction] = None,
                    history: List[MetricSnapshot] = None, fmt: str = "cli") -> str:
    """Generate formatted improvement report."""

# --- pipeline.py ---
def run_dojo_pipeline(days: int = 7, auto_fix: bool = True,
                      report_fmt: str = "telegram") -> str:
    """Run the full dojo pipeline. Main cron entry point."""
```

---

## 7. Error Handling

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| state.db not found | `FileNotFoundError` in `SessionReader.open()` | Return empty `SessionAnalysis` with `sessions_analyzed=0` |
| state.db locked | `sqlite3.OperationalError: database is locked` | Retry 3x with 1s backoff, then skip |
| state.db corrupted | `PRAGMA quick_check` returns non-"ok" | Log warning, return empty analysis |
| WAL file missing | SQLite handles internally | No action needed |
| JSON parse error in tool_calls | `json.JSONDecodeError` | Skip that message, log warning |
| Skill file not found for patch | `FileNotFoundError` | Mark fix as failed, continue with next |
| Patch creates invalid SKILL.md | Post-patch validation (YAML parse) | Auto-rollback from backup |
| metrics.json corrupted | `json.JSONDecodeError` | Start fresh with empty history |
| PII redaction failure | Exception in `redact_pii()` | Replace entire content with `[REDACTED]` |

---

## 8. Security Considerations

### 8.1 PII Redaction Pipeline

```
state.db message → SessionReader.get_tool_calls()
    │
    ▼
privacy.redact_pii(content)
    │  Removes: emails, API keys, file paths with usernames,
    │  IP addresses, Telegram chat IDs, auth tokens
    ▼
FailureClassifier.classify()
    │  Operates on redacted text only
    ▼
SessionAnalysis (PII-free)
    │
    ▼
All downstream consumers (aggregator, nudge, reports)
```

**Rules:**
1. `user_id` is NEVER stored — it's HMAC-SHA256 hashed with a per-install salt
2. `system_prompt` is NEVER read from state.db
3. All `content` fields pass through `privacy.redact_pii()` before any processing
4. Error snippets are capped at 200 chars
5. Tool arguments are stored as SHA256 hashes, never raw
6. Report output is re-scanned with `redact_pii()` before delivery

### 8.2 Credential Scrubbing

Additional patterns beyond existing `privacy.py`:
```python
CREDENTIAL_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",          # OpenAI keys
    r"sk_[a-zA-Z0-9]{20,}",          # ElevenLabs keys
    r"ghp_[a-zA-Z0-9]{36}",          # GitHub PATs
    r"Bearer\s+[a-zA-Z0-9._-]{20,}", # Bearer tokens
    r"(?i)password\s*[=:]\s*\S+",     # Password assignments
]
```

---

## 9. Testing Strategy

### 9.1 Unit Tests (55 tests)

| Module | Tests | Description |
|--------|-------|-------------|
| `session_reader.py` | 12 | Open/close, pagination, PII redaction, integrity check, missing db |
| `failure_classifier.py` | 15 | Each error category, false positive rejection, role filtering, confidence scores |
| `skill_gap_detector.py` | 8 | Pattern matching, threshold, dedup, existing skill check |
| `auto_fixer.py` | 10 | Patch/create decision, rollback, backup creation, invalid skill handling |
| `learning_curve.py` | 5 | Save/load, rotation, sparkline generation, empty history |
| `report_generator.py` | 5 | CLI/Telegram/Discord formats, empty data handling |

### 9.2 Integration Tests (20 tests)

| Test | Description |
|------|-------------|
| `test_reader_to_classifier` | SessionReader output → FailureClassifier |
| `test_classifier_to_analysis` | Classified failures → SessionAnalysis |
| `test_analysis_to_fixer` | SessionAnalysis → AutoFixer recommendations |
| `test_fixer_rollback` | Apply fix → verify → rollback → verify original |
| `test_analysis_to_nudge` | SessionAnalysis → NudgeEngine signals |
| `test_analysis_to_reputation` | SessionAnalysis → ReputationEngine feedback |
| `test_analysis_to_analytics` | SessionAnalysis → AnalyticsEngine metrics |
| `test_analysis_versioning` | Schema version mismatch → graceful skip |
| ... | (12 more covering all module pairs) |

### 9.3 End-to-End Pipeline Tests (5 tests)

| Test | Description |
|------|-------------|
| `test_full_pipeline_with_seeded_data` | Seed state.db → run pipeline → verify report + snapshot |
| `test_pipeline_empty_db` | Empty state.db → graceful empty report |
| `test_pipeline_corrupted_db` | Corrupted state.db → graceful failure with logging |
| `test_pipeline_with_auto_fix` | Run with auto_fix=True → verify backup created + skill patched |
| `test_pipeline_cron_mode` | Simulate cron execution → verify all steps + delivery format |

---

## 10. Migration Plan

1. **Phase 1 is read-only** — no risk to existing functionality
2. All new modules live under `borg/dojo/` — zero changes to existing `borg/core/` in Phase 1
3. Feature flag: `BORG_DOJO_ENABLED = os.getenv("BORG_DOJO_ENABLED", "false").lower() == "true"`
4. Integration points use `try/except ImportError` for graceful degradation
5. Existing tests MUST continue passing — CI gate

---

## 11. Performance

| Operation | Expected Cost | Mitigation |
|-----------|--------------|------------|
| state.db open + integrity check | ~50ms | Quick check only, not full |
| Read 100 sessions | ~10ms | Paginated, indexed query |
| Read messages for 1 session | ~5ms | Indexed on session_id |
| Classify 1 message (50 patterns) | ~0.1ms | Compiled regex cache |
| Full analysis (7 days, ~100 sessions) | ~2-5 seconds | Acceptable for cron |
| Full analysis (30 days, ~500 sessions) | ~10-20 seconds | Still acceptable |
| Metric snapshot save | ~1ms | Atomic write |

**Caching:** `SessionAnalysis` result cached for 1 hour in hermes-plugin to avoid repeated reads during a session.

---

## 12. Dependencies

**Core (stdlib only):**
- `sqlite3`, `json`, `re`, `time`, `hashlib`, `hmac`, `shutil`, `dataclasses`, `pathlib`, `logging`

**Optional:**
- `borg.core.privacy` — for `redact_pii()` (graceful fallback to basic regex if unavailable)

**NOT required:**
- No numpy, pandas, or ML libraries
- No network access (reads local state.db only)
- No GEPA/DSPy (deferred to Phase 4)

---

## 13. Implementation Plan

### Phase 1: Read-Only Analysis (Week 1-2)

| Module | Est. LOC | Priority |
|--------|----------|----------|
| `borg/dojo/__init__.py` | 10 | P0 |
| `borg/dojo/session_reader.py` | 250 | P0 |
| `borg/dojo/failure_classifier.py` | 200 | P0 |
| `borg/dojo/skill_gap_detector.py` | 120 | P0 |
| `borg/dojo/data_models.py` | 100 | P0 |
| Tests for Phase 1 | 500 | P0 |
| **Phase 1 Total** | **~1180** | |

**Milestone:** `analyze_recent_sessions()` returns accurate `SessionAnalysis` from real state.db.

### Phase 2: Auto-Fix + Tracking (Week 3-4)

| Module | Est. LOC | Priority |
|--------|----------|----------|
| `borg/dojo/auto_fixer.py` | 350 | P1 |
| `borg/dojo/learning_curve.py` | 150 | P1 |
| `borg/dojo/report_generator.py` | 200 | P1 |
| Tests for Phase 2 | 400 | P1 |
| **Phase 2 Total** | **~1100** | |

**Milestone:** Full pipeline runs with auto-fix, rollback, and formatted reports.

### Phase 3: Integration + Cron (Week 5-6)

| Module | Est. LOC | Priority |
|--------|----------|----------|
| `borg/dojo/pipeline.py` | 150 | P1 |
| Integration patches to existing modules | 200 | P1 |
| Cron job configuration | 50 | P1 |
| Tests for Phase 3 | 300 | P1 |
| MCP tool: `borg_dojo` | 100 | P2 |
| **Phase 3 Total** | **~800** | |

**Milestone:** Overnight cron delivers morning Telegram report.

### Total: ~3080 new lines of code + ~1200 lines of tests

---

## 14. Success Criteria

| ID | Criterion | Target | Measurement |
|----|-----------|--------|-------------|
| SC1 | Analysis accuracy | >90% precision on error classification | Compare against manually labeled 100-message sample |
| SC2 | Correction detection recall | >85% | Manual review of 50 sessions with known corrections |
| SC3 | Skill gap detection | Finds all gaps with 3+ requests | Cross-reference with user-reported needs |
| SC4 | Auto-fix success rate | >70% of patches produce valid skills | Post-patch YAML validation + manual review |
| SC5 | No PII leakage | 0 PII instances in any output | Automated scan of all reports + snapshots |
| SC6 | State.db safety | 0 write operations to state.db | Read-only mode verified by SQLite trace |
| SC7 | Test coverage | 75+ tests, all passing | CI gate |
| SC8 | Performance | Full analysis < 30s for 30 days | Benchmark on real state.db |
| SC9 | Rollback reliability | 100% rollback success | E2E test with intentional failures |
| SC10 | Report delivery | Reports render correctly on CLI/TG/Discord | Manual verification on each platform |

---

## 15. Means of Verification

| SC | Verification Method |
|----|-------------------|
| SC1 | Create `tests/fixtures/labeled_messages.json` with 100 manually labeled tool results. Run classifier, compare. |
| SC2 | Extract 50 sessions with known user corrections. Run detector, measure recall. |
| SC3 | Plant 5 known skill gaps in test data. Verify all 5 are detected. |
| SC4 | Apply fixes to 10 test skills. Validate each with `yaml.safe_load()` and SKILL.md schema check. |
| SC5 | Run `borg.core.privacy.scan_for_pii()` on all generated reports and metric snapshots. |
| SC6 | Set `PRAGMA query_only = ON` + SQLite operation trace. Verify 0 writes. |
| SC7 | `pytest borg/dojo/tests/ -v --tb=short` → 75+ passed, 0 failed. |
| SC8 | `time python -c "from borg.dojo import analyze_recent_sessions; analyze_recent_sessions(30)"` < 30s |
| SC9 | E2E test: apply fix → corrupt result → verify auto-rollback restores original. |
| SC10 | Send test reports to #test channel on Discord, Telegram DM, and CLI stdout. Screenshot verification. |

---

## 16. Open Questions

| ID | Question | Impact | Proposed Resolution |
|----|----------|--------|-------------------|
| OQ1 | Should dojo modules live under `borg/dojo/` or `borg/core/`? | Architecture | `borg/dojo/` — keeps dojo concerns isolated |
| OQ2 | How often should the hermes-plugin run session analysis? | Performance | Every 50 turns OR when NudgeEngine detects 3+ failures |
| OQ3 | Should auto-fix be opt-in or opt-out? | Safety | Opt-in via `BORG_DOJO_AUTOFIX=true` env var |
| OQ4 | When should we add GEPA self-evolution? | Scope | Phase 4, after proving the patch/create loop works |
| OQ5 | Should session analysis results be shared across the collective? | Privacy | No — raw session data stays local. Only PACKS propagate. |
| OQ6 | Should we add a `borg_dojo` MCP tool? | UX | Yes, Phase 3 — exposes `analyze`, `report`, `history` actions |
| OQ7 | How to handle hermes version differences in state.db schema? | Compatibility | Check schema_version in state.db, support v5+ |

---

## Appendix A: File Manifest

```
borg/dojo/
├── __init__.py              # Package init, feature flag check
├── data_models.py           # All dataclasses (SessionAnalysis, FailureReport, etc.)
├── session_reader.py        # Safe state.db reader with PII pipeline
├── failure_classifier.py    # Error categorization + correction detection
├── skill_gap_detector.py    # Missing capability detection
├── auto_fixer.py            # Patch/create with rollback
├── learning_curve.py        # Metric snapshots + sparklines
├── report_generator.py      # CLI/Telegram/Discord reports
├── pipeline.py              # Full cron pipeline orchestrator
└── tests/
    ├── __init__.py
    ├── test_session_reader.py
    ├── test_failure_classifier.py
    ├── test_skill_gap_detector.py
    ├── test_auto_fixer.py
    ├── test_learning_curve.py
    ├── test_report_generator.py
    ├── test_pipeline.py
    └── fixtures/
        ├── labeled_messages.json
        └── sample_state.db
```

## Appendix B: Borg Module Patches (Phase 3)

```python
# --- borg/core/search.py patch ---
# In classify_task(), after hardcoded keyword map:
def classify_task(text, ...):
    # ... existing code ...
    # Augment with dojo skill gaps (dynamic)
    try:
        from borg.dojo import get_cached_analysis
        analysis = get_cached_analysis()
        if analysis:
            for gap in analysis.skill_gaps:
                if gap.capability in text.lower():
                    categories.add(gap.capability)
    except ImportError:
        pass

# --- borg/integrations/nudge.py patch ---
# In submit_turn(), add correction signal type:
def submit_turn(self, turn_text, turn_index, ...):
    # ... existing signal extraction ...
    # Add dojo correction detection
    try:
        from borg.dojo.failure_classifier import detect_corrections
        corrections = detect_corrections([(turn_text, time.time())])
        for c in corrections:
            self._signals.append(NudgeSignal(
                signal_type="correction",
                value=c.pattern,
                turn_index=turn_index,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
    except ImportError:
        pass
```
