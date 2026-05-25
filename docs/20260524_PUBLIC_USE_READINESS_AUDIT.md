# Borg public-use readiness audit

> Historical/internal — not current product documentation. Use `docs/READINESS.md`, `docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md`, and generated `docs/public/status.json` for current rollout truth.

Rev: 20260524-2304
Repository: `/root/hermes-workspace/borg`
Question: "is Borg ready for public use?"

## verdict

**Broad public use: NO-GO.**

Borg is not ready for broad public self-serve, 100-user rollout, or promotion as a generally-ready public service.

The strongest defensible statement is narrower:

- **Published `agent-borg==3.3.11`:** PyPI install and stdio MCP canary pass, but this is still beta-labeled and does not satisfy public-launch evidence gates.
- **Current source `agent-borg==3.3.12`:** local release candidate is stronger after this audit, but it is **not published**, not on GitHub main/CI, and not cut over into the live served MCP runtime.
- **Live served MCP:** still reports Borg `3.3.7`; this is split-brain against source/PyPI and blocks public trust.
- **Real external users:** first-10 evidence is `0/10`; 100-real-user readiness is therefore also `NO-GO`.

## task decomposition

I split "public use" into independently falsifiable gates:

1. **Published package gate** — can a clean stranger install the public package from PyPI and get working CLI/MCP value?
2. **Source/repo/CI gate** — does current source match package metadata, tests, docs, and CI expectations?
3. **Runtime gate** — does the live served MCP runtime run the same trusted code/version as source/PyPI?
4. **Docs/claims gate** — do public docs avoid stale install pins and unsupported launch/value claims?
5. **Security/privacy gate** — are security checks fail-closed and is the HTTP/MCP surface not accidentally open for unsafe writes?
6. **Real-user evidence gate** — do real external users, not synthetic tests, demonstrate useful ACTION/STOP/VERIFY moments?
7. **100-user rollout gate** — after first-10, is there enough evidence to scale beyond controlled beta?

## threat model used

I treated these as the main ways a false "ready" answer could happen:

- **Local-source contamination:** tests pass because the current checkout is on `PYTHONPATH`, while the actual PyPI wheel behaves differently.
- **Version split-brain:** source, PyPI, GitHub, generated docs, and live MCP each point at different versions.
- **Synthetic-evidence theater:** green tests or simulated users are presented as real public adoption.
- **Claim drift:** generated dashboards/docs say GO while gates say NO-GO.
- **Security theater:** audits are present but allowed to fail silently.
- **MCP transport mismatch:** newline JSON works but standard `Content-Length` MCP framing fails.
- **Stale build artifacts:** local build directories shadow or confuse runtime/test behavior.
- **First-user value gap:** install succeeds, but the first visible rescue gives generic or wrong guidance.

## independent verification performed

### external package / PyPI

- Web/PyPI page check: `agent-borg 3.3.11`, released May 24, 2026.
- PyPI JSON check: latest version `3.3.11`; classifier includes `Development Status :: 4 - Beta`.
- PyPI public metadata summary: `Failure memory CLI and MCP server for AI coding agents`.
- Official fresh PyPI canary for `3.3.11`: **PASS**.
  - `borg --version`: `borg 3.3.11`
  - MCP canary: **PASS**, server info `borg-mcp-server 3.3.11`

Challenge result: published package mechanics work for `3.3.11`, but PyPI is explicitly beta and does not prove public readiness.

### local source / release candidate

Current source was hardened to `3.3.12` during this audit after finding a first-user quality gap in missing-dependency rescue output.

Fix made:

- Added concrete install hints for common `ModuleNotFoundError: No module named X` cases.
- Example: `yaml` now maps to `pip install PyYAML` instead of generic `pip install package-name`.
- Added tests:
  - `test_missing_dependency_rescue_maps_common_import_to_distribution_name`
  - `test_missing_dependency_rescue_uses_import_name_when_mapping_unknown`

Local `3.3.12` release-candidate proof:

- `python -m pytest -q --tb=short`: **2231 passed, 40 skipped, 4 xfailed, 1 xpassed**.
- `scripts/security_gate_check.py`: **PASS**.
- `scripts/benchmark_evidence_contract.py eval/20260515_benchmark_evidence_audit.json`: **valid=true**, `frontier_better_than_proven=false`.
- `scripts/borg_proof_dashboard_lint.py`: **PASS**.
- `python -m compileall -q borg eval scripts tests`: **PASS**.
- `git diff --check`: **PASS**.
- Build/twine check for `3.3.12`: **PASS**.
  - wheel SHA256: `371fe1769561cec423e1e31aac89be887b803a655ec22e6873f20f174d7ef485`
  - sdist SHA256: `dbc740849cbf83b4a4deb899b294b3398d503d5a83cbe0aa8598b3f0ce221016`
- Local wheel install: **PASS**, `borg 3.3.12`.
- Local wheel standard MCP `Content-Length` canary: **PASS**, `borg-mcp-server 3.3.12`.

Challenge result: source is a strong local RC, but it is not public until pushed, CI-verified, published to PyPI, and runtime cut over.

### GitHub / CI

External GitHub check:

- Public repo reachable: `https://github.com/borg-farther/Borg-Directory`.
- GitHub main latest external SHA: `79146eb95ade553464da5e16243a3c1acc083d70`.
- Latest external main CI/security/account-reference runs for that SHA: **success**.

Important limitation:

- Those GitHub results are for the current public `main` state, not the local `3.3.12` audit fix.
- The local `3.3.12` changes have not been pushed and therefore have no GitHub Actions proof yet.

Challenge result: public GitHub is healthy for the existing 3.3.11 line, but not for the new 3.3.12 source changes.

### live served MCP runtime

