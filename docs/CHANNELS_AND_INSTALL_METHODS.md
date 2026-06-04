# Borg channels and install methods

**Version target:** `agent-borg==3.3.18`
**Last updated:** 2026-06-02
**Scope:** what a GitHub/PyPI visitor can use today, what is only a local/dev path, and what must stay blocked until separate evidence exists.

## Executive truth

A user arriving from GitHub can use the exact-SHA source install path when given a 40-hex commit: the source canary proves isolated install, CLI, Python API, generated rules/OpenClaw, and local stdio MCP with direct URL commit binding. A user arriving from PyPI can use basic `agent-borg==3.3.18` CLI/API/MCP signals, but the full PyPI package canary is **red** because immutable `3.3.18` still fails clean-install OpenClaw registry conversion. Controlled first-10 beta is **NO-GO** right now; served-runtime freshness and first-10 evidence are still red and keep the real-user cap at 0. The target path after package, served-runtime, and first-10 evidence gates are green is:

1. `pipx install agent-borg==3.3.18`
2. `borg rescue "ModuleNotFoundError: No module named flask" --short`
3. for MCP clients, configure local stdio command `borg-mcp`

Do not invite controlled first-10 users until PyPI fresh-install/MCP/generate/OpenClaw canaries are green for a new immutable package version, served-runtime freshness passes, and first-10 evidence intake is ready to capture consented rows. Keep served/remote MCP, broad public self-serve, 100-user rollout, and measured external lift blocked until their separate gates pass.

## Channel matrix

| Channel / mix | User command or config | Gate | Current claim |
|---|---|---:|---|
| PyPI CLI via pipx | `pipx install agent-borg==3.3.18`; `borg rescue ...` | `eval/run_pypi_fresh_install_canary.py --version 3.3.18` | Basic install/CLI/API/local stdio MCP signals exist, but the full PyPI canary is red because immutable `3.3.18` fails clean-install OpenClaw registry conversion. Controlled first-10 beta remains blocked until a new immutable package passes, served-runtime freshness passes, ops/watchdog/proof-dashboard gates pass, and first-10 evidence gates pass; public self-serve remains NO-GO |
| PyPI in active Python env | `python -m pip install agent-borg==3.3.18` | same PyPI canary plus `borg-doctor --json` | Basic PyPI runtime signals exist for `3.3.18`; full package proof is red until a new immutable release fixes OpenClaw. Controlled beta is still blocked until package proof, served-runtime freshness, ops/watchdog, and first-10 evidence are green |
| GitHub direct install | `python -m pip install git+https://github.com/borg-farther/Borg-Directory.git@<40-hex-sha>` | `eval/run_github_source_install_canary.py --install-source git+https://github.com/borg-farther/Borg-Directory.git@<sha> --expected-commit <sha>` | exact-commit source smoke is green for the proven PR head; requires pip `direct_url.json` commit binding and non-repo runtime cwd; not public self-serve or unattended onboarding until package, served-runtime, and first-10 external install/MCP/rescue evidence pass |
| Local clone/editable | `git clone ...`; `python -m pip install -e .` | `eval/run_first_user_release_gate.py` and targeted first-user tests | GO for contributors/dev verification, not normal users |
| CLI rescue/search/try | `borg rescue`, `borg search`, `borg try` | first-user release gate + source/PyPI canaries | GitHub exact-SHA source path works; PyPI basic runtime signals work but full PyPI package proof is red until a new release; external beta still waits on served-runtime freshness, ops/watchdog, and first-10 evidence gates |
| Platform rules export | `borg generate systematic-debugging --format all --output ./rules` | first-user release gate + source/PyPI file-output checks | GitHub exact-SHA source path works; full PyPI package proof is red until clean-install OpenClaw passes in a new immutable release |
| OpenClaw export | `borg convert . --format openclaw --all --output ./openclaw-skills` | first-user release gate + source/PyPI file-output checks | GitHub exact-SHA source path works; published PyPI `3.3.18` fails this full canary from a clean environment, so package proof remains red |
| Python API | `import borg; borg.check(...)` | first-user release gate + source/PyPI canaries | GitHub exact-SHA source path works; PyPI basic API signal works, but package-current proof stays red until a new immutable release passes all canaries |
| Generic stdio MCP | MCP config command `borg-mcp` | PyPI/source JSON-RPC initialize/tools/call/fingerprint canary | GitHub exact-SHA local stdio path is canary-green; published PyPI basic stdio signal works, but full package proof is red; served Hermes/remote MCP remains NO-GO until runtime freshness passes |
| Claude Code | `borg setup-claude --scope user --verify --fix` | first-user release gate + setup verification | External beta blocked until package proof, runtime freshness, and ops/watchdog proof pass |
| Hermes Agent | add `mcp_servers.borg` pointing at `borg-mcp` | docs + manual host verification | Local stdio MCP source canary passes; served Hermes runtime remains NO-GO until operator cutover proof |
| Cursor / Cline / Windsurf rules | generated `.cursorrules`, `.clinerules`, `CLAUDE.md`, `.windsurfrules` | generator tests + first-user/source gate | GitHub exact-SHA source path works; full PyPI package proof is red until a new immutable release passes all canaries |
| Docker draft | `deploy/docker/Dockerfile.borg` | presentation contract only | Draft; not the primary first-user path |
| Smithery listing | `deploy/smithery/smithery.yaml` | presentation contract only | Draft/local stdio metadata; remote/HTTP listing remains NO-GO |
| Served/remote MCP | HTTP/remote service endpoint | live runtime fingerprint/cutover proof | NO-GO until actual served process is fingerprinted at current version |
| Broad public self-serve launch | unconstrained public funnel | `eval/public_self_serve_launch_gate.py` + first-10 external rows | NO-GO |
| 100-user rollout | scaled external rollout | `eval/real_user_rollout_gate.py` + first-10 pass | NO-GO |
| Measured external lift | success/lift/savings claims | row-derived external outcome data | NO-GO |

## Required smoke path before saying a channel is current

For any release/version update, the smoke must prove all of these from a clean install or clean venv, not from the maintainer checkout:

```bash
borg --version
borg-doctor --json
borg rescue "ModuleNotFoundError: No module named flask" --json
borg search "django migration table already exists"
borg try systematic-debugging
borg generate systematic-debugging --format all --output ./rules
borg convert . --format openclaw --all --output ./openclaw-skills
python - <<'PY'
import borg, json
r = borg.check("ModuleNotFoundError: No module named flask", top_k=1)
print(json.dumps({"version": borg.__version__, "result_type": type(r).__name__, "count": len(r)}))
PY
```

For stdio MCP, the canary must prove:

- `initialize` returns `serverInfo.name == "borg-mcp-server"` and the current version.
- `tools/list` includes at least `error_lookup`, `borg_rescue`, `borg_observe`, and `borg_runtime_fingerprint`.
- `tools/call error_lookup` returns ACTION / STOP / VERIFY.
- `tools/call borg_runtime_fingerprint` passes the behavior canaries.

## Anti-drift rule

If GitHub source, PyPI latest, README status, proof dashboard, Smithery metadata, and the first-user canaries do not all agree on the same version, the channel is **not current**. Fix the code/docs/proof artifacts or label the channel as blocked; do not silently rely on “latest”.
