# BORG UNIFIED MARKETING PACK
## Living document — strategies, messaging, distribution, funnels
## Updated: 2026-03-28

---

## 1. THE CORE STORY (AB's framing — canonical)

Your agent is doing something. It hits a blocker. It goes in circles — 3, 4, 5 loops — burning tokens and money. You don't see it happening. You don't understand why.

**Before borg:** your agent keeps spinning until it either stumbles onto a fix or gives up. You pay for every wasted loop.

**With borg:** before that cycle even starts, your agent auto-connects back to the network. Someone else's agent already hit this exact blocker. Already burned those tokens. Already found the solution. Your agent pulls it in seconds and keeps moving.

> **"Stop your agent burning tokens on problems someone else already solved."**

That's borg. Not "collective intelligence" — too abstract. Not "23 packs" — nobody cares. The benefit is: **your agent escapes failure loops faster because the network already solved it.**

---

## 2. DEVELOPER PAIN POINTS (ranked by intensity)

What agent developers actually struggle with:

1. **Agents don't finish tasks** — constant hand-holding and re-prompting
2. **Context loss** — agents forget project state mid-task
3. **Poor output quality** — buggy, insecure, architecturally bad code
4. **Debugging is opaque** — why did the agent do THAT?
5. **No native tool integrations** — can't interact with real APIs/databases
6. **Slow iteration** — expensive LLM round-trips, context windows fill up
7. **Prompt engineering overhead** — too much manual crafting for reliable behavior
8. **No multi-agent coordination** — can't parallelize subtasks
9. **No observability** — can't verify agent actions
10. **Model lock-in** — tied to one LLM ecosystem

**Borg addresses:** #1 (proven workflows = fewer failures), #2 (failure memory persists), #3 (safety-scanned packs), #4 (observation + audit trail), #7 (pre-proven approaches replace prompt crafting)

---

## 3. MESSAGING — BENEFITS, NOT FEATURES

### What to say (lead with what THEY get):

| Audience | Message | Why it works |
|----------|---------|-------------|
| Agent dev (individual) | "Your agent is burning tokens looping on a problem. Someone else's agent already solved it. Borg pulls the fix before you even notice." | Token cost = real money, real pain |
| Agent dev (frustrated) | "That 5-loop failure spiral just cost you $2. The answer was already on the network." | Makes the invisible cost visible |
| Framework developer | "Your users' agents stop spinning. They think your framework got smarter. You added one MCP tool." | Zero effort for them, their users credit them |
| Skeptic | "Watch your agent hit a blocker. Then watch it with borg. Count the loops." | Observable, falsifiable |

### What NOT to say:

| ❌ Don't say | Why it fails |
|-------------|-------------|
| "23 proven approaches" | A number without context. Proven by whom? |
| "Collective intelligence for AI agents" | Too abstract, sounds like a whitepaper |
| "12 iterations → 4" | Unverified claim, sounds like marketing BS |
| "Join the borg" (without context) | Cute but doesn't explain the benefit |
| "EigenTrust reputation" | Academic jargon, means nothing to a dev |
| "Conditional phases with skip_if/inject_if" | Implementation detail, not benefit |
| "FTS5 full-text search" | Infrastructure, not value |
| "WAL mode SQLite" | Who cares |

### Tagline options (benefit-first):

1. **"Stop your agent burning tokens on problems someone else already solved"** ← AB's framing, strongest
2. **"Your agent is spinning. The network already has the answer."**
3. **"The collective memory your agent is missing"**
4. **"Every failure loop costs you money. Borg cuts them short."**
5. **"One agent solves it. Every agent learns."**

### The story arc (for landing page / demo):
```
BEFORE: Agent hits blocker → loops 5x → burns $2 in tokens → maybe finds fix, maybe gives up
AFTER:  Agent hits blocker → borg checks network → solution found in 0.3s → moves on → $0.02
```

---

## 4. COMPETITIVE POSITIONING

### How the best tools pitch themselves:

| Tool | Hero message | Lead with |
|------|-------------|-----------|
| Cursor | "The AI-first code editor" | What you accomplish |
| Cline | "Autonomous coding in your IDE" | Autonomy |
| CrewAI | "Multi-agent AI made simple" | Simplicity |
| Vercel AI SDK | "AI-powered streaming UI with any model" | Developer experience |
| Continue | "The leading open-source AI code assistant" | Community |

**Pattern:** Winners lead with what the developer ACCOMPLISHES. Never with internal architecture.

### Borg's unique position:

Nobody else is doing **collective workflow intelligence**:
- DSPy optimizes YOUR prompt for YOUR task
- Borg surfaces what worked across ALL agents doing SIMILAR tasks
- This is the npm of agent workflows — but the packages improve themselves

### Competitive gap:
- MCP registries (Smithery.ai) list tools but don't track what works
- LangChain/CrewAI provide frameworks but not proven approaches
- Prompt libraries are static — borg's packs evolve from feedback
- Nobody has a reputation system for agent workflows

---

## 5. MESSAGING GAP ANALYSIS (honest)

### README currently claims vs reality:

| Claim | Reality | Fix |
|-------|---------|-----|
| 12 MCP tools listed | 3 crash with NameError | Phase 0: fix or remove |
| "Brain" example output shown | Aspirational mockup, not real output | Remove until real |
| "Reduces 12 iterations to 4" | No data behind this | Remove |
| "23 proven approaches" | Unverified quality | Audit packs, then claim |
| bensargotest-sys org | Test org name | Get real org |

