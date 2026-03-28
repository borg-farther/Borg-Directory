# Reputation Engine Wiring Specification
## Borg Agent-Borg Package — M2.4 Integration

---

## 1. Overview

**ReputationEngine** (`borg/db/reputation.py`, 462 lines) exists with full unit-test coverage (`borg/tests/test_reputation.py`, 430 lines) but is **not wired into any core module**. This spec defines exactly how to integrate it into `publish`, `apply`, and `search`.

**Guiding Principles:**
- ReputationEngine is the authoritative source for agent contribution scores, access tiers, and free-rider status
- Core modules (publish/apply/search) call ReputationEngine; ReputationEngine calls AgentStore
- All wiring is additive — existing behavior preserved when ReputationEngine is unavailable (graceful degradation)
- No reputation data is ever required to block core UX flows (apply/search always work; only publish is gated)

---

## 2. ReputationEngine API Surface

### 2.1 Data Classes

```python
@dataclass
class ContributionAction:
    action_type: str           # "pack_publication" | "quality_review" | "bug_report" | ...
    quality: float = 1.0       # 0.0–1.0 multiplier
    confidence: str = "inferred"  # for pack_publication only
    created_at: datetime

@dataclass
class ReputationProfile:
    agent_id: str
    contribution_score: float = 0.0
    access_tier: AccessTier    # COMMUNITY | VALIDATED | CORE | GOVERNANCE
    free_rider_score: float = 0.0
    free_rider_status: FreeRiderStatus  # OK | FLAGGED | THROTTLED | RESTRICTED
    peak_score: float = 0.0
    last_active_at: Optional[datetime] = None
    packs_published: int = 0
    quality_reviews_given: int = 0
    bug_reports_filed: int = 0
    documentation_contributions: int = 0
    governance_votes_cast: int = 0
    packs_consumed: int = 0

class AccessTier(Enum):
    COMMUNITY = "community"      # score < 10
    VALIDATED = "validated"      # score 10–50
    CORE = "core"                # score 50–200
    GOVERNANCE = "governance"   # score > 200

class FreeRiderStatus(Enum):
    OK = "ok"           # score <= 20
    FLAGGED = "flagged" # score 21–50
    THROTTLED = "throttled"  # score 51–100
    RESTRICTED = "restricted"  # score > 100
```

### 2.2 Public Methods

| Method | Signature | Returns | Notes |
|--------|-----------|---------|-------|
| `contribution_score` | `(agent_id, actions, now?)` | `float` | Weighted sum with recency decay |
| `compute_tier` | `(score)` | `AccessTier` | Static tier computation |
| `free_rider_score` | `(consumed, contributed, reviews)` | `float` | `consumed / max(1, contributed + reviews)` |
| `free_rider_status` | `(score)` | `FreeRiderStatus` | Static status computation |
| `delta_pack_published` | `(confidence)` | `int` | guessed=1, inferred=3, tested=7, validated=15 |
| `delta_quality_review` | `(quality: 1–5)` | `int` | 0,1,2,4,5 |
| `delta_pack_used_by_others` | `(current_uses)` | `int` | +1 each, capped at 50/pack/epoch |
| `delta_pack_failure` | `()` | `int` | -2 |
| `delta_calibration_failure` | `()` | `int` | -5 |
| `compute_inactivity_decay` | `(peak, last_active, now?)` | `float` | -5%/month after 90d grace, floor 50% |
| `build_profile` | `(agent_id, now?)` | `ReputationProfile` | Full computed profile from store |
| `apply_pack_published` | `(agent_id, pack_id, confidence)` | `ReputationProfile` | Delta + store update |
| `apply_quality_review` | `(agent_id, feedback_id, quality)` | `ReputationProfile` | Delta + store update |
| `apply_pack_consumed` | `(agent_id, pack_id)` | `ReputationProfile` | Counter update |

### 2.3 Action Weights

