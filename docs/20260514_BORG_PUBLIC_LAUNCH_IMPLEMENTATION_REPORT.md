> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg public launch readiness implementation report

Generated: 2026-05-14T14:41:45Z

Plan path: `.hermes/plans/2026-05-14_1436-borg-public-launch-readiness.md`
Copied public plan: `docs/20260514_BORG_PUBLIC_LAUNCH_READINESS_PLAN.md`
Machine-readable board: `eval/20260514_borg_public_launch_readiness.json`
Full command log JSON: `eval/20260514_borg_public_launch_command_log.json`

## Verdicts

| Verdict | Value | Reason |
|---|---:|---|
| PUBLIC_WAITLIST_NARROW_BETA | NO | Repo hygiene/release branch is blocked; live/user gates also remain caveated. |
| PUBLIC_SELF_SERVE_LAUNCH | NO | Requires all gates PASS including live MCP runtime identity and first 10 real users; those are BLOCKED. |

Do not claim live MCP fixed without approved reload + live canary. This run only proved source/fresh-process behavior.

## Gate table

| Gate | Status | Evidence | Blockers | Exact next action |
|---|---|---|---|---|
| live_mcp_runtime_identity | BLOCKED | Source/fresh-process tests pass: True<br>Fresh-process source canary pass: True<br>No live MCP reload/canary was performed by design. | Requires explicit approved live MCP/Hermes reload window and live served canary; do not claim live MCP fixed without reload. | Get explicit approval for a supervised reload, reload live MCP without killing gateway, then run live borg_runtime_fingerprint plus live borg_observe unrelated/permission canaries. |
| repo_hygiene_release_branch | BLOCKED | git status/diff captured in command log; working tree has many modified/deleted build/dist files and staged generated files.<br>git diff --stat reports large build/lib and dist deletions; git diff --cached --stat includes generated dashboard/security files. | Dirty tree is not a surgical public-readiness release branch; build/dist side effects need review/restoration; no push/admin check performed. | Create/checkout a clean release branch, restore accidental build/dist deletions or deliberately ignore generated dirs, stage only reviewed public-readiness docs/eval/source changes, then rerun git status/diff. |
| self_serve_install_proof | PASS | eval/run_first_user_release_gate.py rc=0<br>Fresh venv local wheel install, borg --version, borg rescue text/json, borg-doctor --json, setup-claude verify all passed in release gate output. | (none) | Repeat from a clean external clone/PyPI or pipx path before broad public claim; record full transcript and version consistency. |
| public_security_baseline | PASS | python scripts/security_gate_check.py rc=0<br>privacy/prompt-injection/atom policy/firewall pytest rc=0 | (none) | Before public launch, add/attach reviewed external dependency/static/secret scan artifacts and confirm consent/redaction/revocation language in onboarding. |
| claims_docs_scrub | PASS | Claim scrub found 13 review-needed phrase occurrences; no clearly unsupported launch/adoption claim was identified by automated review.<br>Hits for “hundreds of users” and “proven collective intelligence” occur in the new plan as forbidden examples (“no …”), not as claims.<br>Hits for “public launch ready”/“production ready” are mostly negative caveats; docs/DEFI_AGENT_RESEARCH.md “Daily Active Users” is a DeFi research note and should be manually reviewed before public packaging. | (none) | Manually review scan findings and keep public copy saying controlled beta / supervised only until live and first-10 gates pass. |
| first_10_real_users | BLOCKED | eval/borg_proof_dashboard.json metrics.verified_external_users=0<br>docs/FIRST_10_BETA_READINESS.md present; status says pre-first-user beta contract, not real-user evidence<br>Verified real users kept at 0; no hard evidence artifact proving real external users was found. | No first-10 real-user outcomes exist. Simulated/logical users are excluded. | Invite first external users under consented narrow beta, record install/rescue/MCP outcomes in first-10 scoreboard, require >=8/10 install success and >=6/10 useful rescue before self-serve launch. |

## Fresh-process source canary

- Command rc: 0
- `unrelated_readiness`: stale_guidance=False, NO_CONFIDENT_MATCH=True, permission_guidance=False, length=654
  First 1000 chars:
  ```
  ACTION: proceed with normal debugging for python; Borg has no proven cache hit.

  STOP: do not force a weak or unrelated pack onto this task.

  VERIFY: collect the exact failing command/output and rerun borg_observe or borg_rescue only if new evidence appears.

  CONFIDENCE: BORG [NO CONFIDENT MATCH] -- no relevant traces, synthetic hits, or pack matches.

  NO_CONFIDENT_MATCH: No confident Borg match for python.
  Borg found no relevant real traces, synthetic hits, or exact pack class match.
  Proceed with normal reasoning; do not treat Borg as evidence for this task.
  After resolving: call borg_rate(helpful=True) only if Borg guidance was actually useful.
  ```
- `permission_denied`: stale_guidance=False, NO_CONFIDENT_MATCH=False, permission_guidance=True, length=558
  First 1000 chars:
  ```
  VERIFY: execute the pack's first checkpoint, then rerun the exact failing command

  CONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]

  ------------------------------------------------------------
  PACK GUIDANCE (bash-permission-denied)
  1. Check file permissions: ls -la <file>
  2. Add execute permission: chmod +x <script.sh>
  3. For directories: chmod +x <directory>
  4. Check ownership: ls -ln <file>
  5. Run as appropriate user: sudo <command>
  6. For SSH keys: chmod 600 ~/.ssh/id_rsa
  ------------------------------------------------------------
  ```

## Claims/docs scrub

Scan findings: 13 review-needed occurrences. Automated review found no clearly unsupported launch/adoption claim; forbidden-phrase hits in the new plan are negative examples, not claims.

| Path | Line | Phrase | Text |
|---|---:|---|---|
| docs/20260504-0635_BORG_CURRENT_STATE_AND_OUTSTANDING_DEEP_DIVE.md | 20 | production ready |    The safe atom substrate exists, but global/tenant promotion, sybil resistance, live adoption proof, full-suite green state, clean release packaging, and controlled utility eval are not done. Do not market as “massive-agent production ready” or “agent-level improvement proven.” |
| docs/20260513_BORG_MULTI_REPO_PRODUCTION_CLEANUP_CUTOVER_PROPOSAL.md | 337 | production ready | Borg is **not done** and not broad-production ready. |
| docs/20260514_BORG_PRODUCTION_REBUILD_MASTER_PLAN.md | 725 | public launch ready | - “Fully autonomous broad public launch ready.” |
| docs/20260514_BORG_PUBLIC_LAUNCH_READINESS_PLAN.md | 66 | proven collective intelligence |   - no “proven collective intelligence” |
| docs/20260514_BORG_PUBLIC_LAUNCH_READINESS_PLAN.md | 67 | hundreds of users |   - no “hundreds of users” unless verified |
| docs/20260514_BORG_PUBLIC_LAUNCH_READINESS_PLAN.md | 68 | production ready |   - no “public production ready” before Gate 6 |
| docs/BORG_PROOF_DASHBOARD.html | 6 | public launch ready | <p class="note"><strong>Ready to share Git now?</strong> YES, supervised only. Do not present as unattended or public launch ready. Capture real first-user outcome evidence immediately.</p> |
| docs/BORG_PROOF_DASHBOARD.html | 26 | public launch ready | **Ready to share Git now?** YES, supervised only — Do not present as unattended or public launch ready.; Capture real first-user outcome evidence immediately. |
| docs/BORG_PROOF_DASHBOARD.md | 14 | public launch ready | **Ready to share Git now?** YES, supervised only — Do not present as unattended or public launch ready.; Capture real first-user outcome evidence immediately. |
| docs/DEFI_AGENT_RESEARCH.md | 249 | active users |   - Daily Active Users: 31,172 |
| docs/public/proof-dashboard/index.html | 6 | public launch ready | <p class="note"><strong>Ready to share Git now?</strong> YES, supervised only. Do not present as unattended or public launch ready. Capture real first-user outcome evidence immediately.</p> |
| docs/public/proof-dashboard/index.html | 26 | public launch ready | **Ready to share Git now?** YES, supervised only — Do not present as unattended or public launch ready.; Capture real first-user outcome evidence immediately. |
| eval/borg_proof_dashboard.json | 313 | public launch ready |       "Do not present as unattended or public launch ready.", |

## First-10 scoreboard evidence

- Verified real external users: 0
- eval/borg_proof_dashboard.json metrics.verified_external_users=0
- docs/FIRST_10_BETA_READINESS.md present; status says pre-first-user beta contract, not real-user evidence
- No fabricated user evidence added.

## Exact blockers

- live_mcp_runtime_identity: Requires explicit approved live MCP/Hermes reload window and live served canary; do not claim live MCP fixed without reload.
- repo_hygiene_release_branch: Dirty tree is not a surgical public-readiness release branch; build/dist side effects need review/restoration; no push/admin check performed.
- first_10_real_users: No first-10 real-user outcomes exist. Simulated/logical users are excluded.

## Exact next actions

- live_mcp_runtime_identity: Get explicit approval for a supervised reload, reload live MCP without killing gateway, then run live borg_runtime_fingerprint plus live borg_observe unrelated/permission canaries.
- repo_hygiene_release_branch: Create/checkout a clean release branch, restore accidental build/dist deletions or deliberately ignore generated dirs, stage only reviewed public-readiness docs/eval/source changes, then rerun git status/diff.
- self_serve_install_proof: Repeat from a clean external clone/PyPI or pipx path before broad public claim; record full transcript and version consistency.
- public_security_baseline: Before public launch, add/attach reviewed external dependency/static/secret scan artifacts and confirm consent/redaction/revocation language in onboarding.
- claims_docs_scrub: Manually review scan findings and keep public copy saying controlled beta / supervised only until live and first-10 gates pass.
- first_10_real_users: Invite first external users under consented narrow beta, record install/rescue/MCP outcomes in first-10 scoreboard, require >=8/10 install success and >=6/10 useful rescue before self-serve launch.

## Commands with rc/stdout/stderr

### `python -m pytest -q borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_runtime_fingerprint.py`
rc: `0`
stdout:
```
.......................                                                  [100%]
23 passed in 5.50s

```
stderr:
(empty)

### `python scripts/build_borg_proof_dashboard.py`
rc: `0`
stdout:
```
docs/BORG_PROOF_DASHBOARD.md
docs/BORG_PROOF_DASHBOARD.html
eval/borg_proof_dashboard.json
docs/public/proof-dashboard/index.html

```
stderr:
(empty)

### `python scripts/borg_proof_dashboard_lint.py`
rc: `0`
stdout:
```
PASS: Borg proof dashboard lint

```
stderr:
(empty)

### `python -m pytest -q eval/tests/test_borg_proof_dashboard.py`
rc: `0`
stdout:
```
..                                                                       [100%]
2 passed in 0.02s

```
stderr:
(empty)

