# Borg public launch blocker board

Generated: 2026-05-14T18:26:13Z
Updated: 2026-05-15T11:30:00Z benchmark evidence hardening + docs reconciliation

## Current verdict

- **PUBLIC_WAITLIST_NARROW_BETA:** YES_WITH_CAVEATS
- **PUBLIC_SELF_SERVE_LAUNCH:** NO
- **SUPERVISED FIRST USER:** YES, with caveats proven by first-user gate and final no-regression gates.
- **FRONTIER_BETTER_THAN_PROVEN:** NO

## Blockers

| ID | Blocker | Status | Why it matters | Done criteria | Safe next action |
|---|---|---|---|---|---|
| PL-01 | Live MCP/runtime identity / stale in-memory observe canary | OPERATOR_GATED_NOT_DIRECTLY_CHECKED_IN_FINAL_PASS | Final pass proved local in-process `borg.integrations.mcp_server.borg_observe` behavior: unrelated readiness prompt returned `NO_CONFIDENT_MATCH`; permission-denied prompt returned `bash-permission-denied`/`chmod`; no stale plugin/BORG_HOME/python-type-error guidance. This still is not a live served MCP gateway proof because autonomous mode did not restart/kill/signal gateway and did not directly exercise the served operator process. | Operator-supervised served MCP canary: served runtime fingerprint/path/hash matches intended deployment; served unrelated `borg_observe` returns `NO_CONFIDENT_MATCH`; served permission canary returns permission guidance. | Operator: run the exact live served canaries through the configured MCP client/process boundary; reload only if needed and approved. |
| PL-02 | Repo hygiene / release branch surgicality | PASS | Generated `build/lib`/`dist` side effects were restored/removed safely; unrelated dirty files may remain out-of-scope. | Staged release diff contains only allowlisted reviewed files; no build/lib or dist mass-adds; gates pass. | Human: review staged diff, handle unrelated unstaged files on separate branch/worktree before release merge. |
| PL-03 | First-10 real users absent | HUMAN_BLOCKED | Local gates prove engineering readiness, not adoption or utility. Public self-serve requires real external outcomes. | Scoreboard has 10 real user rows, ≥8 installs, ≥6 useful rescues, 0 critical privacy/security failures. | Human: invite consented beta users and record redacted evidence. Verified external users now: 0. |
| PL-04 | External clean install / pipx proof | PASS | Public users need a clean install path outside the maintainer working tree. | pipx proof passes, or pipx unavailable and clean local venv install/rescue proof passes as external-ish fallback. | If pipx was unavailable, rerun on a host with pipx before broad self-serve. |
| PL-05 | GitHub admin/push path previously blocked | READ_ONLY_DIAGNOSED | Public release needs canonical repo access and branch/default/governance clarity; autonomous mode may not mutate GitHub. | Correct owner PAT can push/admin after human approval. | Human: with borg-farther PAT, create/push reviewed release branch and perform visibility/protection changes intentionally. Current gh login: `borg-farther`. |
| PL-06 | Claims need final human review | PASS_AUTOMATED_WITH_HUMAN_REVIEW_RECOMMENDED | Automated gates can detect many unsupported claims but cannot replace release-owner review. | Public README/docs/package copy reviewed; no unsupported adoption/network claims. | Human: review public copy before announcement. |

## Non-blockers green in this run

- Targeted learning-loop suite: PASS (`325 passed in 11.92s`).
- Benchmark evidence contract: PASS (`9 passed in 0.07s`); zero-token/zero-duration/null-delta artifacts are explicitly invalid for frontier claims, token-unavailable markers must be explicit allowlisted values, and paired rows must contain control/treatment for the same task.
- Targeted confidence/runtime tests: PASS.
- Proof dashboard build/lint/test: PASS.
- First-user local release gate: PASS.
- Security baseline gate: PASS.
- Privacy/prompt-injection/atom policy/firewall tests: PASS.
- Source canaries: PASS.

## Launch definitions

### Public waitlist / narrow beta
YES_WITH_CAVEATS. Allowed only with caveats if PL-01 remains supervised/human-blocked and no self-serve claims are made.

### Public self-serve launch
NO. Requires live served MCP runtime identity canary and first-10 real-user evidence. Current first-10 real users: 0.
