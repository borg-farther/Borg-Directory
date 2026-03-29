# Agent-Borg Federation Protocol — Design Document

**Author:** Subagent (Federation Design)
**Date:** 2026-03-29
**Status:** Design — not yet implemented
**Supersedes:** Collective Prompt Intelligence Design (R001, §Propagation Layer); Distribution Infrastructure Design (federation extensions)
**Goal:** Independent borg instances running on different agents, possibly across organizations, discover each other and exchange packs with consent, privacy, and conflict resolution.

---

## 1. Overview and Motivation

### 1.1 The Federation Problem

Today, borg is single-node: every agent maintains its own local pack store. The collective intelligence loop is closed within a single deployment. Federation opens that loop across organizational and agent boundaries:

> Agent A at Company X discovers a useful debugging pattern → it propagates (with consent and privacy controls) to Agent B at Company Y.

This is email-like federation but for agent knowledge. It requires:

1. **Peer discovery** — nodes finding each other without a central directory
2. **Pack exchange** — transferring packs with integrity and provenance
3. **Trust establishment** — deciding which federated nodes are safe to receive packs from
4. **Conflict resolution** — when the same pack has diverged on two nodes
5. **Partial sharing** — sharing some packs while keeping others private

### 1.2 Design Principles

- **Consent at every layer**: nodes explicitly opt in to federate, and per-pack sharing policies are respected
- **Privacy by default**: packs are scanned for PII before export; raw execution logs never leave the node
- ** Decentralization**: no single coordinator; federation is peer-to-peer with gossip-based discovery
- **Incremental adoption**: works between two nodes; scales to thousands without architecture changes
- **Leverage existing work**: reuse the existing safety scanner, proof gates, privacy layer, and pack schema

### 1.3 Reference Protocols

| Protocol | Relevant Mechanism | Applicable to Borg Federation |
|----------|-------------------|------------------------------|
| **ActivityPub** (W3C) | Actor model, federated delivery, JSON-LD @context, public/followers collections | Peer addressability via URIs, inbox/outbox delivery |
| **AT Protocol** (Bluesky) | Repo model (Merkle DAG), DIDs for identity, CAR files for batch transport, PDE for personal data servers | Content-addressed pack bundles (CAR), DID-based node identity |
| **IPFS** | Content-addressed blobs, libp2p for routing, Kademlia DHT for discovery | Pack content addressing via CID, DHT peer discovery |
| **Scuttlebutt** | Gossip protocol, feeds with timestamps, CRDT merge | Pack version vectors, conflict-free replicated state |

Borg federation is not a full implementation of any one protocol. Instead, it borrows the most applicable mechanisms from each:

- **From AT Protocol**: DID-based node identity, CAR-file batch transport, repo-style pack bundles
- **From ActivityPub**: actor/inbox model, follow/request model, public vs targeted delivery
- **From IPFS**: CID content addressing for pack integrity, DHT-inspired peer routing table
- **From Scuttlebutt**: version vectors for conflict detection, gossip-based sync

---

## 2. Architecture

### 2.1 Federation Layer Components

```
borg/
├── federation/                    # NEW: Federation layer
│   ├── __init__.py
│   ├── identity.py               # Node identity (DID + signing key)
│   ├── discovery.py               # Peer discovery (gossip DHT)
│   ├── transport.py              # Secure transport (HTTPS + signatures)
│   ├── sync.py                   # Pack sync protocol (push/pull/gossip)
│   ├── trust.py                  # Web-of-Trust, reputation, access policies
│   ├── conflict.py               # CRDT-based conflict resolution
│   ├── sharing.py                # Per-pack sharing policies
│   ├── car_bundle.py             # CAR file pack bundle creation/parsing
│   └── federation_store.py       # SQLite tables for federation state
```

### 2.2 High-Level Data Flow

```
Agent A                          Agent B
   │                                │
   │  [Borg Instance]               │  [Borg Instance]
   │       │                              │
   │       ▼                              │
   │  ┌─────────────────┐                 │
   │  │ Local Pack Store │◄──── Gossip ────►│ Local Pack Store
   │  └────────┬────────┘                 │
   │           │ Pack exchange             │
   │           │ (CAR bundle over HTTPS)   │
   │           ▼                          │
   │  ┌─────────────────┐                 │
   │  │ Federation Store│                 │
   │  │ (peers, policies,│                 │
   │  │  version vectors)│                 │
   │  └─────────────────┘                 │
   │       │                              │
   │       ▼                              │
   │  [Trust Layer] ──── DIDComm ────► [Trust Layer]
   └──────────────────────────────────────────────┘
```