```python
ACTION_WEIGHTS = {
    "pack_publication": 10,
    "quality_review": 3,
    "bug_report": 2,
    "documentation": 2,
    "governance_vote": 1,
}
```

### 2.4 Missing Method to Add

```python
def apply_pack_failure(self, agent_id: str, pack_id: str) -> ReputationProfile:
    """Record a pack execution failure and apply reputation penalty."""
    delta = self.delta_pack_failure()  # -2
    agent = self.store.get_agent(agent_id)
    if agent:
        current_score = float(agent.get("contribution_score") or 0)
        new_score = max(0, current_score + delta)
        self.store.update_agent_stats(
            agent_id,
            contribution_score=new_score,
            last_active_at=datetime.now(timezone.utc).isoformat(),
        )
    return self.build_profile(agent_id)
```

---

## 3. Integration Point: publish.py

### 3.1 Current Behavior

`action_publish()` (line 343) calls `AgentStore().record_publish(...)` after a successful GitHub PR, but **does not update ReputationEngine**.

### 3.2 Required Changes

**File:** `borg/core/publish.py`

**Change 1 — Add import:**
```python
from borg.db.reputation import ReputationEngine
```

**Change 2 — In `action_publish()`, after `log_publish()` and successful PR, replace the existing optional store block:**

Old (lines 462–476):
```python
        # Log publish to reputation store (optional — store may not exist)
        if AgentStore is not None:
            try:
                _store = AgentStore()
                provenance = sanitized_artifact.get("provenance", {})
                _store.record_publish(
                    pack_id=str(artifact_id),
                    author_agent=provenance.get("author_agent", "unknown"),
                    confidence=provenance.get("confidence", "unknown"),
                    outcome="published",
                    metadata={"pr_url": pr_result["pr_url"], "artifact_type": artifact_type},
                )
                _store.close()
            except Exception:
                pass  # Store is optional — never break core flow
```

New:
```python
        # Always log to store
        provenance = sanitized_artifact.get("provenance", {})
        author_agent = provenance.get("author_agent", "unknown")
        confidence = provenance.get("confidence", "unknown")

        if AgentStore is not None:
            try:
                _store = AgentStore()
                _store.record_publish(
                    pack_id=str(artifact_id),
                    author_agent=author_agent,
                    confidence=confidence,
                    outcome="published",
                    metadata={"pr_url": pr_result["pr_url"], "artifact_type": artifact_type},
                )
                _store.close()
            except Exception:
                pass  # Store is optional — never break core flow

        # Update ReputationEngine: record pack publication for the author
        if AgentStore is not None and author_agent and author_agent != "unknown":
            try:
                _store = AgentStore()
                _engine = ReputationEngine(_store)
                _engine.apply_pack_published(author_agent, str(artifact_id), confidence)
                _store.close()
            except Exception:
                pass  # Reputation is optional — never break core flow
```

### 3.3 Publishing Access Gate

Before accepting a publish, check the author's AccessTier.

**Add helper:**
```python
def _check_publish_access(agent_id: str) -> tuple[bool, str]:
    """Check if agent has VALIDATED or higher tier to publish.
    
    Returns (allowed, error_message).
    """
    if AgentStore is None:
        return True, ""  # No store = allow (degraded mode)
    
    try:
        store = AgentStore()
        engine = ReputationEngine(store)
        profile = engine.build_profile(agent_id)
        store.close()
        
        if profile.access_tier == AccessTier.COMMUNITY:
            return False, (
                f"Agent '{agent_id}' is at COMMUNITY tier (score={profile.contribution_score:.1f}). "
                f"Publish requires VALIDATED tier (score >= 10). "
                f"Publish a quality pack or contribute to the guild to raise your score."
            )
        return True, ""
    except Exception:
        return True, ""  # Fail open — reputation check is advisory
```

