# Borg channels and install methods

**Version target:** `agent-borg==3.3.21`
**Last updated:** 2026-06-11
**Scope:** what a GitHub/PyPI visitor can use today, what is only a local/dev path, and what must stay blocked until separate evidence exists.

## Executive truth

The source release candidate is `agent-borg==3.3.21`; controlled first-10 beta is **NO-GO** with cap 0. A channel is current only when the live gate proves that its resolved package version equals the source version and that the fresh-install, stdio MCP, generated-rules, OpenClaw, served-runtime, governance, and watchdog checks pass. Static documentation never promotes a channel. The eventual first-user path is:

1. `pipx install agent-borg==3.3.21` only after the exact version exists on PyPI and its gate is green
2. `borg rescue "ModuleNotFoundError: No module named flask" --short`
3. for MCP clients, configure local stdio command `borg-mcp`

Do not invite controlled first-10 users until every release-control gate is green and evidence intake is ready to capture consented rows. Keep served/remote MCP, broad public self-serve, 100-user rollout, and measured external lift blocked until their separate gates pass.

## Channel matrix

| Channel / mix | User command or config | Gate | Current claim |
|---|---|---:|---|
| PyPI CLI via pipx | `pipx install agent-borg==3.3.21`; `borg rescue ...` | `eval/run_pypi_fresh_install_canary.py --version 3.3.21` | BLOCKED until that exact immutable version exists on PyPI and the full canary passes; no first-10 invite |
| PyPI in active Python env | `python -m pip install agent-borg==3.3.21` | same PyPI canary plus `borg-doctor --json` | BLOCKED until exact-version package/runtime proof is green |
| GitHub direct install | `python -m pip install git+https://github.com/borg-farther/Borg-Directory.git@main` | channel smoke / source local gate | GO for contributors only after `origin/main` has the release commit and CI is green; not public-package proof |
| Local clone/editable | `git clone ...`; `python -m pip install -e .` | `eval/run_first_user_release_gate.py` and targeted first-user tests | GO for contributors/dev verification, not normal users |
| CLI rescue/search/try | `borg rescue`, `borg search`, `borg try` | first-user release gate + exact-version PyPI canary | Source/local path is testable; production channel remains blocked until the PyPI gate agrees |
| Platform rules export | `borg generate systematic-debugging --format all --output ./rules` | first-user release gate + PyPI canary file-output checks | Source/local path is testable; production channel remains blocked until the PyPI gate agrees |
| OpenClaw export | `borg convert . --format openclaw --all --output ./openclaw-skills` | first-user release gate + PyPI canary file-output checks | Source/local path is testable; production channel remains blocked until the PyPI gate agrees |
| Python API | `import borg; borg.check(...)` | first-user release gate + PyPI canary | Source/local path is testable; production channel remains blocked until the PyPI gate agrees |
| Generic stdio MCP | MCP config command `borg-mcp` | PyPI canary JSON-RPC initialize/tools/call/fingerprint | Source/local path is testable; served Hermes/remote MCP remains NO-GO |
| Claude Code | `borg setup-claude --scope user --verify --fix` | first-user release gate + setup verification | External beta blocked until every release-control gate is green |
| Hermes Agent | add `mcp_servers.borg` pointing at `borg-mcp` | docs + manual host verification | Local source verification does not authorize a served-runtime claim |
| Cursor / Cline / Windsurf rules | generated `.cursorrules`, `.clinerules`, `CLAUDE.md`, `.windsurfrules` | generator tests + first-user gate | Source/local path is testable; production channel remains blocked until the PyPI gate agrees |
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
