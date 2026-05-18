#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/template.py << 'PYEOF'
import re

class TemplateEngine:
    """Simple template engine with variable substitution and includes."""
    
    def __init__(self):
        self.templates = {}
    
    def register(self, name, content):
        """Register a named template."""
        self.templates[name] = content
    
    def render(self, template_str, context):
        """Render a template string with the given context."""
        # Replace {{ var }} with context values
        result = template_str
        
        # Handle includes first: {% include "name" %}
        result = self._process_includes(result, context)
        
        # Then substitute variables
        result = self._substitute(result, context)
        
        return result
    
    def _process_includes(self, text, context):
        """Process {% include "name" %} directives."""
        pattern = r'\{%\s*include\s+"(\w+)"\s*%\}'
        
        def replace_include(match):
            name = match.group(1)
            if name not in self.templates:
                return f"[MISSING: {name}]"
            # BUG: doesn't render the included template with context
            # Just inserts raw template text, variables not substituted
            return self.templates[name]
        
        return re.sub(pattern, replace_include, text)
    
    def _substitute(self, text, context):
        """Replace {{ var }} with context values."""
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        
        def replace_var(match):
            var_name = match.group(1)
            if var_name in context:
                return str(context[var_name])
            # BUG: returns the raw template tag instead of empty string
            return match.group(0)
        
        return re.sub(pattern, replace_var, text)
PYEOF

cat > repo/test_template.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from template import TemplateEngine

def test_simple_substitution():
    e = TemplateEngine()
    result = e.render("Hello {{ name }}!", {"name": "World"})
    assert result == "Hello World!", f"Got: {result}"

def test_include_with_variables():
    """Included templates should have their variables substituted."""
    e = TemplateEngine()
    e.register("header", "<h1>{{ title }}</h1>")
    
    result = e.render('{% include "header" %}\n<p>{{ body }}</p>', 
                      {"title": "Welcome", "body": "Content here"})
    assert result == "<h1>Welcome</h1>\n<p>Content here</p>", f"Got: {result}"

def test_missing_var_empty():
    """Missing variables should render as empty string, not raw tag."""
    e = TemplateEngine()
    result = e.render("Value: {{ missing }}", {})
    assert result == "Value: ", f"Got: '{result}'"

def test_nested_include():
    """Include inside an include should work."""
    e = TemplateEngine()
    e.register("inner", "{{ greeting }}")
    e.register("outer", 'Say: {% include "inner" %}!')
    
    result = e.render('{% include "outer" %}', {"greeting": "Hi"})
    assert result == "Say: Hi!", f"Got: '{result}'"

if __name__ == "__main__":
    tests = [test_simple_substitution, test_include_with_variables, test_missing_var_empty, test_nested_include]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            sys.exit(1)
    print("ALL TESTS PASSED")
PYEOF
