# Partial Implementations Status Report
## Date: 2026-03-29
## Repository: `/root/hermes-workspace/borg/`

---

## Executive Summary

Four features were flagged as "partially implemented" in the project audit:
1. **Ed25519 signing** (pack authenticity verification)
2. **V2 pack execution** (V2 schema format packs)
3. **Sybil resistance** (preventing fake agents from gaming trust/reputation)
4. **Adoption metrics** (tracking pack usage)

---

## 1. Ed25519 Signing

### What the README Claims
> `pip install agent-borg[crypto]` — For Ed25519 pack signing

The `pyproject.toml` declares `pynacl>=1.5.0` as an optional crypto dependency.

### What Exists in Code
**Nothing.** Zero Ed25519 implementation found across all 18 Python modules in `borg/`.

Searches for `sign`, `verify`, `signature`, `ed25519`, `nacl` returned zero matches in `borg/` subdirectories.

### What Is Missing
- `borg/crypto.py` or similar module does not exist
- No signing of pack YAML content with Ed25519 private keys
- No signature verification of downloaded packs
- No key generation, key storage, or key management
- No integration with `borg_pull` (download) or `borg_publish` (upload) to sign/verify
- No `signature` field in pack schema or provenance blocks
- No tests for Ed25519 functionality

### Gap Severity: HIGH
This is a security-critical missing piece for a trust/reputation system. Without pack signing:
- Downloaded packs can be tampered with in transit
- No authenticity guarantee that a pack came from a specific agent
- The reputation system cannot anchor trust to a verified identity

### Implementation Spec: Ed25519 Pack Signing

```
Module: borg/core/crypto.py (NEW)

Functions:
  - generate_signing_key(seed: bytes | None = None) -> nacl.signing.SigningKey
    Generate a new Ed25519 signing key. If seed is None, use SecureRandom.
    
  - sign_pack(pack_yaml: str, signing_key: nacl.signing.SigningKey) -> str
    Sign the canonical YAML bytes with Ed25519. Returns base64-encoded signature.
    Canonical form: normalize YAML (yaml.safe_dump with sort_keys=False, default_flow_style=False)
    
  - verify_pack_signature(pack_yaml: str, signature: str, verify_key: nacl.signing.VerifyKey) -> bool
    Verify signature against pack YAML content.
    
  - derive_verify_key(signing_key: nacl.signing.SigningKey) -> nacl.signing.VerifyKey
    Derive the verify key from a signing key for sharing.
    
  - encode_key(key: bytes) -> str
    Encode key as URL-safe base64 string for storage in config/provenance.
    
  - decode_key(encoded: str, key_type: str) -> bytes
    Decode key from URL-safe base64.

Schema Addition:
  provenance:
    signature: "<base64>"      # Ed25519 signature of canonical pack YAML
    signer: "<agent-id>"       # Agent identity (e.g., "agent://hermes/core")
    verify_key: "<base64>"    # Ed25519 verify key (can be shared)

Integration Points:
  - borg_pull: After downloading and validating pack, verify signature if present
  - borg_publish: Before publishing, sign pack with local key (key stored in ~/.hermes/guild/keys/)
  - apply.py: On action_start, verify signature if present in provenance
  - A new optional config: ~/.hermes/guild/keys/default_signing_key (permissions 0600)

Key Storage:
  - Signing keys stored in ~/.hermes/guild/keys/
  - File per agent: {agent_id}.key (mode 0600)
  - Verify keys can be published in agent profiles or packed in provenance
```

---

## 2. V2 Pack Execution

### What Exists
V2 pack detection is implemented in ONE place only:

**`borg/core/safety.py` lines 345-347:**
```python
def _is_v2_pack(pack: dict) -> bool:
    """Return True if this is a V2 pack (has structure[] instead of phases[])."""
    return "structure" in pack and "phases" not in pack
```

This is used in `check_pack_size_limits()` to count phases from the correct field.

**V2 schema difference:**
- V1: `phases: [{name, description, checkpoint, anti_patterns, prompts}]`
- V2: `structure: [{phase_name, description, guidance, checkpoint, anti_patterns}]`

