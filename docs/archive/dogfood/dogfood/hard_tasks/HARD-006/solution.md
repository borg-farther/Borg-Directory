# Solution for HARD-006: Template Engine Bug

## Bug 1: Template Renderer Doesn't Escape Braces

In `src/template.py`, the `render` method doesn't escape literal braces in the content. When `{{` appears in the source content but is NOT a variable expression, it gets incorrectly processed.

### Bug 1 Fix (template.py):
Add a method to escape braces before processing, or use a regex that only matches complete `{{var}}` expressions (whitespace-safe).

Actually the real issue is the regex `{{(.*?)}}` is too greedy and doesn't properly handle edge cases like `{{foo}}` followed by ` bar}}`. A better approach is to only match `{{` followed by whitespace or identifier characters.

## Bug 2: Default Filter Doesn't Handle None

In `src/filters.py`, the `default_filter` function doesn't properly handle `None` values:

```python
def default_filter(value, default_value):
    if value is None:  # This works
        return default_value
    if not value:  # BUG: This treats empty string and 0 as falsy!
        return default_value
    return value
```

The second condition `if not value:` causes problems because:
- `not ""` (empty string) returns `True`, so `default_filter("", "N/A")` returns `"N/A"` - might be intentional
- But `not 0` returns `True`, so `default_filter(0, "zero")` returns `"zero"` - which may not be desired

### Bug 2 Fix (filters.py):
Change `if not value:` to properly check for None only:

```python
def default_filter(value, default_value):
    if value is None:
        return default_value
    return value
```

Or if empty string should also trigger default:
```python
def default_filter(value, default_value):
    if value is None or value == "":
        return default_value
    return value
```

## Why Multiple Bugs Interact

When you fix the default filter to handle None properly, templates like `{{name|default:'Anonymous'}}` will correctly show "Anonymous" when name is None. But then you might notice that `{{}}` or malformed expressions cause issues - this is the template.py bug.

The braces issue in template.py can cause `{{name|default:'Anonymous'}}` to be partially processed if there's a `{{` somewhere in the default value string itself.
