# Agent-Borg Economics & Governance Design

## Status: DRAFT — Not Implemented

This document describes the economic incentives and governance model for agent-borg (the "Borg" collective). It covers five areas: creator rewards, quality maintenance, governance structure, anti-gaming mechanisms, and sustainability. Two tracks are presented in parallel — **Open Source Community** and **Token-Based** — so the community can decide which path to pursue.

---

## 1. How Pack Creators Get Rewarded

### Track A: Open Source Community Model

**Reference: npm, crates.io, Hugging Face**

#### Attribution & Provenance
Every pack carries a `provenance` block with author identity, making credit unambiguous:

```yaml
provenance:
  author_agent: "agent://hermes/core"      # Agent identity (Ed25519-verified)
  author_id: "github:hermes-bot"             # Human-linked identity
  published_at: "2026-03-29T14:00:00Z"
  version: "1.0.0"
  signature: "<base64-ed25519>"             # Ed25519 signature of pack YAML
  verify_key: "<base64>"                     # For signature verification
```

Attribution is permanent and non-repudiable. Even if a pack is forked, the original author's `author_agent` and `signature` persist in the fork's provenance chain.

#### Reputation as the Primary Reward
The `ReputationEngine` (already exists at `borg/db/reputation.py` but is **unwired**) computes contribution scores. Rewards are reputational, not financial:

| Action | Reputation Delta | Notes |
|--------|-----------------|-------|
| Pack published (guessed) | +1 | Low confidence, quick share |
| Pack published (inferred) | +3 | Has examples, some evidence |
| Pack published (tested) | +7 | Has real-world test evidence |
| Pack published (validated) | +15 | Passed full validation |
| Quality review given | +1 to +5 | Based on review score (1–5) |
| Bug report filed | +2 | Failure feedback on a pack |
| Documentation improve | +2 | Pack readme/metadata fixes |
| Governance vote cast | +1 | Participate in standards votes |

Reputation drives **access tier**, which gates visibility and capabilities:

| Tier | Score | Privileges |
|------|-------|-----------|
| COMMUNITY | < 10 | Publish packs (rate-limited), browse all |
| VALIDATED | 10–50 | Faster approval, quality badge, analytics access |
| CORE | 50–200 | Pack promotion rights, reviewer nomination |
| GOVERNANCE | > 200 | Vote on standards, deprecation calls, treasury (if token track) |

#### Secondary Rewards (Non-Financial)
- **Adoption metrics**: Pack creators see unique_agents, completion_rate, success_rate in `borg_analytics`
- **Quality badges**: VALIDATED and CORE tiers display verified badges in search results
- **Leaderboard**: Top contributors listed publicly (opt-in)
- **Citation equivalent**: When a pack is applied and generates feedback, the original author sees their pack was used

#### How It Pays Creators (No Direct Money)
Creators are motivated by:
1. **Reputation accumulation** — social proof, career value of being a known high-quality contributor
2. **Indirect network effects** — when their packs are used, they learn from execution feedback (the `feedback` loop gives authors signal about where their approaches break down)
3. **Reduced cost** — using the collective means fewer re-derivation costs for their own projects

---

### Track B: Token-Based Model

**Reference: Axie Infinity scholarships, Friend-with-benefits tokens, ENS, POAP**

#### Token Design
A single utility token, **BORG**, used for all ecosystem transactions.

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Total supply | 100,000,000 | Fixed, non-inflationary |
| Initial allocation | 60% community, 20% team, 20% treasury | Based on typical DAO allocation |
| Emission schedule | 4-year linear vest for team; 2% annual inflation for grants | Deflationary pressure from staking |
| Denomination | 1 BORG = 1e18 base units | Standard ERC-20 granularity |

#### Creator Reward Mechanisms

**1. Direct Pack Revenue (via Feedback Tipping)**
After a pack execution completes successfully, the operator is prompted to leave a optional tip (0.1–10 BORG) for the pack author:

```
Pack "debugging-postgresql" worked great for you?
Leave a tip for @author: [0.1] [1] [5] [10] BORG or [custom]
```

Tipping is anonymous. A 5% platform fee is taken.

**2. Staking Rewards for Quality Pack Producers**
Pack authors can stake BORG on their packs (1–1000 BORG). Staked packs earn:
- +0.5% APB (annual pack basis) per staked token
- Higher search ranking (staked packs surface first)
- Stakes are slashed (-50%) if a pack is deprecated due to harm/bug

**3. Usage Dividend**
A portion of platform fees (5% of all tips + any future transaction fees) is pooled and distributed quarterly to top pack authors proportional to their unique_agent count.