### What Is Missing
- **`apply.py` does NOT handle V2 packs** — `action_start` at line 179 reads `pack.get("phases", [])` with no V2 `structure` equivalent
- **`apply.py` phase_plan builder** (lines 181-193) only reads V1 field names:
  - `phase.get("name", ...)` — V2 uses `phase_name`
  - `phase.get("checkpoint", ...)` — same
  - `phase.get("anti_patterns", ...)` — same
  - `phase.get("prompts", ...)` — **V2 has `guidance` instead**
- **`action_resume`** similarly only reads `phases` field (line 851)
- **`_generate_feedback`** does not account for V2 structure differences
- **No migration path** from V2 `structure` to V1 `phases` in `convert.py` or elsewhere
- **`schema.py`** only validates V1-style packs, no V2-specific validation
- **`proof_gates.py`** requires `phases` field (line 43: `_REQUIRED_PACK_FIELDS = {"type", "version", "id", "problem_class", "mental_model", "phases", "provenance"}`)

### Gap Severity: MEDIUM
A V2 pack loaded by `action_start` would fail silently — phases would be empty, all checkpoints would be skipped, and execution would immediately fail.

### Implementation Spec: V2 Pack Execution Support

```
Changes to borg/core/apply.py:

1. Add V2 structure normalizer in action_start (after line ~138):
   def _normalize_phases(pack: dict) -> list:
       """Normalize V1 (phases[]) or V2 (structure[]) to V1-equivalent list."""
       if "structure" in pack and "phases" not in pack:
           # V2 format — convert structure[] to phases[]
           return [
               {
                   "name": p.get("phase_name", p.get("name", f"phase_{i}")),
                   "description": p.get("description", ""),
                   "checkpoint": p.get("checkpoint", ""),
                   "anti_patterns": p.get("anti_patterns", []),
                   "prompts": p.get("guidance", []) if isinstance(p.get("guidance"), list) else [p.get("guidance", "")],
                   "status": "pending",
               }
               for i, p in enumerate(pack.get("structure", []))
               if isinstance(p, dict)
           ]
       else:
           # V1 format
           return pack.get("phases", [])

2. Change line ~179 in action_start:
   phases = _normalize_phases(pack)  # was: pack.get("phases", [])

3. Change line ~851 in action_resume:
   phases = _normalize_phases(pack)  # was: pack.get("phases", [])

Changes to borg/core/schema.py:

4. Update _REQUIRED_PACK_FIELDS to accept either "phases" OR "structure":
   def _get_required_pack_fields(pack_type: str) -> frozenset:
       # For workflow_pack, accept either phases or structure
       base = {"type", "version", "id", "provenance"}
       if pack.get("structure") is not None:
           return frozenset(base | {"problem_class", "mental_model", "structure"})
       return frozenset(base | {"problem_class", "mental_model", "phases"})

5. In validate_pack(), check for at least one of phases/structure

Changes to borg/core/proof_gates.py:

6. Line 43: Change "phases" to accept "structure" OR "phases"
```

---

## 3. Sybil Resistance

### What the Spec Claims
From GAP_ANALYSIS.md and SPEC_AUDIT_20260329.md, the reputation system should include:
- SybilGuard-style detection
- Free-rider detection and throttling
- Weighted trust based on operator diversity
- Reputation-gated access tiers

### What Exists
**`borg/db/reputation.py`** — A fully implemented `ReputationEngine` with:
- `contribution_score()` — weighted by action type with recency decay
- `free_rider_score()` — ratio of consumed vs contributed packs
- `AccessTier` enum — COMMUNITY (score<10), VALIDATED (10-50), CORE (50-200), GOVERNANCE (>200)
- `FreeRiderStatus` enum — OK, FLAGGED, THROTTLED, RESTRICTED
- `apply_pack_published()`, `apply_quality_review()`, `apply_pack_consumed()` — record actions
- `build_profile()` — full profile from store data
- `compute_inactivity_decay()` — 5% decay per month after 90 days