### `python eval/run_first_user_release_gate.py`
rc: `0`
stdout:
```
{
  "generated_at_utc": "2026-05-14T14:42:06Z",
  "repo": "/root/hermes-workspace/borg",
  "results": [
    {
      "command": null,
      "detail": "present",
      "duration_s": null,
      "name": "file:pyproject.toml",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "present",
      "duration_s": null,
      "name": "file:borg/__init__.py",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "present",
      "duration_s": null,
      "name": "file:README.md",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "present",
      "duration_s": null,
      "name": "file:LICENSE",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "pyproject=3.3.1 runtime=3.3.1",
      "duration_s": null,
      "name": "version_consistency",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "borg, borg-mcp, borg-doctor declared",
      "duration_s": null,
      "name": "script_entrypoints",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "Homepage/Repository/Documentation/Issues present",
      "duration_s": null,
      "name": "project_urls",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "README must include install + rescue as first-user path",
      "duration_s": null,
      "name": "readme_day_one_path",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "present and non-placeholder",
      "duration_s": null,
      "name": "security_artifact:eval/security_hardening_baseline.json",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "present and non-placeholder",
      "duration_s": null,
      "name": "security_artifact:docs/SECURITY_HARDENING_BASELINE.md",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "present and non-placeholder",
      "duration_s": null,
      "name": "security_artifact:.github/workflows/security-gates.yml",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": null,
      "detail": "present and non-placeholder",
      "duration_s": null,
      "name": "security_artifact:scripts/security_gate_check.py",
      "passed": true,
      "returncode": null,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": [
        "/root/.hermes/hermes-agent/venv/bin/python",
        "-m",
        "venv",
        "/tmp/borg-first-user-gate-kygo2xr8"
      ],
      "detail": "exit=0",
      "duration_s": 3.079,
      "name": "fresh_venv_create",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": ""
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/python",
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "build"
      ],
      "detail": "exit=0",
      "duration_s": 1.577,
      "name": "install_build_tooling",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "Requirement already satisfied: pip in /tmp/borg-first-user-gate-kygo2xr8/lib/python3.11/site-packages (24.0)\nCollecting pip\n  Using cached pip-26.1.1-py3-none-any.whl.metadata (4.6 kB)\nCollecting build\n  Using cached build-1.5.0-py3-none-any.whl.metadata (5.7 kB)\nCollecting packaging>=24.0 (from build)\n  Using cached packaging-26.2-py3-none-any.whl.metadata (3.5 kB)\nCollecting pyproject_hooks (from build)\n  Using cached pyproject_hooks-1.2.0-py3-none-any.whl.metadata (1.3 kB)\nUsing cached pip-26.1.1-py3-none-any.whl (1.8 MB)\nUsing cached build-1.5.0-py3-none-any.whl (26 kB)\nUsing cached packaging-26.2-py3-none-any.whl (100 kB)\nUsing cached pyproject_hooks-1.2.0-py3-none-any.whl (10 kB)\nInstalling collected packages: pyproject_hooks, pip, packaging, build\n  Attempting uninstall: pip\n    Found existing installation: pip 24.0\n    Uninstalling pip-24.0:\n      Successfully uninstalled pip-24.0\nSuccessfully installed build-1.5.0 packaging-26.2 pip-26.1.1 pyproject_hooks-1.2.0\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/python",
        "-m",
        "build",
        "/root/hermes-workspace/borg"
      ],
      "detail": "exit=0",
      "duration_s": 4.278,
      "name": "build_wheel",
      "passed": true,
      "returncode": 0,
      "stderr": "* Creating isolated environment: venv+pip...\n* Installing packages in isolated environment:\n  - setuptools>=68\n  - wheel\n* Getting build dependencies for sdist...\n* Building sdist...\n* Building wheel from sdist\n* Creating isolated environment: venv+pip...\n* Installing packages in isolated environment:\n  - setuptools>=68\n  - wheel\n* Getting build dependencies for wheel...\n* Building wheel...\n",
      "stdout": "running egg_info\nwriting agent_borg.egg-info/PKG-INFO\nwriting dependency_links to agent_borg.egg-info/dependency_links.txt\nwriting entry points to agent_borg.egg-info/entry_points.txt\nwriting requirements to agent_borg.egg-info/requires.txt\nwriting top-level names to agent_borg.egg-info/top_level.txt\nreading manifest file 'agent_borg.egg-info/SOURCES.txt'\nadding license file 'LICENSE'\nwriting manifest file 'agent_borg.egg-info/SOURCES.txt'\nrunning sdist\nrunning egg_info\nwriting agent_borg.egg-info/PKG-INFO\nwriting dependency_links to agent_borg.egg-info/dependency_links.txt\nwriting entry points to agent_borg.egg-info/entry_points.txt\nwriting requirements to agent_borg.egg-info/requires.txt\nwriting top-level names to agent_borg.egg-info/top_level.txt\nreading manifest file 'agent_borg.egg-info/SOURCES.txt'\nadding license file 'LICENSE'\nwriting manifest file 'agent_borg.egg-info/SOURCES.txt'\nrunning check\ncreating agent_borg-3.3.1\ncreating agent_borg-3.3.1/agent_borg.egg-info\ncreating agent_borg-3.3.1/borg\ncreating agent_borg-3.3.1/borg/benchmark/skills\ncreating agent_borg-3.3.1/borg/benchmarks\ncreating agent_borg-3.3.1/borg/benchmarks/tests\ncreating agent_borg-3.3.1/borg/cli\ncreating agent_borg-3.3.1/borg/core\ncreating agent_borg-3.3.1/borg/db\ncreating agent_borg-3.3.1/borg/dojo\ncreating agent_borg-3.3.1/borg/dojo/tests\ncreating agent_borg-3.3.1/borg/eval\ncreating agent_borg-3.3.1/borg/fleet\ncreating agent_borg-3.3.1/borg/integrations\ncreating agent_borg-3.3.1/borg/seeds_data\ncreating agent_borg-3.3.1/borg/seeds_data/borg\ncreating agent_borg-3.3.1/borg/seeds_data/borg-autopilot\ncreating agent_borg-3.3.1/borg/seeds_data/packs\ncreating agent_borg-3.3.1/borg/tests\ncreating agent_borg-3.3.1/borg/tests/fixtures/openclaw\ncreating agent_borg-3.3.1/tests\ncopying files to agent_borg-3.3.1...\ncopying LICENSE -> agent_borg-3.3.1\ncopying README.md -> agent_borg-3.3.1\ncopying pyproject.toml -> agent_borg-3.3.1\ncopying agent_borg.egg-info/PKG-INFO -> agent_borg-3.3.1/agent_borg.egg-info\ncopying agent_borg.egg-info/SOURCES.txt -> agent_borg-3.3.1/agent_borg.egg-info\ncopying agent_borg.egg-info/dependency_links.txt -> agent_borg-3.3.1/agent_borg.egg-info\ncopying agent_borg.egg-info/entry_points.txt -> agent_borg-3.3.1/agent_borg.egg-info\ncopying agent_borg.egg-info/requires.txt -> agent_borg-3.3.1/agent_borg.egg-info\ncopying agent_borg.egg-info/top_level.txt -> agent_borg-3.3.1/agent_borg.egg-info\ncopying borg/__init__.py -> agent_borg-3.3.1/borg\ncopying borg/cli.py -> agent_borg-3.3.1/borg\ncopying borg/benchmark/skills/test_skills.py -> agent_borg-3.3.1/borg/benchmark/skills\ncopying borg/benchmarks/__init__.py -> agent_borg-3.3.1/borg/benchmarks\ncopying borg/benchmarks/report.py -> agent_borg-3.3.1/borg/benchmarks\ncopying borg/benchmarks/runner.py -> agent_borg-3.3.1/borg/benchmarks\ncopying borg/benchmarks/scorer.py -> agent_borg-3.3.1/borg/benchmarks\ncopying borg/benchmarks/tasks.py -> agent_borg-3.3.1/borg/benchmarks\ncopying borg/benchmarks/tests/__init__.py -> agent_borg-3.3.1/borg/benchmarks/tests\ncopying borg/benchmarks/tests/test_benchmarks.py -> agent_borg-3.3.1/borg/benchmarks/tests\ncopying borg/cli/__init__.py -> agent_borg-3.3.1/borg/cli\ncopying borg/cli/__main__.py -> agent_borg-3.3.1/borg/cli\ncopying borg/cli/doctor.py -> agent_borg-3.3.1/borg/cli\ncopying borg/cli/install.py -> agent_borg-3.3.1/borg/cli\ncopying borg/core/__init__.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/agentskills_converter.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/aggregator.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/apply.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/atom_policy.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/atom_retrieval.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/atom_store.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/atom_tenant.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/bm25_index.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/causal.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/changes.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/clustering.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/cold_start.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/conditions.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/confidence_gate.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/contextual_selector.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/convert.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/crypto.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/dirs.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/embeddings.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/failure_memory.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/feedback_loop.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/first_user_readiness.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/generate.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/generator.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/learning_atoms.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/mutation_engine.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/negative_traces.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/openclaw_converter.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/pack_taxonomy.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/privacy.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/prompt_injection.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/proof_gates.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/publish.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/rescue.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/runtime_fingerprint.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/safety.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/schema.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/search.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/seed_loader.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/seeds.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/semantic_search.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/session.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/signals.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/stack.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/synthesis.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/telemetry.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/temporal.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/trace_matcher.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/traces.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/uri.py -> agent_borg-3.3.1/borg/core\ncopying borg/core/v3_integration.py -> agent_borg-3.3.1/borg/core\ncopying borg/db/__init__.py -> agent_borg-3.3.1/borg/db\ncopying borg/db/analytics.py -> agent_borg-3.3.1/borg/db\ncopying borg/db/embeddings.py -> agent_borg-3.3.1/borg/db\ncopying borg/db/migrations.py -> agent_borg-3.3.1/borg/db\ncopying borg/db/reputation.py -> agent_borg-3.3.1/borg/db\ncopying borg/db/store.py -> agent_borg-3.3.1/borg/db\ncopying borg/dojo/__init__.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/auto_fixer.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/cron_runner.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/data_models.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/failure_classifier.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/learning_curve.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/pipeline.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/report_generator.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/session_reader.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/skill_gap_detector.py -> agent_borg-3.3.1/borg/dojo\ncopying borg/dojo/tests/__init__.py -> agent_borg-3.3.1/borg/dojo/tests\ncopying borg/dojo/tests/test_auto_fixer.py -> agent_borg-3.3.1/borg/dojo/tests\ncopying borg/dojo/tests/test_failure_classifier.py -> agent_borg-3.3.1/borg/dojo/tests\ncopying borg/dojo/tests/test_learning_curve.py -> agent_borg-3.3.1/borg/dojo/tests\ncopying borg/dojo/tests/test_pipeline.py -> agent_borg-3.3.1/borg/dojo/tests\ncopying borg/dojo/tests/test_report_generator.py -> agent_borg-3.3.1/borg/dojo/tests\ncopying borg/dojo/tests/test_session_reader.py -> agent_borg-3.3.1/borg/dojo/tests\ncopying borg/dojo/tests/test_skill_gap_detector.py -> agent_borg-3.3.1/borg/dojo/tests\ncopying borg/eval/__init__.py -> agent_borg-3.3.1/borg/eval\ncopying borg/eval/ab_test.py -> agent_borg-3.3.1/borg/eval\ncopying borg/eval/e1a_seed_pack_validation.py -> agent_borg-3.3.1/borg/eval\ncopying borg/eval/production_smoke_test.py -> agent_borg-3.3.1/borg/eval\ncopying borg/fleet/syncer.py -> agent_borg-3.3.1/borg/fleet\ncopying borg/integrations/__init__.py -> agent_borg-3.3.1/borg/integrations\ncopying borg/integrations/agent_hook.py -> agent_borg-3.3.1/borg/integrations\ncopying borg/integrations/http_server.py -> agent_borg-3.3.1/borg/integrations\ncopying borg/integrations/mcp_server.py -> agent_borg-3.3.1/borg/integrations\ncopying borg/integrations/nudge.py -> agent_borg-3.3.1/borg/integrations\ncopying borg/seeds_data/circular-dependency-migration.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/code-review.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/collective_seed.json -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/configuration-error.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/defi-risk-check.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/defi-yield-strategy.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/extended_seeds.yaml -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/import-cycle.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/migration-state-desync.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/missing-dependency.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/missing-foreign-key.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/null-pointer-chain.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/permission-denied.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/race-condition.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/schema-drift.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/systematic-debugging.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/test-driven-development.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/timeout-hang.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/type-mismatch.md -> agent_borg-3.3.1/borg/seeds_data\ncopying borg/seeds_data/borg/SKILL.md -> agent_borg-3.3.1/borg/seeds_data/borg\ncopying borg/seeds_data/borg-autopilot/SKILL.md -> agent_borg-3.3.1/borg/seeds_data/borg-autopilot\ncopying borg/seeds_data/packs/bash-permission-denied.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/django-circular-dependency.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/django-migration-state.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/django-null-pointer.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/django-schema-drift.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/docker-no-space.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/git-merge-conflict.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/pytest-flaky-test.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/python-import-cycle.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/python-missing-dependency.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/seeds_data/packs/systematic-debugging.workflow.yaml -> agent_borg-3.3.1/borg/seeds_data/packs\ncopying borg/tests/__init__.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_agent_hook.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_aggregator.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_analytics.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_apply.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_atom_policy.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_atom_retrieval_firewall.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_atom_store.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_atom_tenant.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_borg_observe_confidence_gate.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_borg_observe_wrapper.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_change_awareness.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_classify_error.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_cli.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_cli_atom.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_conditions.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_confidence_gate.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_contextual_selector.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_convert.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_convert_openclaw.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_dirs.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_distribution_readiness.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_dojo_pipeline.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_e2e_learning_loop.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_e2e_learning_loop_v3.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_embeddings_schema_compat.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_failure_memory.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_feedback_loop.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_first_10_readiness.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_first_user_cli_contract.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_fleet_syncer.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_generate.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_generator.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_golden_queries.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_learning_atom_publish.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_learning_atoms.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_mcp_hardening.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_mcp_server.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_mcp_server_extended.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_mutation_engine.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_nudge.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_observe_search_roundtrip.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_openclaw_converter.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_pack_compatibility.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_privacy.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_privacy_structured.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_prompt_injection.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_proof_gates.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_public_api_check.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_publish.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_publish_flow_debug.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_publish_flow_integration.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_publish_sybil.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_pull_network.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_reputation.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_reputation_integration.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_rescue.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_runtime_doctor.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_runtime_fingerprint.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_safety.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_schema.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_search.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_semantic_search.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_session.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_start_signals.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_store.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_store_concurrency.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_telemetry.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_uri.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_v3_integration.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_version_consistency.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/test_wiring.py -> agent_borg-3.3.1/borg/tests\ncopying borg/tests/fixtures/openclaw/quick_validate.py -> agent_borg-3.3.1/borg/tests/fixtures/openclaw\ncopying tests/test_e2e_verify.py -> agent_borg-3.3.1/tests\ncopying agent_borg.egg-info/SOURCES.txt -> agent_borg-3.3.1/agent_borg.egg-info\nWriting agent_borg-3.3.1/setup.cfg\nCreating tar archive\nremoving 'agent_borg-3.3.1' (and everything under it)\nrunning egg_info\nwriting agent_borg.egg-info/PKG-INFO\nwriting dependency_links to agent_borg.egg-info/dependency_links.txt\nwriting entry points to agent_borg.egg-info/entry_points.txt\nwriting requirements to agent_borg.egg-info/requires.txt\nwriting top-level names to agent_borg.egg-info/top_level.txt\nreading manifest file 'agent_borg.egg-info/SOURCES.txt'\nadding license file 'LICENSE'\nwriting manifest file 'agent_borg.egg-info/SOURCES.txt'\nrunning bdist_wheel\nrunning build\nrunning build_py\ncreating build/lib/borg\ncopying borg/__init__.py -> build/lib/borg\ncopying borg/cli.py -> build/lib/borg\ncreating build/lib/borg/tests\ncopying borg/tests/test_conditions.py -> build/lib/borg/tests\ncopying borg/tests/test_rescue.py -> build/lib/borg/tests\ncopying borg/tests/test_v3_integration.py -> build/lib/borg/tests\ncopying borg/tests/test_public_api_check.py -> build/lib/borg/tests\ncopying borg/tests/test_publish.py -> build/lib/borg/tests\ncopying borg/tests/test_mcp_server_extended.py -> build/lib/borg/tests\ncopying borg/tests/test_reputation_integration.py -> build/lib/borg/tests\ncopying borg/tests/test_wiring.py -> build/lib/borg/tests\ncopying borg/tests/test_learning_atoms.py -> build/lib/borg/tests\ncopying borg/tests/test_failure_memory.py -> build/lib/borg/tests\ncopying borg/tests/test_privacy.py -> build/lib/borg/tests\ncopying borg/tests/test_agent_hook.py -> build/lib/borg/tests\ncopying borg/tests/test_proof_gates.py -> build/lib/borg/tests\ncopying borg/tests/test_prompt_injection.py -> build/lib/borg/tests\ncopying borg/tests/test_feedback_loop.py -> build/lib/borg/tests\ncopying borg/tests/test_publish_sybil.py -> build/lib/borg/tests\ncopying borg/tests/test_store_concurrency.py -> build/lib/borg/tests\ncopying borg/tests/test_generate.py -> build/lib/borg/tests\ncopying borg/tests/test_e2e_learning_loop.py -> build/lib/borg/tests\ncopying borg/tests/test_embeddings_schema_compat.py -> build/lib/borg/tests\ncopying borg/tests/test_semantic_search.py -> build/lib/borg/tests\ncopying borg/tests/test_telemetry.py -> build/lib/borg/tests\ncopying borg/tests/test_mcp_server.py -> build/lib/borg/tests\ncopying borg/tests/test_search.py -> build/lib/borg/tests\ncopying borg/tests/test_contextual_selector.py -> build/lib/borg/tests\ncopying borg/tests/test_analytics.py -> build/lib/borg/tests\ncopying borg/tests/test_pull_network.py -> build/lib/borg/tests\ncopying borg/tests/test_apply.py -> build/lib/borg/tests\ncopying borg/tests/test_runtime_fingerprint.py -> build/lib/borg/tests\ncopying borg/tests/test_nudge.py -> build/lib/borg/tests\ncopying borg/tests/test_runtime_doctor.py -> build/lib/borg/tests\ncopying borg/tests/test_classify_error.py -> build/lib/borg/tests\ncopying borg/tests/test_generator.py -> build/lib/borg/tests\ncopying borg/tests/__init__.py -> build/lib/borg/tests\ncopying borg/tests/test_confidence_gate.py -> build/lib/borg/tests\ncopying borg/tests/test_atom_retrieval_firewall.py -> build/lib/borg/tests\ncopying borg/tests/test_fleet_syncer.py -> build/lib/borg/tests\ncopying borg/tests/test_atom_store.py -> build/lib/borg/tests\ncopying borg/tests/test_first_10_readiness.py -> build/lib/borg/tests\ncopying borg/tests/test_cli.py -> build/lib/borg/tests\ncopying borg/tests/test_atom_policy.py -> build/lib/borg/tests\ncopying borg/tests/test_openclaw_converter.py -> build/lib/borg/tests\ncopying borg/tests/test_publish_flow_integration.py -> build/lib/borg/tests\ncopying borg/tests/test_cli_atom.py -> build/lib/borg/tests\ncopying borg/tests/test_dirs.py -> build/lib/borg/tests\ncopying borg/tests/test_atom_tenant.py -> build/lib/borg/tests\ncopying borg/tests/test_borg_observe_wrapper.py -> build/lib/borg/tests\ncopying borg/tests/test_borg_observe_confidence_gate.py -> build/lib/borg/tests\ncopying borg/tests/test_golden_queries.py -> build/lib/borg/tests\ncopying borg/tests/test_convert_openclaw.py -> build/lib/borg/tests\ncopying borg/tests/test_start_signals.py -> build/lib/borg/tests\ncopying borg/tests/test_observe_search_roundtrip.py -> build/lib/borg/tests\ncopying borg/tests/test_pack_compatibility.py -> build/lib/borg/tests\ncopying borg/tests/test_first_user_cli_contract.py -> build/lib/borg/tests\ncopying borg/tests/test_uri.py -> build/lib/borg/tests\ncopying borg/tests/test_convert.py -> build/lib/borg/tests\ncopying borg/tests/test_session.py -> build/lib/borg/tests\ncopying borg/tests/test_learning_atom_publish.py -> build/lib/borg/tests\ncopying borg/tests/test_safety.py -> build/lib/borg/tests\ncopying borg/tests/test_reputation.py -> build/lib/borg/tests\ncopying borg/tests/test_privacy_structured.py -> build/lib/borg/tests\ncopying borg/tests/test_mutation_engine.py -> build/lib/borg/tests\ncopying borg/tests/test_mcp_hardening.py -> build/lib/borg/tests\ncopying borg/tests/test_store.py -> build/lib/borg/tests\ncopying borg/tests/test_e2e_learning_loop_v3.py -> build/lib/borg/tests\ncopying borg/tests/test_version_consistency.py -> build/lib/borg/tests\ncopying borg/tests/test_distribution_readiness.py -> build/lib/borg/tests\ncopying borg/tests/test_schema.py -> build/lib/borg/tests\ncopying borg/tests/test_change_awareness.py -> build/lib/borg/tests\ncopying borg/tests/test_dojo_pipeline.py -> build/lib/borg/tests\ncopying borg/tests/test_publish_flow_debug.py -> build/lib/borg/tests\ncopying borg/tests/test_aggregator.py -> build/lib/borg/tests\ncreating build/lib/borg/dojo\ncopying borg/dojo/auto_fixer.py -> build/lib/borg/dojo\ncopying borg/dojo/report_generator.py -> build/lib/borg/dojo\ncopying borg/dojo/__init__.py -> build/lib/borg/dojo\ncopying borg/dojo/data_models.py -> build/lib/borg/dojo\ncopying borg/dojo/skill_gap_detector.py -> build/lib/borg/dojo\ncopying borg/dojo/pipeline.py -> build/lib/borg/dojo\ncopying borg/dojo/cron_runner.py -> build/lib/borg/dojo\ncopying borg/dojo/failure_classifier.py -> build/lib/borg/dojo\ncopying borg/dojo/session_reader.py -> build/lib/borg/dojo\ncopying borg/dojo/learning_curve.py -> build/lib/borg/dojo\ncreating build/lib/borg/integrations\ncopying borg/integrations/http_server.py -> build/lib/borg/integrations\ncopying borg/integrations/agent_hook.py -> build/lib/borg/integrations\ncopying borg/integrations/mcp_server.py -> build/lib/borg/integrations\ncopying borg/integrations/__init__.py -> build/lib/borg/integrations\ncopying borg/integrations/nudge.py -> build/lib/borg/integrations\ncreating build/lib/borg/benchmarks\ncopying borg/benchmarks/tasks.py -> build/lib/borg/benchmarks\ncopying borg/benchmarks/runner.py -> build/lib/borg/benchmarks\ncopying borg/benchmarks/scorer.py -> build/lib/borg/benchmarks\ncopying borg/benchmarks/__init__.py -> build/lib/borg/benchmarks\ncopying borg/benchmarks/report.py -> build/lib/borg/benchmarks\ncreating build/lib/borg/eval\ncopying borg/eval/__init__.py -> build/lib/borg/eval\ncopying borg/eval/ab_test.py -> build/lib/borg/eval\ncopying borg/eval/production_smoke_test.py -> build/lib/borg/eval\ncopying borg/eval/e1a_seed_pack_validation.py -> build/lib/borg/eval\ncreating build/lib/borg/fleet\ncopying borg/fleet/syncer.py -> build/lib/borg/fleet\ncreating build/lib/borg/cli\ncopying borg/cli/__init__.py -> build/lib/borg/cli\ncopying borg/cli/install.py -> build/lib/borg/cli\ncopying borg/cli/doctor.py -> build/lib/borg/cli\ncopying borg/cli/__main__.py -> build/lib/borg/cli\ncreating build/lib/borg/db\ncopying borg/db/migrations.py -> build/lib/borg/db\ncopying borg/db/embeddings.py -> build/lib/borg/db\ncopying borg/db/reputation.py -> build/lib/borg/db\ncopying borg/db/store.py -> build/lib/borg/db\ncopying borg/db/__init__.py -> build/lib/borg/db\ncopying borg/db/analytics.py -> build/lib/borg/db\ncreating build/lib/borg/core\ncopying borg/core/atom_policy.py -> build/lib/borg/core\ncopying borg/core/publish.py -> build/lib/borg/core\ncopying borg/core/embeddings.py -> build/lib/borg/core\ncopying borg/core/causal.py -> build/lib/borg/core\ncopying borg/core/dirs.py -> build/lib/borg/core\ncopying borg/core/semantic_search.py -> build/lib/borg/core\ncopying borg/core/clustering.py -> build/lib/borg/core\ncopying borg/core/confidence_gate.py -> build/lib/borg/core\ncopying borg/core/generator.py -> build/lib/borg/core\ncopying borg/core/synthesis.py -> build/lib/borg/core\ncopying borg/core/trace_matcher.py -> build/lib/borg/core\ncopying borg/core/mutation_engine.py -> build/lib/borg/core\ncopying borg/core/telemetry.py -> build/lib/borg/core\ncopying borg/core/openclaw_converter.py -> build/lib/borg/core\ncopying borg/core/session.py -> build/lib/borg/core\ncopying borg/core/privacy.py -> build/lib/borg/core\ncopying borg/core/crypto.py -> build/lib/borg/core\ncopying borg/core/proof_gates.py -> build/lib/borg/core\ncopying borg/core/first_user_readiness.py -> build/lib/borg/core\ncopying borg/core/contextual_selector.py -> build/lib/borg/core\ncopying borg/core/apply.py -> build/lib/borg/core\ncopying borg/core/negative_traces.py -> build/lib/borg/core\ncopying borg/core/v3_integration.py -> build/lib/borg/core\ncopying borg/core/atom_tenant.py -> build/lib/borg/core\ncopying borg/core/convert.py -> build/lib/borg/core\ncopying borg/core/schema.py -> build/lib/borg/core\ncopying borg/core/agentskills_converter.py -> build/lib/borg/core\ncopying borg/core/signals.py -> build/lib/borg/core\ncopying borg/core/__init__.py -> build/lib/borg/core\ncopying borg/core/traces.py -> build/lib/borg/core\ncopying borg/core/failure_memory.py -> build/lib/borg/core\ncopying borg/core/rescue.py -> build/lib/borg/core\ncopying borg/core/temporal.py -> build/lib/borg/core\ncopying borg/core/changes.py -> build/lib/borg/core\ncopying borg/core/seed_loader.py -> build/lib/borg/core\ncopying borg/core/atom_retrieval.py -> build/lib/borg/core\ncopying borg/core/conditions.py -> build/lib/borg/core\ncopying borg/core/pack_taxonomy.py -> build/lib/borg/core\ncopying borg/core/bm25_index.py -> build/lib/borg/core\ncopying borg/core/atom_store.py -> build/lib/borg/core\ncopying borg/core/feedback_loop.py -> build/lib/borg/core\ncopying borg/core/seeds.py -> build/lib/borg/core\ncopying borg/core/learning_atoms.py -> build/lib/borg/core\ncopying borg/core/cold_start.py -> build/lib/borg/core\ncopying borg/core/stack.py -> build/lib/borg/core\ncopying borg/core/prompt_injection.py -> build/lib/borg/core\ncopying borg/core/aggregator.py -> build/lib/borg/core\ncopying borg/core/safety.py -> build/lib/borg/core\ncopying borg/core/uri.py -> build/lib/borg/core\ncopying borg/core/runtime_fingerprint.py -> build/lib/borg/core\ncopying borg/core/generate.py -> build/lib/borg/core\ncopying borg/core/search.py -> build/lib/borg/core\ncreating build/lib/borg/tests/fixtures/openclaw\ncopying borg/tests/fixtures/openclaw/quick_validate.py -> build/lib/borg/tests/fixtures/openclaw\ncreating build/lib/borg/benchmark/skills\ncopying borg/benchmark/skills/test_skills.py -> build/lib/borg/benchmark/skills\ncreating build/lib/borg/dojo/tests\ncopying borg/dojo/tests/test_session_reader.py -> build/lib/borg/dojo/tests\ncopying borg/dojo/tests/test_learning_curve.py -> build/lib/borg/dojo/tests\ncopying borg/dojo/tests/test_skill_gap_detector.py -> build/lib/borg/dojo/tests\ncopying borg/dojo/tests/__init__.py -> build/lib/borg/dojo/tests\ncopying borg/dojo/tests/test_failure_classifier.py -> build/lib/borg/dojo/tests\ncopying borg/dojo/tests/test_auto_fixer.py -> build/lib/borg/dojo/tests\ncopying borg/dojo/tests/test_report_generator.py -> build/lib/borg/dojo/tests\ncopying borg/dojo/tests/test_pipeline.py -> build/lib/borg/dojo/tests\ncreating build/lib/borg/benchmarks/tests\ncopying borg/benchmarks/tests/test_benchmarks.py -> build/lib/borg/benchmarks/tests\ncopying borg/benchmarks/tests/__init__.py -> build/lib/borg/benchmarks/tests\nrunning egg_info\nwriting agent_borg.egg-info/PKG-INFO\nwriting dependency_links to agent_borg.egg-info/dependency_links.txt\nwriting entry points to agent_borg.egg-info/entry_points.txt\nwriting requirements to agent_borg.egg-info/requires.txt\nwriting top-level names to agent_borg.egg-info/top_level.txt\nreading manifest file 'agent_borg.egg-info/SOURCES.txt'\nadding license file 'LICENSE'\nwriting manifest file 'agent_borg.egg-info/SOURCES.txt'\ncreating build/lib/borg/seeds_data\ncopying borg/seeds_data/extended_seeds.yaml -> build/lib/borg/seeds_data\ncopying borg/seeds_data/collective_seed.json -> build/lib/borg/seeds_data\ncopying borg/seeds_data/permission-denied.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/schema-drift.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/defi-risk-check.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/missing-dependency.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/race-condition.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/null-pointer-chain.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/defi-yield-strategy.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/timeout-hang.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/import-cycle.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/type-mismatch.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/configuration-error.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/circular-dependency-migration.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/code-review.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/test-driven-development.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/systematic-debugging.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/migration-state-desync.md -> build/lib/borg/seeds_data\ncopying borg/seeds_data/missing-foreign-key.md -> build/lib/borg/seeds_data\ncreating build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/docker-no-space.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/pytest-flaky-test.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/django-circular-dependency.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/django-null-pointer.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/django-schema-drift.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/python-import-cycle.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/bash-permission-denied.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/python-missing-dependency.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/django-migration-state.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/git-merge-conflict.yaml -> build/lib/borg/seeds_data/packs\ncopying borg/seeds_data/packs/systematic-debugging.workflow.yaml -> build/lib/borg/seeds_data/packs\ncreating build/lib/borg/seeds_data/borg\ncopying borg/seeds_data/borg/SKILL.md -> build/lib/borg/seeds_data/borg\ncreating build/lib/borg/seeds_data/borg-autopilot\ncopying borg/seeds_data/borg-autopilot/SKILL.md -> build/lib/borg/seeds_data/borg-autopilot\ninstalling to build/bdist.linux-x86_64/wheel\nrunning install\nrunning install_lib\ncreating build/bdist.linux-x86_64/wheel\ncreating build/bdist.linux-x86_64/wheel/borg\ncreating build/bdist.linux-x86_64/wheel/borg/tests\ncopying build/lib/borg/tests/test_conditions.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_rescue.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_v3_integration.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_public_api_check.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_publish.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_mcp_server_extended.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_reputation_integration.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_wiring.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_learning_atoms.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_failure_memory.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_privacy.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_agent_hook.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_proof_gates.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_prompt_injection.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_feedback_loop.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_publish_sybil.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_store_concurrency.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_generate.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_e2e_learning_loop.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_embeddings_schema_compat.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_semantic_search.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_telemetry.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_mcp_server.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_search.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_contextual_selector.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_analytics.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_pull_network.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_apply.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_runtime_fingerprint.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_nudge.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_runtime_doctor.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_classify_error.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_generator.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_confidence_gate.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_atom_retrieval_firewall.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_fleet_syncer.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_atom_store.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_first_10_readiness.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_cli.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_atom_policy.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_openclaw_converter.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_publish_flow_integration.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_cli_atom.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncreating build/bdist.linux-x86_64/wheel/borg/tests/fixtures\ncreating build/bdist.linux-x86_64/wheel/borg/tests/fixtures/openclaw\ncopying build/lib/borg/tests/fixtures/openclaw/quick_validate.py -> build/bdist.linux-x86_64/wheel/./borg/tests/fixtures/openclaw\ncopying build/lib/borg/tests/test_dirs.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_atom_tenant.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_borg_observe_wrapper.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_borg_observe_confidence_gate.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_golden_queries.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_convert_openclaw.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_start_signals.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_observe_search_roundtrip.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_pack_compatibility.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_first_user_cli_contract.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_uri.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_convert.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_session.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_learning_atom_publish.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_safety.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_reputation.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_privacy_structured.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_mutation_engine.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_mcp_hardening.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_store.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_e2e_learning_loop_v3.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_version_consistency.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_distribution_readiness.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_schema.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_change_awareness.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_dojo_pipeline.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_publish_flow_debug.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncopying build/lib/borg/tests/test_aggregator.py -> build/bdist.linux-x86_64/wheel/./borg/tests\ncreating build/bdist.linux-x86_64/wheel/borg/benchmark\ncreating build/bdist.linux-x86_64/wheel/borg/benchmark/skills\ncopying build/lib/borg/benchmark/skills/test_skills.py -> build/bdist.linux-x86_64/wheel/./borg/benchmark/skills\ncreating build/bdist.linux-x86_64/wheel/borg/dojo\ncreating build/bdist.linux-x86_64/wheel/borg/dojo/tests\ncopying build/lib/borg/dojo/tests/test_session_reader.py -> build/bdist.linux-x86_64/wheel/./borg/dojo/tests\ncopying build/lib/borg/dojo/tests/test_learning_curve.py -> build/bdist.linux-x86_64/wheel/./borg/dojo/tests\ncopying build/lib/borg/dojo/tests/test_skill_gap_detector.py -> build/bdist.linux-x86_64/wheel/./borg/dojo/tests\ncopying build/lib/borg/dojo/tests/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/dojo/tests\ncopying build/lib/borg/dojo/tests/test_failure_classifier.py -> build/bdist.linux-x86_64/wheel/./borg/dojo/tests\ncopying build/lib/borg/dojo/tests/test_auto_fixer.py -> build/bdist.linux-x86_64/wheel/./borg/dojo/tests\ncopying build/lib/borg/dojo/tests/test_report_generator.py -> build/bdist.linux-x86_64/wheel/./borg/dojo/tests\ncopying build/lib/borg/dojo/tests/test_pipeline.py -> build/bdist.linux-x86_64/wheel/./borg/dojo/tests\ncopying build/lib/borg/dojo/auto_fixer.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/report_generator.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/data_models.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/skill_gap_detector.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/pipeline.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/cron_runner.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/failure_classifier.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/session_reader.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncopying build/lib/borg/dojo/learning_curve.py -> build/bdist.linux-x86_64/wheel/./borg/dojo\ncreating build/bdist.linux-x86_64/wheel/borg/integrations\ncopying build/lib/borg/integrations/http_server.py -> build/bdist.linux-x86_64/wheel/./borg/integrations\ncopying build/lib/borg/integrations/agent_hook.py -> build/bdist.linux-x86_64/wheel/./borg/integrations\ncopying build/lib/borg/integrations/mcp_server.py -> build/bdist.linux-x86_64/wheel/./borg/integrations\ncopying build/lib/borg/integrations/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/integrations\ncopying build/lib/borg/integrations/nudge.py -> build/bdist.linux-x86_64/wheel/./borg/integrations\ncreating build/bdist.linux-x86_64/wheel/borg/benchmarks\ncreating build/bdist.linux-x86_64/wheel/borg/benchmarks/tests\ncopying build/lib/borg/benchmarks/tests/test_benchmarks.py -> build/bdist.linux-x86_64/wheel/./borg/benchmarks/tests\ncopying build/lib/borg/benchmarks/tests/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/benchmarks/tests\ncopying build/lib/borg/benchmarks/tasks.py -> build/bdist.linux-x86_64/wheel/./borg/benchmarks\ncopying build/lib/borg/benchmarks/runner.py -> build/bdist.linux-x86_64/wheel/./borg/benchmarks\ncopying build/lib/borg/benchmarks/scorer.py -> build/bdist.linux-x86_64/wheel/./borg/benchmarks\ncopying build/lib/borg/benchmarks/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/benchmarks\ncopying build/lib/borg/benchmarks/report.py -> build/bdist.linux-x86_64/wheel/./borg/benchmarks\ncreating build/bdist.linux-x86_64/wheel/borg/eval\ncopying build/lib/borg/eval/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/eval\ncopying build/lib/borg/eval/ab_test.py -> build/bdist.linux-x86_64/wheel/./borg/eval\ncopying build/lib/borg/eval/production_smoke_test.py -> build/bdist.linux-x86_64/wheel/./borg/eval\ncopying build/lib/borg/eval/e1a_seed_pack_validation.py -> build/bdist.linux-x86_64/wheel/./borg/eval\ncopying build/lib/borg/__init__.py -> build/bdist.linux-x86_64/wheel/./borg\ncopying build/lib/borg/cli.py -> build/bdist.linux-x86_64/wheel/./borg\ncreating build/bdist.linux-x86_64/wheel/borg/fleet\ncopying build/lib/borg/fleet/syncer.py -> build/bdist.linux-x86_64/wheel/./borg/fleet\ncreating build/bdist.linux-x86_64/wheel/borg/cli\ncopying build/lib/borg/cli/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/cli\ncopying build/lib/borg/cli/install.py -> build/bdist.linux-x86_64/wheel/./borg/cli\ncopying build/lib/borg/cli/doctor.py -> build/bdist.linux-x86_64/wheel/./borg/cli\ncopying build/lib/borg/cli/__main__.py -> build/bdist.linux-x86_64/wheel/./borg/cli\ncreating build/bdist.linux-x86_64/wheel/borg/seeds_data\ncopying build/lib/borg/seeds_data/extended_seeds.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/permission-denied.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/collective_seed.json -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/schema-drift.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/defi-risk-check.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/missing-dependency.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/race-condition.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/null-pointer-chain.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/defi-yield-strategy.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/timeout-hang.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncreating build/bdist.linux-x86_64/wheel/borg/seeds_data/borg\ncopying build/lib/borg/seeds_data/borg/SKILL.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/borg\ncopying build/lib/borg/seeds_data/import-cycle.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncreating build/bdist.linux-x86_64/wheel/borg/seeds_data/borg-autopilot\ncopying build/lib/borg/seeds_data/borg-autopilot/SKILL.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/borg-autopilot\ncopying build/lib/borg/seeds_data/type-mismatch.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncreating build/bdist.linux-x86_64/wheel/borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/docker-no-space.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/pytest-flaky-test.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/django-circular-dependency.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/django-null-pointer.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/django-schema-drift.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/python-import-cycle.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/bash-permission-denied.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/python-missing-dependency.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/django-migration-state.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/git-merge-conflict.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/packs/systematic-debugging.workflow.yaml -> build/bdist.linux-x86_64/wheel/./borg/seeds_data/packs\ncopying build/lib/borg/seeds_data/configuration-error.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/circular-dependency-migration.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/code-review.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/test-driven-development.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/systematic-debugging.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/migration-state-desync.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncopying build/lib/borg/seeds_data/missing-foreign-key.md -> build/bdist.linux-x86_64/wheel/./borg/seeds_data\ncreating build/bdist.linux-x86_64/wheel/borg/db\ncopying build/lib/borg/db/migrations.py -> build/bdist.linux-x86_64/wheel/./borg/db\ncopying build/lib/borg/db/embeddings.py -> build/bdist.linux-x86_64/wheel/./borg/db\ncopying build/lib/borg/db/reputation.py -> build/bdist.linux-x86_64/wheel/./borg/db\ncopying build/lib/borg/db/store.py -> build/bdist.linux-x86_64/wheel/./borg/db\ncopying build/lib/borg/db/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/db\ncopying build/lib/borg/db/analytics.py -> build/bdist.linux-x86_64/wheel/./borg/db\ncreating build/bdist.linux-x86_64/wheel/borg/core\ncopying build/lib/borg/core/atom_policy.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/publish.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/embeddings.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/causal.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/dirs.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/semantic_search.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/clustering.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/confidence_gate.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/generator.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/synthesis.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/trace_matcher.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/mutation_engine.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/telemetry.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/openclaw_converter.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/session.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/privacy.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/crypto.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/proof_gates.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/first_user_readiness.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/contextual_selector.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/apply.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/negative_traces.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/v3_integration.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/atom_tenant.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/convert.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/schema.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/agentskills_converter.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/signals.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/__init__.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/traces.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/failure_memory.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/rescue.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/temporal.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/changes.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/seed_loader.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/atom_retrieval.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/conditions.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/pack_taxonomy.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/bm25_index.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/atom_store.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/feedback_loop.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/seeds.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/learning_atoms.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/cold_start.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/stack.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/prompt_injection.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/aggregator.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/safety.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/uri.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/runtime_fingerprint.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/generate.py -> build/bdist.linux-x86_64/wheel/./borg/core\ncopying build/lib/borg/core/search.py -> build/bdist.linux-x86_64/wheel/./borg/core\nrunning install_egg_info\nCopying agent_borg.egg-info to build/bdist.linux-x86_64/wheel/./agent_borg-3.3.1-py3.11.egg-info\nrunning install_scripts\ncreating build/bdist.linux-x86_64/wheel/agent_borg-3.3.1.dist-info/WHEEL\ncreating '/root/hermes-workspace/borg/dist/.tmp-ats4xvdv/agent_borg-3.3.1-py3-none-any.whl' and adding 'build/bdist.linux-x86_64/wheel' to it\nadding 'agent_borg-3.3.1.dist-info/licenses/LICENSE'\nadding 'borg/__init__.py'\nadding 'borg/cli.py'\nadding 'borg/benchmark/skills/test_skills.py'\nadding 'borg/benchmarks/__init__.py'\nadding 'borg/benchmarks/report.py'\nadding 'borg/benchmarks/runner.py'\nadding 'borg/benchmarks/scorer.py'\nadding 'borg/benchmarks/tasks.py'\nadding 'borg/benchmarks/tests/__init__.py'\nadding 'borg/benchmarks/tests/test_benchmarks.py'\nadding 'borg/cli/__init__.py'\nadding 'borg/cli/__main__.py'\nadding 'borg/cli/doctor.py'\nadding 'borg/cli/install.py'\nadding 'borg/core/__init__.py'\nadding 'borg/core/agentskills_converter.py'\nadding 'borg/core/aggregator.py'\nadding 'borg/core/apply.py'\nadding 'borg/core/atom_policy.py'\nadding 'borg/core/atom_retrieval.py'\nadding 'borg/core/atom_store.py'\nadding 'borg/core/atom_tenant.py'\nadding 'borg/core/bm25_index.py'\nadding 'borg/core/causal.py'\nadding 'borg/core/changes.py'\nadding 'borg/core/clustering.py'\nadding 'borg/core/cold_start.py'\nadding 'borg/core/conditions.py'\nadding 'borg/core/confidence_gate.py'\nadding 'borg/core/contextual_selector.py'\nadding 'borg/core/convert.py'\nadding 'borg/core/crypto.py'\nadding 'borg/core/dirs.py'\nadding 'borg/core/embeddings.py'\nadding 'borg/core/failure_memory.py'\nadding 'borg/core/feedback_loop.py'\nadding 'borg/core/first_user_readiness.py'\nadding 'borg/core/generate.py'\nadding 'borg/core/generator.py'\nadding 'borg/core/learning_atoms.py'\nadding 'borg/core/mutation_engine.py'\nadding 'borg/core/negative_traces.py'\nadding 'borg/core/openclaw_converter.py'\nadding 'borg/core/pack_taxonomy.py'\nadding 'borg/core/privacy.py'\nadding 'borg/core/prompt_injection.py'\nadding 'borg/core/proof_gates.py'\nadding 'borg/core/publish.py'\nadding 'borg/core/rescue.py'\nadding 'borg/core/runtime_fingerprint.py'\nadding 'borg/core/safety.py'\nadding 'borg/core/schema.py'\nadding 'borg/core/search.py'\nadding 'borg/core/seed_loader.py'\nadding 'borg/core/seeds.py'\nadding 'borg/core/semantic_search.py'\nadding 'borg/core/session.py'\nadding 'borg/core/signals.py'\nadding 'borg/core/stack.py'\nadding 'borg/core/synthesis.py'\nadding 'borg/core/telemetry.py'\nadding 'borg/core/temporal.py'\nadding 'borg/core/trace_matcher.py'\nadding 'borg/core/traces.py'\nadding 'borg/core/uri.py'\nadding 'borg/core/v3_integration.py'\nadding 'borg/db/__init__.py'\nadding 'borg/db/analytics.py'\nadding 'borg/db/embeddings.py'\nadding 'borg/db/migrations.py'\nadding 'borg/db/reputation.py'\nadding 'borg/db/store.py'\nadding 'borg/dojo/__init__.py'\nadding 'borg/dojo/auto_fixer.py'\nadding 'borg/dojo/cron_runner.py'\nadding 'borg/dojo/data_models.py'\nadding 'borg/dojo/failure_classifier.py'\nadding 'borg/dojo/learning_curve.py'\nadding 'borg/dojo/pipeline.py'\nadding 'borg/dojo/report_generator.py'\nadding 'borg/dojo/session_reader.py'\nadding 'borg/dojo/skill_gap_detector.py'\nadding 'borg/dojo/tests/__init__.py'\nadding 'borg/dojo/tests/test_auto_fixer.py'\nadding 'borg/dojo/tests/test_failure_classifier.py'\nadding 'borg/dojo/tests/test_learning_curve.py'\nadding 'borg/dojo/tests/test_pipeline.py'\nadding 'borg/dojo/tests/test_report_generator.py'\nadding 'borg/dojo/tests/test_session_reader.py'\nadding 'borg/dojo/tests/test_skill_gap_detector.py'\nadding 'borg/eval/__init__.py'\nadding 'borg/eval/ab_test.py'\nadding 'borg/eval/e1a_seed_pack_validation.py'\nadding 'borg/eval/production_smoke_test.py'\nadding 'borg/fleet/syncer.py'\nadding 'borg/integrations/__init__.py'\nadding 'borg/integrations/agent_hook.py'\nadding 'borg/integrations/http_server.py'\nadding 'borg/integrations/mcp_server.py'\nadding 'borg/integrations/nudge.py'\nadding 'borg/seeds_data/circular-dependency-migration.md'\nadding 'borg/seeds_data/code-review.md'\nadding 'borg/seeds_data/collective_seed.json'\nadding 'borg/seeds_data/configuration-error.md'\nadding 'borg/seeds_data/defi-risk-check.md'\nadding 'borg/seeds_data/defi-yield-strategy.md'\nadding 'borg/seeds_data/extended_seeds.yaml'\nadding 'borg/seeds_data/import-cycle.md'\nadding 'borg/seeds_data/migration-state-desync.md'\nadding 'borg/seeds_data/missing-dependency.md'\nadding 'borg/seeds_data/missing-foreign-key.md'\nadding 'borg/seeds_data/null-pointer-chain.md'\nadding 'borg/seeds_data/permission-denied.md'\nadding 'borg/seeds_data/race-condition.md'\nadding 'borg/seeds_data/schema-drift.md'\nadding 'borg/seeds_data/systematic-debugging.md'\nadding 'borg/seeds_data/test-driven-development.md'\nadding 'borg/seeds_data/timeout-hang.md'\nadding 'borg/seeds_data/type-mismatch.md'\nadding 'borg/seeds_data/borg/SKILL.md'\nadding 'borg/seeds_data/borg-autopilot/SKILL.md'\nadding 'borg/seeds_data/packs/bash-permission-denied.yaml'\nadding 'borg/seeds_data/packs/django-circular-dependency.yaml'\nadding 'borg/seeds_data/packs/django-migration-state.yaml'\nadding 'borg/seeds_data/packs/django-null-pointer.yaml'\nadding 'borg/seeds_data/packs/django-schema-drift.yaml'\nadding 'borg/seeds_data/packs/docker-no-space.yaml'\nadding 'borg/seeds_data/packs/git-merge-conflict.yaml'\nadding 'borg/seeds_data/packs/pytest-flaky-test.yaml'\nadding 'borg/seeds_data/packs/python-import-cycle.yaml'\nadding 'borg/seeds_data/packs/python-missing-dependency.yaml'\nadding 'borg/seeds_data/packs/systematic-debugging.workflow.yaml'\nadding 'borg/tests/__init__.py'\nadding 'borg/tests/test_agent_hook.py'\nadding 'borg/tests/test_aggregator.py'\nadding 'borg/tests/test_analytics.py'\nadding 'borg/tests/test_apply.py'\nadding 'borg/tests/test_atom_policy.py'\nadding 'borg/tests/test_atom_retrieval_firewall.py'\nadding 'borg/tests/test_atom_store.py'\nadding 'borg/tests/test_atom_tenant.py'\nadding 'borg/tests/test_borg_observe_confidence_gate.py'\nadding 'borg/tests/test_borg_observe_wrapper.py'\nadding 'borg/tests/test_change_awareness.py'\nadding 'borg/tests/test_classify_error.py'\nadding 'borg/tests/test_cli.py'\nadding 'borg/tests/test_cli_atom.py'\nadding 'borg/tests/test_conditions.py'\nadding 'borg/tests/test_confidence_gate.py'\nadding 'borg/tests/test_contextual_selector.py'\nadding 'borg/tests/test_convert.py'\nadding 'borg/tests/test_convert_openclaw.py'\nadding 'borg/tests/test_dirs.py'\nadding 'borg/tests/test_distribution_readiness.py'\nadding 'borg/tests/test_dojo_pipeline.py'\nadding 'borg/tests/test_e2e_learning_loop.py'\nadding 'borg/tests/test_e2e_learning_loop_v3.py'\nadding 'borg/tests/test_embeddings_schema_compat.py'\nadding 'borg/tests/test_failure_memory.py'\nadding 'borg/tests/test_feedback_loop.py'\nadding 'borg/tests/test_first_10_readiness.py'\nadding 'borg/tests/test_first_user_cli_contract.py'\nadding 'borg/tests/test_fleet_syncer.py'\nadding 'borg/tests/test_generate.py'\nadding 'borg/tests/test_generator.py'\nadding 'borg/tests/test_golden_queries.py'\nadding 'borg/tests/test_learning_atom_publish.py'\nadding 'borg/tests/test_learning_atoms.py'\nadding 'borg/tests/test_mcp_hardening.py'\nadding 'borg/tests/test_mcp_server.py'\nadding 'borg/tests/test_mcp_server_extended.py'\nadding 'borg/tests/test_mutation_engine.py'\nadding 'borg/tests/test_nudge.py'\nadding 'borg/tests/test_observe_search_roundtrip.py'\nadding 'borg/tests/test_openclaw_converter.py'\nadding 'borg/tests/test_pack_compatibility.py'\nadding 'borg/tests/test_privacy.py'\nadding 'borg/tests/test_privacy_structured.py'\nadding 'borg/tests/test_prompt_injection.py'\nadding 'borg/tests/test_proof_gates.py'\nadding 'borg/tests/test_public_api_check.py'\nadding 'borg/tests/test_publish.py'\nadding 'borg/tests/test_publish_flow_debug.py'\nadding 'borg/tests/test_publish_flow_integration.py'\nadding 'borg/tests/test_publish_sybil.py'\nadding 'borg/tests/test_pull_network.py'\nadding 'borg/tests/test_reputation.py'\nadding 'borg/tests/test_reputation_integration.py'\nadding 'borg/tests/test_rescue.py'\nadding 'borg/tests/test_runtime_doctor.py'\nadding 'borg/tests/test_runtime_fingerprint.py'\nadding 'borg/tests/test_safety.py'\nadding 'borg/tests/test_schema.py'\nadding 'borg/tests/test_search.py'\nadding 'borg/tests/test_semantic_search.py'\nadding 'borg/tests/test_session.py'\nadding 'borg/tests/test_start_signals.py'\nadding 'borg/tests/test_store.py'\nadding 'borg/tests/test_store_concurrency.py'\nadding 'borg/tests/test_telemetry.py'\nadding 'borg/tests/test_uri.py'\nadding 'borg/tests/test_v3_integration.py'\nadding 'borg/tests/test_version_consistency.py'\nadding 'borg/tests/test_wiring.py'\nadding 'borg/tests/fixtures/openclaw/quick_validate.py'\nadding 'agent_borg-3.3.1.dist-info/METADATA'\nadding 'agent_borg-3.3.1.dist-info/WHEEL'\nadding 'agent_borg-3.3.1.dist-info/entry_points.txt'\nadding 'agent_borg-3.3.1.dist-info/top_level.txt'\nadding 'agent_borg-3.3.1.dist-info/RECORD'\nremoving build/bdist.linux-x86_64/wheel\nSuccessfully built agent_borg-3.3.1.tar.gz and agent_borg-3.3.1-py3-none-any.whl\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/pip",
        "install",
        "--no-cache-dir",
        "/root/hermes-workspace/borg/dist/agent_borg-3.3.1-py3-none-any.whl"
      ],
      "detail": "exit=0",
      "duration_s": 1.219,
      "name": "fresh_install_agent_borg",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "Processing ./dist/agent_borg-3.3.1-py3-none-any.whl\nCollecting pyyaml>=6.0 (from agent-borg==3.3.1)\n  Downloading pyyaml-6.0.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)\nDownloading pyyaml-6.0.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (806 kB)\n   \u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501 806.6/806.6 kB 77.0 MB/s  0:00:00\nInstalling collected packages: pyyaml, agent-borg\n\nSuccessfully installed agent-borg-3.3.1 pyyaml-6.0.3\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg",
        "--version"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.104,
      "name": "borg_version",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "borg 3.3.1\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg",
        "--help"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.105,
      "name": "borg_help",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "usage: borg [-h] [--version]\n            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,rescue,first-10,recall,convert,generate,list,observe,atom,reputation,status,version,autopilot,setup-claude,setup-cursor,start}\n            ...\n\nBorg \u2014 Semantic reasoning cache for AI agents.\n\npositional arguments:\n  {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,rescue,first-10,recall,convert,generate,list,observe,atom,reputation,status,version,autopilot,setup-claude,setup-cursor,start}\n    search              Search for packs\n    pull                Fetch and save pack locally\n    try                 Preview pack without saving\n    init                Scaffold a new pack from scratch\n    apply               Start applying a pack\n    publish             Publish pack to GitHub\n    feedback            Generate feedback from session\n    feedback-v3         Record debug guidance outcome to V3 feedback loop\n    debug               Get structured debugging guidance for an error\n    rescue              Agent-ready rescue packet: ACTION / STOP / VERIFY /\n                        human receipt\n    first-10            Print first-user beta readiness gates and smoke path\n    recall              Query prior failure memory for an error message\n    convert             Convert SKILL.md / CLAUDE.md / .cursorrules to\n                        workflow pack\n    generate            Export pack to .cursorrules / .clinerules / CLAUDE.md\n                        / .windsurfrules\n    list                List local packs\n    observe             Record an observation as a trace\n    atom                Manage signed, sanitized, revocable learning atoms\n    reputation          Show agent reputation profile\n    status              Show local Borg runtime status\n    version             Show version\n    autopilot           Zero-config setup: install MCP + skill + auto-suggest\n    setup-claude        Configure borg MCP server for Claude\n    setup-cursor        Configure guild MCP server for Cursor\n    start               Get started \u2014 paste an error, get a fix in 30 seconds\n\noptions:\n  -h, --help            show this help message and exit\n  --version, -V         show program's version number and exit\n\nQuick Start:\n  borg start                     First time? Start here \u2014 paste an error, get a fix\n  borg rescue 'TypeError: ...'   Get ACTION / STOP / VERIFY rescue guidance\n  borg debug 'TypeError: ...'    Get structured debugging guidance for any error\n  borg search debugging          Search for workflow packs\n  borg generate systematic-debugging --format cursorrules\n                                  Export a debugging workflow for Cursor\n  borg setup-claude              Configure borg MCP for Claude Code\n  borg setup-cursor              Configure borg MCP for Cursor\n  borg first-10 --json           Print first-user beta gates and smoke path\n  borg autopilot                 Zero-config setup for Hermes\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg",
        "rescue",
        "ModuleNotFoundError: No module named flask",
        "--short"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.135,
      "name": "borg_rescue_text",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "BORG RESCUE\n============================================================\nstatus: matched\nmatch: missing_dependency [tested]\n\nACTION\n  - pip_install \u2014 run/check: pip install package-name\n  - install_in_venv \u2014 run/check: source venv/bin/activate && pip install package-name\n  - install_editable \u2014 run/check: pip install -e .\n\nSTOP\n  - pip install without a virtualenv \u2014 fails because Pollutes the global Python and causes version conflicts\n  - Manually copying module files to site-packages \u2014 fails because Version conflicts and no automatic updates\n  - Ignoring which virtualenv is activated \u2014 fails because The module is installed but in a different environment\n\nVERIFY\n  - rerun the exact failing command\n  - add or run the smallest regression test\n  - only then continue broader changes\n\nAGENT INSTRUCTION\nACTION: pip_install \u2014 run/check: pip install package-name\nSTOP: avoid pip install without a virtualenv \u2014 fails because Pollutes the global Python and causes version conflicts\nVERIFY: rerun the exact failing command\nSHOW HUMAN: say Borg found this rescue path and whether it worked.\n\nHUMAN RECEIPT\nBorg matched `missing_dependency` (tested). It gave the agent a next move, a dead-end to avoid, and a verification step.\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg",
        "rescue",
        "ModuleNotFoundError: No module named flask",
        "--json"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.144,
      "name": "borg_rescue_json",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "{\n  \"success\": true,\n  \"status\": \"matched\",\n  \"problem_class\": \"missing_dependency\",\n  \"confidence\": \"tested\",\n  \"action\": [\n    \"pip_install \u2014 run/check: pip install package-name\",\n    \"install_in_venv \u2014 run/check: source venv/bin/activate && pip install package-name\",\n    \"install_editable \u2014 run/check: pip install -e .\"\n  ],\n  \"stop\": [\n    \"pip install without a virtualenv \u2014 fails because Pollutes the global Python and causes version conflicts\",\n    \"Manually copying module files to site-packages \u2014 fails because Version conflicts and no automatic updates\",\n    \"Ignoring which virtualenv is activated \u2014 fails because The module is installed but in a different environment\"\n  ],\n  \"verify\": [\n    \"rerun the exact failing command\",\n    \"add or run the smallest regression test\",\n    \"only then continue broader changes\"\n  ],\n  \"next_command\": \"borg feedback-v3 --pack missing_dependency --success yes\",\n  \"agent_instruction\": \"ACTION: pip_install \u2014 run/check: pip install package-name\\nSTOP: avoid pip install without a virtualenv \u2014 fails because Pollutes the global Python and causes version conflicts\\nVERIFY: rerun the exact failing command\\nSHOW HUMAN: say Borg found this rescue path and whether it worked.\",\n  \"human_receipt\": \"Borg matched `missing_dependency` (tested). It gave the agent a next move, a dead-end to avoid, and a verification step.\",\n  \"guidance\": \"============================================================\\nERROR: ModuleNotFoundError: No module named flask\\n============================================================\\n[missing_dependency] (python)\\nProblem: Python cannot find a module or package\\n\\nROOT CAUSE:\\n  Category: missing_dependency\\n  Python cannot find the module because it is not installed in the current environment, not in the Python path, or the wrong Python environment is active.\\n\\nINVESTIGATION TRAIL:\\n  1. [first] requirements.txt\\n     \u2192 Check requirements.txt for missing packages \u2014 particularly recently removed packages\\n  2. [second] pyproject.toml\\n     \u2192 Check pyproject.toml dependencies for version conflicts or missing packages\\n     grep: dependencies|requirements\\n\\nRESOLUTION SEQUENCE:\\n  1. pip_install\\n     Command: pip install package-name\\n     Why: Installs the package in the current Python environment\\n  2. install_in_venv\\n     Command: source venv/bin/activate && pip install package-name\\n     Why: Ensures the package is installed in the correct virtual environment\\n  3. install_editable\\n     Command: pip install -e .\\n     Why: Installs the local package in editable mode for development\\n  4. check_python_path\\n     Command: import sys; print(sys.path)\\n     Why: Verify Python is looking in the right directories\\n\\nANTI-PATTERNS (don't do these):\\n  \u2717 pip install without a virtualenv\\n    Fails because: Pollutes the global Python and causes version conflicts\\n  \u2717 Manually copying module files to site-packages\\n    Fails because: Version conflicts and no automatic updates\\n  \u2717 Ignoring which virtualenv is activated\\n    Fails because: The module is installed but in a different environment\\n\\nEVIDENCE: 42/45 successes (93%) over 45 uses\\n         Avg resolve time: 1.2 min\\n\\n============================================================\",\n  \"automation_policy\": {\n    \"default\": \"automatic_for_agents\",\n    \"call_when\": [\n      \"technical task starts\",\n      \"tool/command error appears\",\n      \"same failure repeats\",\n      \"agent says it is stuck or loops\"\n    ],\n    \"do_not_call_when\": [\n      \"creative writing only\",\n      \"pure preference question\",\n      \"no technical action needed\"\n    ],\n    \"fail_closed\": true,\n    \"human_visibility_required\": true,\n    \"source\": \"cli\"\n  },\n  \"evidence\": {\n    \"success_count\": 42,\n    \"failure_count\": 3,\n    \"uses\": 45,\n    \"success_rate\": 0.93,\n    \"source\": \"seed_pack\"\n  }\n}\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg-doctor",
        "--json"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.76,
      "name": "borg_doctor_json",
      "passed": true,
      "returncode": 0,
      "stderr": "WARNING:borg.core.embeddings:embeddings: sentence-transformers not installed \u2014 keyword fallback active\n",
      "stdout": "{\n  \"checks\": [\n    {\n      \"detail\": \"314 traces at /tmp/borg-first-user-gate-kygo2xr8/borg-home/traces.db\",\n      \"name\": \"trace_db\",\n      \"passed\": true\n    },\n    {\n      \"detail\": \"ACTION: docker build --no-cache (does NOT fix missing packages  wrong approach) | CONFIDENCE: Real traces: 28 | Synthetic: 8 | Most recent: 31d ago | BORG [HIGH CONFIDENCE]\",\n      \"name\": \"borg_observe\",\n      \"passed\": true\n    },\n    {\n      \"detail\": \"BORG: Feedback recorded  guidance worked. Score updated for trace 6b53ee82.\",\n      \"name\": \"borg_rate\",\n      \"passed\": true\n    },\n    {\n      \"detail\": \"responds to initialize\",\n      \"name\": \"mcp_stdio\",\n      \"passed\": true\n    }\n  ],\n  \"runtime\": {\n    \"atom_count\": null,\n    \"atom_db_path\": \"/tmp/borg-first-user-gate-kygo2xr8/borg-home/atoms.db\",\n    \"borg_home\": \"/tmp/borg-first-user-gate-kygo2xr8/borg-home\",\n    \"module_hash\": \"e96fdfa7cd6352a2\",\n    \"module_path\": \"/tmp/borg-first-user-gate-kygo2xr8/lib/python3.11/site-packages/borg/__init__.py\",\n    \"package_version\": \"3.3.1\",\n    \"pid\": 103707,\n    \"python\": \"/tmp/borg-first-user-gate-kygo2xr8/bin/python\",\n    \"trace_count\": 314,\n    \"trace_db_path\": \"/tmp/borg-first-user-gate-kygo2xr8/borg-home/traces.db\"\n  },\n  \"success\": true\n}\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg",
        "try",
        "systematic-debugging"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.264,
      "name": "borg_try_bare",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "[E2E-001] record_outcome() CALLED \u2014 pack_id='borg://hermes/systematic-debugging' success=True category='try'\n[E2E-001]   PATH-1 (SQLite): attempting write to outcomes table...\n[E2E-001]   PATH-1 (SQLite): SUCCESS \u2014 row written\n[E2E-001]   PATH-2 (ContextualSelector.record_outcome): calling with pack='borg://hermes/systematic-debugging' cat='try' success=True\n[E2E-001]   PATH-2 (ContextualSelector): SUCCESS \u2014 Thompson Sampling updated inline\n[E2E-001]   PATH-3 (FeedbackLoop.record): hasattr=True...\n[E2E-001]   PATH-3 (FeedbackLoop.record): SUCCESS\n[E2E-001]   PATH-4 (MutationEngine): hasattr=True ab_ctx=None session_id=None\n[E2E-001]   PATH-4c (MutationEngine): SKIPPED \u2014 no A/B context\nPack: borg://hermes/systematic-debugging (systematic_debugging)\nConfidence: tested\nPhases (4): reproduce, isolate, fix, verify\nVerdict: \u2713 safe\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg",
        "try",
        "borg://hermes/systematic-debugging"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.171,
      "name": "borg_try_borg_uri",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "[E2E-001] record_outcome() CALLED \u2014 pack_id='borg://hermes/systematic-debugging' success=True category='try'\n[E2E-001]   PATH-1 (SQLite): attempting write to outcomes table...\n[E2E-001]   PATH-1 (SQLite): SUCCESS \u2014 row written\n[E2E-001]   PATH-2 (ContextualSelector.record_outcome): calling with pack='borg://hermes/systematic-debugging' cat='try' success=True\n[E2E-001]   PATH-2 (ContextualSelector): SUCCESS \u2014 Thompson Sampling updated inline\n[E2E-001]   PATH-3 (FeedbackLoop.record): hasattr=True...\n[E2E-001]   PATH-3 (FeedbackLoop.record): SUCCESS\n[E2E-001]   PATH-4 (MutationEngine): hasattr=True ab_ctx=None session_id=None\n[E2E-001]   PATH-4c (MutationEngine): SKIPPED \u2014 no A/B context\nPack: borg://hermes/systematic-debugging (systematic_debugging)\nConfidence: tested\nPhases (4): reproduce, isolate, fix, verify\nVerdict: \u2713 safe\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg",
        "try",
        "guild://hermes/systematic-debugging"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.169,
      "name": "borg_try_guild_uri",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "[E2E-001] record_outcome() CALLED \u2014 pack_id='borg://hermes/systematic-debugging' success=True category='try'\n[E2E-001]   PATH-1 (SQLite): attempting write to outcomes table...\n[E2E-001]   PATH-1 (SQLite): SUCCESS \u2014 row written\n[E2E-001]   PATH-2 (ContextualSelector.record_outcome): calling with pack='borg://hermes/systematic-debugging' cat='try' success=True\n[E2E-001]   PATH-2 (ContextualSelector): SUCCESS \u2014 Thompson Sampling updated inline\n[E2E-001]   PATH-3 (FeedbackLoop.record): hasattr=True...\n[E2E-001]   PATH-3 (FeedbackLoop.record): SUCCESS\n[E2E-001]   PATH-4 (MutationEngine): hasattr=True ab_ctx=None session_id=None\n[E2E-001]   PATH-4c (MutationEngine): SKIPPED \u2014 no A/B context\nPack: borg://hermes/systematic-debugging (systematic_debugging)\nConfidence: tested\nPhases (4): reproduce, isolate, fix, verify\nVerdict: \u2713 safe\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/borg",
        "setup-claude",
        "--scope",
        "user",
        "--verify",
        "--fix"
      ],
      "detail": "public command returned expected value signal",
      "duration_s": 0.145,
      "name": "borg_setup_claude_flags",
      "passed": true,
      "returncode": 0,
      "stderr": "",
      "stdout": "[setup-claude] Verify: PASS (initialize handshake ok)\n[setup-claude] Claude Code setup complete!\n  \u2022 MCP config updated \u2192 /tmp/borg-first-user-gate-kygo2xr8/home/.claude.json\n\nNext steps:\n  1. Restart Claude (scope=user) so it reloads MCP config\n  2. Confirm Borg tools appear (borg_observe, borg_search, borg_suggest)\n  3. Run 'borg search <query>' to validate end-to-end\n"
    },
    {
      "command": [
        "/tmp/borg-first-user-gate-kygo2xr8/bin/python",
        "-c",
        "import borg, json; r=borg.check('ModuleNotFoundError: No module named flask', top_k=1); print(json.dumps({'version': borg.__version__, 'result_type': type(r).__name__, 'count': len(r)}))"
      ],
      "detail": "borg.check returned list without crashing",
      "duration_s": 0.201,
      "name": "public_import_api_check",
      "passed": true,
      "returncode": 0,
      "stderr": "embeddings: sentence-transformers not installed \u2014 keyword fallback active\n",
      "stdout": "{\"version\": \"3.3.1\", \"result_type\": \"list\", \"count\": 1}\n"
    }
  ],
  "success": true
}

```
stderr:
(empty)