Live runtime fingerprint result:

- `borg_version`: `3.3.7`
- Runtime Python executable: `/root/.hermes/hermes-agent/venv/bin/python3`
- Loaded path includes `/root/hermes-workspace/borg`
- Confidence-gate canary: passed
- `reload_status`: `loaded_code_has_confidence_gate`

Challenge result: confidence gating exists, but version split-brain remains. A public-facing runtime cannot be called ready while it serves `3.3.7` and source/PyPI are `3.3.11`/`3.3.12`.

### docs / claims

Docs and generated dashboards were regenerated after gate snapshots.

Proof:

- Public claim grep found no `public self-serve launch: **GO**`.
- Public claim grep found no `100 real users: **GO**`.
- Public claim grep found no stale `agent-borg==3.3.11` install pins after the source moved to `3.3.12`.
- `docs_claim_guard`: **true**, `0` violations.
- `scripts/borg_proof_dashboard_lint.py`: **PASS**.

Challenge result: local docs now say the right thing. They truthfully block public use until package/runtime/user-evidence gates pass.

### public launch gates

Final local gate snapshot after fixes:

- Source version: `3.3.12`
- Controlled first-10 beta ready: **false**
- Public self-serve launch ready: **false**
- Max recommended real users now: `0`
- Docs guard: **true**, `0` violations

Blockers:

1. PyPI latest metadata does not match source version or required project URLs.
2. PyPI fresh-install + MCP stdio canary snapshot is missing or failing for source `3.3.12`.
3. First-10 external-user evidence has not passed: `verified=0/10`, `real_users=0/10`, `installs=0/8`, `useful=0/6`, `critical_incidents=0/0`.

Real-user rollout gate:

- Ready for 10 controlled beta: **false**
- Infrastructure ready for 100: **false**
- Ready for 100 real users: **false**

Challenge result: the canonical gates correctly block all public-use claims.

## deliberate disproof attempts

### hypothesis 1: "PyPI installs, so Borg is ready."

Refuted.

PyPI `3.3.11` installs and MCP canary passes, but public use also requires real external-user evidence and runtime consistency. Those fail.

### hypothesis 2: "The tests pass, so Borg is ready."

Refuted.

Tests prove code health, not adoption or hosted runtime correctness. First-10 evidence is `0/10`, and live served MCP is `3.3.7`.

### hypothesis 3: "Controlled beta readiness equals public readiness."

Refuted.

Controlled beta can tolerate supervised evidence capture. Public self-serve requires strangers to succeed without maintainer help and requires first-10 evidence thresholds. Those are not met.

### hypothesis 4: "The live MCP being stale does not matter because users can install locally."

Partly true, but not enough.

For purely local CLI/PyPI testers, live served MCP is not required. But Borg is marketed as an MCP-facing agent tool; public trust cannot claim the live served runtime is current while fingerprint shows `3.3.7`.

### hypothesis 5: "The 3.3.12 local RC should be considered public-ready because it builds and passes tests."

Refuted.

`3.3.12` is not on PyPI, not on GitHub main, not CI-verified remotely, and not loaded by the live served runtime.

### hypothesis 6: "Synthetic or aggregate Borg dashboard metrics prove readiness."

Refuted.

The benchmark evidence contract explicitly says `NO_VALID_EVIDENCE` and `frontier_better_than_proven=false`. Analytics outputs are not a substitute for first-10 external-user evidence.

## weaknesses and uncertainties still present

1. **No real first-10 evidence.** This is the largest blocker and cannot be faked by tests.
2. **No live runtime cutover.** Stale served MCP blocks public trust.
3. **No PyPI `3.3.12`.** The best local fix is not in the public install path.
4. **No GitHub CI proof for local `3.3.12`.** Local tests are green, but remote CI has not run on these local changes.
5. **Published `3.3.11` is mechanically installable but not the final audited code.** It can support controlled beta canaries, but should not be promoted as broad public-ready.
6. **Outcome lift remains unproven.** Benchmark evidence is intentionally conservative and rejects unsupported frontier-better-than-baseline claims.

## final reflective pass from scratch

If I ignore all prior assumptions and ask only: "Can an arbitrary public user rely on Borg today without handholding, current runtime confusion, or misleading claims?" the answer is still **no**.

The evidence chain breaks in three independent places:

1. The live served runtime is stale at `3.3.7`.
2. The current best source is `3.3.12`, but PyPI latest is `3.3.11`.
3. There are zero verified external users in the first-10 gate.

Any one of these would be enough to block broad public use. All three are present.

## exact final decision

- **Broad public self-serve:** NO-GO.
- **100 real-user rollout:** NO-GO.
- **Live served MCP public trust:** NO-GO until runtime fingerprint reports the intended release.
- **Published PyPI local-install beta:** LIMITED GO for controlled beta/canary only on `3.3.11`, with honest beta labeling.
- **Current source release candidate:** GREEN locally as `3.3.12`, but not public until pushed, CI green, published, PyPI canary green, live runtime cut over, and first-10 evidence collected.

## minimum next gates to change the verdict

1. Commit/push the `3.3.12` audit fixes and get GitHub CI/security green.
2. Publish `agent-borg==3.3.12` to PyPI only after pre-release checks stay green.
3. Run PyPI fresh-install + MCP stdio canary for `3.3.12` and record a passing snapshot.
4. Operator-supervised live runtime cutover; fingerprint must report `borg_version: 3.3.12`.
5. Run first-10 real external users and meet the binary threshold:
   - at least 10 real/consented external users,
   - at least 8 installs succeed,
   - at least 6 useful ACTION/STOP/VERIFY moments without maintainer handholding,
   - zero critical privacy/security incidents.
6. Only then rerun public and real-user rollout gates and update the public verdict.
