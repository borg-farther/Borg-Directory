"""Prompt injection sanitizer for retrieval output (B1 / G4).

Borg feeds stored trace text back to calling agents. A malicious trace
could contain instructions that hijack the reading agent. This module
wraps trace text in content boundaries and strips known injection
patterns before the result leaves find_relevant().

Not perfect  no regex sanitizer is  but raises the floor significantly
against naive injection. A prose-level attack surviving this must at
minimum avoid the listed tells and stay under the 4000 char truncation.
"""
import re

_INJECTION_PATTERNS = [
    r'(?i)ignore\s+(all\s+)?previous\s+instructions',
    r'(?i)disregard\s+(all\s+)?(prior|previous|above)',
    r'(?i)system\s*(prompt|message|instruction)s?\s*:',
    r'(?i)override\s+(system|safety|rules)',
    r'(?i)you\s+are\s+now\s+(a|an)\s+\w+',
    r'(?i)new\s+instructions?\s*:',
    r'(?i)forget\s+(everything|all|your\s+instructions)',
    r'(?i)\[/?(system|assistant|user|human)\]',
    r'<\|im_start\|>',
    r'<\|im_end\|>',
    r'(?i)###\s*instruction',
]

_TEXT_FIELDS = (
    'task_description', 'root_cause', 'approach_summary',
    'keywords', 'error_patterns', 'causal_intervention',
)


def sanitize_field(text):
    """Strip injection patterns from a single text field."""
    if not text or not isinstance(text, str):
        return text
    for pattern in _INJECTION_PATTERNS:
        text = re.sub(pattern, '[REDACTED-INJECTION-PATTERN]', text)
    if len(text) > 4000:
        text = text[:4000] + '\n[...truncated at 4000 chars for safety]'
    return text


def sanitize_result(result):
    """Sanitize all text fields in a single retrieval result dict.

    Wraps task_description in [BORG-TRACE-CONTENT]...[/BORG-TRACE-CONTENT]
    boundaries so a consuming agent cannot confuse trace text with its
    own instructions.
    """
    if not isinstance(result, dict):
        return result
    for field in _TEXT_FIELDS:
        if field in result:
            result[field] = sanitize_field(result[field])
    if 'task_description' in result:
        result['task_description'] = (
            '[BORG-TRACE-CONTENT] ' + (result['task_description'] or '') +
            ' [/BORG-TRACE-CONTENT]'
        )
    return result
