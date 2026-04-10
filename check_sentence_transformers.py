#!/usr/bin/env python3
"""Check if sentence_transformers is actually loading heavy deps."""
import time
import sys

# Time just importing sentence_transformers
t0 = time.time()
from sentence_transformers import SentenceTransformer
t1 = time.time()
print(f'sentence_transformers import: {t1-t0:.3f}s', file=sys.stderr)
print(f'SentenceTransformer class loaded OK', file=sys.stderr)
