"""Guild — Semantic reasoning cache for AI agents."""

__version__ = "2.0.5"

# Core modules (M1 complete)
from guild.core.safety import scan_pack_safety, scan_privacy
from guild.core.schema import parse_workflow_pack, validate_pack, collect_text_fields
from guild.core.uri import resolve_guild_uri, fetch_with_retry, get_available_pack_names
from guild.core.proof_gates import validate_proof_gates, compute_pack_tier, check_confidence_decay
from guild.core.privacy import privacy_scan_text, privacy_scan_artifact, privacy_redact
from guild.core.session import save_session, load_session, log_event, compute_log_hash
from guild.core.publish import action_publish, check_rate_limit
from guild.core.apply import apply_handler, action_start, action_checkpoint, action_complete
from guild.core.search import (
    guild_search,
    guild_pull,
    guild_try,
    guild_init,
    generate_feedback,
    check_for_suggestion,
)
from guild.core.convert import (
    convert_auto,
    convert_skill,
    convert_claude_md,
    convert_cursorrules,
)


def check(context: str, constraints: dict = None, top_k: int = 3) -> list:
    """Check the cache for relevant approaches. Returns empty list until M3."""
    return []
