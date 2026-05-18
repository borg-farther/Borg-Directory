#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/config.py << 'PYEOF'
class Config:
    """Configuration manager with layered defaults."""
    
    def __init__(self, defaults=None):
        self._data = defaults if defaults is not None else {}
    
    def merge(self, overrides):
        """Merge overrides into config. Should not mutate the overrides dict."""
        for key, value in overrides.items():
            if key in self._data and isinstance(self._data[key], dict) and isinstance(value, dict):
                # BUG: shallow reference — mutates the original overrides dict
                self._data[key] = value
                self._data[key].update(self._data.get(key, {}))
            else:
                self._data[key] = value
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def to_dict(self):
        return dict(self._data)
PYEOF

cat > repo/test_config.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from config import Config

def test_merge_no_mutation():
    """Overrides dict should not be mutated by merge."""
    defaults = {"db": {"host": "localhost", "port": 5432}}
    overrides = {"db": {"host": "prod-server"}}
    original_overrides = {"db": {"host": "prod-server"}}
    
    c = Config(defaults)
    c.merge(overrides)
    
    # The overrides dict should be unchanged
    assert overrides == original_overrides, f"Overrides mutated: {overrides} != {original_overrides}"
    
    # The merged config should have both values
    db = c.get("db")
    assert db["host"] == "prod-server", f"Host wrong: {db['host']}"
    assert db["port"] == 5432, f"Port missing: {db.get('port')}"

def test_merge_independent():
    """Two configs merged from same overrides should be independent."""
    overrides = {"cache": {"ttl": 300}}
    
    c1 = Config({"cache": {"ttl": 60, "max_size": 100}})
    c1.merge(overrides)
    
    c2 = Config({"cache": {"ttl": 120, "backend": "redis"}})
    c2.merge(overrides)
    
    # They should be independent
    cache1 = c1.get("cache")
    cache2 = c2.get("cache")
    assert cache1.get("max_size") == 100, f"c1 lost max_size"
    assert cache2.get("backend") == "redis", f"c2 lost backend"

if __name__ == "__main__":
    try:
        test_merge_no_mutation()
        print("PASS: test_merge_no_mutation")
    except AssertionError as e:
        print(f"FAIL: test_merge_no_mutation: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: test_merge_no_mutation: {e}")
        sys.exit(1)
    
    try:
        test_merge_independent()
        print("PASS: test_merge_independent")
    except AssertionError as e:
        print(f"FAIL: test_merge_independent: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: test_merge_independent: {e}")
        sys.exit(1)
    
    print("ALL TESTS PASSED")
PYEOF
