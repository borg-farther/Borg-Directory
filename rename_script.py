#!/usr/bin/env python3
"""Bulk rename guild -> borg in all borg/ Python files."""

import os
import re
from pathlib import Path

BASE = Path("/root/hermes-workspace/borg")
BORG_DIR = BASE / "borg"

# Patterns to replace (old -> new)
REPLACEMENTS = [
    # Module-level imports: from guild. -> from borg.
    (r'\bfrom guild\.', 'from borg.'),
    (r'\bimport guild\b', 'import borg'),
    # Submodule references
    (r'\bguild\.core\.', 'borg.core.'),
    (r'\bguild\.db\.', 'borg.db.'),
    (r'\bguild\.integrations\.', 'borg.integrations.'),
]

# Function renames in borg/core/search.py
SEARCH_RENAMES = {
    'guild_search': 'borg_search',
    'guild_pull': 'borg_pull',
    'guild_try': 'borg_try',
    'guild_init': 'borg_init',
}

# Tool renames in borg/integrations/mcp_server.py
TOOL_RENAMES = {
    'guild_search': 'borg_search',
    'guild_pull': 'borg_pull',
    'guild_try': 'borg_try',
    'guild_init': 'borg_init',
    'guild_apply': 'borg_apply',
    'guild_publish': 'borg_publish',
    'guild_feedback': 'borg_feedback',
    'guild_suggest': 'borg_suggest',
    'guild_convert': 'borg_convert',
    'guild_observe': 'borg_observe',
}

def process_file(filepath: Path) -> bool:
    """Process a single file, returning True if modified."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return False
    
    original = content
    
    # Apply module replacements
    for old, new in REPLACEMENTS:
        content = re.sub(old, new, content)
    
    # Apply function renames if in search.py
    if filepath.name == 'search.py' and 'core' in str(filepath):
        for old, new in SEARCH_RENAMES.items():
            # Only rename function definitions and calls, not strings/comments
            # Use word boundary and account for different contexts
            content = re.sub(rf'\b{old}\b', new, content)
    
    # Apply tool renames if in mcp_server.py
    if filepath.name == 'mcp_server.py' and 'integrations' in str(filepath):
        for old, new in TOOL_RENAMES.items():
            content = re.sub(rf'\b{old}\b', new, content)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False

def main():
    modified_count = 0
    
    # Process all .py files under borg/
    for py_file in BORG_DIR.rglob("*.py"):
        if process_file(py_file):
            print(f"  Modified: {py_file.relative_to(BASE)}")
            modified_count += 1
    
    print(f"\nTotal files modified: {modified_count}")

if __name__ == "__main__":
    main()
