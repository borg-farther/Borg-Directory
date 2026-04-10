"""Parser for token stream into AST."""

from typing import List, Any

from .lexer import Token, Lexer


class ASTNode:
    """Base class for AST nodes."""
    pass


class NumberNode(ASTNode):
    def __init__(self, value: float):
        self.value = value
    
    def __repr__(self):
        return f"NumberNode({self.value})"


class BinaryOpNode(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.left = left
        self.op = op
        self.right = right
    
    def __repr__(self):
        return f"BinaryOpNode({self.left}, {self.op}, {self.right})"


class FunctionCallNode(ASTNode):
    def __init__(self, name: str, args: List[ASTNode]):
        self.name = name
        self.args = args
    
    def __repr__(self):
        return f"FunctionCallNode({self.name}, {self.args})"


class Parser:
    """
    Parser that converts token stream to AST.
    """
    
    def __init__(self, lexer: Lexer):
        self._lexer = lexer
        self._tokens: List[Token] = []
        self._pos = 0
    
    def parse(self, input_str: str) -> ASTNode:
        """Parse input string into AST."""
        # Lexer has the bug - second call to tokenize uses stale state
        self._tokens = self._lexer.tokenize(input_str)
        self._pos = 0
        return self._parse_expression()
    
    def _parse_expression(self) -> ASTNode:
        """Parse an expression."""
        if self._pos >= len(self._tokens):
            raise SyntaxError("Unexpected end of input")
        
        return self._parse_additive()
    
    def _parse_additive(self) -> ASTNode:
        """Parse additive expression."""
        left = self._parse_multiplicative()
        
        while self._pos < len(self._tokens):
            token = self._tokens[self._pos]
            if token.type == "OPERATOR" and token.value in ("+", "-"):
                self._pos += 1
                right = self._parse_multiplicative()
                left = BinaryOpNode(left, token.value, right)
            else:
                break
        
        return left
    
    def _parse_multiplicative(self) -> ASTNode:
        """Parse multiplicative expression."""
        left = self._parse_primary()
        
        while self._pos < len(self._tokens):
            token = self._tokens[self._pos]
            if token.type == "OPERATOR" and token.value in ("*", "/"):
                self._pos += 1
                right = self._parse_primary()
                left = BinaryOpNode(left, token.value, right)
            else:
                break
        
        return left
    
    def _parse_primary(self) -> ASTNode:
        """Parse primary expression."""
        if self._pos >= len(self._tokens):
            raise SyntaxError("Unexpected end of input")
        
        token = self._tokens[self._pos]
        self._pos += 1
        
        if token.type == "NUMBER":
            return NumberNode(float(token.value))
        elif token.type == "LPAREN":
            node = self._parse_expression()
            if self._pos >= len(self._tokens) or self._tokens[self._pos].type != "RPAREN":
                raise SyntaxError("Expected closing parenthesis")
            self._pos += 1
            return node
        else:
            raise SyntaxError(f"Unexpected token: {token}")
