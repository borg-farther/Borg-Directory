from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ROOT_FILES = {
    ".dockerignore",
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "Dockerfile",
    "index.json",
    "LICENSE",
    "llms.txt",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "pyproject.toml",
}

ALLOWED_ROOT_DIRS = {
    ".githooks",
    ".github",
    "benchmarks",
    "borg",
    "deploy",
    "docs",
    "eval",
    "examples",
    "scripts",
    "tests",
}

ROOT_SCRIPT_RE = re.compile(
    r"^(audit|check|debug|inspect|measure|cleanup|verify|run)_.*\.(py|sh)$"
)


def _git_ls_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - non-git sdists
        pytest.skip(f"git tracked-file inventory unavailable: {exc}")
    return [line for line in result.stdout.splitlines() if line]


def test_public_root_contains_only_package_surface() -> None:
    """The GitHub root should look like an installable package, not a scratchpad."""
    tracked = _git_ls_files()

    root_files = sorted(path for path in tracked if "/" not in path)
    root_dirs = sorted({path.split("/", 1)[0] for path in tracked if "/" in path})

    assert root_files == sorted(ALLOWED_ROOT_FILES)
    assert root_dirs == sorted(ALLOWED_ROOT_DIRS)


def test_generated_and_internal_artifacts_are_not_tracked_at_root() -> None:
    tracked = _git_ls_files()
    root_files = [path for path in tracked if "/" not in path]

    assert ".coverage" not in root_files
    assert not any(path.endswith(".pdf") for path in root_files)
    assert not any(path.startswith("test_") and path.endswith(".py") for path in root_files)
    assert not any(ROOT_SCRIPT_RE.match(path) for path in root_files)


def test_security_workflow_dependency_audit_is_fail_closed() -> None:
    workflow = (ROOT / ".github" / "workflows" / "security-gates.yml").read_text(encoding="utf-8")
    assert "pip-audit || true" not in workflow
    assert "pip-audit" in workflow


def test_archive_has_a_public_boundary_note() -> None:
    archive_readme = (ROOT / "docs" / "archive" / "README.md").read_text(encoding="utf-8")
    assert "not the current first-user product surface" in archive_readme
    assert "root-pdfs/" in archive_readme
    assert "root-scripts/" in archive_readme
    assert "root-tests/" in archive_readme


def test_public_first_user_docs_have_no_unrendered_placeholders() -> None:
    for relative_path in [
        "docs/QUICKSTART.md",
        "docs/TRYING_BORG.md",
        "docs/ONBOARDING.md",
    ]:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "{PRIMING_PARAGRAPH}" not in text
        assert "borg_rescue" in text
        assert "borg_observe" in text


def test_public_positioning_uses_plain_failure_memory_language() -> None:
    """Public/current surfaces should not sound like vague AI-product slop."""
    active_surfaces = [
        "README.md",
        "pyproject.toml",
        "llms.txt",
        "AGENTS.md",
        "CLAUDE.md",
        ".github/copilot-instructions.md",
        "borg/cli.py",
        "borg/integrations/http_server.py",
        "borg/core/convert.py",
        "borg/core/openclaw_converter.py",
        "borg/db/embeddings.py",
        "borg/seeds_data/borg/SKILL.md",
        "borg/seeds_data/borg-autopilot/SKILL.md",
        "examples/openclaw-skill/SKILL.md",
        "examples/skills/borg/SKILL.md",
        "examples/skills/guild-autopilot/SKILL.md",
        "docs/SECURITY_HARDENING_BASELINE.md",
        "docs/PRIVACY_MODEL.md",
    ]
    banned_snippets = [
        "Semantic reasoning cache",
        "Collective memory MCP server",
        "collective memory MCP server",
        "collective memory",
        "shared collective memory",
        "collective-intelligence-cache",
        "collective agent intelligence",
        "collective intelligence for AI agents",
        "Collective Intelligence for AI Agents",
        "battle-tested workflows from collective agent intelligence",
        "thousands of agents",
        "guild-packs[embeddings]",
        "action=\"advance\"",
        "test-recovery",
        "Zero-config",
        "zero-config",
        "magic success-rate booster",
        "god-tier",
        "world-class",
    ]

    for relative_path in active_surfaces:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "failure memory" in text.lower(), relative_path
        for snippet in banned_snippets:
            assert snippet not in text, f"{snippet!r} leaked into {relative_path}"


def test_agent_readable_surfaces_state_identity_safety_and_rollout_boundary() -> None:
    """Agent-facing files are production surfaces, not generic boilerplate."""
    agent_files = [
        "AGENTS.md",
        "CLAUDE.md",
        ".github/copilot-instructions.md",
        "llms.txt",
    ]
    forbidden_ops = [
        "systemctl restart hermes-gateway",
        "kill hermes-gateway",
        "pkill hermes",
        "kill -9",
    ]

    for relative_path in agent_files:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "agent-borg" in text, relative_path
        assert "borg-mcp" in text, relative_path
        assert "borg-farther/Borg-Directory" in text, relative_path
        assert "first-10" in text.lower(), relative_path
        assert "public self-serve" in text.lower(), relative_path
        for forbidden in forbidden_ops:
            assert forbidden not in text, f"{forbidden!r} leaked into {relative_path}"
