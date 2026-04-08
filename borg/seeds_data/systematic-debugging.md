description: Use when an agent hits a bug, test failure, or unexpected error.

principles:
  - isolate: Separate the failing part from everything else
  - reproduce: Get a consistent repro before touching code
  - binary search: Halve the search space each step
  - check assumptions: Verify what you think is true actually is
  - verify fix: Confirm the fix works and doesn't break anything else

output_format:
  - root_cause: string
  - repro_steps: list of strings
  - fix_applied: string
  - verification: string

example: |
  Input: "TestUserRegistration.test_valid_email fails with 'NoneType has no attribute email'"

  Output:
    root_cause: "UserFactory creates user with null email when chain=external"
    repro_steps:
      - "Run test with chain=external → fails"
      - "Run test with chain=internal → passes"
      - "Factory sets email=None for external chain"
    fix_applied: "Added email validation in UserFactory for external chain"
    verification: "test_valid_email passes for both chains"

edge_cases:
  normal: "Bug in your code, clear stack trace"
  edge: "Race condition, intermittent failure, timing-dependent"
  mess: "Heisenbug that disappears when you look at it, or failure in dependency's dependency"

recovery_loop: |
  1. If no repro after 3 attempts → simplify the environment
  2. If root cause unclear → add logging, retry
  3. If fix doesn't hold → revert and try different approach
  4. If it works but you don't know why → document anyway, understand later
