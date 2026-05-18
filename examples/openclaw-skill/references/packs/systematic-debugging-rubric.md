# Systematic Debugging Rubric

**Confidence:** inferred

---
Author: agent://hermes/skill-retrofit-agent | Confidence: inferred | Created: 2026-03-22T21:22:00Z
Evidence: Derived from the Hermes systematic-debugging skill v1.1.0 phase structure and red flags. Criteria map directly to the skill's four phases and key anti-patterns. Weight distribution emphasizes root cause identification (0.30) reflecting the skill's Iron Law.

Failure cases: Root cause weight (0.30) may over-penalize agents that find the right fix through pattern matching without explicit causal chain, Escalation discipline criterion (0.10) is hard to evaluate when the bug was fixed on first attempt — becomes N/A, Regression testing criterion assumes a test framework exists — unfair for codebases without test infrastructure
