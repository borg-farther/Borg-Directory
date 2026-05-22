# Borg Benchmark Suite

> **Synthetic benchmark design, not public efficacy proof.** This directory is useful for exercising benchmark plumbing and comparing candidate workflows. Do not cite it as external agent-level lift, production success-rate evidence, or real-user adoption proof until it is backed by actual controlled agent runs.

This benchmark suite defines comparison tasks for evaluating agent performance with and without Borg guidance.

## Overview

The benchmark suite evaluates 10 common agent tasks across different scenarios:

| # | Task | Pack | Description |
|:--|:-----|:-----|:-----------|
| 001 | debug_typeerror | systematic-debugging | Debug Python TypeError from wrong argument order |
| 002 | debug_flaky_test | systematic-debugging | Debug race condition causing flaky tests |
| 003 | code_review_pr | github-code-review | Review PR with 3 bugs (SQL injection, resource leak, logic error) |
| 004 | plan_feature_user_auth | writing-plans | Plan implementation of user authentication |
| 005 | setup_github_actions_ci | github-pr-workflow | Set up GitHub Actions CI for Python project |
| 006 | create_issues_from_bug_report | github-issues | Create issues from QA bug report |
| 007 | refactor_long_function | writing-plans | Refactor 150-line function into smaller pieces |
| 008 | fix_import_error_dependency_upgrade | systematic-debugging | Fix import error after requests library upgrade |
| 009 | write_tests_untested_module | test-driven-development | Write tests for untested validation module |
| 010 | debug_production_stack_trace | systematic-debugging | Debug KeyError from Stripe webhook handler |

## Running the Benchmark

```bash
# Run all benchmarks
python runner.py

# List available tasks
python runner.py --list

# Run specific task
python runner.py --task 001

# Output as JSON only
python runner.py --output json
```

## Benchmark Methodology

### Task Structure

Each task is defined in `tasks/NNN_taskname.yaml` with:

```yaml
id: NNN
name: taskname
description: >
  Detailed description of what the task involves.
setup_code: |
  # Python code that creates the problem files
expected_outcome: >
  What success looks like for this task
max_iterations: 5
relevant_pack: guild://hermes/pack-name
```

### Execution Modes

For each task, we run two modes:

1. **without borg** - Agent receives only:
   - Task description
   - Expected outcome
   - Problem files (via setup_code)

2. **with borg** - Agent receives:
   - Task description
   - Expected outcome
   - Borg pack guidance (mental model, phases, prompts)

### Scoring

The scoring function measures:

| Metric | Description |
|:-------|:------------|
| `iterations_taken` | Number of agent iterations to complete |
| `tokens_used` | Estimated tokens consumed |
| `correct_fix` | Boolean - did the agent solve the problem correctly? |

### Iteration Estimation

This benchmark currently uses deterministic placeholder estimates; it does **not** execute independent agents or prove real-world performance.

- **without borg**: `iterations_taken = max_iterations` (baseline from task definition)
- **with borg**: `iterations_taken = max_iterations * 0.6` (design placeholder only)

Treat these numbers as scaffold values for benchmark development, not as public Borg performance claims. Replace them with measured runs before making any efficacy statement.

### Results

Results are saved to `results/` directory:

- `results/results_YYYYMMDD_HHMMSS.md` - Markdown table
- `results/results_YYYYMMDD_HHMMSS.json` - JSON data

## Placeholder Output Shape

Current benchmark outputs may include illustrative scaffold values. They are not real efficacy evidence.

| Metric | Placeholder |
|:-------|:------------|
| Average iterations (baseline) | from task `max_iterations` |
| Average iterations (with borg) | design placeholder until measured |
| Average saved | not claimed |

### Correct Fix Rate

| Mode | Current status |
|:-----|:---------------|
| without borg | not measured by this scaffold |
| with borg | not measured by this scaffold |

The benchmark becomes claim-worthy only after it runs real agents, records raw transcripts/logs, defines a control, and reports statistical uncertainty.

## Pack Coverage

| Pack | Tasks |
|:-----|:------|
| systematic-debugging | 001, 002, 008, 010 |
| github-code-review | 003 |
| writing-plans | 004, 007 |
| github-pr-workflow | 005 |
| github-issues | 006 |
| test-driven-development | 009 |

## Interpreting Results

### Good Signs

- **Iterations saved > 0**: Borg pack is helping
- **Correct fix rate higher with borg**: Systematic approach is working
- **Token efficiency**: More tokens per iteration (borg does more per step)

### Concern Signs

- **Iterations saved < 0**: Pack may be adding overhead
- **No difference in correct_fix**: Task may not benefit from the pack
- **High variance across tasks**: Pack may work better for some task types

## Future Improvements

- [ ] Integrate with real agent framework (AgentForge, etc.)
- [ ] Measure actual token usage from API logs
- [ ] Add timing measurements
- [ ] Support parallel task execution
- [ ] Add statistical significance testing
