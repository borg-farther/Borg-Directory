# Borg Trace Format v1.0

Open format for AI agent debugging traces.

## Required Fields
| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | Unique identifier |
| task_description | string | What the agent was doing |
| outcome | success/failure/partial | Result |
| created_at | ISO 8601 | When session ended |

## Recommended Fields
| Field | Type | Description |
|-------|------|-------------|
| root_cause | string | What caused the problem |
| approach_summary | string | What fixed it |
| technology | string | django/typescript/docker/nodejs/rust/fastapi/python/go |
| tool_calls | integer | Tool calls made |
| helpfulness_score | float 0-1 | Borg guidance rating |
| causal_intervention | string | Specific fix action |
| agent_id | string | Agent identifier |
| source | string | auto=real, seed_pack=synthetic |

## Minimum Viable Trace
```json
{
  "id": "uuid-v4",
  "task_description": "Fix TypeScript type error",
  "outcome": "success",
  "technology": "typescript",
  "agent_id": "my-agent",
  "created_at": "2026-04-13T00:00:00Z"
}
```

## Privacy: Never include API keys, passwords, or PII.
## Install: pip install agent-borg
