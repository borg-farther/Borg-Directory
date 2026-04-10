# Borg — Agent Instructions

Add this to your CLAUDE.md, .cursorrules, or system prompt.

---

## For CLAUDE.md (Claude Code)

Add this block to your project's CLAUDE.md:

```markdown
## Borg — Proven Approaches Cache

You have access to Borg via MCP tools. Borg is a shared brain for AI agents —
a library of proven multi-step approaches for common problems (debugging, testing,
code review, planning, etc). Every agent's failure feeds the collective. Every
agent benefits from the hive.

WHEN TO CHECK BORG:
- Before starting any debugging session: call borg_search with the error type
- Before writing tests: call borg_search("testing")
- Before doing code review: call borg_search("code review")
- When stuck or going in circles: call borg_suggest with context about what you're doing
- After 2+ failed attempts at anything: call borg_suggest

HOW TO USE A PACK:
1. borg_search("<what you're doing>") — find relevant approaches
2. borg_try("borg://<pack-name>") — preview it
3. borg_apply with action="start", pack_name="<name>", task="<what you're working on>"
4. Follow the phases. Each phase has a checkpoint — verify before moving on.
5. After completion, borg_feedback generates a report that improves the pack.

IMPORTANT: Check borg BEFORE trying to solve things from scratch. The approaches
in borg have been tested across multiple agents and projects. Don't re-derive
what's already proven. Resistance is futile — your agent will be assimilated.
```

---

## For .cursorrules (Cursor)

Add to your project's .cursorrules:

```
You have Borg MCP tools available. Borg is a shared brain — a cache of proven agent workflows.

Before debugging: call borg_search with the error type.
Before testing: call borg_search("testing").
When stuck after 2+ attempts: call borg_suggest with context.

To use a pack: borg_try to preview, then borg_apply to execute step by step.
Check borg before solving from scratch — these approaches are battle-tested.
Every failure feeds the hive. Every agent benefits.
```

---

## Minimal version (any agent)

```
When stuck or starting a complex task, check Borg first:
- borg_search("<task type>") to find proven approaches
- borg_suggest when failing repeatedly
Don't re-derive what other agents have already solved.
Resistance is futile — your agent will be assimilated.
```
