#!/usr/bin/env python
"""Debug script to understand why tests fail."""

from unittest.mock import MagicMock
import numpy as np

engine = MagicMock()

def mock_encode(text):
    hash_val = hash(text) % (2**32)
    np.random.seed(hash_val)
    embedding = np.random.randn(128)
    embedding = embedding / np.linalg.norm(embedding)
    return embedding

def mock_search_similar(query_embedding, top_k):
    query_hash = hash(str(query_embedding[:5])) % 100
    if query_hash % 3 == 0:
        return [('pack-debug-001', 0.95), ('pack-code-002', 0.85)]
    elif query_hash % 3 == 1:
        return [('pack-code-002', 0.92), ('pack-data-003', 0.78)]
    else:
        return [('pack-data-003', 0.88), ('pack-debug-001', 0.72)]

engine.encode = mock_encode
engine.search_similar = mock_search_similar

print('hasattr encode:', hasattr(engine, 'encode'))
print('hasattr search_similar:', hasattr(engine, 'search_similar'))
print('hasattr semantic_search:', hasattr(engine, 'semantic_search'))

test_emb = engine.encode('test')
print('encode result type:', type(test_emb))
print('encode result shape:', test_emb.shape if hasattr(test_emb, 'shape') else 'no shape')

result = engine.search_similar(test_emb, 5)
print('search_similar result type:', type(result))
print('search_similar result:', result)

# Now test with actual SemanticSearchEngine
from guild.db.store import GuildStore
from guild.core.semantic_search import SemanticSearchEngine
import tempfile
import os

temp_dir = tempfile.mkdtemp()
db_path = os.path.join(temp_dir, 'test.db')
store = GuildStore(db_path)

# Add a pack
store.add_pack(
    pack_id="pack-debug-001",
    version="1.0.0",
    yaml_content="""name: Systematic Debugging
problem_class: debugging
domain: software
""",
    author_agent="test-agent",
    confidence="tested",
    tier="validated",
    problem_class="debugging",
    domain="software",
    phase_count=3,
)

# Check the engine
sse = SemanticSearchEngine(store, embedding_engine=engine)
print('\nSemanticSearchEngine._embedding_available:', sse._embedding_available)
print('SemanticSearchEngine.embedding_engine:', sse.embedding_engine)

# Try semantic search
sem_results = sse._semantic_search("debugging", 5)
print('\n_semantic_search result:', sem_results)

# Check _check_embedding_available directly
print('\nDirect encode call:')
try:
    enc = engine.encode("test")
    print('encode result:', enc)
    print('has shape:', hasattr(enc, 'shape'))
except Exception as e:
    print('Error:', e)
