# Borg channels and install methods

**Version target:** `agent-borg==3.3.20`
**Last updated:** 2026-06-11
**Scope:** what a GitHub/PyPI visitor can use today, what is only a local/dev path, and what must stay blocked until separate evidence exists.

## Executive truth

A user arriving from GitHub/PyPI can use the production package runtime path, but controlled first-10 beta is **NO-GO** right now. `agent-borg==3.3.20` is published with metadata-correct PyPI long-description and exact-version fresh-install/stdio MCP/generated-rules/OpenClaw runtime canary proof green; served-runtime freshness and first-10 evidence are still red and keep the real-user cap at 0. The target path after served-runtime and first-10 evidence gates are green is:

1. `pipx install agent-borg==3.3.20`
2. `borg rescue "ModuleNotFoundError: No module named flask" --short`
3. for MCP clients, configure local stdio command `borg-mcp`

Do not invite controlled first-10 users until PyPI fresh-install/MCP/generate/OpenClaw canaries remain green, served-runtime freshness passes, and first-10 evidence intake is ready to capture consented rows. Keep served/remote MCP, broad public self-serve, 100-user rollout, and measured external lift blocked until their separate gates pass.

## Channel matrix

| Channel / mix | User command or config | Gate | Current claim |
|---|---|---:|---|
| PyPI CLI via pipx | `pipx install agent-borg==3.3.20`; `borg rescue ...` | `eval/run_pypi_fresh_install_canary.py --version 3.3.20` | PyPI latest metadata, fresh install, CLI, API, local stdio MCP, rules export, and OpenClaw canaries pass for `3.3.20`. Controlled first-10 beta remains blocked until served-runtime freshness, ops/watchdog, proof-dashboard, and first-10 evidence gates pass; public self-serve remains NO-GO |
| PyPI in active Python env | `python -m pip install agent-borg==3.3.20` | same PyPI canary plus `borg-doctor --json` | Runtime and package-metadata canaries pass for `3.3.20`; controlled beta is still blocked until served-runtime freshness, ops/watchdog, and first-10 evidence are green |
| GitHub direct install | `python -m pip install git+https://github.com/borg-farther/Borg-Directory.git@main` | channel smoke / source local gate | GO only after `origin/main` has the release commit and CI is green |
| Local clone/editable | `git clone ...`; `python -m pip install -e .` | `eval/run_first_user_release_gate.py` and targeted first-user tests | GO for contributors/dev verification, not normal users |
| CLI rescue/search/try | `borg rescue`, `borg search`, `borg try` | first-user release gate + PyPI canary | Production PyPI package/runtime path works for `3.3.20`; external beta still waits on served-runtime freshness, ops/watchdog, and first-10 evidence gates |
| Platform rules export | `borg generate systematic-debugging --format all --output ./rules` | first-user release gate + PyPI canary file-output checks | Production PyPI package/runtime path works for `3.3.20`; external beta still waits on served-runtime freshness, ops/watchdog, and first-10 evidence gates |
| OpenClaw export | `borg convert . --format openclaw --all --output ./openclaw-skills` | first-user release gate + PyPI canary file-output checks | Production PyPI package/runtime path works for `3.3.20`; external beta still waits on served-runtime freshness, ops/watchdog, and first-10 evidence gates |
| Python API | `import borg; borg.check(...)` | first-user release gate + PyPI canary | Production PyPI package/runtime path works for `3.3.20`; external beta still waits on served-runtime freshness, ops/watchdog, and first-10 evidence gates |
| Generic stdio MCP | MCP config command `borg-mcp` | PyPI canary JSON-RPC initialize/tools/call/fingerprint | Local stdio path is canaried from `3.3.20`; served Hermes/remote MCP remains NO-GO until runtime freshness passes |
| Claude Code | `borg setup-claude --scope user --verify --fix` | first-user release gate + setup verification | External beta blocked until runtime freshness and ops/watchdog proof pass |
| Hermes Agent | add `mcp_servers.borg` pointing at `borg-mcp` | docs + manual host verification | Local stdio MCP runtime canary passes from PyPI; served Hermes runtime remains NO-GO until operator cutover proof |
| Cursor / Cline / Windsurf rules | generated `.cursorrules`, `.clinerules`, `CLAUDE.md`, `.windsurfrules` | generator tests + first-user gate | Production PyPI package/runtime path works for `3.3.20`; external beta still waits on served-runtime freshness, ops/watchdog, and first-10 evidence gates |
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
