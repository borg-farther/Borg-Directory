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


def test_credential_assignment_redacts_value_keeps_name():
    # Compound env-var names defeat the \b-delimited entropy rule; the name is
    # the signal, so the value is redacted regardless of length or entropy.
    for text in (
        "AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLEKEY99",
        "token=shortsecret1",
        "pwd=hunter2x",
        "db_password: changeme123",
        "API_TOKEN=abc-def-123",
    ):
        result = privacy_scan_structured(text)
        assert any(f.kind == "credential_assignment" for f in result.findings), text
        assert result.blocked is True, text
        value = text.split(":", 1)[-1].split("=", 1)[-1].strip()
        assert value not in result.sanitized, text
        assert "[REDACTED:credential_assignment]" in result.sanitized, text


def test_credential_assignment_leaves_code_kwargs_alone():
    for text in (
        "sorted(items, key=lambda x: x.name)",  # bare key= is a code kwarg
        "tokenizer=BertTokenizer.from_pretrained",  # name does not END with token
        "author=jane_smith_2026",  # 'auth' inside 'author' must not fire
        "token=None",  # too short to be a secret
    ):
        result = privacy_scan_structured(text)
        assert not any(f.kind == "credential_assignment" for f in result.findings), text
        assert result.sanitized == text, text


def test_credential_assignment_does_not_double_redact():
    result = privacy_scan_structured("token=KJH9sdf8SDF7sdf6ASDF5sdf4ASDF3sdf2ZXCVBNMqwerty")  # gitleaks:allow — fake fixture
    # The entropy rule owns long high-entropy values; the credential rule must
    # skip the already-redacted placeholder rather than stacking on top of it.
    assert any(f.kind == "high_entropy" for f in result.findings)
    assert not any(f.kind == "credential_assignment" for f in result.findings)
    assert result.sanitized == "token=[REDACTED:high_entropy]"


def test_privacy_risk_score_scans_nested_objects():
    obj = {"learning": {"worked": "email bob@example.com", "avoid": ["cat ~/.ssh/id_rsa"]}}

    result = privacy_risk_score(obj)

    assert result.blocked is True
    assert result.risk_score >= 70
    assert "bob@example.com" not in str(result.sanitized)
