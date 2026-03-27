import guild
print(f"Version: {guild.__version__}")

from guild import check
print(f"check function: {check}")
result = check("test context")
print(f"check result: {result}")

from guild.core.safety import scan_pack_safety
print(f"scan_pack_safety: {scan_pack_safety}")

from guild.db.store import GuildStore
print(f"GuildStore: {GuildStore}")

# Test MCP entry point
import guild.integrations.mcp_server as mcp
print(f"MCP server main: {mcp.main}")
