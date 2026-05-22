> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg Day-One Automated Rescue

Status: implementation spec + product contract for `borg rescue` / `borg_rescue`.
Revision: 20260505-0700

## blunt answer

Borg should stay automated for agents. Manual `borg rescue` is the visible doorway for humans; automatic `borg_rescue` / `borg_observe` is the product for agents.

The best approach is a **two-lane rescue system**:

1. **automatic lane for agents** — called silently at task start or failure points; returns compact ACTION / STOP / VERIFY instructions.
2. **visible lane for humans** — shows a receipt explaining what Borg matched, what it stopped the agent from doing, and how to verify whether it helped.

Do not make first users learn packs, URIs, registry mechanics, reputation, or governance. Those are infrastructure. Day-one value is rescue.

## why automation is mandatory

If Borg depends on the human remembering to invoke it, it fails its core promise. The pain is that agents burn tokens invisibly while re-deriving known approaches. The fix has to trigger before or during that loop.

Automation is correct when:

- a technical task starts;
- a command/tool returns an error;
- the same failure repeats;
- the agent says it is stuck, looping, or trying again;
- the agent is about to edit code after an unclassified failure.

Automation is wrong when:

- the task is creative/nontechnical;
- the user asks for preference/opinion only;
- no technical action is being taken;
- Borg has no confident match.

The safety rule is **fail closed**: if no confident match, Borg must say `NO_MATCH` and the agent must not pretend Borg helped.

## implemented contract

### CLI

```bash
borg rescue 'ModuleNotFoundError: No module named flask'
pytest -q 2>&1 | borg rescue --json
borg rescue 'PermissionError: [Errno 13] permission denied' --short
```

### MCP

Tool: `borg_rescue`

Input:

```json
{
  "input": "ModuleNotFoundError: No module named flask",
  "source": "agent-loop",
  "show_guidance": true
}
```

Output contract:

```json
{
  "success": true,
  "status": "matched",
  "problem_class": "missing_dependency",
  "confidence": "tested|observed|inferred|unknown",
  "action": ["..."],
  "stop": ["..."],
  "verify": ["..."],
  "next_command": "...",
  "agent_instruction": "ACTION: ...\nSTOP: ...\nVERIFY: ...",
  "human_receipt": "Borg matched ...",
  "automation_policy": {
    "default": "automatic_for_agents",
    "fail_closed": true,
    "human_visibility_required": true
  },
  "evidence": {
    "success_count": 0,
    "failure_count": 0,
    "uses": 0,
    "source": "seed_pack"
  }
}
```

Unknown match output must have:

```json
{
  "success": false,
  "status": "no_confident_match",
  "problem_class": "unknown",
  "agent_instruction": "NO_MATCH: disclose that Borg checked and found no confident match..."
}
```

## agent loop integration

A host agent should wire Borg like this:

```python
from borg.integrations.mcp_server import borg_rescue


def before_technical_work(task_text: str) -> str | None:
    packet = json.loads(borg_rescue(input=task_text, source="pre-task", show_guidance=False))
    if packet["success"]:
        return packet["agent_instruction"]
    return None


def after_tool_error(error_text: str, repeated_failures: int) -> str | None:
    if repeated_failures < 1:
        return None
    packet = json.loads(borg_rescue(input=error_text, source="tool-error", show_guidance=False))
    if packet["success"]:
        return packet["agent_instruction"]
    return packet["agent_instruction"]  # includes NO_MATCH disclosure rule
```

Recommended policy:

- pre-task call: low-cost, short output only;
- first tool error: call if error is concrete;
- repeated failure: mandatory call;
- human-visible receipt: show after match or at final answer;
- outcome feedback: record whether the suggested path worked.

## why this is better than `borg debug` alone

`borg debug` is useful but human-shaped. It prints guidance.

`borg rescue` is product-shaped. It returns:

- next action;
- dead-end to avoid;
- verification step;
- automation policy;
- human receipt;
- machine-readable JSON;
- fail-closed unknown behavior.

That is the difference between a CLI helper and an agent-native rescue layer.

## day-one success metric

North star:

> percentage of first sessions where the user can point to one specific thing Borg saved the agent from doing.

Minimum beta pass:

- 0 P0 onboarding blockers;
- 70%+ first flow completion unaided;
- 60%+ users say value was obvious;
- 50%+ tasks show avoided loop/time/token or improved success;
- every rescue has outcome feedback captured.

## tests added

- `borg/tests/test_rescue.py`
  - known error returns matched ACTION / STOP / VERIFY contract;
  - unknown/non-Python error fails closed;
  - empty input fails closed;
  - renderer exposes human value sections;
  - MCP `borg_rescue` returns JSON contract;
  - MCP dispatcher routes `borg_rescue`.

- `borg/tests/test_cli.py`
  - top-level help includes `rescue`;
  - `borg rescue ... --short` returns visible rescue packet;
  - `borg rescue ... --json --short` fails closed on unknown Rust error.

## design decision

Yes, this is the right approach.

The product should not choose between manual and automated. It needs both:

- **manual** because first humans need to see value instantly;
- **automated** because the real value is preventing invisible agent flailing before the human notices.

The complete product wedge is:

```text
agent starts technical task
        ↓
borg_rescue / borg_observe auto-checks cache
        ↓
if match: inject ACTION / STOP / VERIFY
        ↓
agent executes normal tools
        ↓
human sees receipt: what Borg matched, what it prevented, whether it worked
        ↓
outcome is recorded so future rescue improves
```

That is the smallest permanent product shape that can actually deliver day-one value.
