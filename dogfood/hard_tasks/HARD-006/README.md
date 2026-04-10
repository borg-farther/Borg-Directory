# HARD-006: Template Engine Bug

## Task Description
You are debugging a template rendering system that has multiple interacting bugs. Sometimes fixing one bug reveals another. The error may manifest in one file but be caused by another.

## Problem
The template engine has three components:
1. `template.py` - Simple template renderer that replaces `{{var}}` with values
2. `filters.py` - Filter functions (upper, lower, default)
3. `renderer.py` - Combines templates and filters

When rendering templates with filters and missing variables, the system behaves unexpectedly. Multiple bugs interact - fixing one reveals another.

## Your Goal
Find and fix ALL bugs so that all tests pass. There are at least two bugs that interact with each other.

## Files
- `src/template.py` - Template renderer
- `src/filters.py` - Filter functions
- `src/renderer.py` - Combines templates and filters
- `tests/test_template.py` - Test suite

## Expected Behavior
- Templates should render variables correctly
- Filters should be applied properly
- Missing variables with default filters should use the default value
- Raw braces in content should not be interpreted as variables