**Gate location:** In `action_publish()`, after rate-limit check (line 399), add:
```python
    # Reputation gating: check access tier
    provenance = artifact.get("provenance", {})
    author_agent = provenance.get("author_agent", "unknown")
    if author_agent and author_agent != "unknown":
        allowed, error_msg = _check_publish_access(author_agent)
        if not allowed:
            return json.dumps({
                "success": False,
                "error": "Publish access denied",
                "reason": error_msg,
                "hint": "Raise your contribution score by publishing feedback, "
                        "filing bug reports, or contributing documentation.",
            })
```

**Note:** `feedback` artifacts bypass the tier gate (they have no `author_agent` provenance field in the same way packs do; they route through `parent_artifact`).

---

## 4. Integration Point: apply.py

### 4.1 Current Behavior

`action_complete()` (line 542) calls `AgentStore().record_execution(...)` and writes a feedback draft. **Does not call ReputationEngine**.

### 4.2 Required Changes

**File:** `borg/core/apply.py`

**Change 1 — Add import:**
```python
from borg.db.reputation import ReputationEngine, AccessTier
```

**Change 2 — In `action_complete()`, after `record_execution()` block (line 776), add reputation update:**

Old (lines 776–794):
```python
    # Log execution to reputation store (optional — store may not exist)
    if AgentStore is not None:
        try:
            _store = AgentStore()
            _store.record_execution(
                execution_id=f"{session['pack_id']}-{session_id}",
                session_id=session_id,
                pack_id=session["pack_id"],
                agent_id="guild-v2",  # agent_id not available in session context
                task=session.get("task"),
                status="completed",
                phases_completed=phases_passed,
                phases_failed=phases_failed,
                started_at=session.get("created_at"),
                completed_at=ended.isoformat(),
                log_hash=log_hash,
            )
            _store.close()
        except Exception:
            pass  # Store is optional — never break core flow
```

New:
```python
    # Resolve agent_id for reputation updates
    # Prefer operator-supplied agent_id in context, fallback to "guild-v2"
    agent_id = eval_context.get("agent_id") if eval_context else None
    if not agent_id:
        agent_id = session.get("agent_id") or "guild-v2"

    # Log execution to reputation store (optional — store may not exist)
    if AgentStore is not None:
        try:
            _store = AgentStore()
            _store.record_execution(
                execution_id=f"{session['pack_id']}-{session_id}",
                session_id=session_id,
                pack_id=session["pack_id"],
                agent_id=agent_id,
                task=session.get("task"),
                status="completed",
                phases_completed=phases_passed,
                phases_failed=phases_failed,
                started_at=session.get("created_at"),
                completed_at=ended.isoformat(),
                log_hash=log_hash,
            )
            _store.close()
        except Exception:
            pass  # Store is optional — never break core flow

    # Update ReputationEngine: record pack consumption (execution)
    if AgentStore is not None and agent_id != "guild-v2":
        try:
            _store = AgentStore()
            _engine = ReputationEngine(_store)
            _engine.apply_pack_consumed(agent_id, session["pack_id"])
            _store.close()
        except Exception:
            pass  # Reputation is optional — never break core flow

    # Apply failure penalty if any phases failed
    if AgentStore is not None and agent_id != "guild-v2" and phases_failed > 0:
        try:
            _store = AgentStore()
            _engine = ReputationEngine(_store)
            _engine.apply_pack_failure(agent_id, session["pack_id"])
            _store.close()
        except Exception:
            pass  # Reputation is optional — never break core flow
```

**Change 3 — When feedback is published (action_publish for feedback), also record quality review:**

In `action_complete()`, after generating the feedback draft, record quality review:
```python
    # Record quality review in ReputationEngine when feedback is generated
    if AgentStore is not None and agent_id != "guild-v2":
        try:
            _store = AgentStore()
            _engine = ReputationEngine(_store)
            # Determine quality score from execution outcome
            if phases_failed == 0:
                quality = 5  # All phases passed = highest quality
            elif phases_failed < phases_total / 2:
                quality = 4  # Mostly passed
            elif phases_failed < phases_total:
                quality = 3  # Partial
            else:
                quality = 2  # Mostly failed
            
            feedback_id = feedback_draft.get("id", f"{session['pack_id']}/feedback/{ended.strftime('%Y%m%dT%H%M%S')}")
            _engine.apply_quality_review(agent_id, feedback_id, quality)
            _store.close()
        except Exception:
            pass  # Reputation is optional — never break core flow
```

