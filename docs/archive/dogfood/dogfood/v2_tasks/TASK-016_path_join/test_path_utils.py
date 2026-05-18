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
