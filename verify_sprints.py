import json, sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.embeddings import embed_text, build_index_from_db, semantic_search, get_embedding_stats
from borg.core.traces import TRACE_DB_PATH

print('=== SPRINT 1 VERIFICATION ===')
vec = embed_text('test')
print('model:', 'OK dim='+str(len(vec)) if vec is not None else 'UNAVAILABLE')
if vec is None:
    print('FAIL: model unavailable')
    sys.exit(1)

cache, count = build_index_from_db(TRACE_DB_PATH)
print('indexed:', count)

results = semantic_search('database schema field type mismatch', TRACE_DB_PATH, top_k=3)
print('semantic results:', len(results))
for r in results[:3]:
    print(' -', round(r.get('similarity',0),3), r.get('technology',''), str(r.get('task_description',''))[:50])

from borg.core.search import borg_search
r = json.loads(borg_search('django migration error'))
print('borg_search mode:', r.get('mode'))
print('borg_search total:', r['total'])

stats = get_embedding_stats(TRACE_DB_PATH)
print('coverage:', stats.get('coverage_pct', 0), '%')
print('total traces:', stats.get('total_traces', 0))
print('indexed traces:', stats.get('indexed_traces', 0))

model_pass = vec is not None and len(vec) == 384
indexed_pass = count > 0
mode_pass = r.get('mode') == 'semantic'
cov_pass = stats.get('coverage_pct', 0) > 80
print()
print('SPRINT1 PASS: model=%s indexed=%s mode=%s coverage=%s' % (model_pass, indexed_pass, mode_pass, cov_pass))

print()
print('=== SPRINT 2 SEEDING ===')
from borg.core.traces import TraceCapture, save_trace
cap = TraceCapture(task='Fix Django CharField max_length migration error', agent_id='test-neg')
cap.on_tool_call('terminal', {}, 'ERROR: migration failed')
t = cap.extract_trace(outcome='failure', root_cause='Direct ALTER TABLE bypasses Django', approach_summary='Tried ALTER TABLE')
saved = save_trace(t)
print('seeded:', saved[:30])

from borg.integrations.mcp_server import borg_observe
obs = borg_observe(task='Django migration CharField max_length error', context='DatabaseError')
print('length:', len(obs))
print('has WHAT WORKED:', 'WHAT WORKED' in obs)
print('has WHAT FAILED:', 'WHAT FAILED' in obs)
s2_pass = len(obs) > 300 and 'WHAT WORKED' in obs and 'WHAT FAILED' in obs
print('SPRINT2 PASS:', s2_pass)

print()
print('=== SPRINT 3 VERIFICATION ===')
try:
    from sklearn.cluster import DBSCAN
    import yaml
    print('deps: OK')
except ImportError as e:
    print('FAIL deps:', e)
    sys.exit(1)

import inspect
from borg.core import clustering as cl
has_rdp = hasattr(cl, 'run_clustering_pipeline')
has_gcs = hasattr(cl, 'get_cluster_summary')
has_rdb = hasattr(cl, 'run_dbscan')
print('has run_clustering_pipeline:', has_rdp)
print('has get_cluster_summary:', has_gcs)
print('has run_dbscan:', has_rdb)

if has_rdb:
    sig = inspect.signature(cl.run_dbscan)
    print('run_dbscan eps default:', sig.parameters.get('eps'))
if has_rdp:
    sig = inspect.signature(cl.run_clustering_pipeline)
    print('run_clustering_pipeline eps default:', sig.parameters.get('eps'))

s3_pass = has_rdp and has_gcs and has_rdb
print('SPRINT3 PASS:', s3_pass)
print()
print('=== ALL DONE ===')