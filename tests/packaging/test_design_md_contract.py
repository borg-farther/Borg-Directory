from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_root_design_md_exists_and_covers_borg_console_identity() -> None:
    text = _read("DESIGN.md")

    assert text.startswith("---\nversion: alpha")
    assert "name: Borg Control Room" in text
    for phrase in (
        'primary: "#0D1117"',
        'tertiary: "#58A6FF"',
        'success: "#3FB950"',
        'danger: "#F85149"',
        'button-primary:',
        'code-block:',
    ):
        assert phrase in text


def test_root_design_md_preserves_canonical_section_order() -> None:
    text = _read("DESIGN.md")
    sections = [
        "## Overview",
        "## Colors",
        "## Typography",
        "## Layout",
        "## Elevation & Depth",
        "## Shapes",
        "## Components",
        "## Do's and Don'ts",
    ]
    positions = [text.index(section) for section in sections]
    assert positions == sorted(positions)


def test_docs_index_links_design_md_for_agents_and_dashboards() -> None:
    docs_index = _read("docs/README.md")
    landing = _read("docs/landing-page/index.html")

    assert "../DESIGN.md" in docs_index
    assert "visual identity token spec" in docs_index
    assert "Canonical visual tokens live in /DESIGN.md." in landing
