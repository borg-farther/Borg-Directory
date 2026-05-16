# Borg Production Closure Gate — 2026-05-15

Evidence-grade cron run from `/root/hermes-workspace/borg`. No SSH, no gateway restart/kill/signal, no package install, no venv modification.

- Raw machine-readable capture: `eval/20260515_production_closure_gate_raw.json`
- Captured at UTC: `2026-05-15T08:47:32.957256Z`

## PASS/FAIL table

| # | Check | Status | Evidence / note |
|---:|---|---|---|
| 1 | Repo identity / working tree | PASS | Command exited 0; working tree is dirty with many modified/untracked files. |
| 2 | Confidence gate + observe + first-10 readiness tests | PASS | 32 passed in 5.66s |
| 3 | Rescue + runtime fingerprint + embeddings schema compat tests | FAIL | Fails test_semantic_search_skips_model_load_when_legacy_db_has_no_cached_index. |
| 4 | Security gate check | PASS | PASS: Borg security hardening policy gate |
| 5 | Security hardening baseline eval test | MISSING_NOT_FAILURE | MISSING eval/tests/test_security_hardening_baseline.py |
| 6 | In-process borg_observe MCP canary | PASS | In-process import canary only; live served MCP canary: NOT_CHECKED_FROM_CRON. |
| 7 | First-10 scoreboard read | PASS_READ_BLOCKED | verified_external_users=0, real_users=0, install_successes=0, useful_rescue_moments=0, gate=BLOCKED. |

## Final booleans

- `READY_FOR_SUPERVISED_FIRST_USER`: **NO**
- `READY_FOR_PUBLIC_WAITLIST_OR_NARROW_BETA`: **NO**
- `READY_FOR_SELF_SERVE_PUBLIC_LAUNCH`: **NO**

Rationale: a required compatibility test is failing, live served MCP was not checked from cron, and first-10 real-user evidence is zero.

## Blockers

- Command 3 failed: borg/tests/test_embeddings_schema_compat.py::test_semantic_search_skips_model_load_when_legacy_db_has_no_cached_index loads/builds embeddings for a legacy DB with no cached index; expected [] without model load.
- Live served MCP canary was NOT_CHECKED_FROM_CRON. Only in-process borg.integrations.mcp_server.borg_observe was exercised.
- First-10 scoreboard has verified_external_users=0, real_users=0, install_successes=0, useful_rescue_moments=0; public_self_serve_launch_gate=BLOCKED.
- eval/tests/test_security_hardening_baseline.py is MISSING (recorded as missing, not counted as command failure).
- Working tree is dirty with many modified and untracked files, so evidence is tied to the exact HEAD plus current uncommitted workspace state.

## Raw command captures

### Command 1

```bash
pwd; git status --short; git branch --show-current; git rev-parse HEAD
```
Exit code: `0`

