> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg Production Closure Gate Rerun - 2026-05-15

## Summary

- READY_FOR_SUPERVISED_FIRST_USER: **NO**
- READY_FOR_PUBLIC_WAITLIST_OR_NARROW_BETA: **NO**
- READY_FOR_SELF_SERVE_PUBLIC_LAUNCH: **NO**

## PASS/FAIL table

| Step | Result | Exit code | Command |
|---:|---|---:|---|
| 1 | PASS | 0 | `pwd; git status --short; git branch --show-current; git rev-parse HEAD` |
| 2 | PASS | 0 | `python -m pytest -q borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_first_10_readiness.py` |
| 3 | FAIL | 1 | `python -m pytest -q borg/tests/test_rescue.py borg/tests/test_runtime_fingerprint.py borg/tests/test_embeddings_schema_compat.py` |
| 4 | PASS | 0 | `python scripts/security_gate_check.py` |
| 5 | PASS | 0 | `python -m pytest -q eval/tests/test_security_hardening_baseline.py` |
| 6 | PASS | 0 | `python - <<'PY'` |
| 7 | PASS | 0 | `python - <<'PY'` |

## Blockers

- Step 3 failed with exit code 1: python -m pytest -q borg/tests/test_rescue.py borg/tests/test_runtime_fingerprint.py borg/tests/test_embeddings_schema_compat.py
- First-10 verified external/real users are 0.
- Live served MCP canary was not checked; only in-process borg_observe canary ran.

## Raw command captures

### Step 1

Command:
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
?? docs/20260515_PRODUCTION_CLOSURE_GATE.md
?? docs/FIRST_10_BETA_READINESS.md
?? docs/repo-manifest/
?? eval/20260514_fix_all_preflight.json
?? eval/20260514_fix_all_public_launch_blockers.json
?? eval/20260514_public_self_serve_launch_closure_plan.json
?? eval/20260515_production_closure_gate_raw.json
?? eval/run_first_user_release_gate.py
?? eval/tests/test_security_hardening_baseline.py
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

### Step 2

Command:
```bash
python -m pytest -q borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_first_10_readiness.py
```
Exit code: `0`

stdout:
```text
................................                                         [100%]
32 passed in 7.92s

```
stderr:
```text

```

### Step 3

Command:
```bash
python -m pytest -q borg/tests/test_rescue.py borg/tests/test_runtime_fingerprint.py borg/tests/test_embeddings_schema_compat.py
```
Exit code: `1`

stdout:
```text
...........F                                                             [100%]
=================================== FAILURES ===================================
___ test_semantic_search_skips_model_load_when_legacy_db_has_no_cached_index ___

tmp_path = PosixPath('/tmp/pytest-of-root/pytest-83/test_semantic_search_skips_mod0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x75e6d87882d0>

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
borg/core/embeddings.py:239: in semantic_search
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
1 failed, 11 passed in 0.30s

```
stderr:
```text

```

### Step 4

Command:
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

### Step 5

Command:
```bash
python -m pytest -q eval/tests/test_security_hardening_baseline.py
```
Exit code: `0`

stdout:
```text
.....                                                                    [100%]
5 passed in 0.03s

```
stderr:
```text

```

### Step 6

Command:
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
Loading weights: 100%|██████████| 103/103 [00:00<00:00, 2675.20it/s]
[1mBertModel LOAD REPORT[0m from: sentence-transformers/all-MiniLM-L6-v2
Key                     | Status     |  | 
------------------------+------------+--+-
embeddings.position_ids | UNEXPECTED |  | 

[3mNotes:
- UNEXPECTED[3m	:can be ignored when loading from different task/architecture; not ok if you expect identical arch.[0m

```

### Step 7

Command:
```bash
python - <<'PY'
import json, pathlib
p=pathlib.Path('eval/first_10_user_scoreboard.json')
print('---FIRST10---')
data=json.loads(p.read_text())
print(json.dumps({
   'verified_external_users': data.get('truth_policy',{}).get('verified_external_users'),
   'real_users': data.get('current_counts',{}).get('real_users'),
   'install_successes': data.get('current_counts',{}).get('install_successes'),
   'useful_rescue_moments': data.get('current_counts',{}).get('useful_rescue_moments'),
   'public_self_serve_launch_gate': data.get('current_verdict',{}).get('public_self_serve_launch_gate'),
 }, indent=2))
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