### What Is Missing (UNWIRED)
The GAP_ANALYSIS.md explicitly notes: **"Reputation system is not wired in AT ALL."**

Specific unwired items:
1. **`publish.py`** calls `GuildStore.record_publish()` but does NOT call `ReputationEngine.apply_pack_published()`
2. **`apply.py`** calls `GuildStore.record_execution()` but does NOT call `ReputationEngine.apply_pack_consumed()`
3. **`search.py` or MCP server** does NOT filter packs by access tier based on caller reputation
4. **`mcp_server.py`** does NOT check caller's `AccessTier` before allowing `borg_publish`
5. **No Sybil-specific detection** beyond free-rider scoring (which is itself not enforced)
6. **No reputation-based visibility gating** — all packs visible to all callers regardless of reputation

### What Actually Prevents Sybil Attacks Currently
- Proof gates require real work (evidence, examples, failure_cases for higher confidence)
- Privacy scan catches credential leakage
- Safety scan catches malicious pack content
- Rate limiting (3 publishes/day per agent) in `publish.py`

These are all supply-side checks, not reputation-based access controls.

### Gap Severity: HIGH
Without wiring the reputation engine, there's no enforcement of contribution thresholds. A Sybil attacker could create many low-quality packs that pollute the ecosystem. The free-rider detection exists but does nothing.

### Implementation Spec: Wire Sybil Resistance

```
Priority 1 — Wire ReputationEngine into publish.py:
  - In action_publish(), after successful proof gate validation:
    1. Look up or create agent profile in store
    2. Compute free_rider_score and free_rider_status
    3. If status is RESTRICTED (>100 ratio), reject publish
    4. If status is THROTTLED (51-100), apply extra scrutiny:
       - Require higher evidence bar
       - Set confidence ceiling (cap at "inferred" for THROTTLED agents)
    5. Call ReputationEngine.apply_pack_published()

Priority 2 — Wire into search/browse:
  - In search results, sort/promote packs by author reputation
  - Optionally: hide packs from agents with FREE_RIDER_STATUS.RESTRICTED
  - Show reputation badge (tier) next to pack author in results

Priority 3 — Anti-Sybil heuristics:
  - Detect rapid-fire publications from same agent_id (batch detection)
  - Flag packs with identical/near-identical failure_cases
  - Flag suspiciously similar packs from same author (text similarity)
  - Add honeypot packs (known-bad packs that flag suspicious agents)

Minimum viable wiring requires ~50 lines of changes across apply.py and publish.py.
```

---

## 4. Adoption Metrics

### What Exists
**`borg/db/analytics.py`** — A fully implemented `AnalyticsEngine` with:
- `pack_usage_stats(pack_id)` — pull_count, apply_count, success/failure counts, completion_rate
- `adoption_metrics(pack_id)` — unique_agents (feedback authors), unique_operators (executors)
- `ecosystem_adoption()` — aggregate across ecosystem
- `ecosystem_health()` — total_agents, active_contributors, active_consumers, contributor_ratio, quality scores, tier distribution
- `timeseries_*()` methods — daily/weekly/monthly for publishes, executions, quality scores, active_agents
- Time bucketing with `_daily_buckets`, `_weekly_buckets`, `_monthly_buckets`

### What Is Missing
1. **No public-facing API** — `AnalyticsEngine` is never instantiated in any public module
2. **No MCP tool** — No `borg_analytics` or similar tool in the MCP server
3. **No CLI subcommand** — `borg analytics` does not exist in `cli.py`
4. **No dashboard** — The GAP_ANALYSIS mentions a "Pack analytics dashboard for operators" which doesn't exist
5. **No background collection** — `record_execution()` in `store.py` is called but the analytics engine is never invoked to aggregate
6. **`ecosystem_health()` quality data** — avg_quality_trend always returns 0.0 (placeholder comment: "needs historical data")
7. **Second-pack activation** — analytics.py mentions it but no implementation exists
8. **Contributor conversion** — mentioned in analytics.py docstring but no implementation