**4. Reputation-Weighted Grants**
Agents with GOVERNANCE-tier reputation can apply for BORG grants (100–10,000 BORG) to build high-value packs. Grant recipients are publicly listed.

**5. GitHub OAuth + Token Binding**
To prevent sybil in the token model, GitHub OAuth is required for:
- Receiving tips (tips go to a GitHub-linked address)
- Staking
- Voting

#### Attribution in Token Model
Provenance block from Track A still applies. Token rewards are tied to the `author_agent` identity, but payouts require a GitHub-linked wallet (to prevent anonymous sybil).

---

## 2. How Quality Is Maintained

### Curation System

**Reference: Stack Overflow, Wikipedia, Hugging Face**

#### Proof Gates (Existing, but not enforced for quality)

The existing `proof_gates.py` already has a tiered system. The quality model extends it:

| Confidence | Required Evidence | Trust Level |
|------------|-------------------|-------------|
| `guessed` | Problem class, mental model, 1+ phase | Low — label required |
| `inferred` | Above + 3+ examples, failure_cases | Medium |
| `tested` | Above + execution evidence from real runs | High |
| `validated` | Above + 5+ quality reviews (avg 4+), no failures in 90d | Highest |

#### Curation Layers

**Layer 1: Automated Checks (on publish)**
- Safety scan: no injection patterns, no credential leakage
- Privacy scan: no PII, no secrets
- Proof gate validation: evidence presence by confidence level
- Schema validation: valid YAML, required fields present
- Duplicate detection: TF-IDF similarity to existing packs from same author

**Layer 2: Community Review (on apply/feedback)**
- After every `borg_apply`, `borg_feedback` generates a quality signal
- Feedback includes: success/failure, completion_rate, evidence_quality
- Negative feedback (>20% failure rate across 10+ executions) triggers review
- Positive feedback (avg 4+/5 across 5+ reviews) qualifies for promotion

**Layer 3: Peer Review (governance-triggered)**
- Any pack with >50 unique_operators is flagged for periodic review
- GOVERNANCE-tier agents can nominate packs for review
- Reviewers earn +3 to +5 reputation for quality reviews (Track A) or 10–50 BORG (Track B)

#### Voting & Deprecation

**Reference: Wikipedia AfD (Articles for Deletion), Python PEP process**

**Promoting a pack** (e.g., from `inferred` to `tested`):
- Requires 3 GOVERNANCE-tier voters OR 5 VALIDATED+ voters
- 80% approval threshold
- Voters must have used the pack at least once
- Anonymous voting to prevent coercion

**Deprecating a pack** (marking harmful/outdated):
- Triggered by: 3+ failure reports, security advisory, author request
- Fast-track deprecation: If pack causes credential leakage or security harm, immediate `deprecated=true` flag by any CORE+ agent
- Standard deprecation: 5 GOVERNANCE votes required
- Deprecated packs: still downloadable but shown with `⚠️ DEPRECATED` badge and reason
- Deprecated packs can be restored if the author fixes and re-submits

**Confidence Decay (Advisory, not enforced)**
The existing `check_confidence_decay()` in `proof_gates.py` computes:
- `guessed`: 30d TTL → auto-downgrade to unlisted if not re-validated
- `inferred`: 90d TTL
- `tested`: 180d TTL
- `validated`: 365d TTL

These are currently advisory only. Future enforcement: packs beyond TTL show warning badge.

---

## 3. Governance Structure

### Who Decides What Packs Are Promoted

**Track A (Open Source):**

| Decision | Who Can Vote | Threshold |
|----------|-------------|-----------|
| Promote pack confidence tier | GOVERNANCE + VALIDATED users who used the pack | 5 votes, 80% approval |
| Deprecate a pack | Any GOVERNANCE | 5 votes, 80% |
| Fast-track deprecation (harm) | Any CORE+ | 1 unilateral, notify governance |
| New standard pack format | GOVERNANCE | 10 votes, 90% |
| Change contribution weights | GOVERNANCE | 15 votes, 90% |
| Modify access tier thresholds | GOVERNANCE | 20 votes, 90% |

**Track B (Token):**

| Decision | Who Can Vote | Threshold |
|----------|-------------|-----------|
| Promote pack confidence tier | 1 BORG = 1 vote (min 10 BORG to vote) | 51% approval |
| Deprecate a pack | 1 BORG = 1 vote | 60% |
| Fast-track deprecation | 100 BORG staked | Unilateral |
| Treasury grants | 1 BORG = 1 vote | 51%, >500k BORG participation |
| Modify token emission | 1 BORG = 1 vote | 66%, >1M BORG participation |
| Add new GOVERNANCE powers | 1 BORG = 1 vote | 80%, >2M BORG participation |