stdout:
```text
/root/hermes-workspace/borg
 M GO_NO_GO_DECISION.md
 M LOAD_TEST_REPORT_10.md
 M LOAD_TEST_REPORT_100.md
 M LOAD_TEST_REPORT_1000.md
 M PROJECT_STATUS.md
 M README.md
 M UAT_RESULTS.md
 M borg/cli.py
 M borg/cli/doctor.py
 M borg/core/confidence_gate.py
 M borg/core/embeddings.py
 M borg/core/feedback_loop.py
 M borg/core/uri.py
 M borg/tests/test_borg_observe_confidence_gate.py
 M borg/tests/test_confidence_gate.py
 M borg/tests/test_distribution_readiness.py
 M borg/tests/test_uri.py
 M borg/tests/test_v3_integration.py
 M docs/20260514_BORG_PUBLIC_LAUNCH_BLOCKER_BOARD.md
 M docs/README.md
 M eval/gate_run_snapshot.json
 M eval/load_1000_snapshot.json
 M eval/load_100_snapshot.json
 M eval/load_10_snapshot.json
 M eval/uat_scoreboard_snapshot.json
 M pyproject.toml
?? .hermes/
?? borg/cli/__main__.py
?? borg/core/first_user_readiness.py
?? borg/core/runtime_fingerprint.py
?? borg/seeds_data/packs/systematic-debugging.workflow.yaml
?? borg/tests/test_embeddings_schema_compat.py
?? borg/tests/test_first_10_readiness.py
?? borg/tests/test_first_user_cli_contract.py
?? borg/tests/test_runtime_fingerprint.py
?? docs/20260513_BORG_DEEP_CUTOVER_EXECUTION_BOARD.md
?? docs/20260513_BORG_FULL_AUDIT_AND_OBSERVE_CONFIDENCE_GATE.md
?? docs/20260513_BORG_MULTI_REPO_PRODUCTION_CLEANUP_CUTOVER_PROPOSAL.md
?? docs/20260514_BORG_EMBEDDINGS_SCHEMA_COMPAT_VERIFICATION_RAW.md
?? docs/20260514_BORG_PRODUCTION_REBUILD_MASTER_PLAN.md
?? docs/20260514_BORG_RUNTIME_FINGERPRINT_CANARY_PROOF.md
?? docs/20260514_BORG_RUNTIME_FINGERPRINT_VERIFICATION_RAW.md
?? docs/20260514_BORG_WORLD_CLASS_HARDENING_BOARD.md
?? docs/20260514_FIRST_10_USER_INVITE_PACKET.md
?? docs/20260514_FIX_ALL_PUBLIC_LAUNCH_BLOCKERS_REPORT.md
?? docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md
?? docs/20260515_LIVE_OBSERVE_CANARY_CONTINUATION.md
?? docs/FIRST_10_BETA_READINESS.md
?? docs/repo-manifest/
?? eval/20260514_fix_all_preflight.json
?? eval/20260514_fix_all_public_launch_blockers.json
?? eval/20260514_public_self_serve_launch_closure_plan.json
?? eval/run_first_user_release_gate.py
?? scripts/approved_do_it_all_safe.py
?? scripts/run_embeddings_schema_compat_verification.py
?? scripts/run_runtime_fingerprint_verification.py
?? tmp_readiness_audit_20260506/
public-waitlist-readiness-20260514
a20921610b7d41bcc7db71361f1271c347ecbc58
```
stderr:
```text

```

### Command 2

```bash
python -m pytest -q borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_first_10_readiness.py
```
Exit code: `0`

stdout:
```text
................................                                         [100%]
32 passed in 5.66s
```
stderr:
```text

```

### Command 3

```bash
python -m pytest -q borg/tests/test_rescue.py borg/tests/test_runtime_fingerprint.py borg/tests/test_embeddings_schema_compat.py
```
Exit code: `1`

stdout:
```text
...........F                                                             [100%]
=================================== FAILURES ===================================
___ test_semantic_search_skips_model_load_when_legacy_db_has_no_cached_index ___

tmp_path = PosixPath('/tmp/pytest-of-root/pytest-81/test_semantic_search_skips_mod0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x79553efb0210>

    def test_semantic_search_skips_model_load_when_legacy_db_has_no_cached_index(tmp_path, monkeypatch):
        db_path = tmp_path / "legacy_traces.db"
        _create_legacy_trace_db(db_path)
    
        calls = {"model": 0}
    
        def fake_get_model():
            calls["model"] += 1
            raise AssertionError("semantic_search should not load embedding model when no index exists")
    
        monkeypatch.setattr(embeddings, "_get_model", fake_get_model)
        embeddings._index_cache = None
        embeddings._index_cache_size = 0
    
>       assert embeddings.semantic_search("fix import bug", str(db_path)) == []
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

borg/tests/test_embeddings_schema_compat.py:61: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
borg/core/embeddings.py:219: in semantic_search
    cache = _get_index(db_path)
            ^^^^^^^^^^^^^^^^^^^
borg/core/embeddings.py:206: in _get_index
    build_index_from_db(db_path)
borg/core/embeddings.py:156: in build_index_from_db
    model = _get_model()
            ^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    def fake_get_model():
        calls["model"] += 1
>       raise AssertionError("semantic_search should not load embedding model when no index exists")
E       AssertionError: semantic_search should not load embedding model when no index exists

borg/tests/test_embeddings_schema_compat.py:55: AssertionError
=========================== short test summary info ============================
FAILED borg/tests/test_embeddings_schema_compat.py::test_semantic_search_skips_model_load_when_legacy_db_has_no_cached_index
1 failed, 11 passed in 0.23s
```
stderr:
```text

```

### Command 4

```bash
python scripts/security_gate_check.py
```
Exit code: `0`

