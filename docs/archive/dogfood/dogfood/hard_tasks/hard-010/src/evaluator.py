"""Evaluator for AST."""

from .parser import ASTNode, NumberNode, BinaryOpNode, FunctionCallNode


class Evaluator:
    """
    Evaluates AST to produce values.
    """
    
    def __init__(self):
        self._variables = {}
    
    def evaluate(self, node: ASTNode) -> float:
        """Evaluate an AST node."""
        if isinstance(node, NumberNode):
            return node.value
        elif isinstance(node, BinaryOpNode):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            if node.op == "+":
                return left + right
            elif node.op == "-":
                return left - right
            elif node.op == "*":
                return left * right
            elif node.op == "/":
                return left / right
        elif isinstance(node, FunctionCallNode):
            return self._evaluate_function(node)
        
        raise ValueError(f"Unknown node type: {type(node)}")
    
    def _evaluate_function(self, node: FunctionCallNode) -> float:
        """Evaluate a function call."""
        args = [self.evaluate(arg) for arg in node.args]
        if node.name == "add":
            return sum(args)
        elif node.name == "mul":
            result = 1
            for arg in args:
                result *= arg
            return result
        raise ValueError(f"Unknown function: {node.name}")


def evaluate_expression(input_str: str, lexer: "Lexer", parser: "Parser") -> float:
    """
    Convenience function to evaluate an expression string.
    
    Due to lexer bug, calling this twice with the same lexer instance
    will cause the second evaluation to fail or return wrong values.
    """
    ast = parser.parse(input_str)
    evaluator = Evaluator()
    return evaluator.evaluate(ast)