### `python scripts/security_gate_check.py`
rc: `0`
stdout:
```
PASS: Borg security hardening policy gate

```
stderr:
(empty)

### `python -m pytest -q borg/tests/test_privacy_structured.py borg/tests/test_prompt_injection.py borg/tests/test_atom_policy.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_privacy.py`
rc: `0`
stdout:
```
....................................................................     [100%]
68 passed in 0.13s

```
stderr:
(empty)

### `git status --short`
rc: `0`
stdout:
```
 M GO_NO_GO_DECISION.md
 M LOAD_TEST_REPORT_10.md
 M LOAD_TEST_REPORT_100.md
 M LOAD_TEST_REPORT_1000.md
 M PROJECT_STATUS.md
 M README.md
 M UAT_RESULTS.md
 M borg/cli.py
 M borg/cli/doctor.py
A  borg/core/confidence_gate.py
 M borg/core/embeddings.py
 M borg/core/feedback_loop.py
 M borg/core/uri.py
M  borg/integrations/mcp_server.py
 M borg/tests/test_borg_observe_confidence_gate.py
A  borg/tests/test_confidence_gate.py
 M borg/tests/test_distribution_readiness.py
 M borg/tests/test_uri.py
 M borg/tests/test_v3_integration.py
 D build/lib/borg/__init__.py
 D build/lib/borg/benchmark/skills/test_skills.py
 D build/lib/borg/benchmarks/__init__.py
 D build/lib/borg/benchmarks/report.py
 D build/lib/borg/benchmarks/runner.py
 D build/lib/borg/benchmarks/scorer.py
 D build/lib/borg/benchmarks/tasks.py
 D build/lib/borg/benchmarks/tests/__init__.py
 D build/lib/borg/benchmarks/tests/test_benchmarks.py
 D build/lib/borg/cli.py
 D build/lib/borg/cli/__init__.py
 D build/lib/borg/cli/doctor.py
 D build/lib/borg/cli/install.py
 D build/lib/borg/core/__init__.py
 D build/lib/borg/core/agentskills_converter.py
 D build/lib/borg/core/aggregator.py
 D build/lib/borg/core/apply.py
 D build/lib/borg/core/bm25_index.py
 D build/lib/borg/core/causal.py
 D build/lib/borg/core/changes.py
 D build/lib/borg/core/clustering.py
 D build/lib/borg/core/cold_start.py
 D build/lib/borg/core/conditions.py
AD build/lib/borg/core/confidence_gate.py
 D build/lib/borg/core/contextual_selector.py
 D build/lib/borg/core/convert.py
 D build/lib/borg/core/crypto.py
 D build/lib/borg/core/dirs.py
 D build/lib/borg/core/embeddings.py
 D build/lib/borg/core/failure_memory.py
 D build/lib/borg/core/feedback_loop.py
 D build/lib/borg/core/generate.py
 D build/lib/borg/core/generator.py
 D build/lib/borg/core/mutation_engine.py
 D build/lib/borg/core/negative_traces.py
 D build/lib/borg/core/openclaw_converter.py
 D build/lib/borg/core/pack_taxonomy.py
 D build/lib/borg/core/privacy.py
 D build/lib/borg/core/proof_gates.py
 D build/lib/borg/core/publish.py
 D build/lib/borg/core/safety.py
 D build/lib/borg/core/schema.py
 D build/lib/borg/core/search.py
 D build/lib/borg/core/seed_loader.py
 D build/lib/borg/core/seeds.py
 D build/lib/borg/core/semantic_search.py
 D build/lib/borg/core/session.py
 D build/lib/borg/core/signals.py
 D build/lib/borg/core/stack.py
 D build/lib/borg/core/synthesis.py
 D build/lib/borg/core/telemetry.py
 D build/lib/borg/core/temporal.py
 D build/lib/borg/core/trace_matcher.py
 D build/lib/borg/core/traces.py
 D build/lib/borg/core/uri.py
 D build/lib/borg/core/v3_integration.py
 D build/lib/borg/db/__init__.py
 D build/lib/borg/db/analytics.py
 D build/lib/borg/db/embeddings.py
 D build/lib/borg/db/migrations.py
 D build/lib/borg/db/reputation.py
 D build/lib/borg/db/store.py
 D build/lib/borg/defi/__init__.py
 D build/lib/borg/defi/alpha_signal.py
 D build/lib/borg/defi/api_clients/__init__.py
 D build/lib/borg/defi/api_clients/alchemy.py
 D build/lib/borg/defi/api_clients/arkham.py
 D build/lib/borg/defi/api_clients/base.py
 D build/lib/borg/defi/api_clients/birdeye.py
 D build/lib/borg/defi/api_clients/cache.py
 D build/lib/borg/defi/api_clients/defillama.py
 D build/lib/borg/defi/api_clients/dexscreener.py
 D build/lib/borg/defi/api_clients/goplus.py
 D build/lib/borg/defi/api_clients/helius.py
 D build/lib/borg/defi/cli.py
 D build/lib/borg/defi/cron/__init__.py
 D build/lib/borg/defi/cron/alpha_cron.py
 D build/lib/borg/defi/cron/delivery.py
 D build/lib/borg/defi/cron/liquidation_cron.py
 D build/lib/borg/defi/cron/live_scans.py
 D build/lib/borg/defi/cron/portfolio_cron.py
 D build/lib/borg/defi/cron/risk_cron.py
 D build/lib/borg/defi/cron/state.py
 D build/lib/borg/defi/cron/whale_cron.py
 D build/lib/borg/defi/cron/yield_cron.py
 D build/lib/borg/defi/data_models.py
 D build/lib/borg/defi/dojo_bridge.py
 D build/lib/borg/defi/liquidation_watcher.py
 D build/lib/borg/defi/lp_manager.py
 D build/lib/borg/defi/mcp_tools.py
 D build/lib/borg/defi/mev/__init__.py
 D build/lib/borg/defi/mev/flashbots.py
 D build/lib/borg/defi/mev/jito.py
 D build/lib/borg/defi/portfolio_monitor.py
 D build/lib/borg/defi/risk_engine.py
 D build/lib/borg/defi/security/__init__.py
 D build/lib/borg/defi/security/keystore.py
 D build/lib/borg/defi/security/tx_guard.py
 D build/lib/borg/defi/strategy_backtester.py
 D build/lib/borg/defi/strategy_selector.py
 D build/lib/borg/defi/swap_executor.py
 D build/lib/borg/defi/tests/__init__.py
 D build/lib/borg/defi/tests/test_alchemy.py
 D build/lib/borg/defi/tests/test_alpha_signal.py
 D build/lib/borg/defi/tests/test_api_clients.py
 D build/lib/borg/defi/tests/test_arkham.py
 D build/lib/borg/defi/tests/test_base_client.py
 D build/lib/borg/defi/tests/test_cache.py
 D build/lib/borg/defi/tests/test_cli.py
 D build/lib/borg/defi/tests/test_cron.py
 D build/lib/borg/defi/tests/test_cron_delivery.py
 D build/lib/borg/defi/tests/test_cron_state.py
 D build/lib/borg/defi/tests/test_data_models.py
 D build/lib/borg/defi/tests/test_dojo_bridge.py
 D build/lib/borg/defi/tests/test_e2e_live.py
 D build/lib/borg/defi/tests/test_goplus.py
 D build/lib/borg/defi/tests/test_keystore_unit.py
 D build/lib/borg/defi/tests/test_liquidation_watcher.py
 D build/lib/borg/defi/tests/test_live_scans.py
 D build/lib/borg/defi/tests/test_lp_manager.py
 D build/lib/borg/defi/tests/test_mcp_tools.py
 D build/lib/borg/defi/tests/test_mev.py
 D build/lib/borg/defi/tests/test_portfolio_monitor.py
 D build/lib/borg/defi/tests/test_risk_engine.py
 D build/lib/borg/defi/tests/test_strategy_backtester.py
 D build/lib/borg/defi/tests/test_strategy_selector.py
 D build/lib/borg/defi/tests/test_swap_executor.py
 D build/lib/borg/defi/tests/test_tx_guard_unit.py
 D build/lib/borg/defi/tests/test_v2_borg_bridge.py
 D build/lib/borg/defi/tests/test_v2_circuit_breaker.py
 D build/lib/borg/defi/tests/test_v2_drift.py
 D build/lib/borg/defi/tests/test_v2_integration.py
 D build/lib/borg/defi/tests/test_v2_models.py
 D build/lib/borg/defi/tests/test_v2_outcome_store.py
 D build/lib/borg/defi/tests/test_v2_pack_store.py
 D build/lib/borg/defi/tests/test_v2_recommender.py
 D build/lib/borg/defi/tests/test_v2_reputation.py
 D build/lib/borg/defi/tests/test_v2_seed_packs.py
 D build/lib/borg/defi/tests/test_v2_warnings.py
 D build/lib/borg/defi/tests/test_whale_tracker.py
 D build/lib/borg/defi/tests/test_yield_scanner.py
 D build/lib/borg/defi/v2/__init__.py
 D build/lib/borg/defi/v2/borg_bridge.py
 D build/lib/borg/defi/v2/circuit_breaker.py
 D build/lib/borg/defi/v2/daily_brief.py
 D build/lib/borg/defi/v2/drift.py
 D build/lib/borg/defi/v2/models.py
 D build/lib/borg/defi/v2/outcome_store.py
 D build/lib/borg/defi/v2/pack_store.py
 D build/lib/borg/defi/v2/recommender.py
 D build/lib/borg/defi/v2/reputation.py
 D build/lib/borg/defi/v2/seed_packs.py
 D build/lib/borg/defi/v2/warnings.py
 D build/lib/borg/defi/whale_tracker.py
 D build/lib/borg/defi/yield_scanner.py
 D build/lib/borg/dojo/__init__.py
 D build/lib/borg/dojo/auto_fixer.py
 D build/lib/borg/dojo/cron_runner.py
 D build/lib/borg/dojo/data_models.py
 D build/lib/borg/dojo/failure_classifier.py
 D build/lib/borg/dojo/learning_curve.py
 D build/lib/borg/dojo/pipeline.py
 D build/lib/borg/dojo/report_generator.py
 D build/lib/borg/dojo/session_reader.py
 D build/lib/borg/dojo/skill_gap_detector.py
 D build/lib/borg/dojo/tests/__init__.py
 D build/lib/borg/dojo/tests/test_auto_fixer.py
 D build/lib/borg/dojo/tests/test_failure_classifier.py
 D build/lib/borg/dojo/tests/test_learning_curve.py
 D build/lib/borg/dojo/tests/test_pipeline.py
 D build/lib/borg/dojo/tests/test_report_generator.py
 D build/lib/borg/dojo/tests/test_session_reader.py
 D build/lib/borg/dojo/tests/test_skill_gap_detector.py
 D build/lib/borg/eval/__init__.py
 D build/lib/borg/eval/ab_test.py
 D build/lib/borg/eval/e1a_seed_pack_validation.py
 D build/lib/borg/eval/production_smoke_test.py
 D build/lib/borg/fleet/syncer.py
 D build/lib/borg/integrations/__init__.py
 D build/lib/borg/integrations/agent_hook.py
 D build/lib/borg/integrations/http_server.py
AD build/lib/borg/integrations/mcp_server.py
 D build/lib/borg/integrations/nudge.py
 D build/lib/borg/seeds_data/borg-autopilot/SKILL.md
 D build/lib/borg/seeds_data/borg/SKILL.md
 D build/lib/borg/seeds_data/circular-dependency-migration.md
 D build/lib/borg/seeds_data/code-review.md
 D build/lib/borg/seeds_data/collective_seed.json
 D build/lib/borg/seeds_data/configuration-error.md
 D build/lib/borg/seeds_data/defi-risk-check.md
 D build/lib/borg/seeds_data/defi-yield-strategy.md
 D build/lib/borg/seeds_data/extended_seeds.yaml
 D build/lib/borg/seeds_data/import-cycle.md
 D build/lib/borg/seeds_data/migration-state-desync.md
 D build/lib/borg/seeds_data/missing-dependency.md
 D build/lib/borg/seeds_data/missing-foreign-key.md
 D build/lib/borg/seeds_data/null-pointer-chain.md
 D build/lib/borg/seeds_data/packs/bash-permission-denied.yaml
 D build/lib/borg/seeds_data/packs/django-circular-dependency.yaml
 D build/lib/borg/seeds_data/packs/django-migration-state.yaml
 D build/lib/borg/seeds_data/packs/django-null-pointer.yaml
 D build/lib/borg/seeds_data/packs/django-schema-drift.yaml
 D build/lib/borg/seeds_data/packs/docker-no-space.yaml
 D build/lib/borg/seeds_data/packs/git-merge-conflict.yaml
 D build/lib/borg/seeds_data/packs/pytest-flaky-test.yaml
 D build/lib/borg/seeds_data/packs/python-import-cycle.yaml
 D build/lib/borg/seeds_data/packs/python-missing-dependency.yaml
 D build/lib/borg/seeds_data/permission-denied.md
 D build/lib/borg/seeds_data/race-condition.md
 D build/lib/borg/seeds_data/schema-drift.md
 D build/lib/borg/seeds_data/systematic-debugging.md
 D build/lib/borg/seeds_data/test-driven-development.md
 D build/lib/borg/seeds_data/timeout-hang.md
 D build/lib/borg/seeds_data/type-mismatch.md
 D build/lib/borg/tests/__init__.py
 D build/lib/borg/tests/fixtures/openclaw/quick_validate.py
 D build/lib/borg/tests/test_agent_hook.py
 D build/lib/borg/tests/test_aggregator.py
 D build/lib/borg/tests/test_analytics.py
 D build/lib/borg/tests/test_apply.py
 D build/lib/borg/tests/test_change_awareness.py
 D build/lib/borg/tests/test_classify_error.py
 D build/lib/borg/tests/test_cli.py
 D build/lib/borg/tests/test_conditions.py
 D build/lib/borg/tests/test_contextual_selector.py
 D build/lib/borg/tests/test_convert.py
 D build/lib/borg/tests/test_convert_openclaw.py
 D build/lib/borg/tests/test_dirs.py
 D build/lib/borg/tests/test_dojo_pipeline.py
 D build/lib/borg/tests/test_e2e_learning_loop.py
 D build/lib/borg/tests/test_e2e_learning_loop_v3.py
 D build/lib/borg/tests/test_failure_memory.py
 D build/lib/borg/tests/test_feedback_loop.py
 D build/lib/borg/tests/test_fleet_syncer.py
 D build/lib/borg/tests/test_generate.py
 D build/lib/borg/tests/test_generator.py
 D build/lib/borg/tests/test_mcp_hardening.py
 D build/lib/borg/tests/test_mcp_server.py
 D build/lib/borg/tests/test_mcp_server_extended.py
 D build/lib/borg/tests/test_mutation_engine.py
 D build/lib/borg/tests/test_nudge.py
 D build/lib/borg/tests/test_observe_search_roundtrip.py
 D build/lib/borg/tests/test_openclaw_converter.py
 D build/lib/borg/tests/test_pack_compatibility.py
 D build/lib/borg/tests/test_privacy.py
 D build/lib/borg/tests/test_proof_gates.py
 D build/lib/borg/tests/test_publish.py
 D build/lib/borg/tests/test_publish_flow_debug.py
 D build/lib/borg/tests/test_publish_flow_integration.py
 D build/lib/borg/tests/test_publish_sybil.py
 D build/lib/borg/tests/test_pull_network.py
 D build/lib/borg/tests/test_reputation.py
 D build/lib/borg/tests/test_reputation_integration.py
 D build/lib/borg/tests/test_safety.py
 D build/lib/borg/tests/test_schema.py
 D build/lib/borg/tests/test_search.py
 D build/lib/borg/tests/test_semantic_search.py
 D build/lib/borg/tests/test_session.py
 D build/lib/borg/tests/test_start_signals.py
 D build/lib/borg/tests/test_store.py
 D build/lib/borg/tests/test_store_concurrency.py
 D build/lib/borg/tests/test_telemetry.py
 D build/lib/borg/tests/test_uri.py
 D build/lib/borg/tests/test_v3_integration.py
 D build/lib/borg/tests/test_wiring.py
 D dist/agent_borg-2.4.0-py3-none-any.whl
 D dist/agent_borg-2.4.0.tar.gz
 D dist/agent_borg-2.5.0-py3-none-any.whl
 D dist/agent_borg-2.5.0.tar.gz
 D dist/agent_borg-2.5.1-py3-none-any.whl
 D dist/agent_borg-2.5.1.tar.gz
 D dist/agent_borg-2.5.2-py3-none-any.whl
 D dist/agent_borg-2.5.2.tar.gz
 D dist/agent_borg-2.7.1-py3-none-any.whl
 D dist/agent_borg-2.7.1.tar.gz
 D dist/agent_borg-3.1.0-py3-none-any.whl
 D dist/agent_borg-3.1.0.tar.gz
 D dist/agent_borg-3.1.1-py3-none-any.whl
 D dist/agent_borg-3.1.1.tar.gz
 D dist/agent_borg-3.1.2-py3-none-any.whl
 D dist/agent_borg-3.1.2.tar.gz
 D dist/agent_borg-3.1.3-py3-none-any.whl
 D dist/agent_borg-3.1.3.tar.gz
 D dist/agent_borg-3.2.0-py3-none-any.whl
 D dist/agent_borg-3.2.0.tar.gz
 D dist/agent_borg-3.2.1-py3-none-any.whl
 D dist/agent_borg-3.2.1.tar.gz
 D dist/agent_borg-3.2.2-py3-none-any.whl
 D dist/agent_borg-3.2.2.tar.gz
 D dist/agent_borg-3.2.3-py3-none-any.whl
 D dist/agent_borg-3.2.3.tar.gz
 D dist/agent_borg-3.2.4-py3-none-any.whl
 D dist/agent_borg-3.2.4.tar.gz
 D dist/agent_borg-3.3.0-py3-none-any.whl
 D dist/agent_borg-3.3.0.tar.gz
 D dist/guild_packs-2.0.0-py3-none-any.whl
 D dist/guild_packs-2.0.0.tar.gz
 D dist/guild_packs-2.0.1-py3-none-any.whl
 D dist/guild_packs-2.0.1.tar.gz
 D dist/guild_packs-2.0.2-py3-none-any.whl
 D dist/guild_packs-2.0.2.tar.gz
 D dist/guild_packs-2.0.3-py3-none-any.whl
 D dist/guild_packs-2.0.3.tar.gz
 D dist/guild_packs-2.0.4-py3-none-any.whl
 D dist/guild_packs-2.0.4.tar.gz
 D dist/guild_packs-2.0.5-py3-none-any.whl
 D dist/guild_packs-2.0.5.tar.gz
 D dist/guild_packs-2.0.6-py3-none-any.whl
 D dist/guild_packs-2.0.6.tar.gz
 D dist/guild_packs-2.0.7-py3-none-any.whl
 D dist/guild_packs-2.0.7.tar.gz
 D dist/guild_packs-2.1.0-py3-none-any.whl
 D dist/guild_packs-2.1.0.tar.gz
 D dist/guild_packs-2.1.1-py3-none-any.whl
 D dist/guild_packs-2.1.1.tar.gz
AM docs/BORG_PROOF_DASHBOARD.html
AM docs/BORG_PROOF_DASHBOARD.md
 M docs/README.md
AM docs/public/proof-dashboard/index.html
AM eval/borg_proof_dashboard.json
AM eval/first_user_release_gate_snapshot.json
 M eval/gate_run_snapshot.json
 M eval/load_1000_snapshot.json
 M eval/load_100_snapshot.json
 M eval/load_10_snapshot.json
A  eval/tests/test_borg_proof_dashboard.py
 M eval/uat_scoreboard_snapshot.json
 M pyproject.toml
A  scripts/borg_proof_dashboard_lint.py
A  scripts/build_borg_proof_dashboard.py
?? .hermes/
?? borg/cli/__main__.py
?? borg/core/first_user_readiness.py
?? borg/core/runtime_fingerprint.py
?? borg/seeds_data/packs/systematic-debugging.workflow.yaml
?? borg/tests/test_embeddings_schema_compat.py
?? borg/tests/test_first_10_readiness.py
?? borg/tests/test_first_user_cli_contract.py
?? borg/tests/test_runtime_fingerprint.py
?? dist/agent_borg-3.3.1-py3-none-any.whl
?? dist/agent_borg-3.3.1.tar.gz
?? docs/20260513_BORG_DEEP_CUTOVER_EXECUTION_BOARD.md
?? docs/20260513_BORG_FULL_AUDIT_AND_OBSERVE_CONFIDENCE_GATE.md
?? docs/20260513_BORG_MULTI_REPO_PRODUCTION_CLEANUP_CUTOVER_PROPOSAL.md
?? docs/20260514_BORG_EMBEDDINGS_SCHEMA_COMPAT_VERIFICATION_RAW.md
?? docs/20260514_BORG_GOOGLE_TIER_READINESS_CONTINUATION.md
?? docs/20260514_BORG_PRODUCTION_REBUILD_MASTER_PLAN.md
?? docs/20260514_BORG_PUBLIC_LAUNCH_READINESS_PLAN.md
?? docs/20260514_BORG_RUNTIME_FINGERPRINT_CANARY_PROOF.md
?? docs/20260514_BORG_RUNTIME_FINGERPRINT_VERIFICATION_RAW.md
?? docs/20260514_BORG_WORLD_CLASS_HARDENING_BOARD.md
?? docs/FIRST_10_BETA_READINESS.md
?? docs/repo-manifest/
?? eval/20260514_borg_google_tier_readiness_continuation.json
?? eval/run_first_user_release_gate.py
?? scripts/run_embeddings_schema_compat_verification.py
?? scripts/run_runtime_fingerprint_verification.py
?? tmp_readiness_audit_20260506/

```
stderr:
(empty)

