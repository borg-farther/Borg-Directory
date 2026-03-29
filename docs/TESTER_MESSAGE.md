# Borg Tester Onboarding

**Install:** `pip install agent-borg`

**Try these 3 commands now:**
```bash
borg search debugging
borg try borg://systematic-debugging
borg pull borg://systematic-debugging
```

**MCP setup for Claude Code** — add to `~/.config/claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp"
    }
  }
}
```

Full guide: https://github.com/agent-borg/agent-borg/blob/main/docs/EXTERNAL_TESTER_GUIDE.md

**What we need from you:**
- Commands that worked / commands that broke (exact output helps)
- Anything confusing or counterintuitive
- Edge cases you hit
