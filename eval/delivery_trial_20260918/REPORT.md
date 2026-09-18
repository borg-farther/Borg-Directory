# Borg delivery mechanism trial

**Verdict:** `DIRECTIONAL_MECHANISM_IMPROVEMENT`

This compares mandatory agent tool lookup with pre-first-call retrieval. It reuses the frozen v2 tasks and is not independent evidence of general solve-rate lift.

## Per condition

| condition | solved | valid | median calls | median non-cache tokens | median cache reads | median seconds |
|---|---:|---:|---:|---:|---:|---:|
| T0_tool_empty | 8/8 | 8/8 | 9.0 | 13032.0 | 70464.0 | 65.208 |
| T1_tool_seeded | 8/8 | 8/8 | 9.5 | 20477.5 | 72128.0 | 67.496 |
| P0_prefetch_empty | 8/8 | 8/8 | 7.5 | 12218.0 | 56192.0 | 57.4695 |
| P1_prefetch_seeded | 8/8 | 8/8 | 8.0 | 17261.5 | 60544.0 | 61.673 |

## Primary paired contrast

Negative deltas favor prefetch. Only pairs solved by both conditions are included for efficiency metrics.

| metric | pairs | median delta | 95% bootstrap CI | prefetch lower | tie | tool lower |
|---|---:|---:|---:|---:|---:|---:|
| api_calls | 8 | -1.0 | [-2.0, 0.0] | 5 | 2 | 1 |
| non_cache_tokens | 8 | -195.0 | [-6777.5, 2990.0] | 4 | 0 | 4 |
| wall_seconds | 8 | -4.306999999999995 | [-16.318999999999996, 0.3410000000000011] | 6 | 0 | 2 |
| total_tokens | 8 | -6794.0 | [-19843.0, 3998.0] | 5 | 0 | 3 |
| cache_read_tokens | 8 | -5632.0 | [-19328.0, 5504.0] | 5 | 0 | 3 |
| retrieval_seconds | 8 | 0.005943 | [0.003808, 0.00627] | 0 | 0 | 8 |
| estimated_cost_usd | 8 | 0.0 | [0.0, 0.0] | 0 | 8 | 0 |

Negative-transfer tasks: `[]`

## Token accounting

total_tokens includes provider-reported cache reads; non_cache_tokens is input_tokens + output_tokens. Reasoning tokens are not added separately because provider usage counts them inside output tokens.

## Claim boundary

Eight reused tasks can establish an engineering delivery improvement, not general Borg effectiveness. Product-value claims still require held-out powered replication and first-10 external-user outcomes.
