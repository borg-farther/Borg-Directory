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
