"""Lexer for tokenizing input strings."""

import re
from typing import List, Optional


class Token:
    """Represents a token."""
    
    def __init__(self, type_: str, value: str, position: int):
        self.type = type_
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, {self.position})"


class Lexer:
    """
    Lexer that tokenizes input strings.
    
    BUG: Has internal state (_done flag) that isn't reset between calls!
    If first tokenization completes, _done is True. Second call then
    returns empty list immediately without processing input.
    """
    
    # Token patterns
    PATTERNS = [
        ("NUMBER", r"\d+(\.\d+)?"),
        ("STRING", r'"[^"]*"'),
        ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("OPERATOR", r"[+\-*/=<>!]+"),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("COMMA", r","),
        ("WHITESPACE", r"\s+"),
    ]
    
    def __init__(self):
        # These instance variables persist between calls
        self._position = 0
        self._input = ""
        self._current_char: Optional[str] = None
        # BUG: _done flag is not reset between tokenize() calls
        self._done = False
    
    def tokenize(self, input_str: str) -> List[Token]:
        """
        Tokenize input string.
        
        BUG: The _done flag is not reset between calls. If this method
        was called before and completed, _done remains True, causing
        subsequent calls to return empty list immediately.
        """
        self._input = input_str
        self._position = 0
        self._current_char = self._input[0] if self._input else None
        
        # BUG: Should reset _done here but doesn't!
        # if self._done:
        #     self._done = False
        
        tokens: List[Token] = []
        
        # BUG: If _done is True from previous call, return empty
        if self._done:
            return tokens
        
        while self._current_char is not None:
            # Skip whitespace
            if self._current_char.isspace():
                self._advance()
                continue
            
            # Try each pattern
            matched = False
            for token_type, pattern in self.PATTERNS:
                if token_type == "WHITESPACE":
                    continue
                
                regex = re.compile(pattern)
                match = regex.match(self._input, self._position)
                
                if match:
                    value = match.group(0)
                    tokens.append(Token(token_type, value, self._position))
                    self._position = match.end()
                    self._current_char = self._input[self._position] if self._position < len(self._input) else None
                    matched = True
                    break
            
            if not matched:
                raise SyntaxError(f"Unexpected character '{self._current_char}' at position {self._position}")
        
        # BUG: Set _done but never reset it for next call
        self._done = True
        return tokens
    
    def _advance(self) -> None:
        """Advance to next character."""
        self._position += 1
        self._current_char = self._input[self._position] if self._position < len(self._input) else None