### 4.3 Agent ID Resolution

The session dict in `apply.py` does not currently carry an `agent_id` field. The `eval_context` (passed as `context_dict` in `action_start`) is the preferred source. If not available, the reputation system falls back gracefully (treats as "guild-v2" which is not a real agent).

**Recommended:** Add `agent_id` to the session dict in `action_start` by extracting from `eval_context`:
```python
# In action_start(), after building session dict:
session["agent_id"] = eval_context.get("agent_id") if eval_context else "guild-v2"
```

---

## 5. Integration Point: search.py

### 5.1 Current Behavior

`borg_search()` (line 76) returns ranked results by text match only. Pack reputation (author quality) is **not factored in**.

### 5.2 Required Changes

**File:** `borg/core/search.py`

**Change 1 — Add import:**
```python
from borg.db.reputation import ReputationEngine, AccessTier
```

**Change 2 — Modify `borg_search()` to accept an optional agent context and apply reputation boosting:**

The function signature is:
```python
def borg_search(query: str, mode: str = "text") -> str:
```

Add an optional parameter:
```python
def borg_search(query: str, mode: str = "text", requesting_agent_id: str = None) -> str:
```

**Change 3 — After collecting `all_packs`, before returning, inject author reputation scores:**

After deduplication (after line 173), before the query_lower check (line 175):

```python
        # Inject author reputation scores into pack metadata
        if AgentStore is not None and requesting_agent_id:
            try:
                _store = AgentStore()
                _engine = ReputationEngine(_store)
                
                # Batch-fetch profiles for all unique authors encountered
                author_ids = set(
                    p.get("provenance", {}).get("author_agent", "")
                    for p in all_packs
                    if p.get("provenance", {}).get("author_agent")
                )
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
```

**Change 4 — Apply reputation-weighted re-ranking to text-mode matches:**

In text search mode, after collecting `matches` (line 232), before returning:

```python
        # Apply reputation-weighted re-ranking
        if requesting_agent_id and matches and AgentStore is not None:
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
```

**Change 5 — Semantic/hybrid mode already supports `relevance_score` from SemanticSearchEngine:**

For semantic mode, the engine returns `relevance_score` (0-1). A reputation boost can be applied similarly:
```python
                for pack in matches:
                    rep_boost = pack.get("author_reputation", {})
                    author_tier_val = tier_normalized.get(
                        AccessTier(rep_boost.get("access_tier", "community"))
                        if rep_boost else AccessTier.COMMUNITY, 0.0
                    )
                    # Blend: 80% semantic relevance, 20% author reputation
                    base_score = pack.get("relevance_score", 0.5)
                    pack["final_score"] = base_score * 0.8 + author_tier_val * 0.2
```

---

## 6. Data Flow Diagrams

### 6.1 Publish Flow (with Reputation)

```
action_publish(pack_name)
    │
    ├─► proof_gate validation
    ├─► safety scan
    ├─► privacy scan
    ├─► rate_limit check
    │
    ├─► _check_publish_access(author_agent)      [NEW]
    │       │
    │       └─► AgentStore().get_agent(author_agent)
    │               │
    │               └─► ReputationEngine().build_profile(author_agent)
    │                       │
    │                       └─► AccessTier.from_score(score)
    │                               │
    │                               └──► if COMMUNITY → BLOCK with error
    │
    ├─► save_to_outbox()
    ├─► create_github_pr()
    │       │
    │       └─► if success:
    │               ├─► log_publish()
    │               ├─► AgentStore().record_publish(pack_id, author_agent, confidence)
    │               │
    │               └─► ReputationEngine().apply_pack_published(author_agent, pack_id, confidence)  [NEW]
    │                       │
    │                       ├─► delta = delta_pack_published(confidence)  [+1..+15]
    │                       ├─► AgentStore().update_agent_stats(contribution_score += delta, packs_published++)
    │                       └─► build_profile(author_agent) → ReputationProfile
    │
    └─► return JSON {success, pr_url}
```

