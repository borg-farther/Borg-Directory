"""Simple template renderer that replaces {{var}} with values."""
import re
from typing import Dict, Any


class TemplateError(Exception):
    """Raised when template rendering fails."""
    pass


class Template:
    def __init__(self, template_string: str):
        self.template_string = template_string

    def render(self, context: Dict[str, Any]) -> str:
        """Render the template with the given context."""
        result = self.template_string

        # BUG: This regex matches too greedily and doesn't properly handle
        # edge cases. It can match things like "{{" without closing "}}"
        # The pattern {{(.*?)}} with re.DOTALL allows newlines but also
        # can match across intended boundaries
        pattern = r'{{(.*?)}}'

        matches = re.findall(pattern, result, re.DOTALL)

        for match in matches:
            # Get the full match including braces for replacement
            full_match = '{{' + match + '}}'
            key = match.strip()

            if key in context:
                value = context[key]
                # Apply the value
                result = result.replace(full_match, str(value))
            else:
                # Leave as-is if not in context
                pass

        return result


def render_template(template_string: str, context: Dict[str, Any]) -> str:
    """Render a template string with the given context."""
    template = Template(template_string)
    return template.render(context)
