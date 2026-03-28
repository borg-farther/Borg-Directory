---
name: borg
description: "Use when your agent is stuck in a loop, burning tokens on a problem it can't solve after 3+ attempts. Covers debugging, testing, code review, planning. Borg provides battle-tested workflows from collective agent intelligence. NOT for simple/obvious fixes."
user-invocable: true
metadata: {"openclaw":{"emoji":"🧠","homepage":"https://github.com/bensargotest-sys/guild-tools","always":false}}
---

# 🧠 Borg — Collective Intelligence for AI Agents

Stop burning tokens on problems someone else already solved.

## When to Use

- Your agent hit a blocker and is going in circles (3+ failed attempts)
- You need a structured approach to debugging, testing, code review, or planning
- You want proven workflows that worked for other agents on similar problems

## When NOT to Use

- Simple, obvious fixes (typos, missing imports)
- Tasks that don't benefit from structured phases
- Creative or open-ended tasks with no "right approach"

## How to Use

### Step 1: Find the right pack

Read the pack index to find relevant approaches:

```
read references/pack-index.md
```

### Step 2: Load the pack

Once you find a matching pack, read its full instructions:

```
read references/packs/<pack-name>.md
```

### Step 3: Follow the phases

Each pack has numbered phases with checkpoints. Follow them IN ORDER.
Do NOT skip phases. Do NOT move to the next phase until the checkpoint passes.

⚠️ **Critical:** The phases exist because agents that skip them fail. The checkpoints exist because agents that don't verify their work produce bad fixes. Trust the process.

## Available Packs

**Available packs:**

- *Use when encountering any bug, test failure, or unexpected behavior. 4-phase root cause investigation — NO fixes without understanding the problem first.:*
  - **systematic-debugging** (tested)
- *Generate ASCII art using pyfiglet (571 fonts), cowsay, boxes, toilet, image-to-ascii, remote APIs (asciified, ascii.co.uk), and LLM fallback. No API keys required.:*
  - **ascii-art** (inferred)
- *:*
  - **code-review-rubric** (inferred)
  - **plan-rubric** (inferred)
  - **systematic-debugging-rubric** (inferred)
- *Reviewing code changes (diffs, PRs, or files) for bugs, security vulnerabilities, and quality issues — producing actionable, severity-ranked feedback:*
  - **code-review** (tested)
- *Guidelines for performing thorough code reviews with security and quality focus:*
  - **code-review** (inferred)
- *Inspect and analyze codebases using pygount for LOC counting, language breakdown, and code-vs-comment ratios. Use when asked to check lines of code, repo size, language composition, or codebase stats.:*
  - **codebase-inspection** (inferred)
- *Create hand-drawn style diagrams using Excalidraw JSON format. Generate .excalidraw files for architecture diagrams, flowcharts, sequence diagrams, concept maps, and more. Files can be opened at excalidraw.com or uploaded for shareable links.:*
  - **excalidraw** (inferred)
- *Set up GitHub authentication for the agent using git (universally available) or the gh CLI. Covers HTTPS tokens, SSH keys, credential helpers, and gh auth — with a detection flow to pick the right method automatically.:*
  - **github-auth** (inferred)
- *Review code changes by analyzing git diffs, leaving inline comments on PRs, and performing thorough pre-push review. Works with gh CLI or falls back to git + GitHub REST API via curl.:*
  - **github-code-review** (inferred)
- *Create, manage, triage, and close GitHub issues. Search existing issues, add labels, assign people, and link to PRs. Works with gh CLI or falls back to git + GitHub REST API via curl.:*
  - **github-issues** (inferred)
- *Full pull request lifecycle — create branches, commit changes, open PRs, monitor CI status, auto-fix failures, and merge. Works with gh CLI or falls back to git + GitHub REST API via curl.:*
  - **github-pr-workflow** (inferred)
- *Clone, create, fork, configure, and manage GitHub repositories. Manage remotes, secrets, releases, and workflows. Works with gh CLI or falls back to git + GitHub REST API via curl.:*
  - **github-repo-management** (inferred)
- *Use a live Jupyter kernel for stateful, iterative Python execution via hamelnb. Load this skill when the task involves exploration, iteration, or inspecting intermediate results — data science, ML experimentation, API exploration, or building up complex code step-by-step. Uses terminal to run CLI commands against a live Jupyter kernel. No new tools required.:*
  - **jupyter-live-kernel** (inferred)
- *Plan mode for Hermes — inspect context, write a markdown plan into the active workspace's `.hermes/plans/` directory, and do not execute the work.:*
  - **plan** (inferred)
- *simple debugging:*
  - **quick-debug** (tested)
- *Use when completing tasks, implementing major features, or before merging. Validates work meets requirements through systematic review process.:*
  - **requesting-code-review** (inferred)
- *Use when executing implementation plans with independent tasks. Dispatches fresh delegate_task per task with two-stage review (spec compliance then code quality).:*
  - **subagent-driven-development** (inferred)
- *Agent stuck in circular debugging — trying fixes without understanding root cause, breaking things, reverting, trying again. Use when quick-debug isn't enough.:*
  - **systematic-debugging** (tested)
- *Implementing features or fixing bugs using a test-driven development workflow — writing tests first to define correctness, then implementing the minimal code to pass:*
  - **test-driven-development** (tested)
- *Use when implementing any feature or bugfix, before writing implementation code. Enforces RED-GREEN-REFACTOR cycle with test-first approach.:*
  - **test-driven-development** (inferred)
- *Use when you have a spec or requirements for a multi-step task. Creates comprehensive implementation plans with bite-sized tasks, exact file paths, and complete code examples.:*
  - **writing-plans** (inferred)

---
*Powered by [borg](https://github.com/bensargotest-sys/guild-tools) — collective intelligence for AI agents.*