### `git diff --stat`
rc: `0`
stdout:
```
 GO_NO_GO_DECISION.md                               |   29 +-
 LOAD_TEST_REPORT_10.md                             |   12 +-
 LOAD_TEST_REPORT_100.md                            |   12 +-
 LOAD_TEST_REPORT_1000.md                           |   12 +-
 PROJECT_STATUS.md                                  |   28 +-
 README.md                                          |    7 +
 UAT_RESULTS.md                                     |   37 +-
 borg/cli.py                                        |   45 +-
 borg/cli/doctor.py                                 |   51 +-
 borg/core/embeddings.py                            |   33 +-
 borg/core/feedback_loop.py                         |   17 +-
 borg/core/uri.py                                   |  119 +-
 borg/tests/test_borg_observe_confidence_gate.py    |   61 +
 borg/tests/test_distribution_readiness.py          |   27 +
 borg/tests/test_uri.py                             |   20 +-
 borg/tests/test_v3_integration.py                  |   14 +-
 build/lib/borg/__init__.py                         |    8 -
 build/lib/borg/benchmark/skills/test_skills.py     |  126 -
 build/lib/borg/benchmarks/__init__.py              |   21 -
 build/lib/borg/benchmarks/report.py                |  143 -
 build/lib/borg/benchmarks/runner.py                |  408 ---
 build/lib/borg/benchmarks/scorer.py                |  170 -
 build/lib/borg/benchmarks/tasks.py                 |  468 ---
 build/lib/borg/benchmarks/tests/__init__.py        |    0
 build/lib/borg/benchmarks/tests/test_benchmarks.py |  442 ---
 build/lib/borg/cli.py                              | 1638 ----------
 build/lib/borg/cli/__init__.py                     |   42 -
 build/lib/borg/cli/doctor.py                       |   99 -
 build/lib/borg/cli/install.py                      |  123 -
 build/lib/borg/core/__init__.py                    |    0
 build/lib/borg/core/agentskills_converter.py       |  595 ----
 build/lib/borg/core/aggregator.py                  |  355 ---
 build/lib/borg/core/apply.py                       | 1076 -------
 build/lib/borg/core/bm25_index.py                  |  163 -
 build/lib/borg/core/causal.py                      |   84 -
 build/lib/borg/core/changes.py                     |  202 --
 build/lib/borg/core/clustering.py                  |  238 --
 build/lib/borg/core/cold_start.py                  |   58 -
 build/lib/borg/core/conditions.py                  |  251 --
 build/lib/borg/core/confidence_gate.py             |  230 --
 build/lib/borg/core/contextual_selector.py         | 1039 -------
 build/lib/borg/core/convert.py                     |  870 ------
 build/lib/borg/core/crypto.py                      |  398 ---
 build/lib/borg/core/dirs.py                        |   52 -
 build/lib/borg/core/embeddings.py                  |  287 --
 build/lib/borg/core/failure_memory.py              |  455 ---
 build/lib/borg/core/feedback_loop.py               |  705 -----
 build/lib/borg/core/generate.py                    |  527 ----
 build/lib/borg/core/generator.py                   |  467 ---
 build/lib/borg/core/mutation_engine.py             | 1105 -------
 build/lib/borg/core/negative_traces.py             |   82 -
 build/lib/borg/core/openclaw_converter.py          |  418 ---
 build/lib/borg/core/pack_taxonomy.py               |  659 ----
 build/lib/borg/core/privacy.py                     |  144 -
 build/lib/borg/core/proof_gates.py                 |  381 ---
 build/lib/borg/core/publish.py                     |  579 ----
 build/lib/borg/core/safety.py                      |  347 ---
 build/lib/borg/core/schema.py                      |  339 --
 build/lib/borg/core/search.py                      | 1223 --------
 build/lib/borg/core/seed_loader.py                 |  104 -
 build/lib/borg/core/seeds.py                       |  156 -
 build/lib/borg/core/semantic_search.py             |  514 ----
 build/lib/borg/core/session.py                     |  406 ---
 build/lib/borg/core/signals.py                     |   45 -
 build/lib/borg/core/stack.py                       |   58 -
 build/lib/borg/core/synthesis.py                   |  132 -
 build/lib/borg/core/telemetry.py                   |  114 -
 build/lib/borg/core/temporal.py                    |   45 -
 build/lib/borg/core/trace_matcher.py               |  219 --
 build/lib/borg/core/traces.py                      |  372 ---
 build/lib/borg/core/uri.py                         |  252 --
 build/lib/borg/core/v3_integration.py              |  895 ------
 build/lib/borg/db/__init__.py                      |    0
 build/lib/borg/db/analytics.py                     |  610 ----
 build/lib/borg/db/embeddings.py                    |  262 --
 build/lib/borg/db/migrations.py                    |  182 --
 build/lib/borg/db/reputation.py                    |  561 ----
 build/lib/borg/db/store.py                         | 1165 -------
 build/lib/borg/defi/__init__.py                    |  123 -
 build/lib/borg/defi/alpha_signal.py                | 1044 -------
 build/lib/borg/defi/api_clients/__init__.py        |   27 -
 build/lib/borg/defi/api_clients/alchemy.py         |  346 ---
 build/lib/borg/defi/api_clients/arkham.py          |  354 ---
 build/lib/borg/defi/api_clients/base.py            |  377 ---
 build/lib/borg/defi/api_clients/birdeye.py         |  224 --
 build/lib/borg/defi/api_clients/cache.py           |  282 --
 build/lib/borg/defi/api_clients/defillama.py       |  211 --
 build/lib/borg/defi/api_clients/dexscreener.py     |  167 -
 build/lib/borg/defi/api_clients/goplus.py          |  401 ---
 build/lib/borg/defi/api_clients/helius.py          |  310 --
 build/lib/borg/defi/cli.py                         |  161 -
 build/lib/borg/defi/cron/__init__.py               |   64 -
 build/lib/borg/defi/cron/alpha_cron.py             |  177 --
 build/lib/borg/defi/cron/delivery.py               |  215 --
 build/lib/borg/defi/cron/liquidation_cron.py       |   66 -
 build/lib/borg/defi/cron/live_scans.py             |  442 ---
 build/lib/borg/defi/cron/portfolio_cron.py         |  106 -
 build/lib/borg/defi/cron/risk_cron.py              |  144 -
 build/lib/borg/defi/cron/state.py                  |  182 --
 build/lib/borg/defi/cron/whale_cron.py             |  110 -
 build/lib/borg/defi/cron/yield_cron.py             |  106 -
 build/lib/borg/defi/data_models.py                 |  447 ---
 build/lib/borg/defi/dojo_bridge.py                 |  696 -----
 build/lib/borg/defi/liquidation_watcher.py         |  682 ----
 build/lib/borg/defi/lp_manager.py                  |  868 ------
 build/lib/borg/defi/mcp_tools.py                   |  158 -
 build/lib/borg/defi/mev/__init__.py                |   25 -
 build/lib/borg/defi/mev/flashbots.py               |  234 --
 build/lib/borg/defi/mev/jito.py                    |  169 -
 build/lib/borg/defi/portfolio_monitor.py           |  681 ----
 build/lib/borg/defi/risk_engine.py                 |  725 -----
 build/lib/borg/defi/security/__init__.py           |   36 -
 build/lib/borg/defi/security/keystore.py           |  559 ----
 build/lib/borg/defi/security/tx_guard.py           |  581 ----
 build/lib/borg/defi/strategy_backtester.py         |  814 -----
 build/lib/borg/defi/strategy_selector.py           |  702 -----
 build/lib/borg/defi/swap_executor.py               | 1438 ---------
 build/lib/borg/defi/tests/__init__.py              |    1 -
 build/lib/borg/defi/tests/test_alchemy.py          |  426 ---
 build/lib/borg/defi/tests/test_alpha_signal.py     |  905 ------
 build/lib/borg/defi/tests/test_api_clients.py      |  558 ----
 build/lib/borg/defi/tests/test_arkham.py           |  651 ----
 build/lib/borg/defi/tests/test_base_client.py      |  292 --
 build/lib/borg/defi/tests/test_cache.py            |  503 ---
 build/lib/borg/defi/tests/test_cli.py              |  279 --
 build/lib/borg/defi/tests/test_cron.py             |  708 -----
 build/lib/borg/defi/tests/test_cron_delivery.py    |  246 --
 build/lib/borg/defi/tests/test_cron_state.py       |  315 --
 build/lib/borg/defi/tests/test_data_models.py      |  754 -----
 build/lib/borg/defi/tests/test_dojo_bridge.py      |  976 ------
 build/lib/borg/defi/tests/test_e2e_live.py         |  304 --
 build/lib/borg/defi/tests/test_goplus.py           |  469 ---
 build/lib/borg/defi/tests/test_keystore_unit.py    |  536 ----
 .../borg/defi/tests/test_liquidation_watcher.py    |  776 -----
 build/lib/borg/defi/tests/test_live_scans.py       | 1048 -------
 build/lib/borg/defi/tests/test_lp_manager.py       |  740 -----
 build/lib/borg/defi/tests/test_mcp_tools.py        |  335 --
 build/lib/borg/defi/tests/test_mev.py              |  721 -----
 .../lib/borg/defi/tests/test_portfolio_monitor.py  |  621 ----
 build/lib/borg/defi/tests/test_risk_engine.py      |  729 -----
 .../borg/defi/tests/test_strategy_backtester.py    |  728 -----
 .../lib/borg/defi/tests/test_strategy_selector.py  | 1009 ------
 build/lib/borg/defi/tests/test_swap_executor.py    | 1219 --------
 build/lib/borg/defi/tests/test_tx_guard_unit.py    |  651 ----
 build/lib/borg/defi/tests/test_v2_borg_bridge.py   |  374 ---
 .../lib/borg/defi/tests/test_v2_circuit_breaker.py |  590 ----
 build/lib/borg/defi/tests/test_v2_drift.py         |  393 ---
 build/lib/borg/defi/tests/test_v2_integration.py   |  610 ----
 build/lib/borg/defi/tests/test_v2_models.py        |  537 ----
 build/lib/borg/defi/tests/test_v2_outcome_store.py |  364 ---
 build/lib/borg/defi/tests/test_v2_pack_store.py    |  379 ---
 build/lib/borg/defi/tests/test_v2_recommender.py   |  859 ------
 build/lib/borg/defi/tests/test_v2_reputation.py    |  413 ---
 build/lib/borg/defi/tests/test_v2_seed_packs.py    |  285 --
 build/lib/borg/defi/tests/test_v2_warnings.py      |  428 ---
 build/lib/borg/defi/tests/test_whale_tracker.py    |  515 ----
 build/lib/borg/defi/tests/test_yield_scanner.py    |  593 ----
 build/lib/borg/defi/v2/__init__.py                 |   27 -
 build/lib/borg/defi/v2/borg_bridge.py              |  300 --
 build/lib/borg/defi/v2/circuit_breaker.py          |  397 ---
 build/lib/borg/defi/v2/daily_brief.py              |  129 -
 build/lib/borg/defi/v2/drift.py                    |  151 -
 build/lib/borg/defi/v2/models.py                   |  388 ---
 build/lib/borg/defi/v2/outcome_store.py            |  168 -
 build/lib/borg/defi/v2/pack_store.py               |  180 --
 build/lib/borg/defi/v2/recommender.py              |  582 ----
 build/lib/borg/defi/v2/reputation.py               |  216 --
 build/lib/borg/defi/v2/seed_packs.py               |  399 ---
 build/lib/borg/defi/v2/warnings.py                 |  216 --
 build/lib/borg/defi/whale_tracker.py               |  585 ----
 build/lib/borg/defi/yield_scanner.py               |  405 ---
 build/lib/borg/dojo/__init__.py                    |   15 -
 build/lib/borg/dojo/auto_fixer.py                  |  369 ---
 build/lib/borg/dojo/cron_runner.py                 |  206 --
 build/lib/borg/dojo/data_models.py                 |  305 --
 build/lib/borg/dojo/failure_classifier.py          |  394 ---
 build/lib/borg/dojo/learning_curve.py              |  224 --
 build/lib/borg/dojo/pipeline.py                    |  329 --
 build/lib/borg/dojo/report_generator.py            |  312 --
 build/lib/borg/dojo/session_reader.py              |  436 ---
 build/lib/borg/dojo/skill_gap_detector.py          |  213 --
 build/lib/borg/dojo/tests/__init__.py              |    1 -
 build/lib/borg/dojo/tests/test_auto_fixer.py       |  858 ------
 .../lib/borg/dojo/tests/test_failure_classifier.py |  449 ---
 build/lib/borg/dojo/tests/test_learning_curve.py   |  504 ---
 build/lib/borg/dojo/tests/test_pipeline.py         |  353 ---
 build/lib/borg/dojo/tests/test_report_generator.py |  502 ---
 build/lib/borg/dojo/tests/test_session_reader.py   |  421 ---
 .../lib/borg/dojo/tests/test_skill_gap_detector.py |  486 ---
 build/lib/borg/eval/__init__.py                    |    2 -
 build/lib/borg/eval/ab_test.py                     |  230 --
 build/lib/borg/eval/e1a_seed_pack_validation.py    |  582 ----
 build/lib/borg/eval/production_smoke_test.py       |  127 -
 build/lib/borg/fleet/syncer.py                     |  521 ----
 build/lib/borg/integrations/__init__.py            |    0
 build/lib/borg/integrations/agent_hook.py          |  210 --
 build/lib/borg/integrations/http_server.py         |  113 -
 build/lib/borg/integrations/mcp_server.py          | 3243 --------------------
 build/lib/borg/integrations/nudge.py               |  402 ---
 build/lib/borg/seeds_data/borg-autopilot/SKILL.md  |  140 -
 build/lib/borg/seeds_data/borg/SKILL.md            |  147 -
 .../seeds_data/circular-dependency-migration.md    |   71 -
 build/lib/borg/seeds_data/code-review.md           |   38 -
 build/lib/borg/seeds_data/collective_seed.json     |    1 -
 build/lib/borg/seeds_data/configuration-error.md   |   68 -
 build/lib/borg/seeds_data/defi-risk-check.md       |   38 -
 build/lib/borg/seeds_data/defi-yield-strategy.md   |   37 -
 build/lib/borg/seeds_data/extended_seeds.yaml      |  697 -----
 build/lib/borg/seeds_data/import-cycle.md          |   72 -
 .../lib/borg/seeds_data/migration-state-desync.md  |   63 -
 build/lib/borg/seeds_data/missing-dependency.md    |   64 -
 build/lib/borg/seeds_data/missing-foreign-key.md   |   66 -
 build/lib/borg/seeds_data/null-pointer-chain.md    |   82 -
 .../seeds_data/packs/bash-permission-denied.yaml   |   25 -
 .../packs/django-circular-dependency.yaml          |   20 -
 .../seeds_data/packs/django-migration-state.yaml   |   25 -
 .../borg/seeds_data/packs/django-null-pointer.yaml |   22 -
 .../borg/seeds_data/packs/django-schema-drift.yaml |   23 -
 .../lib/borg/seeds_data/packs/docker-no-space.yaml |   25 -
 .../borg/seeds_data/packs/git-merge-conflict.yaml  |   24 -
 .../borg/seeds_data/packs/pytest-flaky-test.yaml   |   25 -
 .../borg/seeds_data/packs/python-import-cycle.yaml |   25 -
 .../packs/python-missing-dependency.yaml           |   23 -
 build/lib/borg/seeds_data/permission-denied.md     |   62 -
 build/lib/borg/seeds_data/race-condition.md        |   66 -
 build/lib/borg/seeds_data/schema-drift.md          |   66 -
 build/lib/borg/seeds_data/systematic-debugging.md  |   37 -
 .../lib/borg/seeds_data/test-driven-development.md |   32 -
 build/lib/borg/seeds_data/timeout-hang.md          |   65 -
 build/lib/borg/seeds_data/type-mismatch.md         |   72 -
 build/lib/borg/tests/__init__.py                   |    0
 .../borg/tests/fixtures/openclaw/quick_validate.py |  159 -
 build/lib/borg/tests/test_agent_hook.py            |  378 ---
 build/lib/borg/tests/test_aggregator.py            |  468 ---
 build/lib/borg/tests/test_analytics.py             |  506 ---
 build/lib/borg/tests/test_apply.py                 |  674 ----
 build/lib/borg/tests/test_change_awareness.py      |  360 ---
 build/lib/borg/tests/test_classify_error.py        |  359 ---
 build/lib/borg/tests/test_cli.py                   |  669 ----
 build/lib/borg/tests/test_conditions.py            |  490 ---
 build/lib/borg/tests/test_contextual_selector.py   |  957 ------
 build/lib/borg/tests/test_convert.py               |  353 ---
 build/lib/borg/tests/test_convert_openclaw.py      |  729 -----
 build/lib/borg/tests/test_dirs.py                  |   55 -
 build/lib/borg/tests/test_dojo_pipeline.py         | 1000 ------
 build/lib/borg/tests/test_e2e_learning_loop.py     | 1122 -------
 build/lib/borg/tests/test_e2e_learning_loop_v3.py  |  987 ------
 build/lib/borg/tests/test_failure_memory.py        |  528 ----
 build/lib/borg/tests/test_feedback_loop.py         | 1120 -------
 build/lib/borg/tests/test_fleet_syncer.py          |  400 ---
 build/lib/borg/tests/test_generate.py              |  303 --
 build/lib/borg/tests/test_generator.py             |  346 ---
 build/lib/borg/tests/test_mcp_hardening.py         |  296 --
 build/lib/borg/tests/test_mcp_server.py            |  861 ------
 build/lib/borg/tests/test_mcp_server_extended.py   | 2073 -------------
 build/lib/borg/tests/test_mutation_engine.py       |  987 ------
 build/lib/borg/tests/test_nudge.py                 |  481 ---
 .../borg/tests/test_observe_search_roundtrip.py    |  151 -
 build/lib/borg/tests/test_openclaw_converter.py    |  454 ---
 build/lib/borg/tests/test_pack_compatibility.py    |  359 ---
 build/lib/borg/tests/test_privacy.py               |  362 ---
 build/lib/borg/tests/test_proof_gates.py           |  486 ---
 build/lib/borg/tests/test_publish.py               |  581 ----
 build/lib/borg/tests/test_publish_flow_debug.py    |   63 -
 .../borg/tests/test_publish_flow_integration.py    |  279 --
 build/lib/borg/tests/test_publish_sybil.py         |  428 ---
 build/lib/borg/tests/test_pull_network.py          |  182 --
 build/lib/borg/tests/test_reputation.py            |  430 ---
 .../lib/borg/tests/test_reputation_integration.py  | 1080 -------
 build/lib/borg/tests/test_safety.py                |  564 ----
 build/lib/borg/tests/test_schema.py                |  435 ---
 build/lib/borg/tests/test_search.py                | 1330 --------
 build/lib/borg/tests/test_semantic_search.py       |  423 ---
 build/lib/borg/tests/test_session.py               |  570 ----
 build/lib/borg/tests/test_start_signals.py         |  375 ---
 build/lib/borg/tests/test_store.py                 |  946 ------
 build/lib/borg/tests/test_store_concurrency.py     |  344 ---
 build/lib/borg/tests/test_telemetry.py             |  410 ---
 build/lib/borg/tests/test_uri.py                   |  263 --
 build/lib/borg/tests/test_v3_integration.py        |  707 -----
 build/lib/borg/tests/test_wiring.py                |  312 --
 dist/agent_borg-2.4.0-py3-none-any.whl             |  Bin 93738 -> 0 bytes
 dist/agent_borg-2.4.0.tar.gz                       |  Bin 83978 -> 0 bytes
 dist/agent_borg-2.5.0-py3-none-any.whl             |  Bin 356121 -> 0 bytes
 dist/agent_borg-2.5.0.tar.gz                       |  Bin 307444 -> 0 bytes
 dist/agent_borg-2.5.1-py3-none-any.whl             |  Bin 356124 -> 0 bytes
 dist/agent_borg-2.5.1.tar.gz                       |  Bin 307378 -> 0 bytes
 dist/agent_borg-2.5.2-py3-none-any.whl             |  Bin 432358 -> 0 bytes
 dist/agent_borg-2.5.2.tar.gz                       |  Bin 382925 -> 0 bytes
 dist/agent_borg-2.7.1-py3-none-any.whl             |  Bin 432361 -> 0 bytes
 dist/agent_borg-2.7.1.tar.gz                       |  Bin 382916 -> 0 bytes
 dist/agent_borg-3.1.0-py3-none-any.whl             |  Bin 451456 -> 0 bytes
 dist/agent_borg-3.1.0.tar.gz                       |  Bin 401010 -> 0 bytes
 dist/agent_borg-3.1.1-py3-none-any.whl             |  Bin 451620 -> 0 bytes
 dist/agent_borg-3.1.1.tar.gz                       |  Bin 401170 -> 0 bytes
 dist/agent_borg-3.1.2-py3-none-any.whl             |  Bin 478475 -> 0 bytes
 dist/agent_borg-3.1.2.tar.gz                       |  Bin 418819 -> 0 bytes
 dist/agent_borg-3.1.3-py3-none-any.whl             |  Bin 478590 -> 0 bytes
 dist/agent_borg-3.1.3.tar.gz                       |  Bin 418954 -> 0 bytes
 dist/agent_borg-3.2.0-py3-none-any.whl             |  Bin 477650 -> 0 bytes
 dist/agent_borg-3.2.0.tar.gz                       |  Bin 417980 -> 0 bytes
 dist/agent_borg-3.2.1-py3-none-any.whl             |  Bin 478354 -> 0 bytes
 dist/agent_borg-3.2.1.tar.gz                       |  Bin 418721 -> 0 bytes
 dist/agent_borg-3.2.2-py3-none-any.whl             |  Bin 480902 -> 0 bytes
 dist/agent_borg-3.2.2.tar.gz                       |  Bin 421342 -> 0 bytes
 dist/agent_borg-3.2.3-py3-none-any.whl             |  Bin 482434 -> 0 bytes
 dist/agent_borg-3.2.3.tar.gz                       |  Bin 422794 -> 0 bytes
 dist/agent_borg-3.2.4-py3-none-any.whl             |  Bin 484057 -> 0 bytes
 dist/agent_borg-3.2.4.tar.gz                       |  Bin 424438 -> 0 bytes
 dist/agent_borg-3.3.0-py3-none-any.whl             |  Bin 498852 -> 0 bytes
 dist/agent_borg-3.3.0.tar.gz                       |  Bin 435101 -> 0 bytes
 dist/guild_packs-2.0.0-py3-none-any.whl            |  Bin 139852 -> 0 bytes
 dist/guild_packs-2.0.0.tar.gz                      |  Bin 126974 -> 0 bytes
 dist/guild_packs-2.0.1-py3-none-any.whl            |  Bin 141748 -> 0 bytes
 dist/guild_packs-2.0.1.tar.gz                      |  Bin 128755 -> 0 bytes
 dist/guild_packs-2.0.2-py3-none-any.whl            |  Bin 141744 -> 0 bytes
 dist/guild_packs-2.0.2.tar.gz                      |  Bin 128745 -> 0 bytes
 dist/guild_packs-2.0.3-py3-none-any.whl            |  Bin 141755 -> 0 bytes
 dist/guild_packs-2.0.3.tar.gz                      |  Bin 128776 -> 0 bytes
 dist/guild_packs-2.0.4-py3-none-any.whl            |  Bin 143236 -> 0 bytes
 dist/guild_packs-2.0.4.tar.gz                      |  Bin 130204 -> 0 bytes
 dist/guild_packs-2.0.5-py3-none-any.whl            |  Bin 143464 -> 0 bytes
 dist/guild_packs-2.0.5.tar.gz                      |  Bin 130424 -> 0 bytes
 dist/guild_packs-2.0.6-py3-none-any.whl            |  Bin 146037 -> 0 bytes
 dist/guild_packs-2.0.6.tar.gz                      |  Bin 132591 -> 0 bytes
 dist/guild_packs-2.0.7-py3-none-any.whl            |  Bin 146174 -> 0 bytes
 dist/guild_packs-2.0.7.tar.gz                      |  Bin 132740 -> 0 bytes
 dist/guild_packs-2.1.0-py3-none-any.whl            |  Bin 148629 -> 0 bytes
 dist/guild_packs-2.1.0.tar.gz                      |  Bin 134973 -> 0 bytes
 dist/guild_packs-2.1.1-py3-none-any.whl            |  Bin 151208 -> 0 bytes
 dist/guild_packs-2.1.1.tar.gz                      |  Bin 137397 -> 0 bytes
 docs/BORG_PROOF_DASHBOARD.html                     |   14 +-
 docs/BORG_PROOF_DASHBOARD.md                       |   10 +-
 docs/README.md                                     |    4 +
 docs/public/proof-dashboard/index.html             |   14 +-
 eval/borg_proof_dashboard.json                     |   18 +-
 eval/first_user_release_gate_snapshot.json         |   68 +-
 eval/gate_run_snapshot.json                        |   42 +-
 eval/load_1000_snapshot.json                       |   22 +-
 eval/load_100_snapshot.json                        |   22 +-
 eval/load_10_snapshot.json                         |   22 +-
 eval/uat_scoreboard_snapshot.json                  |   28 +-
 pyproject.toml                                     |    3 +-
 343 files changed, 517 insertions(+), 107043 deletions(-)

```
stderr:
(empty)