### 2.3 Federation URI Scheme

Federation introduces a new URI scheme for referencing federated packs:

```
borg://{node_did}/{pack_id}@{version}
```

Examples:
```
borg://did:web:agent-hermes.example.com/hermes/systematic-debugging@v1.2.0
borg://did:web:agent-corp-x.acme.com/acme/security-review@v2.0.0
```

The `borg://` scheme is distinct from `guild://` (which resolves to the centralized guild-packs GitHub repo). A federated pack can also have a `guild://` equivalent if it has been published to the central index.

---

## 3. Peer Discovery Mechanism

### 3.1 Requirements

- Nodes must discover each other without a central directory
- Discovery must work across organizational boundaries (no corporate network assumptions)
- Nodes must be able to specify who they want to connect with (allowlist) and who they want to block (denylist)
- Discovery metadata must be minimal (DID + endpoint + reputation score only)

### 3.2 Approach: Hybrid Gossip DHT

Borg uses a **hybrid gossip DHT** inspired by IPFS Kademlia and SSB feeds:

**Seed nodes**: On first launch, a node is configured with 2–3 seed node DIDs (hardcoded or provided via CLI flag `--federation-seeds`). These are well-known nodes (e.g., `did:web:borg-commons.example.com`) that maintain a public registry of active nodes. This is purely for bootstrap — once a node has peers, it no longer needs seeds.

**Kademlia-style routing table**: Each node maintains a routing table of up to 256 peers, organized by the XOR distance of their DIDs. This enables efficient lookups: to find a specific node or pack owner, a node traverses the DHT by XOR distance.

**Gossip broadcast**: Periodically (every 5 minutes), each node gossips its presence to 3–5 randomly selected peers. The gossip message includes:

```json
{
  "type": "gossip.presence",
  "did": "did:web:agent-hermes.example.com",
  "endpoint": "https://agent-hermes.example.com/borg-federation",
  "rep_score": 0.85,
  "timestamp": "2026-03-29T12:00:00Z",
  "packs_summary": {
    "total": 42,
    "shared": 12,
    "problem_classes": ["debugging", "code-review", "testing"]
  }
}
```

`packs_summary` is intentionally coarse — a list of problem classes, not pack IDs. This enables targeted discovery (find me nodes that have debugging packs) without revealing which specific packs a node has.

**Targeted discovery flow**:

```
Agent A wants packs about "security-review"
  1. A sends discovery query to its known peers:
     GET /federation/discover?problem_class=security-review
  2. Each peer that has matching packs responds with:
     { "did": "...", "endpoint": "...", "rep_score": 0.9 }
  3. A also propagates the query to peers' peers (2 hops max)
  4. A collects responses, filters by rep_score threshold, and
     initiates pack exchange with the best candidates
```

### 3.3 Node Identity (DID-Based)

Every federated borg node has a **DID (Decentralized Identifier)** using the `did:web` method:

```
did:web:{hostname}
```

For example, `did:web:agent-hermes.example.com` resolves to `https://agent-hermes.example.com/.well-known/did.json`.

The DID document contains:

```json
{
  "@context": "https://www.w3.org/ns/did/v1",
  "id": "did:web:agent-hermes.example.com",
  "verificationMethod": [{
    "id": "did:web:agent-hermes.example.com#signing-key",
    "type": "Ed25519VerificationKey2020",
    "controller": "did:web:agent-hermes.example.com",
    "publicKeyMultibase": "zH3C2AVvLMv6gmMNamoiuota6G5mzV9qL..."
  }],
  "service": [{
    "id": "did:web:agent-hermes.example.com#borg-federation",
    "type": "BorgFederationEndpoint",
    "serviceEndpoint": "https://agent-hermes.example.com/borg-federation"
  }]
}
```

This is the **signing key** used to sign pack bundles and federation messages. The corresponding private key is stored locally (never transmitted).

### 3.4 Peer Authorization

Before accepting any federation message from a peer, a node verifies:

1. **Signature**: the message is signed with the peer's signing key (verified via DID document)
2. **Timestamp**: the message timestamp is within 5 minutes of the current time (replay protection)
3. **Allowlist**: the peer's DID is on the node's allowlist (if configured)
4. **Denylist**: the peer's DID is not on the node's denylist
5. **Reputation gate**: the peer's `rep_score` meets the node's minimum threshold (default: 0.5)

