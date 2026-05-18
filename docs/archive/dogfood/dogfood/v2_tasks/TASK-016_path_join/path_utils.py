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
        # Strip leading slashes from part to avoid double slashes
        part = part.lstrip("/")
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
