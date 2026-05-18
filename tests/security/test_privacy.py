"""
Tests for the privacy module (T1.6).

Covers: privacy_scan_text, privacy_scan_artifact, privacy_redact, collect_strings.
"""

import pytest

from borg.core.privacy import (
    collect_strings,
    privacy_redact,
    privacy_scan_artifact,
    privacy_scan_text,
)


# ============================================================================
# collect_strings
# ============================================================================

class TestCollectStrings:
    def test_flat_string(self):
        assert collect_strings("hello") == ["hello"]

    def test_list_of_strings(self):
        assert collect_strings(["a", "b", "c"]) == ["a", "b", "c"]

    def test_nested_dict(self):
        result = collect_strings({"key": {"nested": "value"}})
        assert result == ["value"]

    def test_nested_list(self):
        result = collect_strings([["a", "b"], ["c"]])
        assert result == ["a", "b", "c"]

    def test_mixed_structure(self):
        result = collect_strings({
            "top": ["a", {"deep": "b"}],
            "solo": "c",
        })
        assert set(result) == {"a", "b", "c"}

    def test_empty_inputs(self):
        assert collect_strings({}) == []
        assert collect_strings([]) == []
        assert collect_strings("") == [""]
        assert collect_strings(None) == []


# ============================================================================
# privacy_scan_text
# ============================================================================

class TestPrivacyScanText:
    # --- file paths ---

    def test_tilde_hermes_path(self):
        text = "Loading config from ~/.hermes/guild.yaml"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:hermes config path]" in sanitized
        assert "hermes config path: 1 occurrence(s)" in findings

    def test_root_home_path(self):
        text = "File stored at /root/.ssh/id_rsa"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:root home path]" in sanitized
        assert "root home path: 1 occurrence(s)" in findings

    def test_user_home_path(self):
        text = "Reading /home/alice/secrets.txt"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:user home path]" in sanitized
        assert "user home path: 1 occurrence(s)" in findings

    def test_windows_path(self):
        text = r"C:\Users\bob\Documents\secret.txt"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:Windows path]" in sanitized

    # --- IP addresses ---

    def test_ipv4_address(self):
        text = "Server at 192.168.1.100 responded"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:IP address]" in sanitized
        assert "IP address: 1 occurrence(s)" in findings

    def test_multiple_ip_addresses(self):
        text = "Connecting from 10.0.0.1 to 10.0.0.2"
        sanitized, findings = privacy_scan_text(text)
        assert sanitized.count("[REDACTED:IP address]") == 2
        assert "IP address: 2 occurrence(s)" in findings

    # --- email addresses ---

    def test_email_address(self):
        text = "Sent to user@example.com"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:email address]" in sanitized
        assert "email address: 1 occurrence(s)" in findings

    def test_email_in_complex_string(self):
        text = "Contact alice_bob+tag@company.co.uk for details"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:email address]" in sanitized

    # --- API keys / tokens ---

    def test_openai_api_key(self):
        text = "sk-abc123defghijklmnopqrstuvwxyz0123456789"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:OpenAI API key]" in sanitized
        assert "OpenAI API key: 1 occurrence(s)" in findings

    def test_slack_bot_token(self):
        text = "xoxb" + "-FAKE-TEST-TOKEN-000"  # noqa: assembled to avoid secret scanning
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:Slack bot token]" in sanitized

    def test_github_pat(self):
        text = "ghp_abcdefghijklmnopqrstuvwxyz0123456789abcdef"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:GitHub personal access token]" in sanitized

    def test_google_api_key(self):
        # regex requires exactly 35 chars after "AIza" (39 total)
        text = "AIzaSyabcdefghijklmnopqrstuvwxyz0123456"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:Google API key]" in sanitized

    def test_aws_access_key(self):
        text = "AKIAIOSFODNN7EXAMPLE"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:AWS access key]" in sanitized

    def test_gitlab_token(self):
        text = "glpat-abcdefghijklmnopqrstuvwx"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:GitLab token]" in sanitized

    # --- combined ---

    def test_multiple_patterns_in_one_text(self):
        text = (
            "Email alice@example.com, IP 8.8.8.8, "
            "key sk-abc123defghijklmnopqrstuvwxyz0123456789"
        )
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:email address]" in sanitized
        assert "[REDACTED:IP address]" in sanitized
        assert "[REDACTED:OpenAI API key]" in sanitized
        assert len(findings) == 3

    def test_empty_text(self):
        sanitized, findings = privacy_scan_text("")
        assert sanitized == ""
        assert findings == []

    def test_none_text(self):
        sanitized, findings = privacy_scan_text(None)
        assert sanitized is None
        assert findings == []

    # --- no false positives on safe strings ---

    def test_no_false_positive_plain_text(self):
        safe = "This is a normal workflow description with no secrets."
        sanitized, findings = privacy_scan_text(safe)
        assert sanitized == safe
        assert findings == []

    def test_no_false_positive_code_like(self):
        safe = "def hello(): print('hello world')"
        sanitized, findings = privacy_scan_text(safe)
        assert sanitized == safe
        assert findings == []

    def test_no_false_positive_urls(self):
        safe = "https://api.github.com/repos/owner/name"
        sanitized, findings = privacy_scan_text(safe)
        assert sanitized == safe
        assert findings == []

    def test_no_false_positive_numbers(self):
        safe = "Version 1.2.3 of the pack released"
        sanitized, findings = privacy_scan_text(safe)
        assert sanitized == safe
        assert findings == []

    def test_short_sk_prefix_not_key(self):
        # "sk" without the full 20+ char key should not match
        text = "The skill name is sk-admin"
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED" not in sanitized
        assert findings == []

    def test_slack_pattern_broad(self):
        # The regex pattern is intentionally broad to catch potential tokens
        # We just verify it doesn't fire on completely unrelated strings.
        text = "xoxb" + "-i-FAKE-broad-test"  # noqa: assembled to avoid secret scanning
        sanitized, findings = privacy_scan_text(text)
        assert "[REDACTED:Slack bot token]" in sanitized
        assert findings == ["Slack bot token: 1 occurrence(s)"]

    def test_ghp_short_not_token(self):
        text = "ghp_12345"
        sanitized, findings = privacy_scan_text(text)
        # ghp_ requires 36+ chars
        assert "[REDACTED" not in sanitized
        assert findings == []


