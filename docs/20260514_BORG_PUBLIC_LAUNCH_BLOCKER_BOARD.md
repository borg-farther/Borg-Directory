# Borg public launch blocker board

Generated: 2026-05-14T18:26:13Z

## Current verdict

- **PUBLIC_WAITLIST_NARROW_BETA:** YES_WITH_CAVEATS
- **PUBLIC_SELF_SERVE_LAUNCH:** NO
- **SUPERVISED FIRST USER:** YES, with caveats already proven in first-user gate artifacts.

## Blockers

| ID | Blocker | Status | Why it matters | Done criteria | Safe next action |
|---|---|---|---|---|---|
| PL-01 | Live MCP/runtime identity not proven after reload | HUMAN_BLOCKED | Source and fresh-process canaries pass, but autonomous mode may not restart/kill/signal live Hermes/MCP services. | `borg_runtime_fingerprint` from served process shows expected path/hash; live unrelated `borg_observe` returns `NO_CONFIDENT_MATCH`; live permission canary returns permission guidance. | Human: approve/supervise service reload, then run live canaries. |
| PL-02 | Repo hygiene / release branch surgicality | PASS | Generated `build/lib`/`dist` side effects were restored/removed safely; unrelated dirty files may remain out-of-scope. | Staged release diff contains only allowlisted reviewed files; no build/lib or dist mass-adds; gates pass. | Human: review staged diff, handle unrelated unstaged files on separate branch/worktree before release merge. |
| PL-03 | First-10 real users absent | HUMAN_BLOCKED | Local gates prove engineering readiness, not adoption or utility. Public self-serve requires real external outcomes. | Scoreboard has 10 real user rows, ≥8 installs, ≥6 useful rescues, 0 critical privacy/security failures. | Human: invite consented beta users and record redacted evidence. Verified external users now: 0. |
| PL-04 | External clean install / pipx proof | PASS | Public users need a clean install path outside the maintainer working tree. | pipx proof passes, or pipx unavailable and clean local venv install/rescue proof passes as external-ish fallback. | If pipx was unavailable, rerun on a host with pipx before broad self-serve. |
| PL-05 | GitHub admin/push path previously blocked | READ_ONLY_DIAGNOSED | Public release needs canonical repo access and branch/default/governance clarity; autonomous mode may not mutate GitHub. | Correct owner PAT can push/admin after human approval. | Human: with borg-farther PAT, create/push reviewed release branch and perform visibility/protection changes intentionally. Current gh login: `borg-farther`. |
| PL-06 | Claims need final human review | PASS_AUTOMATED_WITH_HUMAN_REVIEW_RECOMMENDED | Automated gates can detect many unsupported claims but cannot replace release-owner review. | Public README/docs/package copy reviewed; no unsupported adoption/network claims. | Human: review public copy before announcement. |

## Non-blockers green in this run

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
NO. Requires live MCP runtime identity canary and first-10 real-user evidence.
