#!/usr/bin/env python3
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
from datasets import load_dataset
ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
for t in ds:
    if t['instance_id'] == 'django__django-16631':
        with open('/tmp/test_patch_16631.diff', 'w') as f:
            f.write(t['test_patch'])
        print(f"Written {len(t['test_patch'])} chars")
        print(f"FAIL_TO_PASS: {t['FAIL_TO_PASS']}")
        break
