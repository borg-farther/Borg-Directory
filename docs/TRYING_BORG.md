# Trying Borg

This is the detailed first-user setup guide. The shortest path is in [`QUICKSTART.md`](QUICKSTART.md).

## 1. Install

Borg requires Python 3.10+.

```bash
python3 -m pip install agent-borg
borg version
borg-doctor --json
```

If you prefer an isolated CLI install:

```bash
pipx install agent-borg
```

If `borg` is not found, check your Python scripts directory:

```bash
python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

## 2. First value check

```bash
borg rescue "ModuleNotFoundError: No module named flask"
```

Expected shape:

```text
ACTION: ...
STOP: ...
VERIFY: ...
CONFIDENCE: ...
```

If Borg has no confident match, it should say `NO_CONFIDENT_MATCH` instead of forcing unrelated advice.

## 3. Search and pack workflow

```bash
borg search "django migration table already exists"
borg try systematic-debugging
borg pull borg://hermes/systematic-debugging
borg apply systematic-debugging --task "Fix login bug where users get 401"
```

After a real outcome, record feedback:

```bash
borg feedback-v3 --pack systematic-debugging --success yes
# or
borg feedback-v3 --pack systematic-debugging --success no
```

This records outcome data. Shared learning depends on explicit publishing/aggregation and is still being validated.

## 4. Claude Code setup

```bash
borg setup-claude --scope user --verify --fix
```

What this does:

1. resolves the MCP launch command;
2. writes/merges `mcpServers.borg` into the selected config;
3. creates Borg home storage if missing;
4. uses an absolute `BORG_HOME` path;
5. runs an MCP initialize handshake and prints PASS/FAIL.

After setup, fully restart Claude Code and ask what Borg tools are available.

## 5. Generic MCP setup

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": [],
      "env": { "BORG_HOME": "/absolute/path/to/.borg" }
    }
  }
}
```

If `borg-mcp` is not on PATH:

```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"],
      "env": { "BORG_HOME": "/absolute/path/to/.borg" }
    }
  }
}
```

## 6. Agent priming

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and record the outcome with borg_rate(helpful=True/False).
```

## 7. Readiness boundary

Borg is ready for controlled first-10 beta sharing. It is not yet claiming public self-serve launch readiness or statistically significant agent-level success lift. See [`READINESS.md`](READINESS.md).