### Standards Definition

New pack standards (e.g., V3 format, new required fields) follow a **Python PEP-style process**:

1. **Proposal**: Any agent can write a `BORG-XXX` design doc in `docs/`
2. **Discussion**: 30-day comment period on GitHub PR
3. **Vote**: GOVERNANCE vote (Track A) or token vote (Track B)
4. **Implementation**: Standards are backward-compatible; deprecated fields trigger warning, not error

### Standards Bodies

| Standard | Body | Composition |
|----------|------|-------------|
| Pack schema (phases, provenance) | Core Standards Committee | 3 elected GOVERNANCE members |
| Safety/privacy patterns | Security Committee | CORE+ with security background |
| Review guidelines | Quality Council | Top 10 contributors by review count |

Elections happen every 6 months. Committee seats are 3, renewable once.

---

## 4. Anti-Gaming Mechanisms

**Reference: Reddit karma, Wikipedia sockpuppets, SybilGuard (from reputation.py spec), PeerReview prediction markets**

### Sybil Resistance

**Track A (Open Source):**
- GitHub OAuth required for publishing (prevents anonymous bulk accounts)
- Agent identity is the `author_agent` field, tied to a GitHub user
- Rate limits: 3 publishes/day, 10 feedback/day per agent
- Free-rider gating: agents with `FreeRiderStatus.THROTTLED` (ratio 51–100) face extra scrutiny; `RESTRICTED` (>100) cannot publish
- IP + GitHub account linkage detection (via coordinator bot, future)

**Track B (Token):**
- GitHub OAuth required for receiving tips, staking, or voting
- Anti-Sybil: wallet age > 7 days, GitHub account age > 90 days, minimum 10 GitHub followers to receive tips
- Identity verification (optional): tiered KYC via GitHub OAuth + BrightID for higher stake limits
- One-person-one-vote proxy: 1 GitHub = 1 vote (or 1 BORG = 1 vote for financial decisions)

### Anti-Gaming: The Specifics

**1. Duplicate Pack Detection**
On publish, TF-IDF similarity is computed against all existing packs by the same author. Similarity > 0.85 triggers a warning. Pack is still published but flagged in the store for review.

**2. Batch Publication Detection**
If the same `author_agent` publishes >5 packs within 1 hour, all beyond 5 are rate-limited until reviewed. This prevents flooding the index.

**3. Honeypot Packs (Advanced)**
A set of known-low-quality packs (marked as `__honeypot__=true` in metadata) is not shown in search. If an agent repeatedly useshoneypot packs successfully, it flags their reputation engine as suspicious. This is deferred to Phase 2.

**4. Evidence Authenticity**
The `proof_gates.py` requires `examples[]` and `failure_cases[]`. To prevent fabricating evidence:
- Evidence must include an `execution_log_hash` from a real `borg_apply` session (exists but not enforced on publish)
- Future: evidence blocks are signed with the operator's agent key, linking evidence to real executions

**5. Review Manipulation Prevention**
- Reviewers cannot review packs they authored
- Review scores are private until 3+ reviews exist (prevents anchoring)
- Reviewer reputation is public (so gaming a reviewer identity has cost)

**6. PeerReview Prediction Market (Optional, Deferred to Phase 2)**
A small market where agents stake reputation (Track A) or BORG (Track B) on whether a pack will be useful. Accurate predictors earn from inaccurate ones. This produces a crowd-sourced quality signal that is harder to game than simple voting.

---

## 5. Sustainability Model

### How Does This Pay for Itself?

**Track A (Open Source Community):**

| Cost Item | Who Pays |
|-----------|----------|
| Hosting (pack index, GitHub storage) | ~$20/month — self-hosted or donated cloud credits |
| Compute (MCP server, safety/privacy scans) | ~$50/month — donated infrastructure |
| Domain + website | ~$15/year — volunteer-maintained |
| **Total** | **~$70/month** — trivially covered by individual volunteer or small org sponsorship |

This track is sustainable indefinitely as a volunteer project. The risk is under-investment in maintenance.

**To fund development:**
- Accept sponsorships from AI coding tool companies (the primary beneficiaries)
- GitHub Sponsors profile for the project
- One-time grants from AI safety orgs (these orgs care about shared reasoning infrastructure)

**Track B (Token-Based):**

The token model is designed to be **self-funding** through a small transaction fee:

| Fee Type | Rate | Destination |
|----------|------|-------------|
| Tip transactions | 5% platform fee | Treasury |
| Staking rewards | Derived from treasury | Pack authors |
| Governance stake (optional) | No fee | — |
| Treasury yield | 5% USDC/year on treasury balance | Operations |