### 6.2 Apply Flow (with Reputation)

```
action_complete(session_id, outcome)
    │
    ├─► load session
    ├─► count phases_passed / phases_failed
    ├─► generate feedback draft
    │
    ├─► AgentStore().record_execution(execution_id, ..., agent_id)   [FIX: agent_id resolved]
    │
    ├─► ReputationEngine().apply_pack_consumed(agent_id, pack_id)    [NEW]
    │       │
    │       ├─► AgentStore().update_agent_stats(packs_consumed++)
    │       └─► build_profile(agent_id)
    │
    ├─► if phases_failed > 0:
    │       ReputationEngine().apply_pack_failure(agent_id, pack_id)  [NEW]
    │           │
    │           ├─► delta = delta_pack_failure()  [-2]
    │           └─► AgentStore().update_agent_stats(contribution_score += delta)
    │
    ├─► ReputationEngine().apply_quality_review(agent_id, feedback_id, quality)  [NEW]
    │       │
    │       ├─► delta = delta_quality_review(quality)  [0..5]
    │       └─► AgentStore().update_agent_stats(contribution_score += delta, feedback_given++)
    │
    └─► return JSON {summary, feedback_draft}
```

### 6.3 Search Flow (with Reputation Weighting)

```
borg_search(query, mode, requesting_agent_id?)
    │
    ├─► _fetch_index() → remote packs
    ├─► scan BORG_DIR → local packs
    ├─► deduplicate by id/name
    │
    ├─► if requesting_agent_id AND AgentStore available:
    │       │
    │       ├─► ReputationEngine().build_profile(requesting_agent_id)
    │       ├─► For each unique author in results:
    │       │       ReputationEngine().build_profile(author_id)
    │       └─► Attach author_reputation to each pack
    │
    ├─► if mode == "semantic" or "hybrid":
    │       SemanticSearchEngine().search(query)
    │           │
    │           └─► results include relevance_score
    │
    ├─► if mode == "text":
    │       keyword match → matches list
    │
    ├─► if requesting_agent_id AND matches:
    │       │
    │       ├─► tier_normalized = {COMMUNITY:0, VALIDATED:0.25, CORE:0.6, GOVERNANCE:1.0}
    │       ├─► requester_tier_val = tier_normalized[requester.access_tier]
    │       ├─► for each match:
    │       │       author_tier_val = tier_normalized[pack.author_tier]
    │       │       tier_boost = max(0, author_tier_val - requester_tier_val) * 0.3
    │       │       adoption_boost = min(0.2, pack.adoption_count * 0.01)
    │       │       pack.reputation_boost = tier_boost + adoption_boost
    │       └─► reranked.sort(key=lambda p: -p.reputation_boost)
    │
    └─► return JSON {success, matches[], query, total, mode}
            matches[] include: name, id, problem_class, tier, confidence,
                                author_reputation{contribution_score, access_tier},
                                reputation_boost (or final_score for semantic)
```

---

## 7. Edge Cases

### 7.1 Agent Has No Store Record
- `ReputationEngine.build_profile()` returns `ReputationProfile(agent_id=agent_id)` with all defaults (COMMUNITY tier, 0 score)
- Publishing gate: COMMUNITY → blocked
- Search: author_reputation = None, no boost applied
- **No crash**: all entry points wrapped in try/except

