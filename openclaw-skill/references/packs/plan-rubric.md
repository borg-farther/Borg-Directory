# Plan Rubric

**Confidence:** inferred

---
Author: agent://hermes/skill-retrofit-agent | Confidence: inferred | Created: 2026-03-22T21:22:00Z
Evidence: Derived from the Hermes plan skill v1.0.0 output requirements and core behavior rules. Actionability weight (0.30) reflects the skill's emphasis on 'concrete and actionable' plans. Plan-only discipline criterion directly encodes the skill's prohibition on executing changes during plan mode. Context grounding criterion enforces the skill's instruction to inspect the repo before planning.

Failure cases: Plan-only discipline (0.10) is easy to pass and rarely differentiates — most agents don't accidentally execute during planning, Actionability scoring is subjective — 'could another agent execute this' depends on that agent's capabilities, Risk awareness may penalize plans for simple tasks where risks genuinely don't exist, Doesn't evaluate whether the proposed approach is actually correct — only whether the plan is well-structured
