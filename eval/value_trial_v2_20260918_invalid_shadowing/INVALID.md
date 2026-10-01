# INVALID — fixture module shadowed Hermes bootstrap

This partial run must not be used for any product-value claim.

Task 1 completed all three arms. Task 2 created a top-level `plugins.py`; because the process-local one-shot driver started with the task workspace on `sys.path`, that fixture shadowed Hermes' own `plugins` package. All three task-2 subprocesses failed during bootstrap before a model call, with no usage receipt or Borg invocation. The run was terminated before task 3 completed.

The permanent fix removes the task working directory and empty-string entry from `sys.path` only during Hermes bootstrap, while retaining the workspace as the process and tool working directory. A hostile-fixture regression test and live acceptance probe are required before rerun.
