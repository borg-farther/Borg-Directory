from __future__ import annotations

from borg.core.capable_agent_stack import (
    STACK_LEVERS,
    capable_agent_stack_packet,
    render_capable_agent_stack_markdown,
)


EXPECTED_IDS = [
    "capable_base_model",
    "structured_outputs",
    "rag_layer",
    "persistent_memory",
    "real_tools",
    "tight_system_prompt",
    "eval_loop",
]


def test_capable_agent_stack_packet_has_seven_foundational_levers_and_no_hype() -> None:
    packet = capable_agent_stack_packet()

    assert packet["success"] is True
    assert packet["status"] == "minimum_capable_agent_stack"
    assert packet["first_10_claim"] is False
    assert packet["global_promotion_allowed"] is False
    assert packet["public_lift_claim"] is False
    assert packet["commands"]["inspect"] == "borg agent-stack --json"
    assert [lever["id"] for lever in packet["levers"]] == EXPECTED_IDS
    assert packet["implementation_order"] == [
        "capable_base_model",
        "structured_outputs",
        "real_tools",
        "tight_system_prompt",
        "persistent_memory",
        "rag_layer",
        "eval_loop",
    ]
    assert len(packet["minimum_viable_done"]) == 7
    assert packet["eval_contract"]["taskset_path"] == "eval/tasksets/minimum_capable_agent_stack.json"
    assert "fixed eval set" in packet["eval_contract"]["ship_rule"]
    assert len(packet["eval_contract"]["checklist"]) >= 5


def test_capable_agent_stack_markdown_mentions_every_lever_and_command() -> None:
    md = render_capable_agent_stack_markdown()

    assert "Minimum Capable Agent Stack" in md
    assert "borg agent-stack --json" in md
    assert "Claim boundary" in md
    for lever in STACK_LEVERS:
        assert lever.title in md
        assert lever.id in md
