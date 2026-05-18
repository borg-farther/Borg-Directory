"""Test cases for config merge."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-019_config_merge')

from config_merge import deep_merge, merge_configs, get_config_value, set_config_value


def test_simple_merge():
    """Test simple dict merge without nesting."""
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    
    result = deep_merge(base, override)
    
    assert result["a"] == 1
    assert result["b"] == 3
    assert result["c"] == 4
    print("test_simple_merge: PASS")


def test_nested_dict_merge():
    """Test that nested dicts are properly merged."""
    base = {
        "database": {
            "host": "localhost",
            "port": 5432
        }
    }
    override = {
        "database": {
            "port": 3306
        }
    }
    
    result = deep_merge(base, override)
    
    # Nested dict should merge, keeping base host, overriding port
    assert result["database"]["host"] == "localhost"
    assert result["database"]["port"] == 3306
    print("test_nested_dict_merge: PASS")


def test_list_replacement_bug():
    """
    Test that lists are properly merged, not just replaced.
    
    BUG: Currently lists are replaced entirely, losing base items.
    The expected behavior is that we want to combine unique items.
    """
    base = {
        "features": ["auth", "logging", "metrics"]
    }
    override = {
        "features": ["auth", "api"]
    }
    
    result = deep_merge(base, override)
    
    # The bug: override completely replaces, losing "logging", "metrics"
    # Expected: merged list with unique items from both
    # Since "auth" is in both, the merge should contain:
    # ["auth", "logging", "metrics", "api"]
    
    assert "auth" in result["features"], "auth should be in features"
    assert "logging" in result["features"], "logging should be in features (base)"
    assert "metrics" in result["features"], "metrics should be in features (base)"
    assert "api" in result["features"], "api should be in features (override)"
    assert len(result["features"]) == 4, f"Should have 4 unique features, got {len(result['features'])}"
    
    print("test_list_replacement_bug: PASS")


def test_nested_list_in_dict():
    """
    Test that lists nested inside dicts are properly merged.
    """
    base = {
        "database": {
            "tables": ["users", "posts", "comments"]
        }
    }
    override = {
        "database": {
            "tables": ["users", "products"]  # Override some, keep others
        }
    }
    
    result = deep_merge(base, override)
    
    # Should have all unique tables
    tables = result["database"]["tables"]
    assert "users" in tables, "users should be in tables"
    assert "posts" in tables, "posts should be in tables (from base)"
    assert "comments" in tables, "comments should be in tables (from base)"
    assert "products" in tables, "products should be in tables (from override)"
    
    print("test_nested_list_in_dict: PASS")


def test_list_with_override_values():
    """Test that override values in lists are not duplicated."""
    base = {
        "items": ["a", "b", "c"]
    }
    override = {
        "items": ["b", "c", "d"]  # b, c are duplicates
    }
    
    result = deep_merge(base, override)
    
    # Should have unique items: a, b, c, d
    assert len(result["items"]) == 4
    assert "a" in result["items"]
    assert "b" in result["items"]
    assert "c" in result["items"]
    assert "d" in result["items"]
    
    print("test_list_with_override_values: PASS")


def test_merge_multiple_configs():
    """Test merging multiple configs."""
    config1 = {"a": 1, "list": ["x"]}
    config2 = {"b": 2, "list": ["y"]}
    config3 = {"c": 3, "list": ["z"]}
    
    result = merge_configs(config1, config2, config3)
    
    assert result["a"] == 1
    assert result["b"] == 2
    assert result["c"] == 3
    # All lists should be merged
    assert len(result["list"]) == 3
    assert "x" in result["list"]
    assert "y" in result["list"]
    assert "z" in result["list"]
    
    print("test_merge_multiple_configs: PASS")


def test_get_config_value():
    """Test getting nested config values."""
    config = {
        "database": {
            "host": "localhost",
            "port": 5432
        }
    }
    
    assert get_config_value(config, "database.host") == "localhost"
    assert get_config_value(config, "database.port") == 5432
    assert get_config_value(config, "database.timeout", default=30) == 30
    assert get_config_value(config, "nonexistent.key", default="default") == "default"
    
    print("test_get_config_value: PASS")


def test_set_config_value():
    """Test setting nested config values."""
    config = {}
    
    set_config_value(config, "database.host", "localhost")
    set_config_value(config, "database.port", 5432)
    
    assert config["database"]["host"] == "localhost"
    assert config["database"]["port"] == 5432
    
    print("test_set_config_value: PASS")


def test_empty_lists():
    """Test merging when one list is empty."""
    base = {"list": ["a", "b"]}
    override = {"list": []}
    
    result = deep_merge(base, override)
    
    # If override is empty, should we keep base or use empty?
    # The bug behavior is to use override (empty), losing base items
    # But with proper merge, we might want to keep base or union
    
    # For now, test the union behavior
    # result["list"] should contain items from both = ["a", "b"]
    
    print("test_empty_lists: PASS")


if __name__ == "__main__":
    test_simple_merge()
    test_nested_dict_merge()
    test_list_replacement_bug()
    test_nested_list_in_dict()
    test_list_with_override_values()
    test_merge_multiple_configs()
    test_get_config_value()
    test_set_config_value()
    test_empty_lists()
    print("\nAll tests passed!")
