# BORG ROADMAP
## Captured ideas — won't interfere with active work
## Say "roadmap" to add, "show roadmap" to review

---

### R001: Collective Prompt Intelligence System
**Added:** 2026-03-28
**Status:** IDEA — needs research
**Priority:** TBD
**Summary:** A borg-powered system that collectively improves agent prompts. Agents share what prompt patterns work for specific task types, borg aggregates feedback, and surfaces improvements back to users. Could auto-update prompts or suggest improvements based on collective intelligence.
**Open questions:**
- Is there tangible benefit over existing prompt optimization tools?
- What's the right network/protocol to plug into?
- How would this work architecturally within borg?
- Can we access prompt execution metadata without privacy issues?
**See:** Analysis in telegram chat 2026-03-28

---

### R002: Distribution Infrastructure
**Added:** 2026-03-28
**Status:** IDEA — blocks Phase 2+
**Priority:** HIGH
**Summary:** Pack distribution beyond single GitHub URL. CDN, mirrors, offline bundles, fallback when GitHub is down. Currently hardcoded to bensargotest-sys/guild-packs — single point of failure, test org name undermines credibility.
**Open questions:**
- CDN provider? (Cloudflare R2, GitHub Pages, npm-style?)
- Offline bundle format?
- Cache invalidation strategy?
- Custom domain (borg.dev? borgpacks.io?)

---

### R003: Org Name + Domain
**Added:** 2026-03-28
**Status:** DECISION NEEDED
**Priority:** HIGH (blocks credibility)
**Summary:** bensargotest-sys is a test org name that undermines credibility. Need real GitHub org + domain (borg.dev? borgpacks.io? agent-borg.dev?). Blocks README fix, distribution, and all external-facing work.

---

### R004: MCP Registry Listing (Smithery.ai)
**Added:** 2026-03-28
**Status:** IDEA — blocks awareness funnel
**Priority:** HIGH
**Summary:** Borg is not listed on any MCP registry. Smithery.ai is where MCP users discover tools. We should be there. Requires working tools first (Phase 0).

---

### R005: OpenClaw Integration
**Added:** 2026-03-28
**Status:** RESEARCHED — integration path identified
**Priority:** P1
**Summary:** OpenClaw (github.com/openclaw/openclaw) — 339k stars, TypeScript personal AI assistant. Uses SKILL.md format (same as Hermes). NO MCP support. Has ClawHub skill registry (clawhub.com). Integration paths: (1) borg pack → SKILL.md converter for OpenClaw workspace skills, (2) publish borg packs to ClawHub registry, (3) lobby for MCP support (unlikely). Best bet: build a borg_convert --format=openclaw that outputs SKILL.md files compatible with ~/.openclaw/workspace/skills/. This gives 339k potential users access to borg packs without OpenClaw needing to change anything.

---

### R006: README False Advertising Cleanup
**Added:** 2026-03-28
**Status:** BLOCKED on Phase 0
**Priority:** P0
**Summary:** README shows 3 tools that crash (NameError), aspirational "brain" output that doesn't exist yet, unverified "12→4" claim, and "23 proven approaches" that are unaudited. Must fix after Phase 0 tool fixes.

---