### 7.2 agent_id = "guild-v2" (Unknown/Batch Agent)
- `apply_pack_consumed` / `apply_quality_review` skip if agent_id == "guild-v2"
- Rationale: batch/system agents don't earn reputation
- **No profile pollution**

### 7.3 Store Connection Failure
- All reputation calls wrapped in `try/except: pass`
- Core UX continues uninterrupted
- Reputation just doesn't update

### 7.4 First-Time Publisher (Community Tier)
- Publishing blocked at gate with clear error message
- Error includes current score and what's needed
- **No silent failure**

### 7.5 High Free-Rider Score
- `free_rider_status` is computed in `build_profile` but NOT currently used to gate any operation
- **Future extension point**: could throttle apply (too many packs consumed without contribution)
- Not implemented in this spec to avoid UX regression

### 7.6 Pack Has No Provenance / author_agent
- `author_agent = provenance.get("author_agent", "unknown")` — unknown is used
- `_check_publish_access("unknown")` → allowed (no gate applied)
- Reputation update skipped
- **Graceful degradation**

### 7.7 Concurrent Updates
- `AgentStore.update_agent_stats()` is not thread-safe for read-modify-write
- If two rep updates race, one may be lost
- **Acceptable for v1**: reputation scoring is advisory, not authoritative
- Future: use `UPDATE agents SET contribution_score = contribution_score + ?` atomic SQL

### 7.8 Reputation Stale Data
- `build_profile()` always re-computes from current store state (actions, not cached score)
- `apply_pack_published()` etc. use incremental update (current + delta)
- **Eventually consistent**: profile always reflects latest store data

---

## 8. Evaluation Criteria — Tests That Prove It Works

### 8.1 Unit Tests (existing: `test_reputation.py` — already passing)

These tests prove the ReputationEngine core logic is correct:
- `test_single_pack_publication` — ACTION_WEIGHTS["pack_publication"] = 10
- `test_recency_decay_one_epoch` — 30d → λ ≈ 0.607 multiplier
- `test_delta_pack_published` — confidence mapping (guessed→1, inferred→3, tested→7, validated→15)
- `test_delta_quality_review` — quality mapping (1→0, 5→5)
- `test_access_tier_boundaries` — COMMUNITY<10, VALIDATED≥10, CORE≥50, GOVERNANCE>200
- `test_free_rider_score_formula` — consumed/(contributed+reviews)
- `test_apply_pack_published_updates_stats` — profile.packs_published incremented
- `test_build_profile_empty_agent` — community tier, 0 score

### 8.2 New Integration Tests

**File:** `borg/tests/test_reputation_wiring.py` (new file)

