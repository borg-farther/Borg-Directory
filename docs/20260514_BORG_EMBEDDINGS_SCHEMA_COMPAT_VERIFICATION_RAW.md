# 20260514 Borg embeddings schema compatibility verification raw output

generated_at_utc: 2026-05-14T12:26:08Z
passed: False
json: `/root/hermes-workspace/borg/docs/repo-manifest/20260514_embeddings_schema_compat_verification_raw.json`

## assertions

- all_commands_zero: `False`
- causal_intervention_error_absent: `True`
- model_loading_absent_on_canary: `False`
- stale_pack_guidance_absent: `True`
- stale_no_confident_present: `True`
- permission_positive_guidance_present: `True`

## embeddings_schema_and_confidence_tests

cwd: `/root/hermes-workspace/borg`
returncode: `1`
duration_sec: `9.137`

### command
```
/root/.hermes/hermes-agent/venv/bin/python -m pytest -q borg/tests/test_embeddings_schema_compat.py borg/tests/test_runtime_fingerprint.py borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py
```

### stdout
```
.F.....................                                                  [100%]
=================================== FAILURES ===================================
___ test_semantic_search_skips_model_load_when_legacy_db_has_no_cached_index ___

tmp_path = PosixPath('/tmp/pytest-of-root/pytest-78/test_semantic_search_skips_mod0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x794db99e1f90>

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
1 failed, 22 passed in 6.12s

```

### stderr
```

```

## fresh_mcp_stale_and_permission_canaries

cwd: `/root/hermes-workspace/borg`
returncode: `0`
duration_sec: `10.651`

### command
```
/root/.hermes/hermes-agent/venv/bin/python -c 
import json, subprocess, sys
reqs=[
 {'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},
 {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'borg_observe','arguments':{'task':'continue production readiness review and implementation\n\n=== BORG GUIDANCE ===\nCONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]\nPACK GUIDANCE (bash-permission-denied)\n1. Check file permissions: ls -la','context':'operator meta instruction'}}},
 {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'borg_observe','arguments':{'task':'Fix bash: ./deploy.sh: Permission denied','context':'bash: ./deploy.sh: Permission denied'}}},
]
proc=subprocess.Popen([sys.executable,'-m','borg.integrations.mcp_server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
out,err=proc.communicate(''.join(json.dumps(r)+'\n' for r in reqs),timeout=30)
print('EXIT=', proc.returncode)
print('STDERR_START')
print(err)
print('STDERR_END')
print('STDOUT_START')
print(out)
print('STDOUT_END')
print('STDERR_HAS_CAUSAL_ERROR=', 'no such column: causal_intervention' in err)
print('STDERR_HAS_MODEL_LOADING=', 'Loading weights' in err or 'BertModel LOAD REPORT' in err)
for line in out.splitlines():
    try: obj=json.loads(line)
    except Exception: continue
    if obj.get('id') == 2:
        txt=obj.get('result',{}).get('content',[{}])[0].get('text','')
        print('STALE_HAS_PACK_GUIDANCE=', 'PACK GUIDANCE' in txt)
        print('STALE_HAS_NO_CONFIDENT=', 'NO_CONFIDENT_MATCH' in txt or 'NO CONFIDENT MATCH' in txt)
        print('STALE_TEXT_START')
        print(txt[:1500])
        print('STALE_TEXT_END')
    if obj.get('id') == 3:
        txt=obj.get('result',{}).get('content',[{}])[0].get('text','')
        print('PERM_HAS_GUIDANCE=', 'Permission denied' in txt or 'chmod' in txt or 'PACK GUIDANCE' in txt)
        print('PERM_TEXT_START')
        print(txt[:1500])
        print('PERM_TEXT_END')

```

### stdout
```
EXIT= 0
STDERR_START
borg-mcp-server v3.3.1 ready (stdio transport)
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
WARNING:huggingface_hub.utils._http:Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.

Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]
Loading weights: 100%|██████████| 103/103 [00:00<00:00, 2902.96it/s]
[1mBertModel LOAD REPORT[0m from: sentence-transformers/all-MiniLM-L6-v2
Key                     | Status     |  | 
------------------------+------------+--+-
embeddings.position_ids | UNEXPECTED |  | 

[3mNotes:
- UNEXPECTED[3m	:can be ignored when loading from different task/architecture; not ok if you expect identical arch.[0m

STDERR_END
STDOUT_START
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "borg-mcp-server", "version": "1.0.0"}, "capabilities": {"tools": {}}}}
{"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "ACTION: proceed with normal debugging for this task; Borg has no proven cache hit.\n\nSTOP: do not force a weak or unrelated pack onto this task.\n\nVERIFY: collect the exact failing command/output and rerun borg_observe or borg_rescue only if new evidence appears.\n\nCONFIDENCE: BORG [NO CONFIDENT MATCH] -- no relevant traces, synthetic hits, or pack matches.\n\nNO_CONFIDENT_MATCH: No confident Borg match for this task.\nBorg found no relevant real traces, synthetic hits, or exact pack class match.\nProceed with normal reasoning; do not treat Borg as evidence for this task.\nAfter resolving: call borg_rate(helpful=True) only if Borg guidance was actually useful."}], "isError": false}}
{"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "VERIFY: execute the pack's first checkpoint, then rerun the exact failing command\n\nCONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]\n\n------------------------------------------------------------\nPACK GUIDANCE (bash-permission-denied)\n1. Check file permissions: ls -la <file>\n2. Add execute permission: chmod +x <script.sh>\n3. For directories: chmod +x <directory>\n4. Check ownership: ls -ln <file>\n5. Run as appropriate user: sudo <command>\n6. For SSH keys: chmod 600 ~/.ssh/id_rsa\n------------------------------------------------------------"}], "isError": false}}

STDOUT_END
STDERR_HAS_CAUSAL_ERROR= False
STDERR_HAS_MODEL_LOADING= True
STALE_HAS_PACK_GUIDANCE= False
STALE_HAS_NO_CONFIDENT= True
STALE_TEXT_START
ACTION: proceed with normal debugging for this task; Borg has no proven cache hit.

STOP: do not force a weak or unrelated pack onto this task.

VERIFY: collect the exact failing command/output and rerun borg_observe or borg_rescue only if new evidence appears.

CONFIDENCE: BORG [NO CONFIDENT MATCH] -- no relevant traces, synthetic hits, or pack matches.

NO_CONFIDENT_MATCH: No confident Borg match for this task.
Borg found no relevant real traces, synthetic hits, or exact pack class match.
Proceed with normal reasoning; do not treat Borg as evidence for this task.
After resolving: call borg_rate(helpful=True) only if Borg guidance was actually useful.
STALE_TEXT_END
PERM_HAS_GUIDANCE= True
PERM_TEXT_START
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
PERM_TEXT_END

```

### stderr
```

```

