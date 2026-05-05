"""Structured privacy scanner tests for privacy-safe learning atoms."""

from borg.core.privacy import privacy_scan_structured, privacy_risk_score


def test_structured_scan_detects_email_and_blocks_shared_export():
    result = privacy_scan_structured("Contact alice@example.com for access")

    assert result.blocked is True
    assert result.risk_score >= 70
    assert any(f.kind == "email" for f in result.findings)
    assert "alice@example.com" not in result.sanitized


def test_structured_scan_detects_database_url_as_critical_secret():
    result = privacy_scan_structured("DATABASE_URL=postgres://user:pass@db.internal/app")

    assert result.blocked is True
    assert result.risk_score >= 100
    assert any(f.kind == "database_url" and f.severity == "critical" for f in result.findings)
    assert "pass@" not in result.sanitized


def test_structured_scan_detects_bearer_token_as_critical_secret():
    result = privacy_scan_structured("Authorization: Bearer abcdefghijklmnopqrstuvwxyz1234567890")

    assert result.blocked is True
    assert any(f.kind == "bearer_token" for f in result.findings)
    assert "abcdefghijklmnopqrstuvwxyz" not in result.sanitized


def test_structured_scan_detects_high_entropy_secret():
    result = privacy_scan_structured("token=KJH9sdf8SDF7sdf6ASDF5sdf4ASDF3sdf2ZXCVBNMqwerty")

    assert result.blocked is True
    assert any(f.kind == "high_entropy" for f in result.findings)


def test_structured_scan_safe_text_low_risk():
    result = privacy_scan_structured("TypeError from optional config value; validate before split")

    assert result.blocked is False
    assert result.risk_score == 0
    assert result.findings == []


def test_privacy_risk_score_scans_nested_objects():
    obj = {"learning": {"worked": "email bob@example.com", "avoid": ["cat ~/.ssh/id_rsa"]}}

    result = privacy_risk_score(obj)

    assert result.blocked is True
    assert result.risk_score >= 70
    assert "bob@example.com" not in str(result.sanitized)
