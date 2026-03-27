"""Borg — Semantic reasoning cache for AI agents."""

__version__ = "2.3.0"

# Core modules (M1 complete)
from borg.core.safety import scan_pack_safety, scan_privacy
from borg.core.schema import parse_workflow_pack, validate_pack, collect_text_fields
from borg.core.uri import resolve_guild_uri, fetch_with_retry, get_available_pack_names
from borg.core.proof_gates import validate_proof_gates, compute_pack_tier, check_confidence_decay
from borg.core.privacy import privacy_scan_text, privacy_scan_artifact, privacy_redact
from borg.core.session import save_session, load_session, log_event, compute_log_hash
from borg.core.publish import action_publish, check_rate_limit
from borg.core.apply import apply_handler, action_start, action_checkpoint, action_complete
from borg.core.search import (
    borg_search,
    borg_pull,
    borg_try,
    borg_init,
    generate_feedback,
    check_for_suggestion,
)
from borg.core.convert import (
    convert_auto,
    convert_skill,
    convert_claude_md,
    convert_cursorrules,
)


def check(context: str, constraints: dict = None, top_k: int = 3) -> list:
    """Check the cache for relevant approaches. Returns empty list until M3."""
    return []