stdout:
```text
PASS: Borg security hardening policy gate
```
stderr:
```text

```

### Command 5

```bash
if [ -f eval/tests/test_security_hardening_baseline.py ]; then python -m pytest -q eval/tests/test_security_hardening_baseline.py; else echo 'MISSING eval/tests/test_security_hardening_baseline.py'; fi
```
Exit code: `0`

stdout:
```text
MISSING eval/tests/test_security_hardening_baseline.py
```
stderr:
```text

```

### Command 6

```bash
python - <<'PY'
from borg.integrations import mcp_server
cases=[
 ('unrelated', dict(task='continue Borg readiness/get it there: fix borg_observe irrelevant guidance/runtime mismatch and proceed toward first-user readiness', context='python borg mcp runtime readiness')),
 ('permission', dict(task='Fix bash: ./deploy.sh: Permission denied', context='bash permission denied chmod')),
]
for name,kw in cases:
    print('---CANARY', name, '---')
    out=mcp_server.borg_observe(**kw)
    print(out[:2000])
    print('HAS_NO_CONFIDENT_MATCH=', 'NO_CONFIDENT_MATCH' in out or 'NO CONFIDENT MATCH' in out)
    print('HAS_STALE_PLUGIN=', 'Plugin directory ~/.hermes/plugins/' in out or 'BORG_HOME env var' in out)
    print('HAS_PY_TYPE_PACK=', 'PACK GUIDANCE (python-type-error)' in out)
    print('HAS_PERMISSION=', 'Permission denied' in out or 'chmod' in out or 'PACK GUIDANCE (bash-permission-denied)' in out)
PY
```
Exit code: `0`

stdout:
```text
---CANARY unrelated ---
ACTION: proceed with normal debugging for python; Borg has no proven cache hit.

STOP: do not force a weak or unrelated pack onto this task.

VERIFY: collect the exact failing command/output and rerun borg_observe or borg_rescue only if new evidence appears.

CONFIDENCE: BORG [NO CONFIDENT MATCH] -- no relevant traces, synthetic hits, or pack matches.

NO_CONFIDENT_MATCH: No confident Borg match for python.
Borg found no relevant real traces, synthetic hits, or exact pack class match.
Proceed with normal reasoning; do not treat Borg as evidence for this task.
After resolving: call borg_rate(helpful=True) only if Borg guidance was actually useful.
HAS_NO_CONFIDENT_MATCH= True
HAS_STALE_PLUGIN= False
HAS_PY_TYPE_PACK= False
HAS_PERMISSION= False
---CANARY permission ---
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
HAS_NO_CONFIDENT_MATCH= False
HAS_STALE_PLUGIN= False
HAS_PY_TYPE_PACK= False
HAS_PERMISSION= True
```
stderr:
```text
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
WARNING:huggingface_hub.utils._http:Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.

Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]
Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4000.75it/s]
[1mBertModel LOAD REPORT[0m from: sentence-transformers/all-MiniLM-L6-v2
Key                     | Status     |  | 
------------------------+------------+--+-
embeddings.position_ids | UNEXPECTED |  | 

[3mNotes:
- UNEXPECTED[3m	:can be ignored when loading from different task/architecture; not ok if you expect identical arch.[0m
```

### Command 7

```bash
python - <<'PY'
import json, pathlib
p=pathlib.Path('eval/first_10_user_scoreboard.json')
print('---FIRST10---')
if p.exists():
 data=json.loads(p.read_text())
 print(json.dumps({
   'verified_external_users': data.get('truth_policy',{}).get('verified_external_users'),
   'real_users': data.get('current_counts',{}).get('real_users'),
   'install_successes': data.get('current_counts',{}).get('install_successes'),
   'useful_rescue_moments': data.get('current_counts',{}).get('useful_rescue_moments'),
   'public_self_serve_launch_gate': data.get('current_verdict',{}).get('public_self_serve_launch_gate'),
 }, indent=2))
else:
 print('MISSING eval/first_10_user_scoreboard.json')
PY
```
Exit code: `0`

stdout:
```text
---FIRST10---
{
  "verified_external_users": 0,
  "real_users": 0,
  "install_successes": 0,
  "useful_rescue_moments": 0,
  "public_self_serve_launch_gate": "BLOCKED"
}
```
stderr:
```text

```

