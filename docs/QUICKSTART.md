# Borg quickstart

Use this when you want the shortest safe path.

## Install

```bash
python3 -m pip install agent-borg
borg version
borg-doctor --json
```

## Get first value

```bash
borg rescue "ModuleNotFoundError: No module named flask"
```

Look for:

- `ACTION` — what to try next
- `STOP` — what dead-end to avoid
- `VERIFY` — exact check to rerun
- `CONFIDENCE` — tested/observed/inferred, or `NO_CONFIDENT_MATCH`

## Connect Claude Code

```bash
borg setup-claude --scope user --verify --fix
```

Then fully restart Claude Code.

## Prime the agent

```text
{PRIMING_PARAGRAPH}
```

## More

- Full README: [`../README.md`](../README.md)
- Detailed setup: [`TRYING_BORG.md`](TRYING_BORG.md)
- MCP setup: [`MCP_SETUP.md`](MCP_SETUP.md)
- First-10 beta contract: [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md)
