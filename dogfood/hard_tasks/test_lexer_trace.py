import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/hard_tasks/hard-010')

from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator

lexer = Lexer()
parser = Parser(lexer)
evaluator = Evaluator()

# First parse
print("=== First parse: '10 + 20' ===")
tokens1 = lexer.tokenize("10 + 20")
print(f"Tokens: {tokens1}")

ast1 = parser.parse("10 + 20")
result1 = evaluator.evaluate(ast1)
print(f"Result: {result1}")

# Reset parser position
parser._pos = 0

# Second parse
print("\n=== Second parse: '5 + 3' ===")
tokens2 = lexer.tokenize("5 + 3")
print(f"Tokens: {tokens2}")

ast2 = parser.parse("5 + 3")
result2 = evaluator.evaluate(ast2)
print(f"Result: {result2}")
print(f"Expected: 8, Got: {result2}")
