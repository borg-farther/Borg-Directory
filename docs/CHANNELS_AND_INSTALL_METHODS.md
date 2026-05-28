# Borg channels and install methods

**Version target:** `agent-borg==3.3.15`
**Last updated:** 2026-05-28
**Scope:** what a GitHub/PyPI visitor can use today, what is only a local/dev path, and what must stay blocked until separate evidence exists.

## Executive truth

A user arriving from GitHub should be sent to the local Python package path only after the current source, PyPI latest, and proof artifacts agree on the same version. For the 3.3.15 branch, the target path is:

1. `pipx install agent-borg==3.3.15`
2. `borg rescue "ModuleNotFoundError: No module named flask" --short`
3. for MCP clients, configure local stdio command `borg-mcp`

Until `agent-borg==3.3.15` is published and the fresh-install/MCP/generate/OpenClaw canaries pass, this matrix is a release-candidate contract, not an invitation to external users.

The package remains blocked for controlled first-10 beta while PyPI/proof are stale. Do not route users to served/remote MCP, broad public self-serve, 100-user rollout, or measured external lift claims until their gates pass.

## Channel matrix

| Channel / mix | User command or config | Gate | Current claim |
|---|---|---:|---|
| PyPI CLI via pipx | `pipx install agent-borg==3.3.15`; `borg rescue ...` | `eval/run_pypi_fresh_install_canary.py` after release | BLOCKED until PyPI latest + fresh install canary is green for 3.3.15 |
| PyPI in active Python env | `python -m pip install agent-borg==3.3.15` | same PyPI canary plus `borg-doctor --json` | BLOCKED for external users until 3.3.15 is published/canaried |
| GitHub direct install | `python -m pip install git+https://github.com/borg-farther/Borg-Directory.git@main` | channel smoke / source local gate | GO only after `origin/main` has the release commit and CI is green |
| Local clone/editable | `git clone ...`; `python -m pip install -e .` | `eval/run_first_user_release_gate.py` and targeted first-user tests | GO for contributors/dev verification, not normal users |
| CLI rescue/search/try | `borg rescue`, `borg search`, `borg try` | first-user release gate + PyPI canary | source/local GO; external-user GO after PyPI canary |
| Platform rules export | `borg generate systematic-debugging --format all --output ./rules` | first-user release gate + PyPI canary file-output checks | fixed in source; external-user GO after PyPI canary |
| OpenClaw export | `borg convert . --format openclaw --all --output ./openclaw-skills` | first-user release gate + PyPI canary file-output checks | fixed in source; external-user GO after PyPI canary |
| Python API | `import borg; borg.check(...)` | first-user release gate + PyPI canary | source/local GO; external-user GO after PyPI canary |
| Generic stdio MCP | MCP config command `borg-mcp` | PyPI canary JSON-RPC initialize/tools/call/fingerprint | source/local GO; external-user GO after PyPI canary |
| Claude Code | `borg setup-claude --scope user --verify --fix` | first-user release gate + setup verification | source/local GO; external-user GO after PyPI canary and full host restart |
| Hermes Agent | add `mcp_servers.borg` pointing at `borg-mcp` | docs + manual host verification | GO only as local stdio MCP after package proof; exact host config is in `docs/MCP_SETUP.md` |
| Cursor / Cline / Windsurf rules | generated `.cursorrules`, `.clinerules`, `CLAUDE.md`, `.windsurfrules` | generator tests + first-user gate | source/local GO for exported rule files; external-user GO after PyPI canary |
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