These checks are applied before any pack data is processed.

---

## 4. Pack Exchange Protocol

### 4.1 Pack Bundle Format (CAR Files)

Packs are transferred between nodes as **CAR (Content Addressable aRchive) files**, borrowed from the AT Protocol. A CAR file is a binary container holding:

- **Header**: CAR version, root CID
- **Blocks**: serialized DAG nodes (pack metadata + content), each addressed by CID
- **Proof chain**: a compact proof that the pack passed proof gates (for trust verification)

The CAR format is used because:
- Content addressing (CID) ensures pack integrity without trusting the transport
- DAG structure enables partial sync (only fetch the blocks you need)
- Compact encoding (protobuf) is more efficient than JSON for large pack bundles

A pack CAR file contains:

```
CAR v1
└── Root: CID(pack_metadata)
    ├── Block: CID(pack_metadata) — JSON with id, version, problem_class, sharing_policy
    ├── Block: CID(pack_v2.yaml) — raw YAML content (UTF-8)
    ├── Block: CID(safety_proof.json) — proof of safety scan result
    ├── Block: CID(provenance_proof.json) — proof of confidence tier
    └── Block: CID(signature.json) — Ed25519 signature over root CID
```

### 4.2 Exchange Flow

**Happy path — pull model** (Agent B pulls from Agent A):

```
Agent B                          Agent A (Agent B's peer)
   │                                    │
   │  GET /federation/packs?q=debugging │
   │  &since=2026-03-20               │
   │  ──────────────────────────────────►│
   │                                    │ 200 OK: pack index (CID list)
   │  ◄─────────────────────────────────│
   │                                    │
   │  POST /federation/fetch            │
   │  Body: { cids: [cid1, cid2] }
   │  ──────────────────────────────────►│
   │                                    │ 200 OK: CAR file binary
   │  ◄─────────────────────────────────│
   │                                    │
   │  [Verify CAR blocks]
   │  [Verify signatures]
   │  [Safety scan on each pack]
   │  [Apply sharing policy filters]
   │                                    │
   │  Store to local pack store          │
```

**Push model** (Agent A pushes to Agent B, used for live propagation of high-value insights):

```
Agent A                          Agent B
   │                                    │
   │  POST /federation/inbox            │
   │  Header: Authorization: Bearer ... │
   │  Body: CAR file binary             │
   │  ──────────────────────────────────►│
   │                                    │
   │  [Verify sender signature]
   │  [Verify rep_score meets threshold]
   │  [CAR block verification]
   │  [Safety scan]
   │  [Sharing policy check]
   │  [CRDT merge — see §6]             │
   │                                    │
   │  202 Accepted or 409 Conflict       │
   │  ◄─────────────────────────────────│
```

### 4.3 Pack Index and Sync

Each node maintains a **pack index** of all packs it knows about (local + federated), with version vectors:

```json
{
  "pack_id": "hermes/systematic-debugging",
  "owner_did": "did:web:agent-hermes.example.com",
  "latest_version": "1.2.0",
  "sharing_policy": "followers",
  "versions": {
    "1.0.0": { "cid": "Qm...", "published_at": "2026-01-15T10:00:00Z" },
    "1.1.0": { "cid": "Qm...", "published_at": "2026-02-20T14:30:00Z" },
    "1.2.0": { "cid": "Qm...", "published_at": "2026-03-29T08:00:00Z" }
  },
  "version_vector": {
    "did:web:agent-hermes.example.com": 3,
    "did:web:agent-corp-x.acme.com": 1
  }
}
```

**Version vectors** (from Scuttlebutt/CRDT literature) track how many updates each node has seen from each peer. This enables efficient sync: a node can ask a peer "what's changed since version N on your node?" rather than re-fetching everything.

### 4.4 REST API Endpoints (Federation)

