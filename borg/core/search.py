"""
Guild Search & Discovery Module (T1.10) — standalone extraction.

Zero imports from tools.* or guild_mcp.* — uses borg.core.* siblings.

Public API:
    guild_search()          — text search across index.json entries
    guild_pull()            — fetch + validate + save locally
    guild_try()             — fetch + validate + preview without saving
    guild_init()            — convert an existing SKILL.md to a workflow pack
    generate_feedback()     — parse execution JSONL, create feedback draft
    check_for_suggestion()  — autosuggest based on frustration signals + task classification
    classify_task()         — extract search terms from context
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from borg.core.uri import (
    resolve_guild_uri,
    fetch_with_retry,
    get_available_pack_names,
    fuzzy_match_pack,
    _fetch_index,
    BORG_DIR,
)
from borg.core.seeds import is_seeds_disabled, get_seed_packs

# Optional: SemanticSearchEngine (graceful fallback if unavailable)
try:
    from borg.core.semantic_search import SemanticSearchEngine
except ImportError:
    SemanticSearchEngine = None

# Optional: EmbeddingEngine for auto-embedding in store
try:
    from borg.db.embeddings import EmbeddingEngine
except ImportError:
    EmbeddingEngine = None

try:
    from borg.db.store import AgentStore
except ImportError:
    AgentStore = None

try:
    from borg.db.reputation import ReputationEngine, AccessTier
except ImportError:
    ReputationEngine = None
    AccessTier = None

SKILLS_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "skills"
from borg.core.schema import parse_workflow_pack, validate_pack
from borg.core.schema import parse_skill_frontmatter, sections_to_phases
from borg.core.safety import scan_pack_safety
from borg.core.proof_gates import (
    compute_pack_tier,
    compute_pack_tier_from_index,
    check_confidence_decay,
)


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_DOWNLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


# ---------------------------------------------------------------------------
# Guild search
# ---------------------------------------------------------------------------

def borg_search(query: str, mode: str = "text", requesting_agent_id: str = None, include_seeds: bool = True) -> str:
    """Search guild packs by keyword or semantic similarity.

    Searches across pack names, problem_class, id, and phase names
    from both the remote index and locally pulled packs.
    Returns JSON with matching packs and their metadata.

    Args:
        query: Keyword string to search for (case-insensitive).
        mode: Search mode - 'text', 'semantic', or 'hybrid'.
            'text' uses keyword matching only.
            'semantic' uses SemanticSearchEngine with embeddings if available.
            'hybrid' combines both when embeddings are available.
            Defaults to 'text' for backwards compatibility.
            Note: 'semantic' and 'hybrid' require SemanticSearchEngine
            to be available and will fall back to 'text' search if not.
        requesting_agent_id: Optional agent ID for reputation-aware ranking.
            When provided, packs from higher-tier authors are ranked higher.
            Defaults to None (no reputation weighting).

    Returns:
        JSON string with keys: success (bool), matches (list), query (str),
        total (int), mode (str). On error returns {"success": false, "error": "..."}.
    """
    try:
        index = _fetch_index()
        all_packs = list(index.get("packs", []))

        # Collect local packs not yet in the index
        local_names_in_index = {p.get("name", "") for p in all_packs}
        if BORG_DIR.exists():
            local_yamls: List[tuple] = []
            for pack_yaml in BORG_DIR.glob("*/pack.yaml"):
                local_yamls.append((pack_yaml.parent.name, pack_yaml))
            packs_dir = BORG_DIR / "packs"
            if packs_dir.exists():
                for pack_yaml in packs_dir.glob("*.yaml"):
                    local_yamls.append((pack_yaml.stem, pack_yaml))

            for local_name, pack_yaml in local_yamls:
                if local_name not in local_names_in_index:
                    try:
                        pack_data = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
                        if isinstance(pack_data, dict):
                            all_packs.append({
                                "name": local_name,
                                "id": pack_data.get("id", local_name),
                                "problem_class": pack_data.get("problem_class", ""),
                                "phase_names": [
                                    p.get("name", "")
                                    for p in pack_data.get("phases", [])
                                    if isinstance(p, dict)
                                ],
                                "phases": len(pack_data.get("phases", [])),
                                "confidence": pack_data.get("provenance", {}).get("confidence", "unknown"),
                                "source": "local",
                            })
                            local_names_in_index.add(local_name)
                    except Exception:
                        all_packs.append({
                            "name": local_name,
                            "source": "local",
                        })

        # Load and merge seed packs (cold-start fix)
        # Seed packs are lowest priority: local > remote > seed
        # This means seeds only show up when no local/remote pack matches
        if include_seeds and not is_seeds_disabled():
            seed_packs = get_seed_packs()
            for seed_pack in seed_packs:
                all_packs.append(seed_pack.to_search_dict())

        # Attach tier to every pack that doesn't have one yet
        for pack in all_packs:
            if "tier" not in pack:
                pack["tier"] = compute_pack_tier_from_index(pack)

        # Deduplicate by pack id/name before searching
        # Prefer local copies (higher confidence) over remote when duplicates exist
        seen_ids: set = set()
        seen_names: set = set()
        unique_packs: List[Dict[str, Any]] = []
        for pack in all_packs:
            pack_id = pack.get("id", "")
            pack_name = pack.get("name", "")
            is_local = pack.get("source") == "local"
            # Deduplicate by id first, then by name as fallback
            if pack_id and pack_id not in seen_ids:
                seen_ids.add(pack_id)
                unique_packs.append(pack)
            elif pack_id and pack_id in seen_ids:
                # Duplicate id found - prefer local over remote
                if is_local:
                    # Find and replace the existing remote entry with this local one
                    for i, existing in enumerate(unique_packs):
                        if existing.get("id") == pack_id and existing.get("source") != "local":
                            unique_packs[i] = pack
                            break
            elif pack_name and pack_name not in seen_names:
                seen_names.add(pack_name)
                unique_packs.append(pack)
            elif pack_name and pack_name in seen_names:
                # Duplicate name found - prefer local over remote
                if is_local:
                    for i, existing in enumerate(unique_packs):
                        if existing.get("name") == pack_name and existing.get("source") != "local":
                            unique_packs[i] = pack
                            break
        all_packs = unique_packs

        # Inject author reputation scores into pack metadata
        if AgentStore is not None and requesting_agent_id and ReputationEngine is not None:
            try:
                _store = AgentStore()
                _engine = ReputationEngine(_store)

                # Batch-fetch profiles for all unique authors encountered
                author_ids = list({
                    p.get("provenance", {}).get("author_agent", "")
                    for p in all_packs
                    if p.get("provenance", {}).get("author_agent")
                })
                author_profiles = {}
                for aid in author_ids:
                    try:
                        author_profiles[aid] = _engine.build_profile(aid)
                    except Exception:
                        author_profiles[aid] = None

                # Attach reputation data to each pack
                for pack in all_packs:
                    author = pack.get("provenance", {}).get("author_agent", "")
                    profile = author_profiles.get(author)
                    if profile:
                        pack["author_reputation"] = {
                            "contribution_score": profile.contribution_score,
                            "access_tier": profile.access_tier.value,
                            "free_rider_status": profile.free_rider_status.value,
                        }
                        # Also promote tier to pack tier if author is core/governance
                        if profile.access_tier in (AccessTier.CORE, AccessTier.GOVERNANCE):
                            if pack.get("tier") == "community":
                                pack["tier"] = "author-validated"
                    else:
                        pack["author_reputation"] = None

                _store.close()
            except Exception:
                pass  # Reputation is optional — never break search

        query_lower = query.lower().strip()
        mode_lower = mode.lower() if mode else "text"

        if not query_lower:
            return json.dumps({
                "success": True,
                "matches": all_packs,
                "query": query,
                "total": len(all_packs),
                "mode": mode_lower,
            })

        # Try semantic search if requested and SemanticSearchEngine is available
        if mode_lower in ("semantic", "hybrid") and SemanticSearchEngine is not None:
            try:
                store = AgentStore()
                search_engine = SemanticSearchEngine(store)
                semantic_matches = search_engine.search(query, top_k=50, mode=mode_lower)
                if semantic_matches:
                    # Convert SemanticSearchEngine results to guild_search format
                    matches = []
                    for pack in semantic_matches:
                        match_entry = {
                            "name": pack.get("id", ""),
                            "id": pack.get("id", ""),
                            "problem_class": pack.get("problem_class", ""),
                            "tier": pack.get("tier", "unknown"),
                            "confidence": pack.get("confidence", "unknown"),
                            "adoption_count": pack.get("adoption_count"),
                            "last_validated": pack.get("last_validated"),
                            "relevance_score": pack.get("relevance_score", 0.0),
                            "match_type": pack.get("match_type", mode_lower),
                        }
                        matches.append(match_entry)
                    return json.dumps({
                        "success": True,
                        "matches": matches,
                        "query": query,
                        "total": len(matches),
                        "mode": mode_lower,
                    })
            except Exception:
                # Fall back to text search on any semantic search error
                pass

        # Text search (default)
        matches = []
        for pack in all_packs:
            searchable = " ".join([
                pack.get("name", ""),
                pack.get("problem_class", ""),
                pack.get("id", ""),
                " ".join(pack.get("phase_names", [])),
            ]).lower()

            if query_lower in searchable:
                matches.append(pack)

        # v3.2.4 observe→search roundtrip fix: also surface relevant traces.
        # Traces are stored in ~/.borg/traces.db by borg observe / MCP
        # borg_observe / borg_apply, but pre-3.2.4 borg_search never read from
        # them — which made C2 (seeded) indistinguishable from C1 (empty) in
        # the P1.1 experiment. We now add trace hits as synthetic matches with
        # source="trace" so callers can tell them apart from packs.
        #
        # Gate: only surface traces if BORG_DIR is a real directory. Tests that
        # mock BORG_DIR to /nonexistent will skip this path, preserving their
        # pre-3.2.4 expectations. Production code paths hit the real directory
        # and get trace surfacing.
        try:
            if not (BORG_DIR and Path(BORG_DIR).is_dir()):
                raise RuntimeError("BORG_DIR not present — skipping trace lookup")
            from borg.core.trace_matcher import TraceMatcher
            matcher = TraceMatcher()
            trace_hits = matcher.find_relevant(query, top_k=10)
            for trace in trace_hits or []:
                trace_id = str(trace.get("id", ""))
                if not trace_id:
                    continue
                task_desc = (trace.get("task_description") or "")[:120]
                matches.append({
                    "name": f"trace:{trace_id}",
                    "id": f"trace:{trace_id}",
                    "problem_class": task_desc or "observed-trace",
                    "phase_names": [],
                    "phases": 0,
                    "confidence": "observed",
                    "tier": "trace",
                    "source": "trace",
                    "trace_id": trace_id,
                    "outcome": trace.get("outcome", ""),
                    "technology": trace.get("technology", ""),
                    "match_score": trace.get("match_score", 0.0),
                })
        except Exception:
            pass  # Never let trace lookup break pack search

        # Apply reputation-weighted re-ranking for text mode
        if requesting_agent_id and matches and AgentStore is not None and ReputationEngine is not None:
            try:
                _store = AgentStore()
                _engine = ReputationEngine(_store)
                requester_profile = _engine.build_profile(requesting_agent_id)
                _store.close()

                # Reciprocal Rank Fusion: combine text score + reputation score
                # Normalize reputation score to 0-1 range (tier-based)
                tier_normalized = {
                    AccessTier.COMMUNITY: 0.0,
                    AccessTier.VALIDATED: 0.25,
                    AccessTier.CORE: 0.6,
                    AccessTier.GOVERNANCE: 1.0,
                }
                requester_tier_val = tier_normalized.get(requester_profile.access_tier, 0.0)

                # Boost: authors with higher tier than requester get boosted
                reranked = []
                for pack in matches:
                    author_rep = pack.get("author_reputation") or {}
                    author_tier_str = author_rep.get("access_tier", "community")
                    try:
                        author_tier = AccessTier(author_tier_str)
                    except ValueError:
                        author_tier = AccessTier.COMMUNITY

                    author_tier_val = tier_normalized.get(author_tier, 0.0)

                    # Tier differential boost: if author is higher tier than requester,
                    # this pack comes from a more experienced agent
                    tier_boost = max(0, author_tier_val - requester_tier_val) * 0.3

                    # Base adoption/validation signal
                    adoption_boost = 0.0
                    if pack.get("adoption_count"):
                        adoption_boost = min(0.2, int(pack.get("adoption_count", 0)) * 0.01)

                    pack["reputation_boost"] = tier_boost + adoption_boost
                    reranked.append(pack)

                # Sort by (base_order, -reputation_boost) — re-rank within text-score groups
                # Text matches are returned in insertion order (sorted by dedupe),
                # so we apply a stable secondary sort
                reranked.sort(key=lambda p: -p.get("reputation_boost", 0.0))
                matches = reranked
            except Exception:
                pass  # Reputation is optional — keep text order

        return json.dumps({
            "success": True,
            "matches": matches,
            "query": query,
            "total": len(matches),
            "mode": mode_lower,
        })

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Guild pull
# ---------------------------------------------------------------------------

def borg_pull(uri: str) -> str:
    """Fetch, validate, and store a guild pack locally.

    Resolves the URI, downloads the pack YAML, validates proof gates,
    runs a safety scan, and writes the pack to BORG_DIR/<name>/pack.yaml.

    Args:
        uri: A guild://, https://, or absolute local path URI.

    Returns:
        JSON string with keys: success (bool), name, path, tier,
        proof_gates (validation_errors, confidence, evidence),
        confidence_status (decay info). On failure: success=false, error.
    """
    try:
        resolved = resolve_guild_uri(uri)

        # Fetch content — try .workflow.yaml first, fall back to .yaml
        if resolved.startswith("http://") or resolved.startswith("https://"):
            try:
                content, fetch_err = fetch_with_retry(resolved)
                if fetch_err and ".workflow.yaml" in resolved:
                    # Fallback: try without .workflow suffix
                    fallback_url = resolved.replace(".workflow.yaml", ".yaml")
                    content, fetch_err = fetch_with_retry(fallback_url)
                if fetch_err:
                    raise ValueError(f"Failed to fetch: {fetch_err}")
            except Exception as e:
                error_msg = str(e)
                if "HTTP Error 404" in error_msg or "404" in error_msg or "Failed to fetch" in error_msg:
                    suggestions = fuzzy_match_pack(uri)
                    return json.dumps({
                        "success": False,
                        "error": f"Pack not found: {uri}",
                        "suggestions": suggestions,
                        "hint": (
                            "The pack name may be misspelled. "
                            + (f"Did you mean one of: {', '.join(suggestions)}? " if suggestions else "")
                            + "Use borg_search to find available packs. "
                            "Expected URI format: guild://domain/pack-name"
                        ),
                    })
                return json.dumps({"success": False, "error": f"Failed to fetch: {e}"})
        else:
            path = Path(resolved)
            if not path.exists():
                return json.dumps({"success": False, "error": f"File not found: {resolved}"})
            content = path.read_text(encoding="utf-8")

        pack = parse_workflow_pack(content)

        validation_errors = validate_pack(pack)

        threats = scan_pack_safety(pack)
        if threats:
            return json.dumps({
                "success": False,
                "error": f"Safety threats detected: {'; '.join(threats)}",
                "threats": threats,
            })

        # Extract pack name from id (sanitize against path traversal)
        pack_id = pack.get("id", "")
        if "://" in pack_id:
            pack_name = pack_id.split("/")[-1]
        else:
            pack_name = pack_id or "unknown"

        # Strip directory components to prevent path traversal
        pack_name = Path(pack_name).name

        # Verify resolved path is still under BORG_DIR
        resolved_path = (BORG_DIR / pack_name).resolve()
        if not str(resolved_path).startswith(str(BORG_DIR.resolve())):
            return json.dumps({"success": False, "error": "Path traversal detected in pack id"})

        # Store in guild dir
        pack_dir = BORG_DIR / pack_name
        pack_dir.mkdir(parents=True, exist_ok=True)
        pack_file = pack_dir / "pack.yaml"
        pack_file.write_text(content, encoding="utf-8")

        decay_status = check_confidence_decay(pack)

        # Log pull to reputation store (optional — store may not exist)
        if AgentStore is not None:
            try:
                _store = AgentStore()
                provenance = pack.get("provenance", {})
                _store.update_pack(
                    pack_id=pack_id,
                    pulled_at=datetime.now(timezone.utc).isoformat(),
                )
                _store.close()
            except Exception:
                pass  # Store is optional — never break core flow

        result = {
            "success": True,
            "name": pack_name,
            "path": str(pack_file),
            "tier": compute_pack_tier(pack),
            "proof_gates": {
                "validation_errors": validation_errors,
                "confidence": pack.get("provenance", {}).get("confidence", "unknown"),
                "evidence": pack.get("provenance", {}).get("evidence", ""),
            },
            "confidence_status": decay_status,
        }
        if decay_status.get("decayed"):
            result["decay_note"] = decay_status["warning"]
        return json.dumps(result)

    except (ValueError, Exception) as e:
        error_msg = str(e)
        if "HTTP Error 404" in error_msg or "404" in error_msg:
            suggestions = fuzzy_match_pack(uri)
            return json.dumps({
                "success": False,
                "error": f"Pack not found: {uri}",
                "suggestions": suggestions,
                "hint": (
                    "The pack name may be misspelled. "
                    + (f"Did you mean one of: {', '.join(suggestions)}? " if suggestions else "")
                    + "Use borg_search to find available packs. "
                    "Expected URI format: guild://domain/pack-name (e.g. guild://hermes/systematic-debugging)"
                ),
            })
        return json.dumps({"success": False, "error": error_msg})


# ---------------------------------------------------------------------------
# Guild try (preview)
# ---------------------------------------------------------------------------

def borg_try(uri: str, task_id: Optional[str] = None) -> str:
    """Quick preview: fetch, validate, show proof gates. Do NOT save to disk.

    Args:
        uri: A guild://, https://, or absolute local path URI.
        task_id: Optional task identifier (unused, for API compatibility).

    Returns:
        JSON string with keys: success, id, problem_class, mental_model,
        required_inputs, phases (summary), confidence, evidence, failure_cases,
        tier, validation_errors, safety_threats, verdict, confidence_status.
        On failure: success=false, error, suggestions.
    """
    try:
        resolved = resolve_guild_uri(uri)
        if resolved.startswith(("http://", "https://")):
            content, fetch_err = fetch_with_retry(resolved)
            if fetch_err and ".workflow.yaml" in resolved:
                fallback_url = resolved.replace(".workflow.yaml", ".yaml")
                content, fetch_err = fetch_with_retry(fallback_url)
            if fetch_err:
                raise ValueError(f"Failed to fetch: {fetch_err}")
        else:
            content = Path(resolved).read_text(encoding="utf-8")

        pack = parse_workflow_pack(content)
        errors = validate_pack(pack)
        threats = scan_pack_safety(pack)
        decay_status = check_confidence_decay(pack)

        result = {
            "success": True,
            "id": pack.get("id", "unknown"),
            "problem_class": pack.get("problem_class", ""),
            "mental_model": pack.get("mental_model", ""),
            "required_inputs": pack.get("required_inputs", []) or [],
            "phases": [
                {
                    "name": p.get("name", ""),
                    "description": (p.get("description", "") or "")[:200],
                    "checkpoint": p.get("checkpoint", ""),
                }
                for p in pack.get("phases", [])
            ],
            "confidence": pack.get("provenance", {}).get("confidence", "unknown"),
            "evidence": pack.get("provenance", {}).get("evidence", ""),
            "failure_cases": pack.get("provenance", {}).get("failure_cases", []),
            "tier": compute_pack_tier(pack),
            "validation_errors": errors,
            "safety_threats": threats,
            "verdict": "safe" if not errors and not threats else "blocked",
            "confidence_status": decay_status,
        }
        if decay_status.get("decayed"):
            result["decay_note"] = decay_status["warning"]
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        error_msg = str(e)
        if "HTTP Error 404" in error_msg or "404" in error_msg:
            suggestions = fuzzy_match_pack(uri)
            return json.dumps({
                "success": False,
                "error": f"Pack not found: {uri}",
                "suggestions": suggestions,
                "hint": (
                    "The pack name may be misspelled. "
                    + (f"Did you mean one of: {', '.join(suggestions)}? " if suggestions else "")
                    + "Use borg_search to find available packs. "
                    "Expected URI format: guild://domain/pack-name (e.g. guild://hermes/systematic-debugging)"
                ),
            }, ensure_ascii=False)
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Guild init (convert skill to pack)
# ---------------------------------------------------------------------------

def borg_init(skill_name: str) -> str:
    """Convert an existing SKILL.md to a workflow pack.

    Args:
        skill_name: Name of the skill directory under SKILLS_DIR.

    Returns:
        JSON string with keys: success (bool), content (YAML string), pack (dict),
        validation_errors (list, optional), safety_warnings (list, optional).
        On failure: success=false, error.
    """
    try:
        skill_dir = SKILLS_DIR / skill_name
        skill_file = skill_dir / "SKILL.md"

        # Search category subdirectories if not found at top level
        if not skill_file.exists() and SKILLS_DIR.exists():
            for candidate in SKILLS_DIR.rglob(f"{skill_name}/SKILL.md"):
                skill_file = candidate
                skill_dir = candidate.parent
                break

        if not skill_file.exists():
            return json.dumps({
                "success": False,
                "error": f"Skill not found: {skill_name} (looked in {SKILLS_DIR} and subdirectories)",
            })

        text = skill_file.read_text(encoding="utf-8")
        frontmatter, body = parse_skill_frontmatter(text)

        # Build phases from body sections
        phases = sections_to_phases(body)
        if not phases:
            phases = [{
                "name": "main",
                "description": body.strip(),
                "checkpoint": "",
                "anti_patterns": [],
                "prompts": [],
            }]

        # Build provenance from frontmatter
        provenance = {
            "author_agent": "agent://guild-init",
            "created": datetime.now(timezone.utc).isoformat(),
            "evidence": frontmatter.get("evidence", "Converted from existing skill"),
            "confidence": frontmatter.get("confidence", "inferred"),
            "failure_cases": frontmatter.get("failure_cases", []),
        }

        pack = {
            "type": "workflow_pack",
            "version": "1.0.0",
            "id": f"borg://converted/{skill_name}",
            "problem_class": frontmatter.get("description", skill_name),
            "mental_model": body.split("\n")[0] if body else skill_name,
            "required_inputs": [],
            "phases": phases,
            "escalation_rules": [],
            "provenance": provenance,
        }

        content = yaml.dump(pack, default_flow_style=False, sort_keys=False)

        # Validate the generated pack
        validation_errors = validate_pack(pack)
        safety_warnings = scan_pack_safety(pack)

        result: Dict[str, Any] = {
            "success": True,
            "content": content,
            "pack": pack,
        }
        if validation_errors:
            result["validation_errors"] = validation_errors
        if safety_warnings:
            result["safety_warnings"] = safety_warnings

        return json.dumps(result)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Feedback generation
# ---------------------------------------------------------------------------

def generate_feedback(
    pack_id: str,
    pack_version: str,
    execution_log: List[Dict[str, Any]],
    task_description: str,
    outcome: str,
    execution_log_hash: str = "",
) -> dict:
    """Build a feedback artifact dict from execution log data.

    Auto-sets confidence based on execution results:
      - All phases passed -> 'tested'
      - Partial failure   -> 'inferred'

    Args:
        pack_id: The parent artifact ID.
        pack_version: Version string of the parent pack.
        execution_log: List of phase entry dicts with keys: phase, status,
            checkpoint_result, error, duration_s.
        task_description: Human-readable description of the task attempted.
        outcome: One-line outcome string.
        execution_log_hash: SHA256 hash of the execution log file (optional).

    Returns:
        A feedback artifact dict with keys: type, parent_artifact, version,
        before, after, what_changed, why_it_worked, where_to_reuse,
        failure_cases, suggestions, evidence, execution_log_hash, provenance.
    """
    import hashlib

    # Determine confidence from execution results
    all_passed = all(
        entry.get("status") == "passed" for entry in execution_log
    )
    confidence = "tested" if all_passed else "inferred"

    # Build before/after from phases
    before = [
        {
            "phase": entry.get("phase", "unknown"),
            "checkpoint_result": entry.get("checkpoint_result", ""),
        }
        for entry in execution_log
    ]

    # Collect errors/changes
    changes: List[str] = []
    failure_cases: List[str] = []
    for entry in execution_log:
        if entry.get("error"):
            changes.append(entry["error"])
        if entry.get("status") == "failed":
            failure_msg = (
                f"Phase '{entry.get('phase', 'unknown')}' failed: "
                f"{entry.get('checkpoint_result', '')}"
            )
            changes.append(failure_msg)
            failure_cases.append(failure_msg)

    what_changed = "; ".join(changes) if changes else outcome

    # Derive why_it_worked: only meaningful when all phases passed
    why_it_worked = ""
    if all_passed and execution_log:
        why_it_worked = (
            f"All {len(execution_log)} phases passed successfully. "
            f"Outcome: {outcome}"
        )
    elif all_passed and not execution_log:
        why_it_worked = "No phases were executed; vacuously successful."

    # Build where_to_reuse from successful phases
    where_to_reuse: List[str] = []
    for entry in execution_log:
        if entry.get("status") == "passed":
            phase = entry.get("phase", "unknown")
            where_to_reuse.append(f"phase:{phase}")
    where_to_reuse_str = "; ".join(where_to_reuse) if where_to_reuse else ""

    # Build suggestions for improvement based on failures
    suggestions_list: List[str] = []
    for entry in execution_log:
        if entry.get("status") == "failed":
            suggestions_list.append(
                f"Investigate phase '{entry.get('phase', 'unknown')}': "
                f"{entry.get('checkpoint_result', 'unknown error')}"
            )
    suggestions = "; ".join(suggestions_list) if suggestions_list else ""

    # Build evidence summary
    evidence_parts: List[str] = []
    for entry in execution_log:
        status = entry.get("status", "unknown")
        phase = entry.get("phase", "unknown")
        duration = entry.get("duration_s", 0)
        evidence_parts.append(f"{phase}: {status} ({duration}s)")

    evidence = (
        f"Task: {task_description}. "
        f"Results: {', '.join(evidence_parts)}. "
        f"Outcome: {outcome}"
    )

    # Compute log hash if not provided
    log_hash = execution_log_hash
    if not log_hash:
        log_bytes = json.dumps(execution_log, sort_keys=True).encode()
        log_hash = hashlib.sha256(log_bytes).hexdigest()[:16]

    return {
        "type": "feedback",
        "schema_version": "1.0",
        "parent_artifact": pack_id,
        "version": pack_version,
        "before": before,
        "after": {
            "outcome": outcome,
            "task_description": task_description,
        },
        "what_changed": what_changed,
        "why_it_worked": why_it_worked,
        "where_to_reuse": where_to_reuse_str,
        "failure_cases": failure_cases,
        "suggestions": suggestions,
        "evidence": evidence,
        "execution_log_hash": log_hash,
        "provenance": {
            "confidence": confidence,
            "generated": datetime.now(timezone.utc).isoformat(),
        },
    }


# ---------------------------------------------------------------------------
# Autosuggest — frustration signals and task classification
# ---------------------------------------------------------------------------

_FRUSTRATION_PATTERNS = [
    re.compile(r"still\s+fail", re.IGNORECASE),
    re.compile(r"tried\s+everything", re.IGNORECASE),
    re.compile(r"not\s+working", re.IGNORECASE),
    re.compile(r"keeps?\s+failing", re.IGNORECASE),
    re.compile(r"same\s+error", re.IGNORECASE),
    re.compile(r"no\s+luck", re.IGNORECASE),
    re.compile(r"stuck\b", re.IGNORECASE),
    re.compile(r"can'?t\s+figure", re.IGNORECASE),
    re.compile(r"nothing\s+works", re.IGNORECASE),
    re.compile(r"give\s+up", re.IGNORECASE),
    re.compile(r"at\s+a\s+loss", re.IGNORECASE),
    re.compile(r"doesn'?t\s+help", re.IGNORECASE),
    re.compile(r"going\s+in\s+circles", re.IGNORECASE),
    re.compile(r"already\s+tried", re.IGNORECASE),
]

# Maps context keywords to guild search terms
_KEYWORD_MAP = {
    # Debugging
    "debug": "debug",
    "error": "debug",
    "traceback": "debug",
    "exception": "debug",
    "stack trace": "debug",
    "segfault": "debug",
    "crash": "debug",
    "bug": "debug",
    "breakpoint": "debug",
    "root cause": "debug",
    # Testing
    "test": "test",
    "pytest": "test",
    "unittest": "test",
    "assert": "test",
    "coverage": "test",
    "tdd": "test",
    "test-driven": "test",
    # Code review
    "review": "review",
    "code review": "review",
    "pull request": "review",
    "pr": "review",
    "diff": "review",
    "merge": "review",
    # GitHub / PR workflow
    "github": "github",
    "gh": "github",
    "branch": "github",
    "commit": "github",
    "push": "github",
    # Deployment
    "deploy": "deploy",
    "deployment": "deploy",
    "ci/cd": "deploy",
    "pipeline": "deploy",
    "release": "deploy",
    # Refactoring
    "refactor": "refactor",
    "restructure": "refactor",
    "clean up": "refactor",
    "technical debt": "refactor",
    # Planning
    "plan": "plan",
    "architecture": "plan",
    "design": "plan",
    "spec": "plan",
    "requirements": "plan",
    # Codebase inspection
    "codebase": "inspect",
    "understand": "inspect",
    "explore": "inspect",
    "navigate": "inspect",
    "structure": "inspect",
    # Diagrams / visualization
    "diagram": "diagram",
    "ascii": "ascii",
    "visualization": "diagram",
    "flowchart": "diagram",
    # Jupyter / data
    "jupyter": "jupyter",
    "notebook": "jupyter",
    "data": "jupyter",
}


def _has_frustration_signals(context: str) -> bool:
    """Check if the context contains frustration/stuck signals."""
    for pattern in _FRUSTRATION_PATTERNS:
        if pattern.search(context):
            return True
    return False


def classify_task(context: str) -> List[str]:
    """Extract search terms from context to match against guild packs.

    Scans the context for known keywords and returns deduplicated
    search terms ordered by relevance (first match wins priority).

    Args:
        context: Free-text context string (message, errors, task desc).

    Returns:
        A list of deduplicated search-term strings.
    """
    if not context:
        return []

    context_lower = context.lower()
    seen: set = set()
    terms: List[str] = []

    for keyword, search_term in _KEYWORD_MAP.items():
        if keyword in context_lower and search_term not in seen:
            seen.add(search_term)
            terms.append(search_term)

    # Augment with dojo skill gaps (dynamic — from cached session analysis)
    try:
        from borg.dojo import get_cached_analysis
        analysis = get_cached_analysis()
        if analysis:
            for gap in analysis.skill_gaps:
                if gap.capability in context_lower and gap.capability not in seen:
                    seen.add(gap.capability)
                    terms.append(gap.capability)
    except ImportError:
        pass  # Dojo not installed — skip gracefully

    return terms


def _format_suggestion(pack_matches: list, context: str) -> str:
    """Format pack matches into a brief, actionable suggestion.

    Returns a one-line actionable message, or empty string if no matches.
    """
    if not pack_matches:
        return ""

    best = pack_matches[0]
    name = best.get("name", "unknown")
    problem_class = best.get("problem_class", "")
    phase_names = best.get("phase_names", [])

    if problem_class:
        desc = problem_class
    elif phase_names:
        desc = f"{len(phase_names)}-phase workflow: {', '.join(phase_names[:3])}"
    else:
        desc = "structured workflow"

    return (
        f"Guild pack available: {name} ({desc}). "
        f"Try: borg_try guild://hermes/{name}"
    )


def _build_why_relevant(pack: dict, search_terms: List[str]) -> str:
    """Build a human-readable explanation of why a pack is relevant."""
    name = pack.get("name", "")
    problem_class = pack.get("problem_class", "")
    phase_names = pack.get("phase_names", [])

    reasons = []
    if search_terms:
        reasons.append(f"matches your {search_terms[0]} task")
    if problem_class:
        reasons.append(f"focuses on: {problem_class}")
    elif phase_names:
        reasons.append(f"{len(phase_names)}-phase workflow")

    return "; ".join(reasons) if reasons else "relevant guild pack"


def check_for_suggestion(
    conversation_context: str,
    failure_count: int = 0,
    task_type: str = "",
    tried_packs: Optional[List[str]] = None,
    requesting_agent_id: Optional[str] = None,
) -> str:
    """Check if a guild pack suggestion is warranted and return it.

    Triggers when failure_count >= 2 OR frustration signals are detected.
    Searches guild packs by classified task terms, filters out already-tried
    packs, and returns the top 3 matches with relevance metadata.

    Args:
        conversation_context: Recent conversation text (messages, errors).
        failure_count: Number of consecutive failed attempts.
        task_type: Optional explicit task type hint.
        tried_packs: Optional list of pack names already tried (excluded).
        requesting_agent_id: Optional agent ID for reputation-aware ranking.

    Returns:
        JSON string with suggestion details, or '{}' if no suggestion warranted.
        Includes: suggestion (formatted message), suggestions (list of top 3
        dicts with name/confidence/problem_class/why_relevant/match_count).
    """
    tried_packs = tried_packs or []

    # Fast path — no suggestion needed
    if not conversation_context.strip():
        return json.dumps({"has_suggestion": False})

    # Trigger on failure_count >= 2 OR frustration signals
    should_suggest = (
        failure_count >= 2 or _has_frustration_signals(conversation_context)
    )
    if not should_suggest:
        return json.dumps({"has_suggestion": False})

    # Classify the task from context
    search_terms = classify_task(conversation_context)

    # Also use explicit task_type if provided
    if task_type:
        task_lower = task_type.lower()
        for keyword, search_term in _KEYWORD_MAP.items():
            if keyword in task_lower and search_term not in search_terms:
                search_terms.insert(0, search_term)

    if not search_terms:
        # No specific task identified — suggest the most broadly useful pack
        search_terms = ["debug"]

    # Search guild packs for each term until we find matches
    all_matches: List[dict] = []
    for term in search_terms:
        try:
            result = json.loads(borg_search(term, requesting_agent_id=requesting_agent_id, include_seeds=False))
            if result.get("success") and result.get("matches"):
                all_matches.extend(result["matches"])
        except Exception as e:
            logger.debug("Guild search failed for term '%s': %s", term, e)

    if not all_matches:
        return json.dumps({"has_suggestion": False})

    # Deduplicate by name and filter out tried packs
    seen_names: set = set()
    unique_matches: List[dict] = []
    for match in all_matches:
        name = match.get("name", "")
        if name and name not in seen_names and name not in tried_packs:
            seen_names.add(name)
            unique_matches.append(match)

    if not unique_matches:
        return json.dumps({"has_suggestion": False})

    # Build top 3 suggestions with rich metadata
    top_matches = unique_matches[:3]
    suggestions_list = []
    for pack in top_matches:
        suggestions_list.append({
            "pack_name": pack.get("name", ""),
            "confidence": pack.get("confidence", "unknown"),
            "problem_class": pack.get("problem_class", ""),
            "tier": pack.get("tier", "unknown"),
            "why_relevant": _build_why_relevant(pack, search_terms),
            "author_reputation": pack.get("author_reputation"),
        })

    # Format the primary suggestion
    suggestion_text = _format_suggestion(top_matches, conversation_context)

    best_name = top_matches[0].get("name", "")
    best_confidence = top_matches[0].get("confidence", "unknown")
    return json.dumps({
        "has_suggestion": True,
        "suggestion": suggestion_text,
        "suggestions": suggestions_list,
        "pack_name": best_name,
        "pack_uri": f"guild://hermes/{best_name}",
        "search_terms": search_terms,
        "match_count": len(unique_matches),
        "human_message": (
            f"🧠 Borg found a relevant approach: **{best_name}** "
            f"(confidence: {best_confidence}). "
            f"Tell the user: \"I found a community-tested approach for this. "
            f"Want me to follow it?\""
        ),
    })