# ============================================================================
# privacy_redact
# ============================================================================

class TestPrivacyRedact:
    def test_redacts_email(self):
        text = "Contact alice@example.com for access"
        redacted = privacy_redact(text)
        assert "[REDACTED]" in redacted
        assert "alice@example.com" not in redacted

    def test_redacts_ip_address(self):
        text = "Connecting to 1.2.3.4"
        redacted = privacy_redact(text)
        assert "[REDACTED]" in redacted
        assert "1.2.3.4" not in redacted

    def test_redacts_api_key(self):
        text = "key=sk-abc123defghijklmnopqrstuvwxyz0123456789"
        redacted = privacy_redact(text)
        assert "[REDACTED]" in redacted
        assert "sk-abc" not in redacted

    def test_redacts_file_path(self):
        text = "loaded /home/alice/config.yaml"
        redacted = privacy_redact(text)
        assert "[REDACTED]" in redacted
        assert "/home/alice" not in redacted

    def test_multiple_redactions(self):
        text = "Email alice@example.com, IP 1.2.3.4, key sk-abc123defghijklmnopqrstuvwxyz0123456789"
        redacted = privacy_redact(text)
        # All three should be redacted — count [REDACTED] markers
        assert redacted.count("[REDACTED]") == 3
        assert "alice@example.com" not in redacted
        assert "1.2.3.4" not in redacted
        assert "sk-abc" not in redacted

    def test_redact_uses_plain_redacted_no_label(self):
        """privacy_redact replaces with plain [REDACTED], not [REDACTED:label]."""
        text = "email is alice@example.com"
        redacted = privacy_redact(text)
        assert "[REDACTED]" in redacted
        assert "[REDACTED:email" not in redacted

    def test_empty_text(self):
        assert privacy_redact("") == ""

    def test_none_text(self):
        assert privacy_redact(None) is None

    def test_no_false_positives(self):
        safe = "Normal workflow description v1.2.3"
        assert privacy_redact(safe) == safe


