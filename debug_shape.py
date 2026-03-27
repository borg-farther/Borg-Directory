#!/usr/bin/env python
"""Debug script for MagicMock shape check."""
from unittest.mock import MagicMock
import numpy as np

m = MagicMock()
print('MagicMock hasattr shape:', hasattr(m, 'shape'))
print('MagicMock shape attr:', m.shape)
print('MagicMock type of shape:', type(m.shape))

# Test with real numpy array
arr = np.array([1,2,3])
print('\nreal array hasattr shape:', hasattr(arr, 'shape'))
print('real array shape:', arr.shape)
print('real array type of shape:', type(arr.shape))

# Now test the actual encode function
def mock_encode(text):
    hash_val = hash(text) % (2**32)
    np.random.seed(hash_val)
    embedding = np.random.randn(128)
    embedding = embedding / np.linalg.norm(embedding)
    return embedding

result = mock_encode("test")
print('\nencode result type:', type(result))
print('encode result hasattr shape:', hasattr(result, 'shape'))
print('encode result hasattr len:', hasattr(result, '__len__'))
print('encode result shape:', result.shape)
