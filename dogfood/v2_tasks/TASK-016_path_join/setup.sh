#!/bin/bash
# TASK-016: Incorrect file path joining (Windows vs Unix separator)

mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-016_path_join

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-016_path_join/path_utils.py << 'EOF'
"""File path utilities with a cross-platform path joining bug."""

import os
from typing import List, Optional


def join_paths(*parts: str) -> str:
    """
    Join multiple path parts into a single path.
    
    This is a simplified version of os.path.join that should work
    cross-platform, but has a subtle bug.
    
    Args:
        *parts: Path components to join
        
    Returns:
        Joined path string
    """
    if not parts:
        return ""
    
    result = parts[0]
    
    for part in parts[1:]:
        # BUG: We use string concatenation with "/" instead of
        # properly handling the separator based on whether parts
        # already have separators or not.
        #
        # The issue: if a part starts with "/" (Unix absolute path),
        # or if a part contains "\" (Windows path), the simple
        # concatenation breaks.
        #
        # We should use os.path.join but we don't!
        if result.endswith("/") or result.endswith("\\"):
            result = result + part
        else:
            result = result + "/" + part
    
    return result


def normalize_path(path: str) -> str:
    """
    Normalize a path by replacing backslashes with forward slashes.
    
    This helps with cross-platform compatibility but doesn't fully
    fix path joining issues.
    """
    return path.replace("\\", "/")


def get_extension(path: str) -> str:
    """Get file extension from path."""
    return os.path.splitext(path)[1]


def split_path(path: str) -> List[str]:
    """Split a path into its components."""
    normalized = normalize_path(path)
    parts = []
    
    while normalized:
        head, tail = os.path.split(normalized)
        if tail:
            parts.insert(0, tail)
        elif head:
            parts.insert(0, head)
            break
        else:
            break
        normalized = head
    
    return parts


def build_config_path(base_dir: str, config_name: str) -> str:
    """
    Build a full config file path from base directory and config name.
    
    Args:
        base_dir: Base directory path
        config_name: Config file name
        
    Returns:
        Full path to config file
    """
    # BUG: Using simple string concatenation instead of proper path joining
    # This works on Unix but breaks on Windows, or when paths have mixed separators
    return join_paths(base_dir, "config", config_name)


def get_data_path(base_dir: str, filename: str) -> str:
    """
    Build a full data file path.
    
    Args:
        base_dir: Base directory path  
        filename: Data file name
        
    Returns:
        Full path to data file
    """
    return join_paths(base_dir, "data", filename)


def main():
    """Demonstrate the path joining bug."""
    
    print("=== Path Join Tests ===\n")
    
    # Test 1: Normal Unix paths
    path1 = join_paths("/home", "user", "config")
    print(f"join_paths('/home', 'user', 'config') = '{path1}'")
    
    # Test 2: Paths with leading separator
    path2 = join_paths("/home", "/user", "config")  # Problematic!
    print(f"join_paths('/home', '/user', 'config') = '{path2}'")
    
    # Test 3: Windows-style paths
    path3 = join_paths("C:\\Users", "AppData", "config")
    print(f"join_paths('C:\\Users', 'AppData', 'config') = '{path3}'")
    
    # Test 4: Mixed separators (common in cross-platform code)
    path4 = join_paths("/home/user", "data\\files", "test.txt")
    print(f"join_paths('/home/user', 'data\\files', 'test.txt') = '{path4}'")
    
    # Test 5: Using build_config_path
    config_path = build_config_path("/etc", "app.conf")
    print(f"\nbuild_config_path('/etc', 'app.conf') = '{config_path}'")
    
    print("\n=== The Bug ===")
    print("Simple string concatenation with '/' doesn't handle:")
    print("- Parts that already start with '/' (double slashes)")
    print("- Parts that have mixed separators (Unix vs Windows)")
    print("- Parts that have trailing separators")


if __name__ == "__main__":
    main()
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-016_path_join/test_path_utils.py << 'EOF'
"""Test cases for path utilities."""
import sys
import os
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-016_path_join')

from path_utils import (
    join_paths, normalize_path, get_extension,
    split_path, build_config_path, get_data_path
)


def test_join_two_paths():
    """Test joining two simple paths."""
    result = join_paths("/home", "user")
    assert "/" in result, f"Result should contain /: {result}"
    print("test_join_two_paths: PASS")


def test_join_three_paths():
    """Test joining three simple paths."""
    result = join_paths("/home", "user", "config")
    assert result == "/home/user/config", f"Expected /home/user/config, got {result}"
    print("test_join_three_paths: PASS")


def test_join_with_leading_slash():
    """
    Test joining paths where a part has leading slash.
    
    BUG: join_paths('/home', '/user', 'config') produces '/home//user/config'
    because we don't strip leading slashes from parts.
    """
    result = join_paths("/home", "/user", "config")
    # The bug causes double slashes or wrong path
    # Should be /home/user/config but might be /home//user/config
    assert result == "/home/user/config", \
        f"Expected /home/user/config, got {result}"
    assert "//" not in result, f"Should not have double slashes: {result}"
    print("test_join_with_leading_slash: PASS")


def test_join_with_trailing_slash():
    """Test joining paths where a part has trailing slash."""
    result = join_paths("/home/", "user", "config")
    assert result == "/home/user/config", f"Expected /home/user/config, got {result}"
    print("test_join_with_trailing_slash: PASS")


def test_build_config_path():
    """Test building config path."""
    result = build_config_path("/etc", "app.conf")
    assert result == "/etc/config/app.conf", f"Expected /etc/config/app.conf, got {result}"
    print("test_build_config_path: PASS")


def test_build_config_path_no_double_slash():
    """
    Test that build_config_path doesn't create double slashes.
    
    BUG: If base_dir ends with /, we get double slash
    """
    result = build_config_path("/etc/", "app.conf")
    assert result == "/etc/config/app.conf", f"Expected /etc/config/app.conf, got {result}"
    assert "//" not in result, f"Should not have double slashes: {result}"
    print("test_build_config_path_no_double_slash: PASS")


def test_get_data_path():
    """Test building data path."""
    result = get_data_path("/var/lib", "data.json")
    assert result == "/var/lib/data/data.json", f"Expected /var/lib/data/data.json, got {result}"
    print("test_get_data_path: PASS")


def test_normalize_path():
    """Test path normalization."""
    result = normalize_path("C:\\Users\\test")
    assert result == "C:/Users/test", f"Expected C:/Users/test, got {result}"
    print("test_normalize_path: PASS")


def test_split_path():
    """Test path splitting."""
    result = split_path("/home/user/config/app.conf")
    assert "home" in result
    assert "user" in result
    assert "config" in result
    assert "app.conf" in result
    print("test_split_path: PASS")


def test_join_preserves_components():
    """Test that join_paths preserves all components in order."""
    result = join_paths("a", "b", "c", "d")
    assert result == "a/b/c/d", f"Expected a/b/c/d, got {result}"
    print("test_join_preserves_components: PASS")


def test_empty_parts():
    """Test handling of empty parts."""
    result = join_paths("/home", "", "user")
    # Empty string should not cause issues
    assert "user" in result
    assert "//" not in result.replace("/ /", "/")  # Handle spaces issue
    print("test_empty_parts: PASS")


if __name__ == "__main__":
    test_join_two_paths()
    test_join_three_paths()
    test_join_with_leading_slash()
    test_join_with_trailing_slash()
    test_build_config_path()
    test_build_config_path_no_double_slash()
    test_get_data_path()
    test_normalize_path()
    test_split_path()
    test_join_preserves_components()
    test_empty_parts()
    print("\nAll tests passed!")
EOF
