#!/usr/bin/env python3
"""Fix remaining guild references in borg/ Python files."""

import re
from pathlib import Path

BASE = Path("/root/hermes-workspace/borg")
BORG_DIR = BASE / "borg"

def main():
    for py_file in BORG_DIR.rglob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"ERROR reading {py_file}: {e}")
            continue
        
        original = content
        
        # Fix patch decorators: @patch("guild.cli.borg_search") -> @patch("borg.cli.borg_search")
        content = re.sub(r'@patch\(["\']guild\.cli\.', '@patch("borg.cli.', content)
        
        # Fix imports in tests that still use guild_search/guild_pull etc.
        content = re.sub(r'from borg\.core\.search import ([\w, ]+)\b', 
                        lambda m: 'from borg.core.search import ' + 
                                  m.group(1).replace('guild_search', 'borg_search')
                                           .replace('guild_pull', 'borg_pull')
                                           .replace('guild_try', 'borg_try')
                                           .replace('guild_init', 'borg_init'),
                        content)
        
        # Fix test function names that reference guild_*
        content = re.sub(r'def (test_\w*guild_search\w*)', 
                        lambda m: 'def ' + m.group(1).replace('guild_search', 'borg_search'),
                        content)
        content = re.sub(r'def (test_\w*guild_pull\w*)', 
                        lambda m: 'def ' + m.group(1).replace('guild_pull', 'borg_pull'),
                        content)
        content = re.sub(r'def (test_\w*guild_try\w*)', 
                        lambda m: 'def ' + m.group(1).replace('guild_try', 'borg_try'),
                        content)
        content = re.sub(r'def (test_\w*guild_init\w*)', 
                        lambda m: 'def ' + m.group(1).replace('guild_init', 'borg_init'),
                        content)
        
        # Fix error message strings mentioning guild_try
        content = content.replace(
            '"Try: guild_try guild://hermes/systematic-debugging"',
            '"Try: borg_try guild://hermes/systematic-debugging"'
        )
        
        # Fix test function names with borg_search in them
        content = re.sub(r'test_(guild_search)', r'test_borg_search', content)
        
        # Fix mcp_server tests that reference guild_search tool names
        content = re.sub(r'test_tools_call_guild_search', 'test_tools_call_borg_search', content)
        content = re.sub(r'test_tools_call_guild_init', 'test_tools_call_borg_init', content)
        content = re.sub(r'test_call_tool_guild_search', 'test_call_tool_borg_search', content)
        content = re.sub(r'test_call_tool_guild_init', 'test_call_tool_borg_init', content)
        
        # Fix wiring tests
        content = re.sub(r'test_guild_search_', 'test_borg_search_', content)
        
        # Fix agent_hook tests
        content = re.sub(r'guild_search', 'borg_search', content)
        
        if content != original:
            py_file.write_text(content, encoding='utf-8')
            print(f"Fixed: {py_file.relative_to(BASE)}")

if __name__ == "__main__":
    main()
