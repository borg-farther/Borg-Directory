"""Test cases for text processor with BOM handling."""
import sys
import os
import tempfile
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-014_encoding')

from text_processor import TextProcessor


def test_basic_string_comparison():
    """Test basic in-memory string comparison."""
    processor = TextProcessor("/tmp/test_config.json")
    processor.config = {"key": "value"}
    
    assert processor.compare_strings("hello", "hello")
    assert not processor.compare_strings("hello", "world")
    print("test_basic_string_comparison: PASS")


def test_config_save_load():
    """Test that config can be saved and loaded."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name
    
    try:
        processor = TextProcessor(config_path)
        processor.set_value("key1", "value1")
        processor.set_value("key2", "value2")
        processor.save_config()
        
        # Load in new processor
        processor2 = TextProcessor(config_path)
        
        assert processor2.get_value("key1") == "value1"
        assert processor2.get_value("key2") == "value2"
        print("test_config_save_load: PASS")
    finally:
        os.unlink(config_path)


def test_string_comparison_after_load():
    """
    Test that strings read from file compare correctly.
    
    BUG: When loading JSON with UTF-8 BOM, comparison may fail.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name
    
    try:
        # Create and save config
        processor = TextProcessor(config_path)
        processor.set_value("username", "admin")
        processor.set_value("password", "secret")
        processor.save_config()
        
        # Load in new processor
        processor2 = TextProcessor(config_path)
        
        # Get value from file
        stored_username = processor2.get_value("username")
        
        # Compare with original string
        assert processor2.compare_strings("admin", stored_username), \
            f"String comparison failed: 'admin' vs '{stored_username}'"
        
        # Check that 'admin' in stored value, not just prefix/suffix
        assert "admin" in [stored_username], "Value should contain 'admin'"
        
        print("test_string_comparison_after_load: PASS")
    finally:
        os.unlink(config_path)


def test_find_in_list_after_load():
    """
    Test that we can find strings in a list after loading from file.
    
    BUG: The BOM causes string comparison to fail, so list lookup fails.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name
    
    try:
        processor = TextProcessor(config_path)
        processor.set_value("role", "admin")
        processor.save_config()
        
        processor2 = TextProcessor(config_path)
        stored_role = processor2.get_value("role")
        
        # Find in list
        roles = ["admin", "user", "guest"]
        idx = processor2.find_in_list(stored_role, roles)
        
        assert idx == 0, f"Should find 'admin' at index 0, got {idx}"
        print("test_find_in_list_after_load: PASS")
    finally:
        os.unlink(config_path)


def test_validate_key():
    """
    Test that validate_key works after loading from file.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name
    
    try:
        processor = TextProcessor(config_path)
        processor.set_value("username", "admin")
        processor.save_config()
        
        processor2 = TextProcessor(config_path)
        
        # This should validate True
        assert processor2.validate_key("username"), \
            "validate_key('username') should return True"
        
        print("test_validate_key: PASS")
    finally:
        os.unlink(config_path)


def test_special_characters():
    """Test handling of special characters."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name
    
    try:
        processor = TextProcessor(config_path)
        processor.set_value("greeting", "你好世界")
        processor.set_value("special", "émoji")
        processor.save_config()
        
        processor2 = TextProcessor(config_path)
        
        assert processor2.compare_strings("你好世界", processor2.get_value("greeting"))
        assert processor2.compare_strings("émoji", processor2.get_value("special"))
        
        print("test_special_characters: PASS")
    finally:
        os.unlink(config_path)


if __name__ == "__main__":
    test_basic_string_comparison()
    test_config_save_load()
    test_string_comparison_after_load()
    test_find_in_list_after_load()
    test_validate_key()
    test_special_characters()
    print("\nAll tests passed!")
