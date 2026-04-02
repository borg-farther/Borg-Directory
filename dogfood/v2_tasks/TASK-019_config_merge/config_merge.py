"""Configuration merging with a subtle bug in deep merge handling of lists."""

from typing import Any, Dict, List, Union
import copy


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    For nested dicts, values from 'override' take precedence.
    For lists, the bug is that we might be replacing instead of merging,
    or merging in the wrong way.
    
    Args:
        base: Base configuration
        override: Override configuration (takes precedence)
        
    Returns:
        Merged configuration
    """
    result = copy.deepcopy(base)
    
    for key, value in override.items():
        if key in result:
            # Key exists in both - need to merge
            base_value = result[key]
            
            if isinstance(base_value, dict) and isinstance(value, dict):
                # Both are dicts - recursively merge
                result[key] = deep_merge(base_value, value)
            elif isinstance(base_value, list) and isinstance(value, list):
                # Both are lists - merge by combining unique items
                combined = list(base_value)
                for item in value:
                    if item not in combined:
                        combined.append(item)
                result[key] = combined
            else:
                # Different types or one is not a dict - override wins
                result[key] = value
        else:
            # Key only in override - add it
            result[key] = value
    
    return result


def merge_configs(*configs: Dict) -> Dict:
    """
    Merge multiple configurations.
    
    Later configs take precedence over earlier ones.
    """
    if not configs:
        return {}
    
    result = configs[0]
    for config in configs[1:]:
        result = deep_merge(result, config)
    
    return result


def get_config_value(config: Dict, key_path: str, default: Any = None) -> Any:
    """
    Get a nested config value using dot notation.
    
    Example: get_config_value(config, "database.host", default="localhost")
    """
    keys = key_path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def set_config_value(config: Dict, key_path: str, value: Any):
    """
    Set a nested config value using dot notation.
    
    Creates intermediate dicts if needed.
    """
    keys = key_path.split('.')
    current = config
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def main():
    """Demonstrate the deep merge bug with lists."""
    
    # Base configuration
    base = {
        "app_name": "MyApp",
        "features": ["auth", "logging", "metrics"],
        "database": {
            "host": "localhost",
            "port": 5432,
            "tables": ["users", "posts", "comments"]
        }
    }
    
    # Override configuration
    override = {
        "features": ["auth", "api"],  # Overwrites entirely - loses "logging", "metrics"!
        "database": {
            "port": 3306  # Only override port, keep host
        }
    }
    
    print("=== Base Config ===")
    print(base)
    
    print("\n=== Override Config ===")
    print(override)
    
    merged = deep_merge(base, override)
    
    print("\n=== Merged Config ===")
    print(merged)
    
    print("\n=== The Bug ===")
    print("When merging lists, the override list REPLACES the base list")
    print("instead of merging them.")
    print()
    print("Expected features:", ['auth', 'logging', 'metrics', 'api'])
    print("Actual features:", merged['features'])
    print()
    print("Expected database.tables:", ['users', 'posts', 'comments'])
    print("Actual database.tables:", merged.get('database', {}).get('tables', 'NOT FOUND'))


if __name__ == "__main__":
    main()
