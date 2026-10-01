"""Machine-readable minimum capable agent host stack for Borg users.

Borg improves technical debugging loops, but it cannot compensate for a weak
host agent. This module defines the free/local baseline an agent host should
have before users expect strong results from Borg or any other retrieval layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class StackLever:
    """One leverage point in a minimum capable agent host."""

    id: str
    title: str
    why_it_matters: str
    minimum_free_path: List[str]
    done_when: List[str]
    proof: List[str]
    anti_patterns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


STACK_LEVERS: List[StackLever] = [
    StackLever(
        id="capable_base_model",
        title="Capable base model",
        why_it_matters=(
            "Model quality is the biggest single lever. A weak default model"
            " wastes every downstream improvement."
        ),
        minimum_free_path=[
            "Use the most capable currently-free open model your host can reach; OpenRouter free-tier open models are a common path.",
            "Pin one known-good default model for the main task instead of floating on 'latest free'.",
            "Keep a cheaper fallback model only for background or non-critical work.",
        ],
        done_when=[
            "The host has one pinned default reasoning model that is clearly stronger than the weakest available default.",
            "Model changes are tracked in the eval log instead of being swapped ad hoc.",
        ],
        proof=[
            "Host config records provider + exact model id.",
            "A fixed eval set is rerun before/after any model switch.",
        ],
        anti_patterns=[
            "Shipping on the weakest base model because it is free.",
            "Floating model ids across eval runs.",
            "Treating retrieval or prompting as a substitute for insufficient model capability.",
        ],
    ),
    StackLever(
        id="structured_outputs",
        title="Structured outputs",
        why_it_matters=(
            "JSON-schema output contracts sharply reduce hallucinated tool calls,"
            " broken parsing, and glue-code drift."
        ),
        minimum_free_path=[
            "Use native JSON-schema or schema-constrained output mode whenever the host/provider supports it.",
            "Validate the model response against the schema before using it.",
            "Fail closed when validation fails; do not silently coerce malformed output into tool arguments.",
        ],
        done_when=[
            "Tool-selection and machine-readable answers flow through an explicit schema.",
            "Malformed outputs are visible in tests and logs instead of being silently repaired.",
        ],
        proof=[
            "Eval cases include at least one exact-schema response and one invalid-schema negative control.",
            "Tool argument payloads are validated before execution.",
        ],
        anti_patterns=[
            "Free-form prose that downstream code regex-parses.",
            "Best-effort parsing that hides model failures.",
            "Letting the model invent tool names or argument shapes.",
        ],
    ),
    StackLever(
        id="rag_layer",
        title="RAG over your own docs",
        why_it_matters=(
            "Even a small local knowledge base beats guessing from stale priors"
            " when the answer already exists in your docs, specs, or runbooks."
        ),
        minimum_free_path=[
            "Index operator docs, runbooks, API references, and project conventions into a local vector store.",
            "Chroma or Qdrant local mode is sufficient for a first pass.",
            "Retrieve the smallest relevant chunks and cite the source path/section in the answer.",
        ],
        done_when=[
            "The agent can answer doc-backed questions from local material instead of memory alone.",
            "Retrieved snippets carry source metadata the operator can inspect.",
        ],
        proof=[
            "Eval cases include questions whose answers appear only in local docs.",
            "The answer includes retrieval provenance instead of unsupported certainty.",
        ],
        anti_patterns=[
            "Indexing nothing and calling it RAG.",
            "Dumping huge irrelevant contexts into the prompt.",
            "Claiming retrieval helped without citing the retrieved source.",
        ],
    ),
    StackLever(
        id="persistent_memory",
        title="Persistent memory",
        why_it_matters=(
            "An agent that forgets user preferences, corrections, and prior"
            " decisions every turn barely compounds."
        ),
        minimum_free_path=[
            "Persist durable user preferences, recurring corrections, and stable project conventions in SQLite or an equivalent local store.",
            "Differentiate durable memory from ephemeral conversation history.",
            "Load only compact, still-relevant facts into the prompt.",
        ],
        done_when=[
            "The agent remembers stable user and project facts across sessions.",
            "Temporary task state is not confused with durable memory.",
        ],
        proof=[
            "A repeated user preference persists across a fresh session.",
            "An eval case checks that a prior correction is applied without re-teaching.",
        ],
        anti_patterns=[
            "Stateless sessions for every turn.",
            "Stuffing the entire conversation transcript into memory.",
            "Saving stale execution logs or temporary TODOs as long-term facts.",
        ],
    ),
    StackLever(
        id="real_tools",
        title="Real tools, not just chat",
        why_it_matters=(
            "Without tools, the agent cannot ground itself against the real world"
            " and becomes a chatbot wearing an operator costume."
        ),
        minimum_free_path=[
            "Expose file read/write, code execution, and web lookup at minimum.",
            "Use explicit tool schemas and verify tool arguments before execution.",
            "Require the agent to use tools for current facts instead of guessing.",
        ],
        done_when=[
            "The host can inspect files, run verification commands, and fetch missing facts.",
            "Tool use is available in both happy-path and evaluation flows.",
        ],
        proof=[
            "Eval cases require a web/file/tool action the model cannot solve from priors alone.",
            "Tool-call transcripts show grounded evidence, not imaginary tool results.",
        ],
        anti_patterns=[
            "Calling the system an agent when it cannot act.",
            "Inventing tool outputs when calls fail.",
            "Disabling tools in evals and still claiming production readiness.",
        ],
    ),
    StackLever(
        id="tight_system_prompt",
        title="Tight system prompt",
        why_it_matters=(
            "Clear role, constraints, output shape, and failure behavior fix more"
            " bugs than most libraries."
        ),
        minimum_free_path=[
            "State the agent role, operating boundaries, response format, and failure modes explicitly.",
            "Tell the agent when to say 'I don't know', when to call tools, and when to verify before answering.",
            "Keep the prompt small enough that the important rules are not buried.",
        ],
        done_when=[
            "The prompt defines tool-use expectations, schema expectations, and fail-closed behavior.",
            "The operator can point to one canonical prompt source of truth.",
        ],
        proof=[
            "Eval cases include negative controls for guessing instead of tool use.",
            "Prompt changes are versioned and rerun through the same eval set.",
        ],
        anti_patterns=[
            "Vague 'helpful assistant' prompts for agent workflows.",
            "Prompt bloat that hides the few rules that matter.",
            "Changing prompt text without rerunning evals.",
        ],
    ),
    StackLever(
        id="eval_loop",
        title="Eval loop",
        why_it_matters=(
            "Without a fixed eval set, every tweak is vibes. With one, you can"
            " tell whether a change helped, regressed, or only moved style around."
        ),
        minimum_free_path=[
            "Keep a small fixed set of real operator questions, failures, and tool-use tasks.",
            "Promptfoo is a fine local harness when available, but any repeatable local scorer is acceptable.",
            "Rerun the same eval set for model, prompt, tool, memory, or RAG changes before shipping.",
        ],
        done_when=[
            "Every meaningful host change has before/after eval evidence.",
            "Regression cases are added when the agent fails in production or dogfood.",
        ],
        proof=[
            "Eval results are logged per model/prompt/tool configuration.",
            "Shipping is blocked when the fixed eval set regresses on grounded tasks.",
        ],
        anti_patterns=[
            "Shipping based on anecdotal one-off wins.",
            "Changing multiple variables at once and calling the outcome causal.",
            "No regression suite for previously-seen failures.",
        ],
    ),
]


IMPLEMENTATION_ORDER = [
    "capable_base_model",
    "structured_outputs",
    "real_tools",
    "tight_system_prompt",
    "persistent_memory",
    "rag_layer",
    "eval_loop",
]


EVAL_CHECKLIST = [
    "Can the host emit exact schema-valid JSON for a tool-selection or structured-answer task?",
    "Does it call tools instead of guessing when current facts or files are required?",
    "Can it answer a question that only exists in local docs via retrieval with provenance?",
    "Does it remember a prior user preference or correction in a fresh session?",
    "Does it say NO_CONFIDENT_MATCH / insufficient context instead of faking certainty when evidence is absent?",
]


def capable_agent_stack_packet() -> Dict[str, Any]:
    """Return the minimum host stack Borg expects around itself."""
    return {
        "success": True,
        "schema_version": "1.0",
        "status": "minimum_capable_agent_stack",
        "summary": (
            "Borg helps most when the host agent is already competent. This packet"
            " defines the minimum free/local stack: capable model, structured"
            " outputs, local retrieval, durable memory, real tools, a tight prompt,"
            " and a fixed eval loop."
        ),
        "implementation_order": list(IMPLEMENTATION_ORDER),
        "levers": [lever.to_dict() for lever in STACK_LEVERS],
        "minimum_viable_done": [
            "A capable pinned default model is configured.",
            "Machine-readable responses are schema-constrained and validated.",
            "Local docs are searchable through a retrieval layer.",
            "Durable user/project facts persist across sessions.",
            "The host can use grounded tools for files, execution, and current facts.",
            "The system prompt defines constraints and fail-closed behavior.",
            "A fixed eval set is rerun before shipping changes.",
        ],
        "eval_contract": {
            "ship_rule": (
                "Do not ship a model/prompt/tool/memory/RAG change until the same"
                " fixed eval set has been rerun and reviewed."
            ),
            "taskset_path": "eval/tasksets/minimum_capable_agent_stack.json",
            "checklist": list(EVAL_CHECKLIST),
        },
        "commands": {
            "inspect": "borg agent-stack --json",
            "first_user_contract": "borg first-10 --json",
            "host_priming": "borg agent-priming <host> --json",
        },
        "claim_boundary": (
            "This is a local host-hardening checklist. It is not proof of first-10"
            " lift, public lift, or global promotion."
        ),
        "first_10_claim": False,
        "global_promotion_allowed": False,
        "public_lift_claim": False,
    }


def render_capable_agent_stack_markdown() -> str:
    """Render the packet as operator-readable markdown/text."""
    packet = capable_agent_stack_packet()
    lines = [
        "# Minimum Capable Agent Stack",
        "",
        packet["summary"],
        "",
        "## Implementation order",
        "",
    ]
    lever_by_id = {lever.id: lever for lever in STACK_LEVERS}
    for idx, lever_id in enumerate(packet["implementation_order"], start=1):
        lever = lever_by_id[lever_id]
        lines.append(f"{idx}. **{lever.title}** (`{lever.id}`)")
    lines.extend([
        "",
        "## The seven levers",
        "",
    ])
    for lever in STACK_LEVERS:
        lines.extend([
            f"### {lever.title}",
            "",
            lever.why_it_matters,
            "",
            "Minimum free/local path:",
            *[f"- {item}" for item in lever.minimum_free_path],
            "",
            "Done when:",
            *[f"- {item}" for item in lever.done_when],
            "",
            "Proof:",
            *[f"- {item}" for item in lever.proof],
            "",
            "Anti-patterns:",
            *[f"- {item}" for item in lever.anti_patterns],
            "",
        ])
    lines.extend([
        "## Eval contract",
        "",
        packet["eval_contract"]["ship_rule"],
        "",
        f"Taskset: `{packet['eval_contract']['taskset_path']}`",
        "",
        *[f"- {item}" for item in packet["eval_contract"]["checklist"]],
        "",
        "## Commands",
        "",
        f"- Inspect: `{packet['commands']['inspect']}`",
        f"- First-user contract: `{packet['commands']['first_user_contract']}`",
        f"- Host priming: `{packet['commands']['host_priming']}`",
        "",
        f"**Claim boundary:** {packet['claim_boundary']}",
        "",
    ])
    return "\n".join(lines)
