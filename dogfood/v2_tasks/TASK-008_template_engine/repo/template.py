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
