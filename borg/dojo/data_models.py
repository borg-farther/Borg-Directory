"""
Borg Dojo Data Models — Shared dataclasses for dojo analysis pipeline.

All SessionAnalysis objects are PII-free. user_id and system_prompt
are intentionally omitted.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ToolCallRecord:
    """A single tool invocation extracted from messages.

    Attributes:
        session_id: Which session this tool call belongs to.
        tool_name: Name of the tool invoked.
        arguments_hash: SHA256 of the tool arguments (never raw — PII safety).
        result_snippet: First 200 chars of the result, PII-redacted.
        is_error: True if the result was classified as an error.
        error_type: Classified error category (empty if is_error=False).
        timestamp: Unix timestamp of the result.
        turn_index: Which turn within the session this tool call occurred.
    """

    session_id: str
    tool_name: str
    arguments_hash: str
    result_snippet: str
    is_error: bool
    error_type: str
    timestamp: float
    turn_index: int


@dataclass
class SessionSummary:
    """Aggregated session metadata — PII-free.

    Attributes:
        session_id: Unique session identifier.
        source: Message source (cli|telegram|discord|slack|...).
        model: Model used in this session.
        started_at: Unix timestamp when session started.
        ended_at: Unix timestamp when session ended (None if still active).
        tool_call_count: Number of tool invocations.
        message_count: Number of messages in the session.
        estimated_cost_usd: Estimated cost in USD (None if unknown).

    PII fields intentionally omitted: user_id, system_prompt.
    """

    session_id: str
    source: str
    model: str
    started_at: float
    ended_at: Optional[float]
    tool_call_count: int
    message_count: int
    estimated_cost_usd: Optional[float]


@dataclass
class FailureReport:
    """A classified tool failure.

    Attributes:
        tool_name: Name of the tool that failed.
        error_category: One of the 8 error categories.
        error_snippet: PII-redacted excerpt, max 200 chars.
        session_id: Session this failure belongs to.
        timestamp: Unix timestamp of the failure.
        confidence: Classification confidence 0.0-1.0.
    """

    tool_name: str
    error_category: str  # path_not_found|timeout|permission_denied|command_not_found|rate_limit|syntax_error|network|generic
    error_snippet: str
    session_id: str
    timestamp: float
    confidence: float

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        if len(self.error_snippet) > 200:
            self.error_snippet = self.error_snippet[:200]


@dataclass
class CorrectionSignal:
    """A detected user correction in a conversation.

    Attributes:
        pattern: Which correction pattern was matched.
        confidence: Detection confidence 0.0-1.0.
        timestamp: Unix timestamp of the user message.
        snippet: PII-redacted excerpt of the correction.
    """

    pattern: str
    confidence: float
    timestamp: float
    snippet: str


@dataclass
class SkillGap:
    """A detected missing capability.

    Attributes:
        capability: Normalized capability name (e.g. "csv-parsing").
        request_count: How many times user asked for this capability.
        session_ids: Which sessions contained these requests.
        confidence: Detection confidence based on pattern matching.
        existing_skill: Name of an existing skill that covers this
            capability but may be insufficient.
    """

    capability: str
    request_count: int
    session_ids: List[str]
    confidence: float
    existing_skill: Optional[str] = None

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")


@dataclass
class ToolMetric:
    """Aggregated metrics for a single tool.

    Attributes:
        tool_name: Name of the tool.
        total_calls: Total invocation count.
        successful_calls: Successful invocations (no error).
        failed_calls: Failed invocations.
        success_rate: successful_calls / total_calls as float 0.0-1.0.
        top_error_category: Most common error category for this tool.
        top_error_snippet: Example error text from the top category.
    """

    tool_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    success_rate: float = 0.0
    top_error_category: str = "none"
    top_error_snippet: str = ""


@dataclass
class RetryPattern:
    """A detected retry loop on a single tool.

    Attributes:
        tool_name: Tool being retried.
        consecutive_count: Number of consecutive retries.
        session_id: Session this pattern appeared in.
        time_window_seconds: How wide the retry window was.
    """

    tool_name: str
    consecutive_count: int
    session_id: str
    time_window_seconds: float


@dataclass
class SessionAnalysis:
    """Complete analysis result. The single interface contract between dojo and borg.

    Schema version MUST be incremented on any field change.
    Consumers MUST check schema_version before accessing fields.

    Attributes:
        schema_version: Must be 1. Increment on any change.
        analyzed_at: Unix timestamp when analysis ran.
        days_covered: Number of days the analysis covers.
        sessions_analyzed: Number of sessions processed.
        total_tool_calls: Total tool invocations seen.
        total_errors: Total errors detected.
        overall_success_rate: Success rate as percentage 0.0-100.0.
        user_corrections: Number of user correction signals detected.
        tool_metrics: Per-tool aggregated metrics.
        failure_reports: All classified failures.
        skill_gaps: Detected missing capabilities.
        retry_patterns: Detected retry loops.
        weakest_tools: Top tools sorted by error count desc.
    """

    schema_version: int = 1
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
    weakest_tools: List[ToolMetric] = field(default_factory=list)

    # Supported schema version — update when schema changes
    SUPPORTED_SCHEMA_VERSION: int = 1