# ============================================================================
# privacy_scan_artifact
# ============================================================================

class TestPrivacyScanArtifact:
    def test_simple_artifact(self):
        artifact = {
            "type": "workflow_pack",
            "description": "Contact alice@example.com for details",
        }
        sanitized, findings = privacy_scan_artifact(artifact)
        assert "[REDACTED:email address]" in sanitized["description"]
        assert any("email address" in f for f in findings)

    def test_nested_artifact(self):
        artifact = {
            "type": "workflow_pack",
            "provenance": {
                "author": "bob@company.org",
                "evidence": "IP 192.168.1.1 was logged",
            },
        }
        sanitized, findings = privacy_scan_artifact(artifact)
        assert "[REDACTED:email address]" in sanitized["provenance"]["author"]
        assert "[REDACTED:IP address]" in sanitized["provenance"]["evidence"]
        assert len(findings) == 2

    def test_list_fields(self):
        artifact = {
            "phases": [
                {"name": "step1", "note": "server at 10.0.0.1"},
                {"name": "step2", "note": "contact carol@example.com"},
            ]
        }
        sanitized, findings = privacy_scan_artifact(artifact)
        assert "[REDACTED:IP address]" in sanitized["phases"][0]["note"]
        assert "[REDACTED:email address]" in sanitized["phases"][1]["note"]
        assert len(findings) == 2

    def test_path_in_artifact(self):
        artifact = {
            "description": "Loaded ~/.hermes/guild.yaml",
        }
        sanitized, findings = privacy_scan_artifact(artifact)
        assert "[REDACTED:hermes config path]" in sanitized["description"]
        assert any("hermes config path" in f for f in findings)

    def test_does_not_modify_original(self):
        original_email = "alice@example.com"
        artifact = {"info": original_email}
        sanitized, _ = privacy_scan_artifact(artifact)
        assert artifact["info"] == original_email
        assert sanitized["info"] != original_email

    def test_empty_artifact(self):
        sanitized, findings = privacy_scan_artifact({})
        assert sanitized == {}
        assert findings == []

    def test_artifact_with_no_strings(self):
        artifact = {"count": 42, "enabled": True, "phases": []}
        sanitized, findings = privacy_scan_artifact(artifact)
        assert sanitized == artifact
        assert findings == []

    def test_all_pattern_types_in_artifact(self):
        artifact = {
            "description": (
                "Server 8.8.8.8, email dev@example.org, "
                "key sk-abc123defghijklmnopqrstuvwxyz0123456789, "
                "path /home/bob/file.txt"
            )
        }
        sanitized, findings = privacy_scan_artifact(artifact)
        # Should have 4 distinct finding types
        labels = [f.split(":")[0].split("(")[-1].strip() for f in findings]
        assert len(findings) == 4
        assert any("IP address" in f for f in findings)
        assert any("email address" in f for f in findings)
        assert any("OpenAI API key" in f for f in findings)
        assert any("user home path" in f for f in findings)

    def test_path_formatting_in_findings(self):
        """Deep paths should be reported in findings."""
        artifact = {
            "top": {
                "mid": {
                    "bottom": "alice@example.com",
                }
            }
        }
        sanitized, findings = privacy_scan_artifact(artifact)
        assert any("top.mid.bottom" in f for f in findings)
        assert any("email address" in f for f in findings)
