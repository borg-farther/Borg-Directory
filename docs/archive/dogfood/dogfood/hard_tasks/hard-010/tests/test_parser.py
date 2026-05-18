"""Tests for parser state machine bug."""

import pytest
from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator, evaluate_expression


def test_lexer_single_parse():
    """Test that lexer works for a single parse."""
    lexer = Lexer()
    tokens = lexer.tokenize("1 + 2")
    
    assert len(tokens) == 3
    assert tokens[0].type == "NUMBER"
    assert tokens[0].value == "1"


def test_evaluator_single_expression():
    """Test evaluating a single expression."""
    lexer = Lexer()
    parser = Parser(lexer)
    evaluator = Evaluator()
    
    ast = parser.parse("1 + 2")
    result = evaluator.evaluate(ast)
    
    assert result == 3


def test_second_parse_fails():
    """
    Test that demonstrates the lexer state bug.
    
    The lexer doesn't reset _current_char between calls,
    so the second parse fails or returns wrong values.
    """
    lexer = Lexer()
    parser = Parser(lexer)
    evaluator = Evaluator()
    
    # First parse - works correctly
    ast1 = parser.parse("10 + 20")
    result1 = evaluator.evaluate(ast1)
    assert result1 == 30
    
    # Second parse - BUG: lexer state from first parse interferes
    ast2 = parser.parse("5 + 3")
    result2 = evaluator.evaluate(ast2)
    
    # BUG: This should be 8, but due to lexer state bug it may be wrong
    assert result2 == 8, f"Expected 8 but got {result2}"


def test_multiple_parses_with_same_lexer():
    """
    Test multiple parses with the same lexer instance.
    
    This exposes the bug where _current_char is not reset.
    """
    lexer = Lexer()
    parser = Parser(lexer)
    
    expressions = ["1 + 2", "3 * 4", "5 - 2", "10 / 2"]
    expected = [3, 12, 3, 5]
    
    evaluator = Evaluator()
    
    for expr, exp in zip(expressions, expected):
        ast = parser.parse(expr)
        result = evaluator.evaluate(ast)
        assert result == exp, f"Expression '{expr}' expected {exp} but got {result}"


def test_complex_expression_after_simple():
    """Test that complex expression works after simple one."""
    lexer = Lexer()
    parser = Parser(lexer)
    evaluator = Evaluator()
    
    # Simple first
    ast1 = parser.parse("100 + 200")
    assert evaluator.evaluate(ast1) == 300
    
    # Complex second - BUG: state from first parse corrupts second
    ast2 = parser.parse("(10 + 5) * 3")
    result = evaluator.evaluate(ast2)
    assert result == 45, f"Expected 45 but got {result}"


def test_evaluate_expression_helper():
    """
    Test the evaluate_expression helper function.
    
    Using the same lexer for multiple calls exposes the bug.
    """
    lexer = Lexer()
    parser = Parser(lexer)
    
    # First call
    result1 = evaluate_expression("7 + 8", lexer, parser)
    assert result1 == 15
    
    # Second call - BUG: lexer state corrupted
    result2 = evaluate_expression("9 + 1", lexer, parser)
    assert result2 == 10, f"Expected 10 but got {result2}"
