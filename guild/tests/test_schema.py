"""
Tests for guild.core.schema — pack parsing, validation, and field collection.
"""

import pytest

from guild.core.schema import (
    collect_text_fields,
    parse_skill_frontmatter,
    parse_workflow_pack,
    sections_to_phases,
    validate_pack,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def minimal_pack(**overrides):
    """Return a minimal valid pack with optional field overrides."""
    base = {
        "type": "workflow_pack",
        "version": "1.0.0",
        "id": "guild://test/minimal",
        "problem_class": "Test problem",
        "mental_model": "Think step by step.",
        "phases": [
            {
                "name": "plan",
                "description": "Plan the approach.",
                "checkpoint": "Plan approved.",
                "prompts": ["Make a plan."],
                "anti_patterns": ["Rushing ahead."],
            },
        ],
        "provenance": {
            "author_agent": "agent://test",
            "evidence": "Tested in CI.",
            "confidence": "tested",
            "failure_cases": ["Skipped planning phase."],
        },
        "required_inputs": ["task description"],
        "escalation_rules": ["Escalate on error."],
    }
    base.update(overrides)
    return base


def pack_to_yaml(pack):
    import yaml
    return yaml.dump(pack, default_flow_style=False)


# ---------------------------------------------------------------------------
# parse_workflow_pack
# ---------------------------------------------------------------------------

class TestParseWorkflowPack:
    def test_valid_pack(self):
        pack = minimal_pack()
        result = parse_workflow_pack(pack_to_yaml(pack))
        assert result["id"] == "guild://test/minimal"
        assert result["version"] == "1.0.0"

    def test_missing_required_field_raises(self):
        pack = minimal_pack()
        del pack["id"]
        with pytest.raises(ValueError, match="Missing required fields"):
            parse_workflow_pack(pack_to_yaml(pack))

    def test_missing_multiple_required_fields_raises(self):
        pack = minimal_pack()
        del pack["id"]
        del pack["version"]
        with pytest.raises(ValueError, match="id.*version|version.*id"):
            parse_workflow_pack(pack_to_yaml(pack))

    def test_malformed_yaml_raises(self):
        with pytest.raises(ValueError, match="Invalid YAML"):
            # Tab indentation in a context where it's not allowed makes this truly malformed
            parse_workflow_pack("type: workflow_pack\n\tbad: indent")

    def test_top_level_scalar_raises(self):
        with pytest.raises(ValueError, match="expected a mapping at top level"):
            parse_workflow_pack("just a string")

    def test_top_level_list_raises(self):
        with pytest.raises(ValueError, match="expected a mapping at top level"):
            parse_workflow_pack("- item1\n- item2")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_workflow_pack("")

    def test_only_comments_raises(self):
        # yaml.safe_load returns None for a document with only comments
        with pytest.raises(ValueError, match="expected a mapping"):
            parse_workflow_pack("# just a comment\n")

    def test_version_field_missing(self):
        pack = minimal_pack()
        del pack["version"]
        with pytest.raises(ValueError, match="Missing required fields"):
            parse_workflow_pack(pack_to_yaml(pack))

    def test_phases_missing(self):
        pack = minimal_pack()
        del pack["phases"]
        with pytest.raises(ValueError, match="Missing required fields"):
            parse_workflow_pack(pack_to_yaml(pack))

    def test_provenance_missing(self):
        pack = minimal_pack()
        del pack["provenance"]
        with pytest.raises(ValueError, match="Missing required fields"):
            parse_workflow_pack(pack_to_yaml(pack))


# ---------------------------------------------------------------------------
# validate_pack
# ---------------------------------------------------------------------------

class TestValidatePack:
    def test_valid_pack_no_errors(self):
        pack = minimal_pack()
        assert validate_pack(pack) == []

    def test_missing_provenance_field(self):
        # When provenance key is absent entirely, pack.get("provenance", {}) yields {},
        # which passes the isinstance check; validation then fails on evidence/confidence.
        pack = minimal_pack()
        del pack["provenance"]
        errors = validate_pack(pack)
        assert any("evidence" in e for e in errors)
        assert any("confidence" in e for e in errors)

    def test_provenance_not_dict_raises(self):
        pack = minimal_pack(provenance="not a dict")
        errors = validate_pack(pack)
        assert "Provenance must be a mapping" in errors

    def test_missing_evidence(self):
        pack = minimal_pack()
        pack["provenance"] = dict(pack["provenance"])
        del pack["provenance"]["evidence"]
        errors = validate_pack(pack)
        assert any("evidence" in e for e in errors)

    def test_empty_evidence(self):
        pack = minimal_pack()
        pack["provenance"] = dict(pack["provenance"], evidence="")
        errors = validate_pack(pack)
        assert any("evidence" in e for e in errors)

    def test_missing_confidence(self):
        pack = minimal_pack()
        pack["provenance"] = dict(pack["provenance"])
        del pack["provenance"]["confidence"]
        errors = validate_pack(pack)
        assert any("confidence" in e for e in errors)

    def test_invalid_confidence_value(self):
        pack = minimal_pack()
        pack["provenance"] = dict(pack["provenance"], confidence="invalid")
        errors = validate_pack(pack)
        assert any("invalid" in e.lower() for e in errors)

    def test_all_valid_confidence_values(self):
        for confidence in ("guessed", "inferred", "tested", "validated"):
            pack = minimal_pack()
            pack["provenance"] = dict(pack["provenance"], confidence=confidence)
            assert validate_pack(pack) == [], f"confidence={confidence} should be valid"

    def test_missing_failure_cases(self):
        pack = minimal_pack()
        pack["provenance"] = dict(pack["provenance"])
        del pack["provenance"]["failure_cases"]
        errors = validate_pack(pack)
        assert any("failure_cases" in e for e in errors)

    def test_missing_required_inputs(self):
        pack = minimal_pack()
        del pack["required_inputs"]
        errors = validate_pack(pack)
        assert any("required_inputs" in e for e in errors)

    def test_empty_required_inputs(self):
        pack = minimal_pack(required_inputs=[])
        errors = validate_pack(pack)
        assert any("required_inputs" in e for e in errors)

    def test_required_inputs_not_list(self):
        pack = minimal_pack(required_inputs="not a list")
        errors = validate_pack(pack)
        assert any("required_inputs" in e for e in errors)

    def test_missing_escalation_rules(self):
        pack = minimal_pack()
        del pack["escalation_rules"]
        errors = validate_pack(pack)
        assert any("escalation_rules" in e for e in errors)

    def test_empty_escalation_rules(self):
        pack = minimal_pack(escalation_rules=[])
        errors = validate_pack(pack)
        assert any("escalation_rules" in e for e in errors)

    def test_escalation_rules_not_list(self):
        pack = minimal_pack(escalation_rules="not a list")
        errors = validate_pack(pack)
        assert any("escalation_rules" in e for e in errors)

    def test_multiple_errors(self):
        pack = minimal_pack()
        pack["provenance"] = {}
        del pack["required_inputs"]
        del pack["escalation_rules"]
        errors = validate_pack(pack)
        assert len(errors) >= 4

    def test_valid_pack_with_only_required_provenance_fields(self):
        pack = minimal_pack()
        pack["provenance"] = {
            "evidence": "Some evidence.",
            "confidence": "guessed",
            "failure_cases": ["Case 1."],
        }
        assert validate_pack(pack) == []


# ---------------------------------------------------------------------------
# collect_text_fields
# ---------------------------------------------------------------------------

class TestCollectTextFields:
    def test_empty_pack(self):
        assert collect_text_fields({}) == []

    def test_mental_model(self):
        pack = minimal_pack(mental_model="Step by step.")
        assert "Step by step." in collect_text_fields(pack)

    def test_phase_description(self):
        pack = minimal_pack()
        texts = collect_text_fields(pack)
        assert "Plan the approach." in texts

    def test_phase_checkpoint(self):
        pack = minimal_pack()
        texts = collect_text_fields(pack)
        assert "Plan approved." in texts

    def test_phase_prompts(self):
        pack = minimal_pack()
        texts = collect_text_fields(pack)
        assert "Make a plan." in texts

    def test_phase_anti_patterns(self):
        pack = minimal_pack()
        texts = collect_text_fields(pack)
        assert "Rushing ahead." in texts

    def test_escalation_rules(self):
        pack = minimal_pack(escalation_rules=["Rule 1.", "Rule 2."])
        texts = collect_text_fields(pack)
        assert "Rule 1." in texts
        assert "Rule 2." in texts

    def test_required_inputs(self):
        pack = minimal_pack(required_inputs=["input A", "input B"])
        texts = collect_text_fields(pack)
        assert "input A" in texts
        assert "input B" in texts

    def test_missing_phase_fields_default_to_empty(self):
        pack = minimal_pack()
        pack["phases"] = [
            {"name": "empty_phase"},  # no description, checkpoint, prompts, anti_patterns
        ]
        texts = collect_text_fields(pack)
        assert "empty_phase" not in texts  # name is not a text field here

    def test_non_dict_phase_skipped(self):
        pack = minimal_pack()
        pack["phases"] = ["not a dict", 123, None]
        # Should not raise, just skip invalid entries
        texts = collect_text_fields(pack)
        assert "not a dict" not in texts

    def test_numeric_values_coerced_to_string(self):
        pack = minimal_pack()
        pack["mental_model"] = 42
        texts = collect_text_fields(pack)
        assert "42" in texts

    def test_empty_phases_list(self):
        pack = minimal_pack(phases=[])
        texts = collect_text_fields(pack)
        # mental_model, required_inputs, and escalation_rules are still present
        assert "Think step by step." in texts
        assert "task description" in texts
        assert "Escalate on error." in texts


# ---------------------------------------------------------------------------
# parse_skill_frontmatter
# ---------------------------------------------------------------------------

class TestParseSkillFrontmatter:
    def test_no_frontmatter(self):
        text = "Some body text.\n\n## Section"
        fm, body = parse_skill_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_empty_frontmatter(self):
        text = "---\n---"
        fm, body = parse_skill_frontmatter(text)
        assert fm == {}
        assert body == ""

    def test_valid_frontmatter(self):
        text = "---\nname: Test Skill\nevidence: It works.\n---\nBody content."
        fm, body = parse_skill_frontmatter(text)
        assert fm["name"] == "Test Skill"
        assert fm["evidence"] == "It works."
        assert body == "Body content."

    def test_frontmatter_with_multiple_fields(self):
        text = "---\nname: My Skill\nconfidence: tested\nfailure_cases:\n  - case1\n  - case2\n---\nBody."
        fm, body = parse_skill_frontmatter(text)
        assert fm["name"] == "My Skill"
        assert fm["confidence"] == "tested"
        assert fm["failure_cases"] == ["case1", "case2"]

    def test_frontmatter_malformed_yaml_skipped(self):
        text = "---\nname: Test\n  bad indent: value\n---\nBody."
        fm, body = parse_skill_frontmatter(text)
        assert fm == {}  # malformed frontmatter yields empty dict
        assert "Body." in body

    def test_no_closing_dashes(self):
        text = "---\nname: Test\nNo closing delimiter."
        fm, body = parse_skill_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_body_stripped_of_leading_whitespace(self):
        text = "---\nname: Test\n---\n  Body text."
        _, body = parse_skill_frontmatter(text)
        # .strip() removes leading/trailing whitespace from the body
        assert body == "Body text."

    def test_empty_string(self):
        fm, body = parse_skill_frontmatter("")
        assert fm == {}
        assert body == ""


# ---------------------------------------------------------------------------
# sections_to_phases
# ---------------------------------------------------------------------------

class TestSectionsToPhases:
    def test_no_sections(self):
        body = "Just plain text without headers."
        phases = sections_to_phases(body)
        assert phases == []

    def test_single_section(self):
        body = "## Planning\n\nMake a plan.\n\n## Execution\n\nDo it."
        phases = sections_to_phases(body)
        assert len(phases) == 2
        assert phases[0]["name"] == "planning"
        assert phases[0]["description"] == "Make a plan."
        assert phases[1]["name"] == "execution"
        assert phases[1]["description"] == "Do it."

    def test_section_with_multiline_content(self):
        body = "## Phase1\n\nLine one.\nLine two.\n\nLine three."
        phases = sections_to_phases(body)
        assert phases[0]["description"] == "Line one.\nLine two.\n\nLine three."

    def test_meta_sections_skipped(self):
        body = (
            "## overview\n\nThis is overview.\n\n"
            "## planning\n\nThis is planning.\n\n"
            "## references\n\nSee also."
        )
        phases = sections_to_phases(body)
        names = [p["name"] for p in phases]
        assert "overview" not in names
        assert "references" not in names
        assert "planning" in names

    def test_all_meta_sections_skipped(self):
        meta = ["overview", "when_to_use", "quick_reference",
                "common_rationalizations", "real_world_impact",
                "integration", "pitfalls", "known_issues", "references"]
        body = "\n\n".join(f"## {m}\nContent for {m}." for m in meta)
        phases = sections_to_phases(body)
        assert phases == []

    def test_slugification(self):
        body = "## Step One: Planning\n\nContent."
        phases = sections_to_phases(body)
        # Non-alphanumeric chars (space, colon) each become underscores
        assert phases[0]["name"] == "step_one__planning"

    def test_phase_fields_defaults(self):
        body = "## My Phase\n\nPhase content."
        phase = sections_to_phases(body)[0]
        assert phase["checkpoint"] == ""
        assert phase["anti_patterns"] == []
        assert phase["prompts"] == []

    def test_last_section_without_trailing_header(self):
        body = "## Phase1\n\nContent 1.\n\n## Phase2\n\nContent 2."
        phases = sections_to_phases(body)
        assert len(phases) == 2
        assert phases[1]["name"] == "phase2"

    def test_empty_body(self):
        assert sections_to_phases("") == []

    def test_only_whitespace(self):
        assert sections_to_phases("   \n\n  ") == []

    def test_header_without_content(self):
        body = "## Phase1\n\n## Phase2\n\nContent for phase2."
        phases = sections_to_phases(body)
        assert len(phases) == 2
        assert phases[0]["description"] == ""
        assert phases[1]["description"] == "Content for phase2."