### `git diff --cached --stat`
rc: `0`
stdout:
```
 borg/core/confidence_gate.py               |  230 ++
 borg/integrations/mcp_server.py            |  166 +-
 borg/tests/test_confidence_gate.py         |  138 ++
 build/lib/borg/core/confidence_gate.py     |  230 ++
 build/lib/borg/integrations/mcp_server.py  | 3243 ++++++++++++++++++++++++++++
 docs/BORG_PROOF_DASHBOARD.html             |   99 +
 docs/BORG_PROOF_DASHBOARD.md               |   85 +
 docs/public/proof-dashboard/index.html     |   99 +
 eval/borg_proof_dashboard.json             |  332 +++
 eval/first_user_release_gate_snapshot.json |  332 +++
 eval/tests/test_borg_proof_dashboard.py    |   52 +
 scripts/borg_proof_dashboard_lint.py       |   87 +
 scripts/build_borg_proof_dashboard.py      |  363 ++++
 13 files changed, 5354 insertions(+), 102 deletions(-)

```
stderr:
(empty)

### `python -c <fresh-process borg.integrations.mcp_server.borg_observe canary>`
rc: `0`
stdout:
```
{
  "unrelated_readiness": {
    "first_1000_chars": "ACTION: proceed with normal debugging for python; Borg has no proven cache hit.\n\nSTOP: do not force a weak or unrelated pack onto this task.\n\nVERIFY: collect the exact failing command/output and rerun borg_observe or borg_rescue only if new evidence appears.\n\nCONFIDENCE: BORG [NO CONFIDENT MATCH] -- no relevant traces, synthetic hits, or pack matches.\n\nNO_CONFIDENT_MATCH: No confident Borg match for python.\nBorg found no relevant real traces, synthetic hits, or exact pack class match.\nProceed with normal reasoning; do not treat Borg as evidence for this task.\nAfter resolving: call borg_rate(helpful=True) only if Borg guidance was actually useful.",
    "length": 654,
    "stale_guidance": false,
    "no_confident_match": true,
    "permission_guidance": false
  },
  "permission_denied": {
    "first_1000_chars": "VERIFY: execute the pack's first checkpoint, then rerun the exact failing command\n\nCONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]\n\n------------------------------------------------------------\nPACK GUIDANCE (bash-permission-denied)\n1. Check file permissions: ls -la <file>\n2. Add execute permission: chmod +x <script.sh>\n3. For directories: chmod +x <directory>\n4. Check ownership: ls -ln <file>\n5. Run as appropriate user: sudo <command>\n6. For SSH keys: chmod 600 ~/.ssh/id_rsa\n------------------------------------------------------------",
    "length": 558,
    "stale_guidance": false,
    "no_confident_match": false,
    "permission_guidance": true
  }
}

```
stderr:
```
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
WARNING:huggingface_hub.utils._http:Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.

Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]
Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4370.79it/s]
[1mBertModel LOAD REPORT[0m from: sentence-transformers/all-MiniLM-L6-v2
Key                     | Status     |  |
------------------------+------------+--+-
embeddings.position_ids | UNEXPECTED |  |

[3mNotes:
- UNEXPECTED[3m	:can be ignored when loading from different task/architecture; not ok if you expect identical arch.[0m

```
