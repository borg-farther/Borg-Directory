# Try Borg in 2 Minutes

Borg gives your AI coding agent a shared memory of error fixes. Before your agent burns tool calls on a known error, Borg surfaces what worked in prior sessions.

## 1. Install (one command)

```bash
pip install agent-borg
```

This installs `agent-borg` and its dependencies.

**Lighter install** (no optional extras):

```bash
pip install --no-deps agent-borg
pip install click typer pyyaml
```

## 2. Add to your agent's MCP config

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"],
      "env": { "BORG_HOME": "~/.borg" }
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`)  same format.

**Claude Code**  add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"],
      "env": { "BORG_HOME": "~/.borg" }
    }
  }
}
```

**Cline**  add via Cline MCP settings, same command and args.

## 3. Verify

Restart your agent after editing the config. You should see `borg_observe` in the available tools list.

Or from the terminal:

```bash
borg-doctor
```

This checks the install, DB path, and trace count.

## 4. How it works

Your agent now has access to these tools:

- **`borg_observe(task, context)`**  "I'm about to work on this error. What do you know?" Returns up to 5 prior fixes ranked by relevance.
- **`borg_rate(helpful, trace_id)`**  After the fix, tell Borg if the trace was useful. Improves ranking for future queries.

On the first call, Borg creates `~/.borg/traces.db` with seed data (~150 traces covering common errors). As your agent solves problems, it automatically saves new traces. Over time, the seed data fades out and your real experience dominates.

## 5. What you'll see

Results come back with labels:

- `[real]`  from an actual agent session (yours or shared)
- `[synthetic]`  from the seed data (pre-populated coverage)

Text is wrapped in `[BORG-TRACE-CONTENT]...[/BORG-TRACE-CONTENT]` boundaries  this is the prompt injection sanitizer keeping trace content clearly separated from your agent's instructions.

## Feedback

This is private beta. Things will break. When they do:

- DM Alesh directly (fastest)
- Or open an issue: https://github.com/borg-farther/Borg-Directory/issues

What's most useful: "I hit error X, Borg returned Y, it was [helpful/useless/wrong]."