```python
"""Integration tests for ReputationEngine wired into core modules."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# 8.2.1 Publish → ReputationEngine.apply_pack_published called
class TestPublishReputationWiring:
    
    def test_publish_calls_apply_pack_published_on_success(self, tmp_path):
        """On successful PR, author's reputation is updated."""
        # Mock AgentStore and GitHub CLI
        with patch("borg.core.publish.AgentStore") as mock_store_cls, \
             patch("borg.core.publish.ReputationEngine") as mock_engine_cls:
            
            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store
            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine
            mock_engine.apply_pack_published.return_value = MagicMock()
            
            # ... call action_publish() ...
            # assert mock_engine.apply_pack_published.called
            # assert mock_engine.apply_pack_published.call_args[0] == ("author-agent", "pack-id", "validated")

    def test_community_agent_blocked_from_publishing(self, tmp_path):
        """Agent at COMMUNITY tier cannot publish packs."""
        with patch("borg.core.publish.AgentStore") as mock_store_cls, \
             patch("borg.core.publish.ReputationEngine") as mock_engine_cls:
            
            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store
            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine
            
            # Return a COMMUNITY-tier profile
            from borg.db.reputation import ReputationProfile, AccessTier
            mock_engine.build_profile.return_value = ReputationProfile(
                agent_id="community-agent",
                contribution_score=5.0,
                access_tier=AccessTier.COMMUNITY,
            )
            
            # ... call action_publish() ...
            # result = json.loads(...)
            # assert result["success"] == False
            # assert "COMMUNITY tier" in result["error"]

    def test_publish_failure_does_not_call_reputation(self, tmp_path):
        """On outbox fallback (PR failed), reputation update is skipped."""
        # ...

# 8.2.2 Apply → ReputationEngine.apply_pack_consumed called on complete
class TestApplyReputationWiring:
    
    def test_complete_calls_apply_pack_consumed(self, tmp_path):
        """action_complete increments pack_consumed counter for the agent."""
        # ...

    def test_complete_calls_apply_pack_failure_on_phases_failed(self, tmp_path):
        """If phases_failed > 0, apply_pack_failure is called (delta = -2)."""
        # ...

    def test_complete_calls_apply_quality_review(self, tmp_path):
        """Feedback quality review is recorded with correct quality score."""
        # quality=5 when all passed, 2 when all failed
        # ...

    def test_guild_v2_agent_skips_reputation_update(self, tmp_path):
        """System agent 'guild-v2' does not pollute reputation."""
        # ...

# 8.2.3 Search → Reputation-weighted re-ranking
class TestSearchReputationWiring:
    
    def test_search_injects_author_reputation(self):
        """Search results include author_reputation metadata."""
        # ...

    def test_search_reranks_by_tier_differential(self):
        """Higher-tier authors get boosted over lower-tier authors."""
        # ...
    
    def test_search_without_agent_id_unchanged(self):
        """When requesting_agent_id=None, search returns text-order results."""
        # ...
```

### 8.3 Schema/Migration Tests

- Verify `agents` table has `contribution_score`, `free_rider_score`, `access_tier` columns
- Verify `update_agent_stats()` accepts all reputation fields
- **Already covered by:** `test_store.py` lines 441, 484, 489, 872

### 8.4 Load/Degradation Tests

```python
def test_reputation_unavailable_does_not_break_publish():
    """If AgentStore raises, publish succeeds without reputation."""
    with patch("borg.core.publish.AgentStore", side_effect=Exception("DB error")):
        result = action_publish(pack_name="test-pack")
        assert json.loads(result)["success"] == True

def test_reputation_unavailable_does_not_break_search():
    """If ReputationEngine raises, search returns unranked results."""
    with patch("borg.core.search.ReputationEngine", side_effect=Exception("DB error")):
        result = borg_search("debug")
        assert json.loads(result)["success"] == True
        assert "author_reputation" not in json.loads(result)["matches"][0]
```

---

## 9. Summary of All Changes

| File | Change Type | Lines Affected | What Changes |
|------|-------------|----------------|--------------|
| `borg/core/publish.py` | Modify | ~15 | Import ReputationEngine; wire `apply_pack_published()` after PR success; add `_check_publish_access()` gate |
| `borg/core/apply.py` | Modify | ~35 | Import ReputationEngine; wire `apply_pack_consumed()`, `apply_pack_failure()`, `apply_quality_review()` in `action_complete()`; fix agent_id resolution |
| `borg/core/search.py` | Modify | ~50 | Import ReputationEngine; add `requesting_agent_id` param to `borg_search()`; inject author_reputation into pack results; apply RRF re-ranking |
| `borg/db/reputation.py` | Add method | ~15 | Add `apply_pack_failure()` method |
| `borg/tests/test_reputation_wiring.py` | New file | ~200 | Full integration test suite for wiring |

---

## 10. Implementation Order

1. **Add `apply_pack_failure()` to ReputationEngine** (no dependencies)
2. **Wire publish.py** (isolated, easy to test)
3. **Wire apply.py** (isolated, easy to test)
4. **Wire search.py** (adds parameter, backward-compatible)
5. **Write integration tests** (requires mocked store)
6. **Run full test suite** — verify no regressions in existing tests

---

*Spec version: 1.0 | For questions contact: borg-team@hermes*
