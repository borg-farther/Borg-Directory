description: Use when implementing a new feature or fixing a bug.

principles:
  - write test first: Test defines the contract before implementation
  - minimal implementation: Get to green as fast as possible
  - refactor: Clean up only AFTER tests pass

output_format:
  - test_written: string (test name and what it verifies)
  - implementation_status: passing | failing | incomplete
  - refactor_done: boolean
  - next_step: string

example: |
  Input: "Feature: calculate compound interest for savings accounts"

  Output:
    test_written: "test_compound_interest_5_percent_1_year_returns_105"
    implementation_status: failing
    refactor_done: false
    next_step: "Implement interest calculation in SavingsAccount.interest()"

edge_cases:
  normal: "Feature is well-defined, test covers happy path + 1 edge case"
  edge: "Feature has ambiguous requirements, test clarifies behavior"
  mess: "Existing codebase has no testing infra, start with integration test"

recovery_loop: |
  1. If test fails but implementation looks right → check test assertion
  2. If test passes but shouldn't → review what you actually tested
  3. If stuck on implementation → delete and re-read the test
  4. If refactor breaks tests → you went too far, revert and be smaller
