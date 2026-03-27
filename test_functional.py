#!/usr/bin/env python
"""Quick functional test of setup-claude and setup-cursor."""
import json
import tempfile
import os
import sys
from pathlib import Path

# Add guild-v2 to path
sys.path.insert(0, '/root/hermes-workspace/guild-v2')

from borg.cli import main

def test_setup_claude():
    with tempfile.TemporaryDirectory() as tmpdir:
        home = Path(tmpdir) / "home"
        home.mkdir()
        proj = Path(tmpdir) / "project"
        proj.mkdir()
        
        old_home = os.environ.get("HOME")
        old_cwd = os.getcwd()
        os.environ["HOME"] = str(home)
        os.chdir(proj)
        
        try:
            sys.argv = ["guildpacks", "setup-claude"]
            code = main()
            assert code == 0, f"setup-claude returned {code}"
            
            # Check config
            config_file = home / ".config" / "claude" / "claude_desktop_config.json"
            assert config_file.exists(), f"Config not created at {config_file}"
            cfg = json.loads(config_file.read_text())
            assert "mcpServers" in cfg
            assert "guild" in cfg["mcpServers"]
            assert cfg["mcpServers"]["guild"]["command"] == "python"
            
            # Check CLAUDE.md
            claude_md = proj / "CLAUDE.md"
            assert claude_md.exists()
            assert "Guild Workflow Packs" in claude_md.read_text()
            
            print("✓ setup-claude functional test passed")
        finally:
            os.environ["HOME"] = old_home or "/root"
            os.chdir(old_cwd)

def test_setup_cursor():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = Path(tmpdir) / "project"
        proj.mkdir()
        old_cwd = os.getcwd()
        os.chdir(proj)
        
        try:
            sys.argv = ["guildpacks", "setup-cursor"]
            code = main()
            assert code == 0, f"setup-cursor returned {code}"
            
            # Check mcp.json
            mcp_file = proj / ".cursor" / "mcp.json"
            assert mcp_file.exists(), f"mcp.json not created at {mcp_file}"
            cfg = json.loads(mcp_file.read_text())
            assert "mcpServers" in cfg
            assert "guild" in cfg["mcpServers"]
            
            # Check .cursorrules
            cursor_rules = proj / ".cursorrules"
            assert cursor_rules.exists()
            assert "Guild Workflow Packs" in cursor_rules.read_text()
            
            print("✓ setup-cursor functional test passed")
        finally:
            os.chdir(old_cwd)

if __name__ == "__main__":
    test_setup_claude()
    test_setup_cursor()
    print("\nAll functional tests passed!")