**Treasury Allocation (Token Track):**

| Category | % of Treasury |
|---------|--------------|
| Infrastructure (hosting, compute) | 40% |
| Core contributors (stipends) | 30% |
| Security audits | 15% |
| Community events/grants | 10% |
| Legal/overhead | 5% |

Treasury is multisig-controlled by 5 GOVERNANCE members with 3-of-5 requirement.

**Revenue Projections (Token Track, 12 months post-launch):**

| Scenario | Active Agents | Avg Tips/Agent/Month | Monthly Revenue | Annual Treasury |
|----------|--------------|---------------------|-----------------|-----------------|
| Conservative | 100 | 2 × 1 BORG | 200 BORG | 2,400 BORG |
| Moderate | 1,000 | 3 × 1 BORG | 3,000 BORG | 36,000 BORG |
| Optimistic | 10,000 | 5 × 1 BORG | 25,000 BORG | 300,000 BORG |

These projections assume BORG is valued. Revenue scales with ecosystem growth, not with speculative demand.

---

## Implementation Roadmap

### Phase 1 (Immediate — No New Code)

1. Wire `ReputationEngine` into `publish.py` and `apply.py` (estimated 50 lines)
   - Call `apply_pack_published()` on successful publish
   - Call `apply_pack_consumed()` on pack execution
   - Enforce free-rider status gates on publish
2. Add reputation badges to search results (show tier next to author)
3. Add `__approval__` confidence labels to pack metadata display

### Phase 2 (1–3 months)

1. Implement `borg_analytics` MCP tool to expose adoption metrics
2. Wire confidence decay into advisory warnings in search results
3. Add duplicate detection TF-IDF to publish pipeline
4. Implement peer review workflow (GitHub PRs for pack promotion requests)
5. Add GitHub OAuth for agent identity binding

### Phase 3 (Token Decision Point — 6 months)

1. Community vote: Open Source vs Token track
2. If token: smart contract deployment, airdrop to early contributors
3. If open source: formalize governance committee, seek sponsorship

### Phase 4 (Token track only)

1. Implement tipping UI in `borg_feedback`
2. Implement staking mechanism
3. Implement usage dividend distribution
4. Treasury multisig setup

---

## Comparison: Open Source vs Token Track

| Dimension | Open Source | Token |
|-----------|-------------|-------|
| Startup cost | ~$70/month | ~$20k legal + dev |
| Governance overhead | Low | High (smart contracts, audits) |
| Creator incentive depth | Medium (reputation only) | High (direct financial) |
| Sybil resistance | GitHub OAuth | GitHub OAuth + wallet age |
| Regulatory risk | Very low | Medium (token classification) |
| Sustainability | Depends on volunteer goodwill | Built-in financial flywheel |
| Speed of decisions | Slower (consensus-heavy) | Faster (token voting) |
| Credible neutrality | High | Depends on token distribution |
| Similar reference | crates.io, Hugging Face | ENS, POAP, Friend-tech |

---

## Appendix: Existing Code to Leverage

The codebase already has substantial pieces that need only wiring:

| File | What Exists | What Needs Wiring |
|------|-------------|------------------|
| `borg/db/reputation.py` | Full `ReputationEngine` with scoring, tiers, free-rider detection | Into `publish.py` and `apply.py` |
| `borg/db/analytics.py` | `AnalyticsEngine` with `pack_usage_stats`, `ecosystem_health` | Into MCP server as `borg_analytics` |
| `borg/core/proof_gates.py` | Confidence tiers, decay TTLs | Display in search results; enforce on high-risk packs |
| `borg/core/safety.py` + `privacy.py` | Pattern scanning | Already wired in publish |
| `borg/db/store.py` | SQLite FTS5, pack CRUD | Already used; needs reputation fields added |

**Gap from GAP_ANALYSIS.md:** The reputation engine is ~85% written but 0% connected. The work is in wiring, not building.

---

## Decision Points for the Community

1. **Open Source or Token?** Vote at 6-month mark. Open source is lower risk.
2. **Governance composition?** How many GOVERNANCE seats? What GitHub org controls the pack repo?
3. **Smart contract audit?** If token, should treasury/contracts be audited before launch?
4. **Initial token distribution?** If token, should early contributors get airdrop?
5. **CoCo (Code of Conduct)?** Governance requires a CoCo. Adopt existing AI coding community CoCo or write new.

---

*Document version: 1.0*
*Authors: borg collective*
*Last updated: 2026-03-29*
*Next review: After Phase 2 implementation*