All federation API endpoints are under `/borg-federation/` on the node's web endpoint:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/federation/nodeinfo` | Node capabilities, DID, reputation score |
| GET | `/federation/discover` | Discover peers by problem_class or keyword |
| GET | `/federation/packs` | List packs available from this node (filtered by requester's access) |
| POST | `/federation/fetch` | Fetch specific pack CIDs as a CAR file |
| POST | `/federation/inbox` | Receive a pushed pack bundle (ActivityPub inbox model) |
| POST | `/federation/sync` | Bidirectional sync: exchange version vectors, receive missing packs |
| GET | `/federation/policy` | Get this node's sharing policy |
| PUT | `/federation/policy/packs/{pack_id}` | Update sharing policy for a specific pack |

Authentication: all endpoints require a signed request (`Authorization: Bearer <node_jwt>`). The JWT is signed by the requesting node's signing key and includes the node's DID and current timestamp.

---

## 5. Trust Establishment

### 5.1 Trust Model

Trust in borg federation is **graduated and bidirectional**:

- **Zero trust by default**: a node does not accept packs from an unknown peer until trust is explicitly established
- **Reputation-as-trust**: a node's `rep_score` (0.0–1.0) reflects its reliability based on observed behavior
- **Web-of-Trust**: a node's trust in a peer can be informed by what trusted other peers think of that peer

### 5.2 Reputation Score

Each node computes a `rep_score` for itself (local reputation) and observes scores for peers (remote reputation):

```
rep_score = (adoption_weight * adoption_score)
           + (quality_weight * quality_score)
           + (longevity_weight * longevity_score)
           - (penalty_weight * penalty_score)
```

Components:
- **adoption_score** (0.0–0.35): how many other nodes have pulled this node's shared packs
- **quality_score** (0.0–0.30): based on feedback from packs — if agents report success after using this node's packs, score increases
- **longevity_score** (0.0–0.20): how long the node has been active (nodes that disappear after sharing low-quality packs are penalized)
- **penalty_score** (0.0–1.0): increments when a node shares a pack that fails safety scan, has PII, or is a duplicate/garbage submission

The weights are configurable (default: 0.35/0.30/0.20/0.15). Scores are gossiped alongside presence updates.

### 5.3 Trust Establishment Flow

**Handshake** (first time Node B connects to Node A):

```
Node B                          Node A
   │                                │
   │  GET /.well-known/did.json    │
   │  ◄─────────────────────────────│  (Fetch Node A's DID doc)
   │                                │
   │  POST /federation/connect      │
   │  Body: { did: "did:web:agent-b...",
   │          endpoint: "https://...",
   │          rep_score: 0.7,
   │          signed_challenge }    │
   │  ─────────────────────────────►│
   │                                │
   │                                │  [Verify signature]
   │                                │  [Check denylist/allowlist]
   │                                │  [Verify rep_score ≥ threshold]
   │                                │
   │  200 OK: { status: "peers",
   │            peer_list: [...] }  │
   │  ◄─────────────────────────────│
   │                                │
   │  [Store Node A as trusted peer]│
```

After the handshake, both nodes add each other to their peer list and can exchange packs.

### 5.4 Trust Chains

For organizational compliance, borg supports **trust chains**: an organization can designate a **trust anchor** (a well-known node operated by the org or a trusted third party). All org agents configure their borg instances to trust the anchor, and the anchor can certify other nodes:

```
Org Trust Anchor
  └── certifies --> Agent A (employee)
  └── certifies --> Agent B (employee)
  └── certifies --> External Partner Node (via manual approval)
```

Certification is a signed message: `{ "certifier": "did:web:corp.example.com", "certified": "did:web:partner-x.example.com", "scope": ["debugging", "code-review"], "expires": "2027-01-01" }`

This is analogous to TLS certificate chains and X.509 CA certificates.

### 5.5 Access Policies

Each node enforces two access policies:

**Node-level policy**:
- `federation_mode`: `open` | `allowlist` | `denylist`
- `min_rep_score`: minimum reputation score to accept packs from (default 0.3)
- `allowed_problem_classes`: list of problem classes this node will federate about (default: all)

**Pack-level policy** (per pack, set by the pack owner):
- `sharing_policy`: `public` | `followers` | `private` | `org-only`
  - `public`: anyone can pull
  - `followers`: only nodes that have followed this node can pull
  - `private`: not shared via federation (local-only)
  - `org-only`: only nodes within the same org trust chain can pull

The `followers` model mirrors ActivityPub: a node "follows" another node by sending a follow request. The followed node accepts or rejects the request. Accepted follows are stored in the node's `followers` collection.

---

## 6. Conflict Resolution

### 6.1 When Conflicts Occur

A conflict occurs when the same `pack_id` has been modified on two or more nodes independently, and those modifications are then propagated. This can happen when:

1. Two different agents create packs with the same ID
2. The same pack is edited on two nodes (e.g., an agent improves a community pack locally)
3. A pack is updated on the canonical guild-packs repo and also modified locally

### 6.2 Conflict Detection

Borg uses **version vectors** (as described in §4.3) to detect conflicts. When a node's version vector shows that two peers have both updated a pack since last sync, a conflict is flagged:

```
Conflict detected for pack_id="acme/security-scan":
  - Node A (did:web:a.example.com): version 2 updates (last: v1.1.0, 2026-03-28)
  - Node B (did:web:b.example.com): version 1 update (last: v1.0.1, 2026-03-29)
  - Common ancestor: v1.0.0
```

### 6.3 Resolution Strategy: CRDT Merge with Owner Priority

Borg uses a **CRDT-inspired merge strategy** with the following precedence rules:

**Rule 1 — Content-addressed wins for identical content**:
If two versions produce the same CID (i.e., the YAML content is identical after normalization), they are the same pack. No conflict — just deduplicate.

**Rule 2 — Later timestamp + higher reputation wins for different content**:
If the two versions differ, the version with:
1. the later `provenance.updated_at` timestamp, AND
2. the node with the higher `rep_score`
...is selected as the canonical version. The losing version is stored as an **alternate**.

**Rule 3 — Owner authority for org-owned packs**:
If a pack has `namespace` matching an organization's claimed namespace (via trust chain certificate), that organization's nodes have priority over external nodes for that pack.

**Rule 4 — User override**:
If an agent has manually edited a pack locally, their local version takes precedence over any federated update. The agent can manually resolve by choosing which version to keep.

### 6.4 Conflict Metadata

When a conflict is detected, both versions are stored alongside a conflict record:

```json
{
  "pack_id": "acme/security-scan",
  "conflict_id": "conf_abc123",
  "detected_at": "2026-03-29T12:00:00Z",
  "versions": [
    {
      "source_did": "did:web:a.example.com",
      "version": "v1.1.0",
      "cid": "QmX...",
      "rep_score": 0.8,
      "provenance.updated_at": "2026-03-28T10:00:00Z"
    },
    {
      "source_did": "did:web:b.example.com",
      "version": "v1.0.1",
      "cid": "QmY...",
      "rep_score": 0.65,
      "provenance.updated_at": "2026-03-29T08:00:00Z"
    }
  ],
  "resolution": "pending",
  "selected_version": null
}
```

The agent is notified of unresolved conflicts via `borg list --conflicts`. They can resolve with:
```
borg resolve acme/security-scan --select=v1.1.0
```

### 6.5 Gang-Avoidance (Anti-Entropy)

To prevent garbage/proliferation attacks (where a malicious node floods the network with fake pack updates), borg implements:

- **Minimum rep_score gate**: packs from nodes with rep_score < 0.2 are not propagated
- **Maximum propagation fan-out**: a single pack version can be forwarded to at most 10 peers per hour (rate-limited)
- **Cross-reference validation**: when a pack is received from a peer, it is cross-referenced against the pack's provenance chain. If the pack claims to be "validated" confidence but has no corresponding proof_gate evidence, the pack is downgraded or rejected

---

## 7. Partial Sharing

### 7.1 Per-Pack Sharing Policies

The core of partial sharing is the **sharing policy** on each pack:

```yaml
sharing:
  policy: public          # public | followers | private | org-only
  allowed_dids: []        # optional: explicit list of DIDs allowed (for custom)
  excluded_dids: []       # optional: explicit list of DIDs blocked
  allowed_orgs: []        # org trust anchors allowed to access (for org-only)
  federate_versions: ["*"] # which versions can be shared (default: all)
```

When `policy: private`, the pack is never included in any federation response, not even in the pack index. The local node behaves as if the pack does not exist for federation purposes.

### 7.2 Selective Sync

Beyond per-pack policies, nodes can configure **selective sync** at the node level:

```
borg federation sync --policy=problem_class:debugging,code-review
borg federation sync --exclude=namespace:hermes/core
borg federation sync --only=did:web:trusted-partner.example.com
```

This filters which packs are pulled from or pushed to the federation, independent of the pack's own sharing policy. Useful for:
- Organizations that only want debugging-related packs
- Bandwidth-constrained agents that cannot sync everything
- Security-sensitive environments that limit incoming pack sources

### 7.3 Minimal Disclosure

Borg federation is designed to minimize information disclosure:

1. **Pack index queries** only return packs the requester is authorized to see (based on sharing policy + trust chain)
2. **Problem-class discovery** reveals only the coarse problem_class list, not individual pack IDs
3. **Reputation scores** are public but raw adoption/quality data is aggregated
4. **Execution logs are never shared** — only pack content and metadata
5. **PII scan runs locally** before any pack is shared; only packs that pass are exported

---

## 8. Security Considerations

### 8.1 Threat Model

| Threat | Mitigation |
|--------|-----------|
| Malicious pack injection | Safety scan + privacy scan run locally before any pack is shared; signed CAR bundles |
| Replay attacks | Timestamp validation (5-min window) on all federation messages |
| Spoofed DID | DID document fetched via HTTPS; signing key verified against DID doc |
| Pack tampering in transit | CAR CID verification — any block with wrong CID is rejected |
| Denial of service | Rate limiting on all federation endpoints (10 req/min per peer) |
| Garbage/proliferation | rep_score gate + anti-entropy checks + maximum fan-out |
| Privacy leakage via discovery | Problem-class-only queries; no pack ID disclosure without auth |
| Org data exfiltration | `org-only` sharing policy; trust chains; selective sync |

### 8.2 Signing and Verification

Every CAR file is signed by the sharing node's Ed25519 signing key. The signature is stored in the CAR header:

```json
{
  "type": "application/vnd.ipfs.car",
  "version": 1,
  "root_cid": "Qm...",
  "signature": "base64(Ed25519 signature of root_cid)",
  "signer_did": "did:web:agent-hermes.example.com",
  "signed_at": "2026-03-29T12:00:00Z"
}
```

On receipt, the signature is verified:
1. Resolve `signer_did` to DID document
2. Verify DID document has not been revoked (check `alsoKnownAs` or rotation evidence)
3. Verify signature using the `verificationMethod` in the DID doc

### 8.3 Privacy Gates

Before any pack is shared, it must pass:

1. **Privacy scan** (existing `privacy.py`): all text fields checked for PII patterns. If any PII is detected (even if redacted), the pack is flagged `privacy_flags` and may be blocked from federation based on policy
2. **Safety scan** (existing `safety.py`): 13 injection patterns checked. Any match results in `safety_flags` being set
3. **Federation-specific check**: the pack's `sharing.policy` must not be `private`

These checks run locally before any pack leaves the node. No remote node ever sees an unscanned pack.

---

## 9. Comparison with Related Protocols

### 9.1 Borg Federation vs. ActivityPub

| Aspect | ActivityPub | Borg Federation |
|--------|------------|----------------|
| Identity | ActivityStreams Actors (HTTP(S) URLs) | DID (did:web) |
| Content model | Objects (JSON-LD) | Workflow Packs (YAML + CAR) |
| Delivery | Inbox/outbox, public collections | CAR bundles via REST |
| Trust | OAuth 2.0 + followers | DID signatures + Web-of-Trust |
| Discovery | WebFinger | Gossip DHT + seed nodes |
| Conflict handling | Last-write-wins (server-side) | CRDT-inspired + owner priority |

### 9.2 Borg Federation vs. AT Protocol

| Aspect | AT Protocol | Borg Federation |
|--------|------------|----------------|
| Identity | DID (multiple methods) | DID (did:web) |
| Repo structure | DAG of records (repo) | Pack index + version vectors |
| Transport | HTTPS (XRPC) + WebSocket | REST over HTTPS + CAR files |
| Sync | Repo sync with blob exchange | Bidirectional version vector sync |
| Data type | Generic records | Workflow packs (YAML) |
| Trust | AppBsky ( Bluesky) PDS model | Web-of-Trust + trust chains |

### 9.3 Borg Federation vs. IPFS

| Aspect | IPFS | Borg Federation |
|--------|------|----------------|
| Content addressing | CID v1 (multihash) | CID v1 (same) |
| Routing | Kademlia DHT | Hybrid gossip DHT |
| Transport | libp2p | HTTPS REST |
| Data model | Arbitrary blobs | Workflow packs + CAR bundles |
| Trust | None (content-addressed only) | DID signatures + rep_score |
| Partial sharing | N/A (all content public) | Sharing policies per pack |

### 9.4 Borg Federation vs. Scuttlebutt

| Aspect | Scuttlebutt | Borg Federation |
|--------|------------|----------------|
| Identity | Feed ID (Ed25519 key) | DID (did:web) |
| Sync | Gossip with vector clock | Version vectors + CAR sync |
| Conflict resolution | CRDT (automatic) | CRDT-inspired + owner priority |
| Content type | Markdown messages | Workflow packs (YAML) |
| Trust | Manual following | Web-of-Trust + trust chains |

---

## 10. Migration Path from Current Architecture

### 10.1 Current State

Today, borg federation is not implemented. The existing `DISTRIBUTION_INFRA_DESIGN.md` describes a centralized model:
- Single GitHub repo as canonical store
- `guild://` URIs resolve to GitHub raw URLs
- No peer-to-peer exchange

### 10.2 Migration Steps

**Phase 1 (Federation MVP — two nodes)**:
- Implement node identity (DID + signing key)
- Implement basic HTTPS REST endpoints for pack exchange
- Implement CAR bundle creation/parsing
- Manual peer configuration (no DHT, just two nodes configured to trust each other)

**Phase 2 (Trust + Discovery)**:
- Implement Web-of-Trust scoring
- Implement gossip presence + discovery queries
- Implement sharing policies (public/followers/private)
- Implement version vectors for sync

**Phase 3 (Conflict Resolution + Selective Sync)**:
- Implement CRDT conflict detection + resolution
- Implement selective sync filters
- Implement trust chains for orgs
- Implement anti-entropy / gang-avoidance

**Phase 4 (Scale)**:
- DHT bootstrap nodes become configurable seed nodes
- Support for `did:key` in addition to `did:web`
- Federation gateway for browsers/clients that cannot run full nodes

### 10.3 Backward Compatibility

- `guild://` URIs continue to work as before (centralized guild-packs GitHub repo)
- `borg://` URIs are introduced for federated pack references
- A pack can have both a `guild://` canonical ID and federated `borg://` references
- The existing safety scanner, proof gates, and privacy layer are reused without modification

---

## 11. Open Questions and Future Work

1. **Incentive design**: What encourages nodes to share packs? Currently purely altruistic. Future: reputation scores could unlock access to higher-quality packs from others (a kind of "pack karma").

2. **Anonymous federation**: Can an agent federate without revealing its DID? Options: `did:key` with rotation, ZK proofs of rep_score. This is a future enhancement.

3. **Pack migration across orgs**: When an employee leaves, what happens to their locally-developed packs? Should they be transferable to the org's namespace? This requires a pack transfer protocol.

4. **Commercial pack licensing**: How do pack authors indicate license terms (MIT, proprietary, etc.)? This requires a license field in the pack schema and federation-level license enforcement.

5. **Federation with ActivityPub**: Could borg packs be published as ActivityPub objects, enabling borg to federate with Mastodon-style social graphs? This is a speculative future integration.

6. **IPFS as optional transport**: For very large pack bundles, IPFS could serve as a backend blob store with borg using CAR files as the IPLD graph. This would reduce server bandwidth costs at scale.

---

## 12. Summary

Borg federation enables independent borg instances to discover each other and exchange packs across organizational boundaries. The design:

1. **Peer discovery**: Hybrid gossip DHT with DID-based node identity. Seed nodes bootstrap; Kademlia-style routing enables efficient peer lookup; coarse-grained discovery queries prevent information leakage.

2. **Pack exchange**: CAR (Content Addressable aRchive) files over HTTPS REST. CAR format provides content integrity (CID verification) and efficient partial sync. Mirrors AT Protocol's repo exchange model.

3. **Trust establishment**: Graduated Web-of-Trust with rep_score. DID signatures verify peer identity. Trust chains enable organizational hierarchies. Allowlist/denylist/min_rep_score controls give node operators fine-grained access control.

4. **Conflict resolution**: Version vectors detect conflicts; CRDT-inspired merge with owner priority + timestamp + reputation precedence resolves them. Manual override available.

5. **Partial sharing**: Per-pack sharing policies (`public`, `followers`, `private`, `org-only`) control what is shared. Node-level selective sync filters provide additional control. Privacy scan runs locally before any export.

The design borrows the most applicable mechanisms from ActivityPub (inbox/outbox, follow model), AT Protocol (CAR files, DIDs, repo sync), IPFS (CID content addressing, DHT routing), and Scuttlebutt (version vectors, gossip sync), adapted for borg's specific requirements as a workflow-pack exchange network.