### Gap Severity: MEDIUM
The analytics engine is complete but has zero consumer. It's a data warehouse with no queries.

### Implementation Spec: Adoption Metrics Exposure

```
Priority 1 — MCP tool (borg_analytics):
  New tool in mcp_server.py TOOLS array:
    {
        "name": "borg_analytics",
        "description": "Get adoption metrics for packs or the ecosystem. Returns usage stats, unique adopters, and ecosystem health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["pack", "ecosystem"],
                    "default": "ecosystem"
                },
                "pack_id": {"type": "string"},  # required if scope=pack
                "metric_type": {
                    "type": "string",
                    "enum": ["usage", "adoption", "health", "timeseries"],
                    "default": "health"
                },
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
                "days": {"type": "integer", "default": 30}
            }
        }
    }

  Implementation:
    def _tool_borg_analytics(arguments: dict) -> dict:
        scope = arguments.get("scope", "ecosystem")
        store = GuildStore()
        engine = AnalyticsEngine(store)
        
        if scope == "pack":
            pack_id = arguments.get("pack_id")
            if not pack_id:
                return {"error": "pack_id required when scope=pack"}
            mt = arguments.get("metric_type", "adoption")
            if mt == "usage":
                return engine.pack_usage_stats(pack_id)
            elif mt == "adoption":
                return engine.adoption_metrics(pack_id)
            elif mt == "timeseries":
                return engine.timeseries_pack_publishes(arguments.get("period", "daily"), arguments.get("days", 30))
            else:
                return {"error": f"Unknown metric_type: {mt}"}
        else:
            # ecosystem scope
            mt = arguments.get("metric_type", "health")
            if mt == "adoption":
                return engine.ecosystem_adoption()
            elif mt == "health":
                return engine.ecosystem_health()
            elif mt == "timeseries":
                return engine.timeseries(arguments.get("metric", "pack_publishes"), arguments.get("period", "daily"), arguments.get("days", 30))
            else:
                return {"error": f"Unknown metric_type: {mt}"}

Priority 2 — CLI subcommand:
  New subcommand in cli.py: _cmd_analytics
  Mirrors MCP tool functionality.

Priority 3 — Wire into MCP search results:
  When returning borg_search results, include adoption_metrics for each pack:
    "adoption": {"unique_agents": N, "unique_operators": M, "completion_rate": 0.X}
```

---

## Summary Table

| Feature | Status | Severity | Data Integrity | Wired In |
|---------|--------|----------|---------------|----------|
| Ed25519 Signing | NOT STARTED | HIGH | Security gap | No |
| V2 Pack Execution | PARTIAL (detect only) | MEDIUM | V2 packs fail silently | No |
| Sybil Resistance | PARTIAL (engine exists) | HIGH | Unwired | No |
| Adoption Metrics | PARTIAL (engine exists) | MEDIUM | No consumer | No |

---

## Files Created/Modified by This Audit

### New Files to Create
- `borg/core/crypto.py` — Ed25519 signing module (TODO)
- `docs/ED25519_SIGNING_SPEC.md` — Implementation spec (embedded in this report)
- `docs/ADOPTION_METRICS_SPEC.md` — Implementation spec (embedded in this report)

### Existing Files Needing Changes
1. `borg/core/apply.py` — Add `_normalize_phases()` for V2 support
2. `borg/core/schema.py` — Accept "structure" OR "phases" in required fields
3. `borg/core/proof_gates.py` — Accept "structure" OR "phases"
4. `borg/core/publish.py` — Wire ReputationEngine into publish flow
5. `borg/integrations/mcp_server.py` — Add `borg_analytics` tool
6. `borg/cli.py` — Add `analytics` subcommand

---

## Recommended Priority Order

1. **V2 pack execution** — Fix silent failure (low effort, prevents broken V2 packs)
2. **Sybil wiring** — Wire reputation engine into publish.py (~50 lines)
3. **Ed25519 signing** — Full crypto module (~200 lines + tests)
4. **Adoption metrics** — MCP tool + CLI (~100 lines)

All four features are described in sufficient detail above to be implemented without additional research.
