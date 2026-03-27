"""Quick verification that the backtick false positive is fixed."""
from guild.core.safety import scan_pack_safety

# Test: markdown inline code should NOT be flagged
pack = {
    'type': 'workflow', 'version': '1.0', 'id': 'test',
    'problem_class': 'classification', 'mental_model': 'fast-thinker',
    'phases': [{'description': 'Step', 'prompts': [
        'Use `myVariable` and handle `TypeError` exceptions.',
        'Here is a code example: `print("hello")`'
    ]}]
}
threats = scan_pack_safety(pack)
print('Threats for markdown inline code:', threats)
assert threats == [], f"Expected no threats for markdown, got: {threats}"

# Test: actual $(command) substitution SHOULD still be flagged
pack2 = {
    'type': 'workflow', 'version': '1.0', 'id': 'test',
    'problem_class': 'classification', 'mental_model': 'fast-thinker',
    'phases': [{'description': 'Step', 'prompts': [
        'Result is $(ls /tmp)',
        'Run $(whoami) to check user'
    ]}]
}
threats2 = scan_pack_safety(pack2)
print('Threats for $(command):', threats2)
assert len(threats2) >= 1, "Expected $(command) to be flagged"

print("ALL CHECKS PASSED - backtick false positive is fixed!")
