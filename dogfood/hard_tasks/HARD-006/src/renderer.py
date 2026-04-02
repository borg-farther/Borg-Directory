"""Combines templates and filters for rendering."""
import re
from typing import Dict, Any
from template import Template, TemplateError
from filters import upper_filter, lower_filter, default_filter, capitalize_filter, strip_filter


class Renderer:
    """Combines template rendering with filter application."""

    def __init__(self):
        self.filters = {
            'upper': upper_filter,
            'lower': lower_filter,
            'default': default_filter,
            'capitalize': capitalize_filter,
            'strip': strip_filter,
        }

    def render(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template with filters applied."""
        # Pattern to match {{variable|filter1|filter2:param}}
        pattern = r'{{\s*(\w+)(.*?)}}'

        def replace_with_filters(match):
            var_name = match.group(1)
            filter_part = match.group(2)

            # Get the raw value from context
            value = context.get(var_name)

            # Apply each filter in sequence
            filters_to_apply = self._parse_filters(filter_part)

            for filter_info in filters_to_apply:
                filter_name = filter_info['name']
                filter_args = filter_info['args']

                if filter_name in self.filters:
                    filter_func = self.filters[filter_name]
                    if filter_args:
                        value = filter_func(value, *filter_args)
                    else:
                        value = filter_func(value)

            # Return the filtered value directly
            return str(value)

        # Replace all template expressions with their filtered values
        result = re.sub(pattern, replace_with_filters, template_string)
        return result

    def _parse_filters(self, filter_part: str) -> list:
        """Parse filter part like '|upper|default:Anonymous' into list."""
        filters = []

        if not filter_part.strip():
            return filters

        # Split by | but keep the filter names
        parts = filter_part.split('|')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if ':' in part:
                # Has arguments like 'default:Anonymous'
                filter_name, filter_args_str = part.split(':', 1)
                filter_args = [arg.strip() for arg in filter_args_str.split(',')]
                filters.append({'name': filter_name, 'args': filter_args})
            else:
                filters.append({'name': part, 'args': []})

        return filters


def render(template_string: str, context: Dict[str, Any]) -> str:
    """Render a template string with filters and context."""
    renderer = Renderer()
    return renderer.render(template_string, context)
