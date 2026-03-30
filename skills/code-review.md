description: Use when reviewing code changes before merge.

principles:
  - correctness first: Does it do what it claims?
  - security second: Inputs sanitized? Secrets exposed? Permissions correct?
  - readability third: Can others understand and maintain this?

output_format:
  - blocking_issues: list of {file, line, issue, severity}
  - suggestions: list of {file, line, suggestion, impact}
  - approval: approved | requested_changes | rejected

example: |
  Input: "PR #123 adds async payment processing to checkout flow"

  Output:
    blocking_issues:
      - file: checkout/async_payment.py
        line: 47
        issue: "No timeout on external payment API call"
        severity: high
    suggestions:
      - file: checkout/async_payment.py
        line: 23
        suggestion: "Use PaymentProcessor.get_instance() singleton"
        impact: "minor - avoids potential double-init"
    approval: requested_changes

edge_cases:
  normal: "Small PR, clear intent, 1-2 blocking issues"
  edge: "Large PR touching 10+ files, unclear motivation"
  mess: "PR with known tech debt, fix is correct but ugly"

recovery_loop: |
  1. If blocking issue found → comment and request changes
  2. If suggestion not critical → approve with optional suggestions
  3. If PR is too large → ask for split PR
  4. If intent unclear → ask author for context before reviewing
