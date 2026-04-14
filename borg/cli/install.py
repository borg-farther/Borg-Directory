"""borg install — install borg MCP server into Claude Desktop config."""

import json
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Platform-specific Claude Desktop config paths
PLATFORM_PATHS = {
    "darwin": Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    "linux": Path.home() / ".config" / "claude" / "claude_desktop_config.json",
    "windows": Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
}


def _get_config_path() -> Path:
    """Detect Claude Desktop config path for current platform."""
    system = platform.system().lower()
    if system == "darwin":
        return PLATFORM_PATHS["darwin"]
    elif system == "linux":
        return PLATFORM_PATHS["linux"]
    elif system == "windows":
        return PLATFORM_PATHS["windows"]
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def _find_borg_executable() -> str:
    """Find the borg executable path."""
    # Try to find it via the installed package
    try:
        import borg
        # borg is installed as a package — find the executable
        import borg.cli
        cli_path = Path(borg.cli.__file__).parent
        # The entry point 'borg' resolves to the module — use python -m borg
        return "python -m borg"
    except Exception:
        pass

    # Fall back to bare 'borg' command
    return "borg"


def _load_config(path: Path) -> dict:
    """Load Claude Desktop config, or return empty structure."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"mcpServers": {}}


def _save_config(path: Path, config: dict, backup: bool = True) -> None:
    """Save config with optional timestamped backup."""
    if backup and path.exists():
        backup_path = path.with_name(f"{path.name}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}")
        shutil.copy2(path, backup_path)
        print(f"  Backup: {backup_path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Written: {path}")


def _build_borg_mcp_entry() -> dict:
    """Build the borg MCP server entry for claude_desktop_config.json."""
    borg_cmd = _find_borg_executable()
    return {
        "command": borg_cmd,
        "args": ["serve"],
        "env": {
            "BORG_HOME": os.getenv("BORG_HOME", str(Path.home() / ".borg")),
        }
    }


def main() -> int:
    print("\n=== BORG INSTALL ===\n")

    try:
        config_path = _get_config_path()
    except RuntimeError as e:
        print(f"❌ {e}")
        return 1

    print(f"Platform: {platform.system()}")
    print(f"Config: {config_path}")

    if not config_path.exists():
        print(f"\n⚠️  Config not found at {config_path}")
        print("   Has Claude Desktop been run at least once?")
        print("   Creating new config...\n")
        config = {"mcpServers": {}}
    else:
        config = _load_config(config_path)

    mcp_servers = config.get("mcpServers", {})
    borg_key = "borg"

    if borg_key in mcp_servers:
        print(f"\n⚠️  'borg' MCP server already registered.")
        print(f"   Existing entry: {mcp_servers[borg_key]}")
        response = input("   Replace? [y/N]: ").strip().lower()
        if response != "y":
            print("   Aborted.")
            return 0

    mcp_servers[borg_key] = _build_borg_mcp_entry()
    config["mcpServers"] = mcp_servers

    _save_config(config_path, config)
    print(f"\n✅ 'borg' MCP server registered.")
    print(f"   Restart Claude Desktop to activate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
