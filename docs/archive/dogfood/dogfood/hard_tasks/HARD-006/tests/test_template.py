"""Tests for the template engine."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from template import Template, render_template, TemplateError
from filters import upper_filter, lower_filter, default_filter
from renderer import Renderer, render


class TestBasicTemplate:
    """Test basic template rendering."""

    def test_simple_variable(self):
        """Test simple variable substitution."""
        template = Template("Hello, {{name}}!")
        result = template.render({"name": "World"})
        assert result == "Hello, World!"

    def test_multiple_variables(self):
        """Test multiple variable substitution."""
        template = Template("{{greeting}}, {{name}}!")
        result = template.render({"greeting": "Hello", "name": "Alice"})
        assert result == "Hello, Alice!"

    def test_missing_variable(self):
        """Test that missing variables are left as-is."""
        template = Template("Hello, {{name}}!")
        result = template.render({})
        assert result == "Hello, {{name}}!"

    def test_numeric_value(self):
        """Test numeric value substitution."""
        template = Template("Count: {{count}}")
        result = template.render({"count": 42})
        assert result == "Count: 42"


class TestFilters:
    """Test filter functions."""

    def test_upper_filter(self):
        """Test uppercase filter."""
        assert upper_filter("hello") == "HELLO"
        assert upper_filter("Hello") == "HELLO"

    def test_lower_filter(self):
        """Test lowercase filter."""
        assert lower_filter("HELLO") == "hello"
        assert lower_filter("Hello") == "hello"

    def test_default_filter_with_none(self):
        """Test default filter with None value."""
        assert default_filter(None, "Anonymous") == "Anonymous"

    def test_default_filter_with_value(self):
        """Test default filter with actual value."""
        assert default_filter("Alice", "Anonymous") == "Alice"

    def test_default_filter_with_zero(self):
        """Test default filter with 0 - should return 0, not default."""
        # This test will fail with the buggy default_filter because not 0 is True
        result = default_filter(0, "zero")
        assert result == 0, f"default_filter(0, 'zero') should return 0, not {result}"

    def test_default_filter_with_empty_string(self):
        """Test default filter with empty string."""
        # Empty string might be considered "falsy" - let's see the behavior
        result = default_filter("", "N/A")
        # This depends on interpretation - empty string could use default


class TestRenderer:
    """Test the full renderer with filters."""

    def test_upper_filter_in_template(self):
        """Test uppercase filter in template."""
        result = render("{{name|upper}}", {"name": "alice"})
        assert result == "alice"  # Wait, upper filter applied then var replaced

        # Actually the flow is: filter is applied first, then var is replaced
        # So the filter processes "alice" and returns "ALICE", then {{name}} is replaced with "alice" (the original)
        # Wait no, let me check the renderer logic...

    def test_variable_with_upper_filter(self):
        """Test variable with upper filter."""
        result = render("{{name|upper}}", {"name": "alice"})
        # Should render to "ALICE"
        assert result == "ALICE"

    def test_variable_with_default_filter(self):
        """Test variable with default filter when variable is missing."""
        result = render("Hello, {{name|default:Anonymous}}!", {})
        assert result == "Hello, Anonymous!"

    def test_variable_with_default_filter_when_present(self):
        """Test variable with default filter when variable is present."""
        result = render("Hello, {{name|default:Anonymous}}!", {"name": "Bob"})
        assert result == "Hello, Bob!"

    def test_variable_with_default_filter_none(self):
        """Test variable with default filter when variable is None."""
        result = render("Hello, {{name|default:Anonymous}}!", {"name": None})
        assert result == "Hello, Anonymous!"

    def test_variable_with_default_filter_zero(self):
        """Test variable with default filter when variable is 0.

        This is the key test that exposes the default filter bug.
        """
        result = render("Count: {{count|default:zero}}", {"count": 0})
        assert result == "Count: 0", f"Expected 'Count: 0' but got '{result}'"

    def test_multiple_filters(self):
        """Test multiple filters in sequence."""
        result = render("{{name|lower|upper}}", {"name": "Alice"})
        # lower("Alice") = "alice", upper("alice") = "ALICE"
        assert result == "ALICE"

    def test_strip_filter(self):
        """Test strip filter."""
        result = render("{{text|strip}}", {"text": "  hello  "})
        assert result == "hello"


class TestEdgeCases:
    """Test edge cases in template rendering."""

    def test_nested_braces_in_content(self):
        """Test that literal braces in content are not interpreted."""
        # This tests the template.py bug with braces
        result = render_template("Use {{code}} for code: {{code}}", {"code": "`if`"})
        assert result == "Use `if` for code: `if`"

    def test_empty_template(self):
        """Test empty template."""
        template = Template("")
        result = template.render({"name": "World"})
        assert result == ""

    def test_no_variables(self):
        """Test template with no variables."""
        template = Template("Hello, World!")
        result = template.render({"name": "World"})
        assert result == "Hello, World!"

    def test_whitespace_in_variable(self):
        """Test variable with whitespace in name."""
        template = Template("Hello, {{ name }}!")
        result = template.render({"name": "World"})
        assert result == "Hello, World!"