### Real differentiators NOT in README:

| Feature | Why it matters to devs |
|---------|----------------------|
| Reputation system | Quality signal — know which packs actually work |
| Aggregator loop | Packs self-improve from collective failure data |
| Failure memory | Your agent remembers what didn't work |
| Proof gates + confidence tiers | "tested" means tested, not "someone wrote it" |
| Auto anti-pattern discovery | System finds what NOT to do automatically |

---

## 6. TARGET AUDIENCES (detailed)

### 6a. Agent Framework Developers (Hermes, Cline, Cursor, OpenClaw)
- **Their pain:** agents fail unpredictably, users blame the framework
- **Our value:** pre-proven workflows that make their agents look smarter out of the box
- **Pitch:** "Add `borg_observe` to your agent loop. It watches what works and what doesn't. Your agents get smarter without you writing a single new prompt."
- **Integration effort:** MCP server config (5 min) + optional deep integration

### 6b. Individual Agent Users
- **Their pain:** agent keeps making the same mistakes, no learning between sessions
- **Our value:** cross-session, cross-agent memory of what works
- **Pitch:** "Your agent failed at debugging 3 times yesterday. Borg knows 47 other agents hit the same issue. Here's the approach that worked."
- **Trigger to install:** A frustrating agent failure + hearing about borg

### 6c. Enterprise / Teams (Phase 4)
- **Their pain:** inconsistent agent behavior, compliance, auditability
- **Our value:** standardized approaches, safety-scanned, audit trail
- **Pitch:** TBD — not targeting yet

---

## 7. DISTRIBUTION STRATEGY

### Current channels:

| Channel | Status | Priority | Notes |
|---------|--------|----------|-------|
| PyPI (agent-borg) | LIVE v2.3.1 | P0 | Primary install path |
| GitHub | LIVE (test org) | P0 | Needs real org name |
| Hermes MCP | PARTIAL | P0 | Must work 100% |
| OpenClaw | NOT STARTED | P0 | Must work 100% — need more research |
| Smithery.ai | NOT LISTED | P1 | MCP registry — should be there |
| Discord (#agent-borg) | EXISTS | P2 | Community |
| Blog/docs site | NONE | P2 | Need borgpacks.io or similar |

### Distribution problems (see ROADMAP R002):
- Single GitHub URL = single point of failure
- bensargotest-sys undermines credibility
- No CDN, no mirrors, no offline mode
- Not listed on any MCP registry
- No presence where MCP users discover tools

---

## 8. FUNNEL

```
AWARENESS          → INTEREST           → TRIAL              → ADOPTION           → CONTRIBUTION
(where do they     (why do they click)  (first 5 minutes)    (why stay)           (why give back)
 find us)
```

### Awareness
- MCP registries (Smithery.ai, mcp.so)
- Reddit (r/LocalLLaMA, r/ChatGPTCoding, r/ClaudeAI)
- Hacker News ("Show HN: Borg — collective memory for AI agents")
- Discord communities (AI agent servers)
- GitHub trending
- Word of mouth from framework integrations

### Interest
- Hero message: "Your agent stops repeating everyone's mistakes"
- 30-second demo GIF showing before/after
- Real benchmark data (not made up)

### Trial (must be <5 minutes)
```
pip install agent-borg
borg search "debugging"
borg try debugging-systematic
→ see your agent actually perform better
```

### Adoption
- Packs actually improve output quality
- Failure memory = agent gets smarter over time
- New packs appear from the network = value grows

### Contribution
- Reputation score rewards
- Your improvements help your own future runs
- "I published a pack" = social proof

---

## 9. ANTI-PATTERNS TO AVOID

- ❌ Buzzword salad ("leverage AI-powered next-gen synergies")
- ❌ Feature lists without benefits ("we support 50+ models!")
- ❌ Generic superlatives ("the most advanced platform")
- ❌ Leading with pricing or benchmarks before value
- ❌ "We're like X but better" positioning
- ❌ Integration count as a selling point
- ❌ Dark pattern freemium that gates actual value
- ❌ Statistics without story ("12 → 4 iterations" means nothing without context)

---

## 10. IDEAS PARKING LOT

- [ ] Collective prompt intelligence as killer feature (ROADMAP R001)
- [ ] Benchmark results as social proof (PLAN.md Phase 3.3)
- [ ] "Before/after" demos — same task with and without borg
- [ ] Video: agent failing repeatedly → borg → agent succeeds
- [ ] Discord bot showing live pack usage stats
- [ ] "Borg score" badge for GitHub repos (like code coverage badges)
- [ ] Integration with popular frameworks as PR contributions (not just docs)
- [ ] Conference talks / demos at AI agent meetups
- [ ] "Pack of the week" newsletter / social content

---

## 11. OPEN QUESTIONS

- [ ] Org name? (bensargotest-sys → what?)
- [ ] Domain? (borg.dev? borgpacks.io? agent-borg.dev?)
- [ ] Logo / visual identity?
- [ ] Launch strategy — soft launch or announcement?
- [ ] Pricing — always free? Freemium? Enterprise?
- [ ] Content creation — who writes blog posts, docs, demos?
- [ ] OpenClaw integration details — need more research (web search was down)

---
