# Codebase Inspection

**Confidence:** inferred
**Problem class:** Inspect and analyze codebases using pygount for LOC counting, language breakdown, and code-vs-comment ratios. Use when asked to check lines of code, repo size, language composition, or codebase stats.

## Required Inputs
- task_description: what you need to accomplish

## Phases

### 1__basic_summary__most_common
Get a full language breakdown with file counts, code lines, and comment lines:

```bash
cd /path/to/repo
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
  .
```

**IMPORTANT:** Always use `--folders-to-skip` to exclude dependency/build directories, otherwise pygount will crawl them and take a very long time or hang.

**Checkpoint:** Verify 1. basic summary (most common) is complete and correct.

### 2__common_folder_exclusions
Adjust based on the project type:

```bash
# Python projects
--folders-to-skip=".git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache"

# JavaScript/TypeScript projects
--folders-to-skip=".git,node_modules,dist,build,.next,.cache,.turbo,coverage"

# General catch-all
--folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party"
```

**Checkpoint:** Verify 2. common folder exclusions is complete and correct.

### 3__filter_by_specific_language
```bash
# Only count Python files
pygount --suffix=py --format=summary .

# Only count Python and YAML
pygount --suffix=py,yaml,yml --format=summary .
```

**Checkpoint:** Verify 3. filter by specific language is complete and correct.

### 4__detailed_file_by_file_output
```bash
# Default format shows per-file breakdown
pygount --folders-to-skip=".git,node_modules,venv" .

# Sort by code lines (pipe through sort)
pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
```

**Checkpoint:** Verify 4. detailed file-by-file output is complete and correct.

### 5__output_formats
```bash
# Summary table (default recommendation)
pygount --format=summary .

# JSON output for programmatic use
pygount --format=json .

# Pipe-friendly: Language, file count, code, docs, empty, string
pygount --format=summary . 2>/dev/null
```

**Checkpoint:** Verify 5. output formats is complete and correct.

### 6__interpreting_results
The summary table columns:
- **Language** — detected programming language
- **Files** — number of files of that language
- **Code** — lines of actual code (executable/declarative)
- **Comment** — lines that are comments or documentation
- **%** — percentage of total

Special pseudo-languages:
- `__empty__` — empty files
- `__binary__` — binary files (images, compiled, etc.)
- `__generated__` — auto-generated files (detected heuristically)
- `__duplicate__` — files with identical content
- `__unknown__` — unrecognized file types

**Checkpoint:** Verify 6. interpreting results is complete and correct.


## Examples
**Example 1:**
- Problem: User asked for LOC count but agent counted node_modules, producing a misleading 500K LOC figure
- Solution: 1__basic_summary__most_common: Always uses --folders-to-skip with proper exclusions. Correct count: 12K LOC in src/ only.
- Outcome: Accurate codebase size reported. node_modules excluded from analysis.

**Example 2:**
- Problem: Agent needed to justify a refactoring effort to management — needed language breakdown
- Solution: 1__basic_summary__most_common + 5__output_formats: Ran pygount --format=json to get programmatic breakdown. Python 67%, TypeScript 23%, YAML 10%.
- Outcome: Data-driven justification for refactoring timeline. Showed Python dominates.

**Example 3:**
- Problem: Agent was asked if there were duplicate files in a codebase — scanned manually and missed several
- Solution: 6__interpreting_results: Used __duplicate__ pseudo-language detection. Found 4 duplicate utility files across different directories.
- Outcome: Duplicates identified in 30 seconds. Manual scan would have taken an hour.


## Escalation
- If stuck after 2 attempts, ask the user for guidance

---
Author: agent://hermes-seed | Confidence: inferred | Created: 2026-03-24T12:00:00Z
Evidence: Auto-generated from codebase-inspection skill. Requires validation through usage.
Failure cases: May not apply to all codebase inspection scenarios
