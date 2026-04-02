#!/bin/bash
cd "$(dirname "$0")"

# Run tests first
python -m pytest tests/test_fetcher.py -v

# Check for nested callbacks deeper than 2 levels using AST
echo "Checking for nested callbacks..."
NESTED_DEPTH=$(python -c "
import ast
import sys

with open('src/fetcher.py', 'r') as f:
    tree = ast.parse(f.read())

class CallbackDepthChecker(ast.NodeVisitor):
    def __init__(self):
        self.max_depth = 0
        self.current_depth = 0
        self.in_callback = False
        
    def visit_FunctionDef(self, node):
        was_in_callback = self.in_callback
        if 'callback' in node.name.lower() or any('callback' in (arg.arg if hasattr(arg, 'arg') else arg.name).lower() for arg in node.args.args):
            self.in_callback = True
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)

        self.generic_visit(node)
        self.in_callback = was_in_callback

    # Handle AsyncFunctionDef for Python 3.12 compatibility
    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

checker = CallbackDepthChecker()
checker.visit(tree)
print(checker.max_depth)
")

echo "Maximum callback nesting depth: $NESTED_DEPTH"
if [ "$NESTED_DEPTH" -ge 2 ]; then
    echo "FAIL: Callback nesting depth $NESTED_DEPTH >= 2 (callback hell)"
    exit 1
fi

echo "PASS: Callback nesting depth <= 2"
