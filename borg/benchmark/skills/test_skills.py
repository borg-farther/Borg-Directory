#!/usr/bin/env python3
"""
Test suite for Borg lean skill format validation.
Validates: frontmatter, line count, required sections, trigger quality.
"""

import re
from pathlib import Path

SKILLS_DIR = Path("/root/hermes-workspace/borg/borg/benchmark/skills")
REQUIRED_SECTIONS = ["Principles", "Output Format", "Edge Cases", "Example", "Recovery"]
MAX_LINES = 30


def parse_frontmatter(content: str) -> dict:
    """Extract name and trigger from YAML frontmatter."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    frontmatter = match.group(1)
    result = {}
    for line in frontmatter.split("\n"):
        if ": " in line:
            key, val = line.split(": ", 1)
            result[key.strip()] = val.strip().strip('"')
    return result


def parse_sections(content: str) -> list[str]:
    """Extract all ## section headers from content."""
    return re.findall(r"^## (.+)$", content, re.MULTILINE)


def count_non_frontmatter_lines(content: str) -> int:
    """Count non-blank lines after frontmatter (excludes blank lines for realism)."""
    match = re.search(r"^---\n.*?\n---\n", content, re.DOTALL)
    if match:
        remaining = content[match.end():]
    else:
        remaining = content
    lines = [l for l in remaining.split("\n") if l.strip()]
    return len(lines)


def test_skill_structure(skill_path: Path) -> dict:
    """Test a single skill file for structural validity."""
    content = skill_path.read_text()
    errors = []

    # Parse frontmatter
    fm = parse_frontmatter(content)
    if "name" not in fm:
        errors.append("Missing 'name' in frontmatter")
    if "trigger" not in fm:
        errors.append("Missing 'trigger' in frontmatter")
    elif len(fm.get("trigger", "")) < 10:
        errors.append("Trigger too short — must be one line describing WHEN to fire")
    elif '"' in fm.get("trigger", "") and fm["trigger"].count('"') != 2:
        errors.append("Trigger should be one line, no internal quotes breaking YAML")

    # Check required sections
    sections = parse_sections(content)
    for req in REQUIRED_SECTIONS:
        if req not in sections:
            errors.append(f"Missing '## {req}' section")

    # Check line count (excluding frontmatter)
    line_count = count_non_frontmatter_lines(content)
    if line_count > MAX_LINES:
        errors.append(f"Skill has {line_count} lines, max allowed is {MAX_LINES}")

    # Check Principles has reasoning (not just steps)
    principles_match = re.search(r"## Principles\s+(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if principles_match:
        principles_text = principles_match.group(1)
        # Check for numbered steps pattern (anti-pattern)
        if re.search(r"^\d+\.", principles_text, re.MULTILINE):
            # Check if each item has reasoning (contains because, since, reason, or is long)
            lines = [l.strip() for l in principles_text.split("\n") if l.strip() and not l.strip().startswith("#")]
            for line in lines:
                if line and len(line) < 30 and not any(w in line.lower() for w in ["because", "since", "reason", "why"]):
                    errors.append(f"Principle may be a step, not reasoning: {line[:50]}")
                    break

    return {
        "file": skill_path.name,
        "passed": len(errors) == 0,
        "errors": errors,
        "line_count": line_count,
        "sections_found": sections,
    }


def main():
    """Run all skill validation tests."""
    skill_files = sorted(SKILLS_DIR.glob("*.md"))
    if not skill_files:
        print(f"No skill files found in {SKILLS_DIR}")
        return

    print(f"Testing {len(skill_files)} skill files in {SKILLS_DIR}\n")

    all_passed = True
    results = []
    for skill_path in skill_files:
        result = test_skill_structure(skill_path)
        results.append(result)
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"{status}: {result['file']} ({result['line_count']} lines)")
        if not result["passed"]:
            all_passed = False
            for err in result["errors"]:
                print(f"  → {err}")

    print(f"\n{'='*50}")
    if all_passed:
        print(f"All {len(results)} skills passed validation!")
    else:
        failed = [r["file"] for r in results if not r["passed"]]
        print(f"FAILED: {', '.join(failed)}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
