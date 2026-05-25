"""First-10 user readiness contract for Borg.

This module is intentionally pure-Python and side-effect-light.  It gives the
CLI, docs, tests, and launch checklist one shared source of truth for the seven
pre-first-user gates AB asked Borg to clear.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ReadinessGate:
    """One binary gate in the first-10 readiness contract."""

    id: str
    title: str
    pass_criteria: List[str]
    proof: List[str]
    user_visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


FIRST_10_SUCCESS_METRIC = (
    "At least 6 of the first 10 users get one relevant ACTION/STOP/VERIFY "
    "moment without maintainer handholding, and every miss is recorded as "
    "NO_CONFIDENT_MATCH or explicit negative feedback instead of being hidden."
)

PRIMING_PARAGRAPH = (
    "Before attempting technical fixes for errors, bugs, installs, configs, deployments, "
    "or tests, call Borg first. For a concrete failure in MCP, call "
    "error_lookup(input=\"<exact error or failing command output>\"); it is the plain-English "
    "alias for borg_rescue(input=\"<exact error or failing command output>\") and returns the same "
    "ACTION/STOP/VERIFY packet. The CLI equivalent is borg rescue \"<exact error>\". Use "
    "borg_observe(task=\"<exact task or error>\", context=\"<tech stack>\") for broader task-start "
    "guidance when there is not yet a concrete failure. Treat Borg output as advisory: follow ACTION "
    "when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, "
    "and verify with the exact failing command or smallest regression test. After the outcome, "
    "record it with borg_feedback if you used a pack session, or borg_record_failure if you are "
    "recording a concrete error-pattern success/failure."
)

MCP_FIRST_CALL = (
    "error_lookup(input=\"ModuleNotFoundError: No module named flask\", show_guidance=False) "
    "or borg_rescue(input=\"ModuleNotFoundError: No module named flask\", show_guidance=False); "
    "both must return the same ACTION/STOP/VERIFY rescue packet."
)

SUPPORTED_FIRST_USER_MIXES = [
    "Human only: CLI or Python API, no MCP required.",
    "Human chat UI plus agent host: Telegram/Discord/Slack/API sessions through Hermes, with Borg configured once in Hermes.",
    "MCP-native coding agents: Claude Code, Cursor, Cline, Continue, Goose, Codex-style CLIs, or custom runners with borg-mcp configured.",
    "Any model provider behind the host: ChatGPT/OpenAI, Claude, OpenRouter, local models, or other OpenAI-compatible endpoints.",
    "Chat app with no MCP/tool execution: run borg rescue/search outside the chat and paste ACTION/STOP/VERIFY back, or route through an MCP-capable host.",
]

FIRST_10_GATES: List[ReadinessGate] = [
    ReadinessGate(
        id="G1",
        title="Real-vs-synthetic confidence is impossible to miss",
        pass_criteria=[
            "Every rescue/observe path exposes confidence and evidence source.",
            "Synthetic-only guidance is labeled synthetic or inferred, never proven.",
            "Real trace count is visible before detailed guidance.",
        ],
        proof=[
            "borg rescue '<known error>' --json includes evidence.source and confidence",
            "borg_observe output includes CONFIDENCE with Real traces and Synthetic counts",
        ],
    ),
    ReadinessGate(
        id="G2",
        title="Retrieval fails closed instead of hallucinating relevance",
        pass_criteria=[
            "Low-similarity trace hits are filtered before rendering.",
            "Content-free trace hits cannot become ACTION guidance.",
            "Unrelated pack matches return NO_CONFIDENT_MATCH rather than random pack advice.",
            "Observe injection boundaries suppress NO_CONFIDENT_MATCH, synthetic-only pack advice, and permission guidance unless the task has concrete permission-denied signals.",
        ],
        proof=[
            "_trace_match_is_confident rejects similarity < 0.45 and empty causal traces",
            "_pack_match_is_confident requires domain/lexical overlap",
            "_guidance_is_safe_to_inject fails closed before prompt injection",
            "unknown observe output starts ACTION/STOP/VERIFY/CONFIDENCE + NO_CONFIDENT_MATCH",
        ],
    ),
    ReadinessGate(
        id="G3",
        title="Day-one packet answers what to do, avoid, and verify",
        pass_criteria=[
            "borg_rescue / error_lookup returns ACTION, STOP, VERIFY, human_receipt, automation_policy, and a no-hype value_receipt.",
            "borg_observe returns ACTION, STOP or explicit no-match STOP, VERIFY, CONFIDENCE.",
            "Agents are instructed not to blend weak retrieval into normal reasoning.",
        ],
        proof=[
            "tests/core/test_rescue.py",
            "tests/readiness/test_first_10_readiness.py",
        ],
    ),
    ReadinessGate(
        id="G4",
        title="Fresh-user install gauntlet is canonical",
        pass_criteria=[
            "One clean install command is documented.",
            "doctor/version/rescue/search/MCP setup are the public smoke path.",
            "MCP configs use absolute BORG_HOME paths, not '~'.",
        ],
        proof=[
            "README evaluator smoke path",
            "docs/FIRST_10_BETA_READINESS.md",
        ],
    ),
    ReadinessGate(
        id="G5",
        title="Claims are truthful for a 10-user beta",
        pass_criteria=[
            "Docs describe Borg as a reasoning-cache/rescue-memory beta, not magic lift.",
            "Unproven network effects and non-Python breadth are listed as limitations.",
            "Success metric is user-observed ACTION/STOP value, not vanity test count.",
        ],
        proof=[
            "README What is proven / Honest limitations sections",
            "docs/FIRST_10_BETA_READINESS.md first-10 success metric",
        ],
    ),
    ReadinessGate(
        id="G6",
        title="Security and privacy baseline is linked into launch flow",
        pass_criteria=[
            "Security baseline exists and is referenced from README/docs index.",
            "Secret scan, dependency audit, static security scan, and policy check are CI gates.",
            "First users are told not to paste secrets into shared reports.",
        ],
        proof=[
            "docs/SECURITY_HARDENING_BASELINE.md",
            "scripts/security_gate_check.py",
            ".github/workflows/security-gates.yml",
        ],
    ),
    ReadinessGate(
        id="G7",
        title="10-user beta is instrumented as learning, not theatre",
        pass_criteria=[
            "Each tester gets the same install, priming, three tasks, and feedback receipt.",
            "Outcomes are captured as helpful/not helpful/no match plus optional before/after minutes or tokens.",
            "Measured savings are derived only from consented external-user rows; rescue packets may not claim savings at call time.",
            "GO/NO-GO after first 10 is binary against the 6/10 useful moment threshold.",
        ],
        proof=[
            "first_10_readiness_packet()",
            "docs/FIRST_10_BETA_READINESS.md",
        ],
    ),
]


def first_10_readiness_packet() -> Dict[str, Any]:
    """Return the full machine-readable first-10 readiness contract."""
    return {
        "success": True,
        "status": "first_10_beta_contract",
        "success_metric": FIRST_10_SUCCESS_METRIC,
        "priming_paragraph": PRIMING_PARAGRAPH,
        "mcp_first_call": MCP_FIRST_CALL,
        "supported_mixes": list(SUPPORTED_FIRST_USER_MIXES),
        "gates": [gate.to_dict() for gate in FIRST_10_GATES],
        "smoke_commands": [
            "python3 -m pip install agent-borg",
            "borg version",
            "borg-doctor --json",
            "borg rescue 'ModuleNotFoundError: No module named flask' --json",
            "borg search 'django migration table already exists'",
            "borg setup-claude --scope user --verify --fix",
            "borg first-10 --json",
        ],
        "feedback_fields": [
            "tester_id",
            "task_id",
            "did_borg_return_action_stop_verify",
            "was_guidance_relevant",
            "did_it_prevent_a_dead_end",
            "helpful_true_false",
            "exact_no_match_or_miss_reason",
            "baseline_minutes_without_borg",
            "actual_minutes_with_borg",
            "net_minutes_saved",
            "baseline_tokens_without_borg",
            "actual_tokens_with_borg",
            "net_tokens_saved",
            "savings_counterfactual_basis",
            "dead_end_avoided_confirmed",
            "user_confirmed_value",
        ],
    }


def render_first_10_readiness_markdown() -> str:
    """Render the contract for docs/CLI."""
    packet = first_10_readiness_packet()
    lines = [
        "# Borg First-10 Beta Readiness Contract",
        "",
        f"**Success metric:** {packet['success_metric']}",
        "",
        "## Agent priming paragraph",
        "",
        "```text",
        packet["priming_paragraph"],
        "```",
        "",
        "## Clean-user smoke path",
        "",
        "```bash",
        *packet["smoke_commands"],
        "```",
        "",
        "## MCP first call",
        "",
        packet["mcp_first_call"],
        "",
        "## Supported first-user mixes",
        "",
        *[f"- {mix}" for mix in packet["supported_mixes"]],
        "",
        "For every mix: install Borg where tools execute, prime the agent/human to call Borg before technical fixes, and record helpful/not-helpful/no-match outcomes.",
        "",
        "## Binary gates",
        "",
    ]
    for gate in FIRST_10_GATES:
        lines.append(f"### {gate.id}. {gate.title}")
        lines.append("")
        lines.append("Pass criteria:")
        lines.extend(f"- {item}" for item in gate.pass_criteria)
        lines.append("")
        lines.append("Proof:")
        lines.extend(f"- `{item}`" if item.endswith(".py") or item.startswith("borg") or item.startswith("README") or item.startswith("docs/") or item.startswith("scripts/") or item.startswith(".github") else f"- {item}" for item in gate.proof)
        lines.append("")
    lines.extend([
        "## First-10 feedback form fields",
        "",
        *[f"- `{field}`" for field in packet["feedback_fields"]],
        "",
        "## GO / NO-GO after 10 users",
        "",
        "GO only if >=6/10 users record a relevant ACTION/STOP/VERIFY moment without maintainer handholding and all security/install P0s remain closed.",
        "NO-GO if Borg frequently returns unrelated guidance, hides weak confidence, or needs maintainer explanation to be useful.",
        "",
    ])
    return "\n".join(lines)
