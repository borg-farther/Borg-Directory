# Borg channels and install methods

**Version target:** `agent-borg==3.3.18`
**Last updated:** 2026-06-02
**Scope:** what a GitHub/PyPI visitor can use today, what is only a local/dev path, and what must stay blocked until separate evidence exists.

## Executive truth

A GitHub-source visitor has a narrow **GO** path when the committed canary snapshot is green: clean VCS install from canonical GitHub passes CLI, Python API, rescue/doctor, and local stdio MCP canaries. A PyPI visitor can still install the published `agent-borg==3.3.18`, but current-source PyPI/package proof is **NO-GO** until a new immutable package release includes the bundled-pack clean-install fix and the PyPI fresh-install/OpenClaw canary is green. Controlled first-10 beta is **NO-GO / cap 0** until source/package/release/ops/docs gates and first-10 evidence are green. The source-channel smoke command is:

Exact committed canary command recorded by `eval/github_source_install_snapshot.json`: `python -m pip install 'git+https://github.com/borg-farther/Borg-Directory.git@36688c1c3dfbfd0083f14399d14a5135c9a892a6'`.

1. `python -m pip install 'git+https://github.com/borg-farther/Borg-Directory.git@main'`
2. `borg rescue "ModuleNotFoundError: No module named flask" --short`
3. for MCP clients, configure local stdio command `borg-mcp`

Do not invite controlled first-10 users until current-source PyPI fresh-install/MCP/generate/OpenClaw canaries are green, release/ops/docs gates remain green, and first-10 evidence intake is ready to capture consented rows. Keep served/remote MCP, broad public self-serve, 100-user rollout, and measured external lift blocked until their separate gates pass.

## Channel matrix

| Channel / mix | User command or config | Gate | Current claim |
|---|---|---:|---|
| GitHub direct install | `python -m pip install 'git+https://github.com/borg-farther/Borg-Directory.git@main'`; canaried exact commit: `python -m pip install 'git+https://github.com/borg-farther/Borg-Directory.git@341a0df821117b7c85a7da04f15b561f2e0ede48'` | GitHub source exact-commit canary | **GO for source-channel smoke** when `eval/github_source_install_snapshot.json` is green: CLI, Python API, rescue/doctor, and local stdio MCP canaries pass. Not a PyPI/current-package or public beta GO |
| PyPI CLI via pipx | `pipx install agent-borg==3.3.18`; `borg rescue ...` | `eval/run_pypi_fresh_install_canary.py --version 3.3.18` | Published package exists and is metadata-correct, but current-source PyPI proof is **NO-GO** until the next immutable release includes the bundled-pack clean-install fix and OpenClaw canary passes |
| PyPI in active Python env | `python -m pip install agent-borg==3.3.18` | same PyPI canary plus `borg-doctor --json` | Runtime path remains usable, but current-source package proof is blocked until the next release/canary |
| Local clone/editable | `git clone ...`; `python -m pip install -e .` | `eval/run_first_user_release_gate.py` and targeted first-user tests | GO for contributors/dev verification, not normal users |
| CLI rescue/search/try | `borg rescue`, `borg search`, `borg try` | first-user release gate + source/PyPI canaries | Source-channel smoke is GO at the exact GitHub commit; PyPI current-source proof waits on the next package release |
| Platform rules export | `borg generate systematic-debugging --format all --output ./rules` | source/PyPI file-output checks | Source/package gate covered; current-source PyPI proof waits on next immutable release |
| OpenClaw export | `borg convert . --format openclaw --all --output ./openclaw-skills` | source/PyPI file-output checks | Source fix keeps clean installs on bundled packs; PyPI current-source OpenClaw proof waits on next immutable release |
| Python API | `import borg; borg.check(...)` | first-user release gate + source/PyPI canaries | Source-channel smoke is GO at the exact GitHub commit; PyPI current-source proof waits on the next package release |
| Generic stdio MCP | MCP config command `borg-mcp` | source/PyPI JSON-RPC initialize/tools/call/fingerprint canary | Local stdio path is canaried from the exact GitHub source commit; served Hermes/remote MCP remains NO-GO until runtime freshness passes |
| Claude Code | `borg setup-claude --scope user --verify --fix` | first-user release gate + setup verification | External beta blocked until runtime freshness and ops/watchdog proof pass |
| Hermes Agent | add `mcp_servers.borg` pointing at `borg-mcp` | docs + manual host verification | Local stdio MCP source path is green; served Hermes runtime remains NO-GO until operator cutover proof |
| Cursor / Cline / Windsurf rules | generated `.cursorrules`, `.clinerules`, `CLAUDE.md`, `.windsurfrules` | generator tests + first-user gate | Source-channel smoke is GO; current-source PyPI proof waits on next immutable release; external beta still waits on release/ops/docs/first-10 evidence gates |
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
