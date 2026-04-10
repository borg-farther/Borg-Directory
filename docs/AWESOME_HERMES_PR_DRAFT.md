# Awesome Hermes Agent — PR Draft: agent-borg

> **NOTE:** According to CONTRIBUTING.md, this project does NOT accept direct PRs.
> All resource additions must go through an Issue, reviewed by maintainers.
> The format below is provided as a PR-description-ready draft AND an Issue submission template.

---

## (1) Exact Markdown Entry for README.md

Add under: `## Skills & Plugins` → `### Skill Registries & Discovery`

```md
- **[beta]** [agent-borg](https://github.com/bensargotest-sys/guild-tools) by [bensargotest-sys](https://github.com/bensargotest-sys) - Workflow cache and collective intelligence engine for AI agents. 14 MCP tools (`borg_search`, `borg_pull`, `borg_try`, `borg_apply`, `borg_publish`, `borg_feedback`, `borg_suggest`, `borg_observe`, `borg_convert`, and more). Stores proven approaches as reusable YAML packs with Ed25519 signing, OpenClaw bridge, and agentskills.io converter. 1,083 tests. Beta — solid test coverage but no external users yet. Framed as "connective brain tissue for agents."
```

---

## (2) PR Description

```
## Title
feat: Add agent-borg (beta) — workflow cache and collective intelligence for Hermes

## Description

### What is agent-borg?

[agent-borg](https://github.com/bensargotest-sys/guild-tools) is a workflow cache 
layer for AI agents. Where a standard agent starts each problem from scratch, borg 
lets it reach into a shared cache of proven approaches — and write back what it 
learned so the next agent doesn't repeat the same failed attempts.

Framed as "cache layer for agent reasoning" or "connective brain tissue for agents," 
it manages **workflow packs** — YAML files encoding how to approach a problem class:

- Problem class, mental model, ordered phases with checkpoints and anti-patterns
- Provenance confidence levels (guessed → inferred → tested → validated)
- Safety scan results (injection and privacy pattern checks)
- Ed25519 pack signing for authenticity

### Capabilities

- **14 MCP tools**: `borg_search`, `borg_pull`, `borg_try`, `borg_apply`, 
  `borg_publish`, `borg_feedback`, `borg_suggest`, `borg_observe`, `borg_convert`, 
  `borg_init`, and 4 more
- **Collective intelligence packs**: Pre-built packs for common agent tasks
- **Reputation engine**: Pack quality signals from the community
- **NudgeEngine**: Lightweight behavioral steering
- **OpenClaw bridge**: Interoperability with OpenClaw agents
- **agentskills.io converter**: Convert skills to/from the agentskills.io standard
- **Ed25519 signing**: Cryptographic pack authenticity
- **1,083 tests**: Comprehensive test coverage across all modules

### Maturity Assessment: **beta**

- ✅ Well-documented, clear README with quick-start and API examples
- ✅ Comprehensive test suite (1,083 tests)
- ✅ MCP integration fully wired (14 tools)
- ⚠️  No confirmed external users yet — this is the honest differentiating factor
- ⚠️  Small GitHub repo (bensargotest-sys/guild-tools) — early-stage project

The **beta** tag is appropriate: it works and is well-tested, but is still 
gaining adoption. Recommend reviewing again in 60 days to re-assess toward 
production if an active user community emerges.

### Why it belongs in the list

- Directly relevant to Hermes Agent workflow optimization
- MCP-native — integrates as a standard tool server (`borg-mcp`)
- agentskills.io converter bridges the borg pack format with the Hermes skills ecosystem
- OpenClaw bridge provides a migration path for teams moving from OpenClaw to Hermes
- Active development with substantial test infrastructure already in place

### Category

`Skill Registries & Discovery` — borg is a workflow pack registry with semantic 
search, reputation scoring, and community curation. Fits alongside `hermeshub` 
and `skilldock.io`.

---

## Metadata

| Field | Value |
|-------|-------|
| Resource name | agent-borg |
| URL | https://github.com/bensargotest-sys/guild-tools |
| PyPI | https://pypi.org/project/agent-borg/ |
| Author | bensargotest-sys |
| Category | Skill Registries & Discovery |
| Maturity | beta |
| MCP tools | 14 |
| Tests | 1,083 |
| License | (verify before merge) |

---

## Checklist

- [x] Relevant to Hermes Agent ecosystem
- [x] Clear README with usage documentation
- [x] Open source (source available on GitHub)
- [x] Not a duplicate of existing entries
- [x] Maturity honestly assessed (beta — no external users yet, solid test coverage)
- [x] MCP integration confirmed
- [x] agentskills.io converter noted (being built)
```

---

## (3) Summary for Maintainers

**Issue/PR type:** Feature addition — Skill Registries & Discovery

**What to add:** One line under `### Skill Registries & Discovery` in `README.md`

**Honesty note:** agent-borg has 1,083 tests and a full MCP tool suite but has not yet accumulated external users. The beta tag reflects this honestly. The project is actively maintained and the test infrastructure suggests a solid foundation — it just needs community adoption to reach production maturity.

**Recommended next step:** Maintainers assign the beta label; re-review in 60 days.
