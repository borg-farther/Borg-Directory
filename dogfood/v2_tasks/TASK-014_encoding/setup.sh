#!/bin/bash
# TASK-014: UTF-8 BOM causes string comparison failure

mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-014_encoding

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-014_encoding/text_processor.py << 'EOF'
"""Text processor that has issues with UTF-8 BOM."""

import json
from typing import Optional


class TextProcessor:
    """
    A text processor that reads configuration and compares strings.
    
    The config file is written with UTF-8 encoding and should be
    read back with the same encoding, but there's a subtle bug.
    """
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file."""
        # BUG: When opening the file, we don't specify encoding.
        # This causes issues on some systems where the BOM (Byte Order Mark)
        # is not properly handled. When reading a file with a UTF-8 BOM,
        # the BOM bytes stay at the start of the content, causing comparison
        # failures when comparing with strings that don't have the BOM.
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
    
    def save_config(self):
        """Save configuration to JSON file."""
        # When writing, we specify utf-8 encoding
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
    
    def set_value(self, key: str, value: str):
        """Set a configuration value."""
        self.config[key] = value
    
    def get_value(self, key: str) -> Optional[str]:
        """Get a configuration value."""
        return self.config.get(key)
    
    def compare_strings(self, s1: str, s2: str) -> bool:
        """
        Compare two strings for equality.
        Returns True if they match.
        """
        # Simple string comparison
        return s1 == s2
    
    def find_in_list(self, needle: str, haystack: list) -> int:
        """
        Find a string in a list.
        Returns index if found, -1 if not found.
        """
        for i, item in enumerate(haystack):
            if self.compare_strings(needle, item):
                return i
        return -1
    
    def validate_key(self, key: str) -> bool:
        """
        Validate that a key exists in config and matches expected value.
        """
        stored = self.get_value(key)
        if stored is None:
            return False
        return self.compare_strings(key, stored)


def main():
    """Demonstrate the BOM comparison issue."""
    
    config_path = "/tmp/test_config.json"
    
    # Create processor and set up config
    processor = TextProcessor(config_path)
    processor.set_value("username", "admin")
    processor.set_value("password", "secret123")
    processor.save_config()
    
    print("=== Config saved ===")
    print(f"Config: {processor.config}")
    
    # Create a new processor to read the config back
    processor2 = TextProcessor(config_path)
    
    print("\n=== Config reloaded ===")
    print(f"Config: {processor2.config}")
    
    # Try to compare strings
    original = "admin"
    from_file = processor2.get_value("username")
    
    print(f"\n=== String Comparison ===")
    print(f"Original string: '{original}' (len={len(original)})")
    print(f"From file string: '{from_file}' (len={len(from_file)})")
    
    # Check byte-by-byte
    print(f"\nOriginal bytes: {original.encode('utf-8')}")
    print(f"From file bytes: {from_file.encode('utf-8') if from_file else None}")
    
    # Direct comparison
    result = processor2.compare_strings(original, from_file)
    print(f"\nDirect comparison: {result}")
    
    # Try list lookup
    test_list = ["admin", "user", "guest"]
    idx = processor2.find_in_list(from_file, test_list)
    print(f"Looking for '{from_file}' in {test_list}: index={idx}")
    
    # Validate key
    valid = processor2.validate_key("username")
    print(f"\nValidating 'username' key: {valid}")
    
    if not result or idx == -1:
        print("\nBUG: String comparison failed due to BOM issue!")
        print("The JSON file reader didn't handle UTF-8 BOM correctly.")


if __name__ == "__main__":
    main()
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-014_encoding/test_processor.py << 'EOF'
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
EOF
