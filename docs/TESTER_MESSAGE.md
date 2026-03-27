# Guild-v2 Tester Onboarding

**Install:** `pip install guild-packs`

**Try these 3 commands now:**
```bash
guildpacks search debugging
guildpacks try guild://systematic-debugging
guildpacks pull guild://systematic-debugging
```

**MCP setup for Claude Code** — add to `~/.config/claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "guild-mcp"
    }
  }
}
```

Full guide: https://github.com/bensargotest-sys/guild-packs/blob/v2/docs/EXTERNAL_TESTER_GUIDE.md

**What we need from you:**
- Commands that worked / commands that broke (exact output helps)
- Anything confusing or counterintuitive
- Edge cases you hit
