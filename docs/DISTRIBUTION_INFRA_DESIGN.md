# Agent-Borg Distribution Infrastructure — Design Doc

**Author:** Subagent (Distribution Design)
**Date:** 2026-03-29
**Status:** Draft for Implementation
**Target:** Zero users → thousands of agents

---

## 1. Overview

This document designs the distribution infrastructure for agent-borg ("borg"),
the collective-intelligence system for AI coding agents. It covers how packs move
from publishers to consumers across the network, at scale from 0 to thousands of
simultaneous agents.

**Current state (as-is):**
- Packs are YAML files stored in a single GitHub repo (`bensargotest-sys/guild-packs`)
- Pack index is a single `index.json` at repo root (flat key-value map, ~20 packs)
- `guild://` URIs resolve to GitHub raw URLs via `uri.py`
- Publishing is a GitHub PR via `gh` CLI, with a local outbox fallback
- No coordinator service, no authentication beyond `gh` CLI auth, no versioning strategy

**Target state (to-be):**
- Multiple publishers can publish packs without stepping on each other
- Agents can discover, query, and pull packs from multiple sources
- Versioning, updates, and deprecation are first-class
- Publisher authentication is scoped and revokable
- The system works for 0 users and scales to thousands

---

## 2. Architecture

### 2.1 System Context

