# Guild — Agent Instructions

Add this to your CLAUDE.md, .cursorrules, or system prompt.

---

## For CLAUDE.md (Claude Code)

Add this block to your project's CLAUDE.md:

```markdown
## Guild — Proven Approaches Cache

You have access to Guild via MCP tools. Guild is a library of proven multi-step
approaches for common problems (debugging, testing, code review, planning, etc).

WHEN TO CHECK GUILD:
- Before starting any debugging session: call guild_search with the error type
- Before writing tests: call guild_search("testing") 
- Before doing code review: call guild_search("code review")
- When stuck or going in circles: call guild_suggest with context about what you're doing
- After 2+ failed attempts at anything: call guild_suggest

HOW TO USE A PACK:
1. guild_search("<what you're doing>") — find relevant approaches
2. guild_try("guild://<pack-name>") — preview it
3. guild_apply with action="start", pack_name="<name>", task="<what you're working on>"
4. Follow the phases. Each phase has a checkpoint — verify before moving on.
5. After completion, guild_feedback generates a report that improves the pack.

IMPORTANT: Check guild BEFORE trying to solve things from scratch. The approaches
in guild have been tested across multiple agents and projects. Don't re-derive
what's already proven.
```

---

## For .cursorrules (Cursor)

Add to your project's .cursorrules:

```
You have Guild MCP tools available. Guild is a cache of proven agent workflows.

Before debugging: call guild_search with the error type.
Before testing: call guild_search("testing").
When stuck after 2+ attempts: call guild_suggest with context.

To use a pack: guild_try to preview, then guild_apply to execute step by step.
Check guild before solving from scratch — these approaches are battle-tested.
```

---

## Minimal version (any agent)

```
When stuck or starting a complex task, check Guild first:
- guild_search("<task type>") to find proven approaches
- guild_suggest when failing repeatedly
Don't re-derive what other agents have already solved.
```
