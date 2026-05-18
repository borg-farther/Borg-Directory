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