```
┌──────────────────────────────────────────────────────────────────┐
│                         Agent (Consumer)                          │
│  borg search "debugging" → borg pull guild://hermes/systematic-debugging  │
│  borg apply systematic-debugging --task "fix pytest failures"    │
└──────────────────────────┬───────────────────────────────────────┘
                           │ guild:// or https://
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                  DISTRIBUTION LAYER (this doc)                   │
│                                                                  │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │ Pack Index  │   │ Distribution  │   │ Auth / Publisher  │   │
│  │  Registry   │◄──│  Mechanism    │◄──│   Identity        │   │
│  └─────────────┘   └──────────────┘   └────────────────────┘   │
│                                                                  │
│  Components:                                                     │
│  1. Registry API   — query, search, discover packs              │
│  2. CDN/Storage    — serve pack tarballs/blobs                  │
│  3. Index Sync     — keep distributed indexes consistent        │
│  4. Auth Flow      — authenticate & authorize publishers        │
│  5. Versioning     — semver strategy for pack updates           │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Publisher (Producer)                       │
│  borg publish --pack my-pack.yaml  →  GitHub PR or direct API   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Proposed Architecture (MVP)

For the MVP targeting zero-to-thousands scale, a **hybrid GitHub + JSON API**
approach is chosen:

```
                        ┌─────────────────┐
                        │  GitHub Repo    │
                        │ (guild-packs)   │
                        │  packs/*.yaml   │
                        │  index.json     │
                        └────────┬────────┘
                                 │ webhooks / push
                                 ▼
                        ┌─────────────────┐
                        │  Registry API   │  ← new service (lightweight)
                        │  (index + fetch)│
                        └────────┬────────┘
                                 │ HTTPS JSON
                    ┌────────────┴────────────┐
                    │                         │
              ┌─────▼─────┐             ┌─────▼──────┐
              │  Agent A  │             │  Agent B   │
              │  (pull)   │             │  (publish) │
              └───────────┘             └────────────┘
```

**Why this approach:**
- GitHub is already the store — no additional infrastructure
- GitHub's CDN (raw.githubusercontent.com) handles serving files globally
- Adding a thin Registry API layer (stateless, ~200 lines) enables:
  - Structured queries (search, filter by tag/tier/confidence)
  - Multiple index sources (federation in future)
  - Authentication without touching GitHub ACLs directly
- Scales from 0 (no infrastructure to operate) to thousands (GitHub handles CDN)

---

## 3. Pack Registry / Index

### 3.1 Current Index Structure

The current `index.json` is a flat key-value map at repo root:

```json
{
  "guild://converted/systematic-debugging": {
    "type": "workflow_pack",
    "version": "1.0.0",
    "id": "guild://converted/systematic-debugging",
    "problem_class": "...",
    "phases": [...],
    "tier": "community",
    "confidence": "tested"
  }
}
```

**Problems with flat structure:**
- No support for multiple versions of the same pack
- No support for multiple sources (multiple GitHub orgs)
- No structured metadata for filtering
- No total ordering or pagination

### 3.2 Proposed Registry Schema

```json
{
  "schema_version": "1.0",
  "indexed_at": "2026-03-29T12:00:00Z",
  "sources": [
    {
      "source_id": "guild-packs",
      "type": "github",
      "repo": "bensargotest-sys/guild-packs",
      "branch": "main",
      "base_url": "https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main"
    }
  ],
  "packs": [
    {
      "pack_id": "guild://hermes/systematic-debugging",
      "source": "guild-packs",
      "versions": {
        "1.0.0": {
          "version": "1.0.0",
          "pack_url": "https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/packs/systematic-debugging.workflow.yaml",
          "sha256": "abc123...",
          "confidence": "tested",
          "tier": "validated",
          "problem_class": "debugging",
          "phase_count": 4,
          "published_at": "2026-01-15T10:00:00Z",
          "author_agent": "agent://hermes/core",
          "adoption_count": 42
        },
        "1.1.0": {
          "version": "1.1.0",
          "pack_url": "https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/packs/systematic-debugging.workflow.v1.1.0.yaml",
          "sha256": "def456...",
          "confidence": "tested",
          "tier": "validated",
          "problem_class": "debugging",
          "phase_count": 5,
          "published_at": "2026-03-01T10:00:00Z",
          "author_agent": "agent://hermes/core",
          "adoption_count": 12
        }
      },
      "latest_version": "1.1.0",
      "deprecated": false,
      "tags": ["debugging", "testing", "root-cause"]
    }
  ],
  "total_packs": 1,
  "last_updated": "2026-03-29T12:00:00Z"
}
```

### 3.3 Registry API Endpoints

All endpoints return JSON. Errors use `{"error": "message"}`.

```
GET /v1/index
    Returns: full index JSON (cached 5 min, immutable between TTLs)
    Query params:
      since=<ISO8601>    — return only packs updated after this time
      tag=<tag>          — filter packs by tag
      tier=<tier>        — filter by tier (core|validated|community)
      confidence=<conf>  — filter by confidence (guessed|inferred|tested|validated)
      problem_class=<pc> — filter by problem class (prefix match)
      limit=<n>          — max packs returned (default 100, max 500)
      offset=<n>         — pagination offset

GET /v1/packs/{pack_id}
    Returns: all versions of a specific pack
    Response: { pack_id, source, versions: {...}, latest_version, deprecated, tags }

GET /v1/packs/{pack_id}/versions/{version}
    Returns: metadata for a specific version + signed download URL
    Response: { version, sha256, pack_url, expires_in }

GET /v1/search
    Query params:
      q=<query>          — search term (matches name, problem_class, tags)
      mode=<text|semantic|hybrid>
      limit=<n>          — default 20
    Returns: ranked list of pack versions

GET /v1/sources
    Returns: list of configured pack sources

POST /v1/sync (internal)
    Triggers re-index from configured sources
    Requires: API key header X-Borg-Sync-Key
    Rate limited: once per 5 minutes
```

---

## 4. Distribution Mechanism

### 4.1 Storage: GitHub as CDN

**Current:** Each pack is a `.workflow.yaml` file committed to the repo.

**MVP approach:** Keep GitHub as the canonical store. Packs continue to be committed
as YAML files. The index tracks which files exist and their SHA256 hashes.

```
# Pack file location convention
packs/{pack-id}.workflow.yaml        # latest / canonical
packs/{pack-id}.workflow.v{ver}.yaml # versioned copies (preserved)
```

**Why preserve old versions:**
- Enables reproducibility (agents can pull exact version)
- Enables rollback
- Supports the feedback loop (older executions reference older pack versions)

### 4.2 File Download Flow

```
Agent calls borg pull guild://hermes/systematic-debugging

1. resolve_guild_uri("guild://hermes/systematic-debugging")
   → https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/packs/systematic-debugging.workflow.yaml

2. Fetch index from /v1/packs/hermes/systematic-debugging
   → get latest version info + SHA256

3. Fetch pack YAML from pack_url
   → verify SHA256 matches

4. Save to ~/.hermes/guild/{pack-name}/pack.yaml
```

### 4.3 Index Sync Strategy

The Registry API maintains the index by:

1. **GitHub webhook** (push to main branch): triggers re-index within 30s
2. **Polling fallback** (if webhook fails): agents poll `/v1/index?since=<last_seen>` every 5 min
3. **Agent-local cache**: index cached 5 min, stale-safe (agents always verify SHA256 on pull)

```
┌──────────────┐    push    ┌─────────────────┐
│ GitHub Repo  │ ──────────►│ Registry API    │
│ (guild-packs)│           │ (index builder) │
└──────────────┘           └────────┬─────────┘
                                   │ serves
                                   ▼
                            ┌──────────────┐
                            │ Agent Cache   │
                            │ ~/.hermes/    │
                            │  guild/index │
                            └──────────────┘
```

### 4.4 Scaling Path (Future)

When GitHub alone is insufficient (thousands of agents, millions of packs):

| Component | MVP (0-100 agents) | Growth (100-1K) | Scale (1K-10K+) |
|-----------|-------------------|-----------------|------------------|
| Pack storage | GitHub files | GitHub + S3 backup | S3/GCS + CDN |
| Index | JSON file | PostgreSQL + API | PostgreSQL + read replicas |
| Search | Text + FTS | PostgreSQL FTS + cached vectors | Dedicated search cluster |
| Auth | GitHub token | API keys + GitHub OAuth | Dedicated auth service |

For the MVP, we stay entirely in the left column. The design accommodates migration
to later columns without breaking changes.

---

## 5. Versioning Strategy

### 5.1 Pack Versioning Model

Packs use **Semantic Versioning** (`MAJOR.MINOR.PATCH`):

- **MAJOR**: Breaking change to phases, prompts, or required_inputs
- **MINOR**: New phases, expanded anti_patterns, new failure_cases
- **PATCH**: Bug fixes, clarifications, documentation changes

**Compatibility rules:**
- Agents always pull the latest MINOR by default (patch updates are automatic)
- Major version changes require explicit opt-in (`borg pull pack --version="2.0.0"`)
- The registry tracks which major version ranges are currently "supported"

### 5.2 Version Lifecycle

```
Published → Deprecated → Archived
    │           │
    │           └─ Deprecated: still served, no new adoptions counted
    │              (shown with warning in search results)
    │
    └─ Archived: removed from index, not served (SHA256 still in metadata for audit)
```

### 5.3 Confidence Decay (Advisory)

Per the existing `proof_gates.py` implementation:

| Confidence | Decay TTL | Behavior |
|------------|-----------|----------|
| guessed    | 30 days   | Shown with warning badge |
| inferred   | 90 days   | Shown with warning badge |
| tested     | 180 days  | Normal display |
| validated  | 365 days  | Normal display |

Decay is **advisory only** (does not block usage). Packs auto-upgrade their
confidence to the next tier when re-published with new evidence.

### 5.4 Version Discovery

```
GET /v1/packs/{id}/versions        → list all available versions
GET /v1/packs/{id}/versions/{ver}  → specific version metadata + download URL
```

Agents can pin to a specific version:
```
borg pull guild://hermes/systematic-debugging@1.0.0
```

---

## 6. Authentication Flow for Publishers

### 6.1 Current State

Publishing currently uses the publisher's local `gh` CLI credentials. Any user
with `gh` auth and repo write access can publish. No scoped credentials exist.

### 6.2 MVP Publisher Auth

For the MVP, we implement a **Personal API Token** model:

```
┌──────────────────┐    POST /v1/auth/token    ┌─────────────────┐
│  Publisher       │ ───────────────────────► │  Registry API   │
│  (agent/operator)│                           │                 │
│                  │ ◄───────────────────────  │  - Verify gh    │
│                  │    { token: "gbp_xxx" }   │    token scope  │
└──────────────────┘                           │  - Issue API    │
                                                │    token        │
                                                └─────────────────┘

Publisher then uses:
POST /v1/packs              — submit pack for review
  Header: Authorization: Bearer gbp_xxx
  Body: pack YAML + metadata
```

### 6.3 Token Types

| Token Type | Scope | Lifetime | Use Case |
|------------|-------|----------|----------|
| `gbp_personal` | Full publish + index read | 90 days | Individual publishers |
| `gbp_agent` | Publish from specific agent ID only | 30 days | Automated/CI publishers |
| `gbp_org` | Publish to org-owned namespaces | 1 year | Organization publishers |

### 6.4 Publisher Identity

Each published pack records:

```yaml
provenance:
  author_agent: agent://hermes/core        # agent identity
  author_operator: human@example.com      # human operator (if any)
  published_via: gbp_agent_abc123         # token used
  published_at: 2026-03-29T12:00:00Z
  revision_of: guild://hermes/pack-name@1.0.0  # if update
```

### 6.5 Rate Limiting

Per the existing implementation (`publish.py`):
- **3 publishes per agent per day** (hard limit)
- Feedback submissions: unlimited (part of the feedback loop)

Registry API additional limits:
- **100 API reads per minute** per token (read-heavy workload)
- **10 publishes per day** per token (matches existing gh PR rate limit)

### 6.6 Publisher Namespace

Pack IDs include a namespace prefix to prevent collisions:

```
guild://{namespace}/{pack-name}
```

Valid namespaces:
- `hermes` — project-maintained core packs (restricted)
- `community` — open community packs
- `{github-org}` — org-scoped packs (e.g., `github-acme-corp/my-pack`)

Namespace registration is handled via a lightweight registry config file
(`namespaces.json` in the repo root):

```json
{
  "namespaces": {
    "hermes": { "type": "core", "allowed_authors": ["agent://hermes/*"], "description": "..." },
    "community": { "type": "open", "allowed_authors": ["*"], "description": "..." }
  }
}
```

---

## 7. Distribution Flow Diagrams

### 7.1 Publish Flow (Happy Path)

```
Publisher                              Registry API              GitHub
   │                                        │                       │
   │  borg publish --pack my-pack.yaml     │                       │
   │  ─────────────────────────────────────►│                       │
   │                                        │  Validate YAML schema │
   │                                        │  ────────────────────│
   │                                        │  Check rate limit     │
   │                                        │  ────────────────────│
   │                                        │  Safety scan          │
   │                                        │  ────────────────────│
   │                                        │  Proof gate check     │
   │                                        │  ────────────────────│
   │                                        │                       │
   │                                        │  gh pr create         │
   │                                        │  ────────────────────►│
   │                                        │                       │ PR created
   │                                        │◄─────────────────────│
   │                                        │  PR URL returned      │
   │                                        │                       │
   │  { success: true, pr_url: "..." }     │                       │
   │◄───────────────────────────────────────│                       │
   │                                        │                       │
   [On PR merge]                            │                       │
   │                                        │  Webhook: push to main│
   │                                        │◄──────────────────────│
   │                                        │  Re-index             │
   │                                        │  Update pack listing   │
```

### 7.2 Consumer Pull Flow

```
Agent                              Registry API          GitHub Raw
   │                                     │                    │
   │  borg pull guild://hermes/my-pack  │                    │
   │  ──────────────────────────────────►│                    │
   │                                     │                    │
   │  GET /v1/packs/hermes/my-pack       │                    │
   │  ◄──────────────────────────────────│                    │
   │  { latest_version: "1.2.0",         │                    │
   │    versions: {                      │                    │
   │      "1.2.0": { pack_url, sha256 }  │                    │
   │    } }                              │                    │
   │                                     │                    │
   │  Fetch pack YAML                    │                    │
   │  ───────────────────────────────────│────────────────────►│
   │                                     │    200 OK + YAML    │
   │  ◄──────────────────────────────────│◄────────────────────│
   │                                     │                    │
   │  Verify SHA256 matches              │                    │
   │  Validate schema + safety scan     │                    │
   │                                     │                    │
   │  Save to ~/.hermes/guild/my-pack/  │                    │
   │                                     │                    │
   │  { success: true, path: "..." }    │                    │
```

### 7.3 Search Flow

```
Agent                              Registry API
   │                                     │
   │  borg search "debugging exceptions" │
   │  ──────────────────────────────────►│
   │                                     │
   │  GET /v1/search?q=debugging+exception&mode=text │
   │  ◄──────────────────────────────────│
   │                                     │
   │  { matches: [                       │
   │      { pack_id, version, score,    │
   │        problem_class, confidence,  │
   │        tier, adoption_count },      │
   │      ...                            │
   │    ],                               │
   │    total: 5,                        │
   │    query: "debugging exceptions"    │
   │  }                                  │
   │                                     │
   │  [Agent displays results, user picks one] │
```

---

## 8. API Specification

### 8.1 Index Object

```yaml
Index:
  schema_version: string        # "1.0"
  indexed_at: string            # ISO8601
  sources: Source[]             # configured pack sources
  packs: PackEntry[]            # all known packs
  total_packs: integer
  last_updated: string         # ISO8601

Source:
  source_id: string            # unique identifier
  type: string                 # "github"
  repo: string                 # "owner/repo"
  branch: string               # "main"
  base_url: string             # raw content base URL

PackEntry:
  pack_id: string              # "guild://namespace/name"
  source: string               # source_id reference
  versions: VersionMap         # version -> VersionInfo
  latest_version: string       # semver
  deprecated: boolean
  tags: string[]

VersionInfo:
  version: string              # semver
  pack_url: string             # direct download URL
  sha256: string               # content hash for integrity
  confidence: string           # guessed|inferred|tested|validated
  tier: string                # core|validated|community
  problem_class: string
  phase_count: integer
  published_at: string         # ISO8601
  author_agent: string         # agent identity
  adoption_count: integer     # executions recorded
```

### 8.2 Search Response

```yaml
SearchResponse:
  query: string
  matches: SearchMatch[]
  total: integer
  mode: string                 # text|semantic|hybrid

SearchMatch:
  pack_id: string
  version: string
  problem_class: string
  confidence: string
  tier: string
  adoption_count: integer
  relevance_score: float      # 0.0 - 1.0
  match_type: string          # how it matched (text/semantic)
```

### 8.3 Error Responses

```yaml
ErrorResponse:
  error: string               # human-readable message
  code: string                # machine-readable code
  details: optional object    # additional context

Error Codes:
  PACK_NOT_FOUND        # pack_id does not exist
  VERSION_NOT_FOUND      # specific version does not exist
  RATE_LIMITED           # too many requests
  AUTH_REQUIRED          # missing or invalid token
  VALIDATION_FAILED      # pack YAML failed validation
  SAFETY_BLOCKED         # pack failed safety scan
  PROOF_GATES_FAILED     # pack failed proof gate requirements
```

---

## 9. Implementation Plan

### 9.1 Phases

**Phase 1: Foundation (MVP — 2-3 days)**
- Structured index format (`index.json` v2 with versions)
- Registry API server (stateless, single-file Flask or FastAPI)
- Update `uri.py` to use new index endpoints
- Preserve GitHub as the pack store
- Rate limiting already implemented in `publish.py`

**Phase 2: Auth (1-2 days)**
- API token issuance via `POST /v1/auth/token`
- Token validation middleware on publish endpoints
- Publisher identity recording in pack provenance

**Phase 3: Polish (1-2 days)**
- Deprecation and version lifecycle
- Namespace registration
- Confidence decay warnings in search results
- CLI support for version pinning (`@1.0.0`)

### 9.2 Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `borg/distribution/registry.py` | **Create** | Registry API server (Flask/FastAPI) |
| `borg/distribution/indexer.py` | **Create** | GitHub webhook handler + index builder |
| `borg/distribution/auth.py` | **Create** | Token issuance and validation |
| `borg/distribution/client.py` | **Create** | Client-side index fetching and caching |
| `borg/core/uri.py` | **Modify** | Add version resolution (`@1.0.0` syntax) |
| `borg/core/search.py` | **Modify** | Route through registry API for search |
| `borg/core/publish.py` | **Modify** | Use new auth tokens instead of raw `gh` |
| `borg/cli.py` | **Modify** | Add `borg registry` subcommand |
| `docs/DISTRIBUTION_INFRA_DESIGN.md` | **Create** | This document |

### 9.3 New CLI Commands

```
borg registry serve --port 8080        # Start registry API server
borg registry sync                      # Manually trigger re-index
borg registry tokens create --type personal  # Issue a new token
borg registry tokens revoke <token-id>      # Revoke a token
borg pull guild://hermes/pack@1.0.0    # Pull specific version
```

### 9.4 Test Plan

| Test | Coverage |
|------|----------|
| `test_distribution_registry_search` | Search returns relevant results |
| `test_distribution_registry_versioned_pull` | Specific version is returned |
| `test_distribution_auth_token_issuance` | Valid gh token → gbp token issued |
| `test_distribution_auth_publish_blocked` | Invalid token → 401 |
| `test_distribution_rate_limiting` | Over-limit → 429 |
| `test_distribution_index_sync` | GitHub push → index updated within 30s |
| `test_distribution_sha256_verification` | Downloaded pack matches SHA256 |

---

## 10. Scaling Considerations

### 10.1 Bandwidth

- Each pack YAML: ~5-50 KB
- Index JSON: ~500 KB for 1000 packs
- Agent poll interval: 5 min = 12 req/hour/agent
- At 1000 agents: ~12,000 req/hour = ~3 req/second
- GitHub raw CDN handles this trivially
- Registry API at 3 req/s needs ~minimal resources (512MB VM)

### 10.2 Storage

- Pack storage: GitHub handles this (unlimited for public repos)
- Registry SQLite: ~1MB per 10,000 pack entries (minimal)
- Agent local: each agent stores ~20-50 packs = ~2-5 MB

### 10.3 Failure Modes

| Component | Failure | Impact | Mitigation |
|-----------|---------|--------|------------|
| Registry API | Down | Agents can't search/discover | Fall back to direct GitHub raw + index polling |
| GitHub raw CDN | Down | Agents can't download packs | Already-indexed packs still work from local |
| Webhook | Missed push | Index stale up to 5 min | Polling fallback catches up |
| API token service | Down | No new publishes | Existing gh CLI path still works |

---

## 11. Open Questions

1. **Coordinator Bot**: The Gap Analysis identified this as the #1 blocker for
   external adoption. The MVP auth flow assumes publishers have gh credentials
   directly. A coordinator bot (per the spec) would enable publishers without
   direct gh access. Should we build the coordinator bot before or after MVP?

2. **Private Packs**: No support for private/authenticated-only packs in MVP.
   How should private pack publishing work in the future?

3. **Index Hosting**: MVP uses a single Registry API instance. For HA, we'd
   need multiple instances behind a load balancer. When does that become necessary?

4. **Federation**: The design supports multiple sources but doesn't implement
   guild-to-guild pack sharing. What's the minimal federation story for Phase 2?

---

## 12. Summary

The distribution infrastructure for agent-borg is deliberately minimal for MVP:
- **GitHub as store + CDN** — no new infrastructure, leverages existing assets
- **Thin Registry API** — adds structured queries, auth, and versioning without
  adding operational complexity
- **API token auth** — scoped, revokable, GitHub-OAuth-backed
- **Semver versioning** — enables updates without breaking reproducibility
- **Graceful degradation** — agents fall back to direct GitHub if registry is down

This design grows from zero users to thousands by deferring complexity until
it's actually needed. The critical path for adoption is the coordinator bot
(Gap Analysis finding), not additional infrastructure.
