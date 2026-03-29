#!/usr/bin/env python3
"""Comprehensive guild -> borg rename for all borg/ Python files."""

import os
import re
from pathlib import Path

BASE = Path("/root/hermes-workspace/borg")
BORG_DIR = BASE / "borg"

# Function renames
SEARCH_FUNCS = {
    'guild_search': 'borg_search',
    'guild_pull': 'borg_pull',
    'guild_try': 'borg_try',
    'guild_init': 'borg_init',
}

# Agent hook renames
HOOK_FUNCS = {
    'guild_on_failure': 'borg_on_failure',
    'guild_on_task_start': 'borg_on_task_start',
}

# Tool renames in mcp_server.py
TOOL_FUNCS = {
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

def process_search_file(filepath: Path) -> bool:
    """Process search.py - rename function names."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return False
    
    original = content
    
    # Rename function definitions and calls
    for old, new in SEARCH_FUNCS.items():
        # Match function calls and definitions
        content = re.sub(rf'\b{old}\b', new, content)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False

def process_mcp_server(filepath: Path) -> bool:
    """Process mcp_server.py - rename tool names and function calls."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return False
    
    original = content
    
    # Rename tool definitions (in TOOLS list)
    for old, new in TOOL_FUNCS.items():
        content = re.sub(rf'"{old}"', f'"{new}"', content)
        content = re.sub(rf'\b{old}\b', new, content)
    
    # Also rename the function definitions at the bottom
    for old, new in TOOL_FUNCS.items():
        content = re.sub(rf'\bdef {old}\b', f'def {new}', content)
        content = re.sub(rf'\b{old}\b', new, content)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False

def process_agent_hook(filepath: Path) -> bool:
    """Process agent_hook.py - rename hook function names."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return False
    
    original = content
    
    for old, new in HOOK_FUNCS.items():
        content = re.sub(rf'\b{old}\b', new, content)
    
    # Also rename guild_search to borg_search inside agent_hook
    content = re.sub(r'\bguild_search\b', 'borg_search', content)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False

def process_apply_file(filepath: Path) -> bool:
    """Process apply.py - update error messages."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return False
    
    original = content
    
    # Update error messages that reference old function names
    content = content.replace("guild_pull", "borg_pull")
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False

def process_generic_file(filepath: Path) -> bool:
    """Generic processing for other files."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return False
    
    original = content
    
    # Rename function imports and calls
    for old, new in {**SEARCH_FUNCS, **HOOK_FUNCS}.items():
        content = re.sub(rf'\b{old}\b', new, content)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False

def main():
    modified_count = 0
    
    for py_file in BORG_DIR.rglob("*.py"):
        rel_path = py_file.relative_to(BASE)
        modified = False
        
        if py_file.name == 'search.py':
            modified = process_search_file(py_file)
        elif py_file.name == 'mcp_server.py':
            modified = process_mcp_server(py_file)
        elif py_file.name == 'agent_hook.py':
            modified = process_agent_hook(py_file)
        elif py_file.name == 'apply.py':
            modified = process_apply_file(py_file)
        else:
            modified = process_generic_file(py_file)
        
        if modified:
            print(f"  Modified: {rel_path}")
            modified_count += 1
    
    print(f"\nTotal files modified: {modified_count}")

if __name__ == "__main__":
    main()
