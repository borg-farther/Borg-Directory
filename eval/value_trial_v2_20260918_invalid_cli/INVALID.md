# INVALID — Hermes CLI argument placement

This artifact must not be used for any product-value claim.

All 24 subprocesses were rejected by the Hermes argument parser before any model call because `--max-turns 7` was passed to the root CLI instead of the `chat` subcommand. Evidence: every model return code was 2, usage metrics were absent, both Borg-arm invocation counts were zero, and median wall time was under one second.

The hidden graders then ran against unchanged buggy fixtures, as designed, and failed. Those failures measure no agent and no Borg condition.

The runner was subsequently changed to use `hermes --usage-file <path> chat --query <prompt> ... --max-turns 7`, with a regression test and a live one-query CLI acceptance smoke before rerun.
