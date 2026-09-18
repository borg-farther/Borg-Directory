# INVALID — working-directory contamination

This run was terminated during task 6 and must not be used for any product-value claim.

## Why it is invalid

Hermes child processes inherited the parent `TERMINAL_CWD`, so some agents edited task files in `/root/hermes-workspace/borg` while the grader evaluated isolated copies under `/tmp/borg-value-trial-*/workspaces/`. This produced impossible self-reports (the agent said it fixed a task while the hidden grader correctly found the isolated candidate unchanged).

The three root-level contaminant files (`retry.py`, `framing.py`, and `pathsafe.py`) were removed after the trial process was terminated. No tracked task implementation file was changed by the trial.

## Permanent runner fix

The replacement runner pins both `TERMINAL_CWD` and `HERMES_CWD` to each randomized workspace, passes `--no-restore-cwd`, runs from an immutable copied Borg source snapshot, and fails if the parent repository's tracked diff or task target paths change.
