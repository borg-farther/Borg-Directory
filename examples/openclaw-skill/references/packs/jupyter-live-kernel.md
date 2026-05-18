# Jupyter Live Kernel

**Confidence:** inferred
**Problem class:** Use a live Jupyter kernel for stateful, iterative Python execution via hamelnb. Load this skill when the task involves exploration, iteration, or inspecting intermediate results — data science, ML experimentation, API exploration, or building up complex code step-by-step. Uses terminal to run CLI commands against a live Jupyter kernel. No new tools required.


## Required Inputs
- task_description: what you need to accomplish

## Phases

### core_workflow
All commands return structured JSON. Always use `--compact` to save tokens.

### 1. Discover servers and notebooks

```
uv run "$SCRIPT" servers --compact
uv run "$SCRIPT" notebooks --compact
```

### 2. Execute code (primary operation)

```
uv run "$SCRIPT" execute --path <notebook.ipynb> --code '<python code>' --compact
```

State persists across execute calls. Variables, imports, objects all survive.

Multi-line code works with $'...' quoting:
```
uv run "$SCRIPT" execute --path scratch.ipynb --code $'import os\nfiles = os.listdir(".")\nprint(f"Found {len(files)} files")' --compact
```

### 3. Inspect live variables

```
uv run "$SCRIPT" variables --path <notebook.ipynb> list --compact
uv run "$SCRIPT" variables --path <notebook.ipynb> preview --name <varname> --compact
```

### 4. Edit notebook cells

```
# View current cells
uv run "$SCRIPT" contents --path <notebook.ipynb> --compact

# Insert a new cell
uv run "$SCRIPT" edit --path <notebook.ipynb> insert \
  --at-index <N> --cell-type code --source '<code>' --compact

# Replace cell source (use cell-id from contents output)
uv run "$SCRIPT" edit --path <notebook.ipynb> replace-source \
  --cell-id <id> --source '<new code>' --compact

# Delete a cell
uv run "$SCRIPT" edit --path <notebook.ipynb> delete --cell-id <id> --compact
```

### 5. Verification (restart + run all)

Only use when the user asks for a clean verification or you need to confirm
the notebook runs top-to-bottom:

```
uv run "$SCRIPT" restart-run-all --path <notebook.ipynb> --save-outputs --compact
```

**Checkpoint:** Verify core workflow is complete and correct.

### practical_tips_from_experience
1. **First execution after server start may timeout** — the kernel needs a moment
   to initialize. If you get a timeout, just retry.

2. **The kernel Python is JupyterLab's Python** — packages must be installed in
   that environment. If you need additional packages, install them into the
   JupyterLab tool environment first.

3. **--compact flag saves significant tokens** — always use it. JSON output can
   be very verbose without it.

4. **For pure REPL use**, create a scratch.ipynb and don't bother with cell editing.
   Just use `execute` repeatedly.

5. **Argument order matters** — subcommand flags like `--path` go BEFORE the
   sub-subcommand. E.g.: `variables --path nb.ipynb list` not `variables list --path nb.ipynb`.

6. **If a session doesn't exist yet**, you need to start one via the REST API
   (see Setup section). The tool can't execute without a live kernel session.

7. **Errors are returned as JSON** with traceback — read the `ename` and `evalue`
   fields to understand what went wrong.

8. **Occasional websocket timeouts** — some operations may timeout on first try,
   especially after a kernel restart. Retry once before escalating.

**Checkpoint:** Verify practical tips from experience is complete and correct.

### timeout_defaults
The script has a 30-second default timeout per execution. For long-running
operations, pass `--timeout 120`. Use generous timeouts (60+) for initial
setup or heavy computation.

**Checkpoint:** Verify timeout defaults is complete and correct.


## Examples
**Example 1:**
- Problem: Agent ran a cell that took 10 minutes — hit the default 30s timeout
- Solution: timeout_defaults: Retried with --timeout 120 for long-running computation. Used practical_tips_from_experience guidance to set generous timeout.
- Outcome: Cell completed successfully. Long computation accepted with proper timeout.

**Example 2:**
- Problem: Agent tried to execute code but got timeout errors repeatedly — kernel wasn't initialized
- Solution: core_workflow: Discovered session didn't exist. Started Jupyter server via REST API first, then executed code against live kernel.
- Outcome: Kernel initialized, state persists across execute calls. Workflow succeeded.

**Example 3:**
- Problem: Agent ran cells in wrong order and got NameError — variables from earlier cells weren't defined
- Solution: core_workflow: Restarted kernel and ran restart-run-all to verify notebook executes top-to-bottom cleanly. Found missing import in cell 3.
- Outcome: Execution order issue identified. Notebook fixed to run deterministically.


## Escalation
- If stuck after 2 attempts, ask the user for guidance

---
Author: agent://hermes-seed | Confidence: inferred | Created: 2026-03-24T12:00:00Z
Evidence: Auto-generated from jupyter-live-kernel skill. Requires validation through usage.
Failure cases: May not apply to all jupyter live kernel scenarios
