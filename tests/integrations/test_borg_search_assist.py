from __future__ import annotations

import importlib

import pytest


EXACT_PSYCOPG2_MESSAGE = (
    "pip install psycopg2 fails with pg_config executable not found - how do I fix it?"
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("error TS2307: Cannot find module './thing'", "typescript-error"),
        ("Docker container cannot resolve postgres hostname", "docker-error"),
        ("why does npm throw EADDRINUSE on startup?", "nodejs-error"),
    ],
)
def test_existing_ecosystem_classes_stay_unchanged(text: str, expected: str) -> None:
    assist = importlib.import_module("borg.integrations.borg_search_assist")

    assert assist.detect_error_class(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (EXACT_PSYCOPG2_MESSAGE, "python-package-build-error"),
        (
            "psycopg2 fails with pg_config executable not found during pip install",
            "python-package-build-error",
        ),
        (
            "getting ModuleNotFoundError when I run python app.py",
            "python-import-error",
        ),
        (
            "why does pytest throw AssertionError in test_user_login?",
            "python-error",
        ),
        (
            "cargo build fails with error[E0382] borrow of moved value",
            "rust-error",
        ),
    ],
)
def test_conversational_error_reports_require_phrase_and_technical_token(
    text: str, expected: str
) -> None:
    assist = importlib.import_module("borg.integrations.borg_search_assist")

    assert assist.detect_error_class(text) == expected


def test_raw_traceback_is_classified_without_conversation_words() -> None:
    assist = importlib.import_module("borg.integrations.borg_search_assist")
    traceback_text = """
Traceback (most recent call last):
  File "app.py", line 2, in <module>
    import flask
ModuleNotFoundError: No module named 'flask'
"""

    assert assist.detect_error_class(traceback_text) == "python-import-error"


@pytest.mark.parametrize(
    "text",
    [
        "hi good morning, all good?",
        "good morning — how are you doing today?",
        "Last login: Fri May 15 10:00:00 on pts/0\nWelcome to Ubuntu 24.04 LTS\n0 failed login attempts since last login",
        "status?",
        "what is the current status of the rollout?",
        "what is psycopg2 and when should I use it?",
        "how do I fix it?",
        "can you explain what pg_config is used for?",
    ],
)
def test_benign_text_does_not_match(text: str) -> None:
    assist = importlib.import_module("borg.integrations.borg_search_assist")

    assert assist.detect_error_class(text) is None


def test_pre_llm_no_match_does_not_call_search(monkeypatch, tmp_path) -> None:
    assist = importlib.import_module("borg.integrations.borg_search_assist")
    monkeypatch.setattr(assist, "LOG_PATH", tmp_path / "recipe.log")
    monkeypatch.setattr(assist, "_ensure_borg_importable", lambda: pytest.fail("no search expected"))

    result = assist.on_pre_llm_call(
        session_id="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        user_message="hi good morning, all good?",
    )

    assert result is None
    assert "no error class matched" in (tmp_path / "recipe.log").read_text(encoding="utf-8")


def test_pre_llm_search_uses_detected_error_class(monkeypatch, tmp_path) -> None:
    assist = importlib.import_module("borg.integrations.borg_search_assist")
    monkeypatch.setattr(assist, "LOG_PATH", tmp_path / "recipe.log")
    monkeypatch.setattr(assist, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(assist, "_ensure_borg_importable", lambda: True)
    monkeypatch.setattr(assist, "find_local_traces", lambda *args, **kwargs: pytest.fail("local fallback not expected"))

    seen: dict[str, str] = {}

    class FakeTop:
        trace_id = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
        preview = "install libpq development headers before building psycopg2 from source"

    class FakeResults:
        count = 1
        results = [FakeTop()]

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def search(self, *, error_class: str, limit: int):
            seen["error_class"] = error_class
            seen["limit"] = str(limit)
            return FakeResults()

    class FakeClientFactory:
        @staticmethod
        def from_config():
            return FakeClient()

    monkeypatch.setattr(assist, "Client", FakeClientFactory)

    result = assist.on_pre_llm_call(
        session_id="fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
        user_message=EXACT_PSYCOPG2_MESSAGE,
    )

    assert seen == {"error_class": "python-package-build-error", "limit": "3"}
    assert result is not None
    assert "python-package-build-error" in result["context"]
    assert "hint_emitted=1" in (tmp_path / "recipe.log").read_text(encoding="utf-8")


def test_pre_llm_falls_back_to_local_trace_when_federation_empty(monkeypatch, tmp_path) -> None:
    assist = importlib.import_module("borg.integrations.borg_search_assist")
    monkeypatch.setattr(assist, "LOG_PATH", tmp_path / "recipe.log")
    monkeypatch.setattr(assist, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(assist, "_ensure_borg_importable", lambda: True)

    class EmptyResults:
        count = 0
        results = []

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def search(self, *, error_class: str, limit: int):
            assert error_class == "python-package-build-error"
            assert limit == 3
            return EmptyResults()

    class FakeClientFactory:
        @staticmethod
        def from_config():
            return FakeClient()

    monkeypatch.setattr(assist, "Client", FakeClientFactory)
    monkeypatch.setattr(
        assist,
        "find_local_traces",
        lambda user_msg, error_class, limit=3: [
            {
                "id": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "approach_summary": "install the PostgreSQL development headers so pg_config is available before building psycopg2",
            }
        ],
    )

    result = assist.on_pre_llm_call(
        session_id="fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
        user_message=EXACT_PSYCOPG2_MESSAGE,
    )

    assert result is not None
    assert "prior local trace" in result["context"]
    assert "PostgreSQL development headers" in result["context"]
    assert "local_search_id" in (tmp_path / "state.json").read_text(encoding="utf-8")
    assert "local fallback" in (tmp_path / "recipe.log").read_text(encoding="utf-8")


def test_repo_canonical_shim_imports_repo_plugin_module() -> None:
    shim = importlib.import_module("borg.integrations.hermes_plugins.borg_search_assist")

    assert shim.detect_error_class(EXACT_PSYCOPG2_MESSAGE) == "python-package-build-error"
    assert callable(shim.register)

