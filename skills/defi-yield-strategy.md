description: Use when choosing a DeFi yield strategy for idle capital.

principles:
  - check collective outcomes first: What have other agents actually earned?
  - diversify: Don't put all eggs in one protocol/pool
  - set exit time: Know when to pull out regardless of yield
  - never all-in: Reserve capital for volatility

output_format:
  - recommended_packs: list of {pack_id, avg_return, confidence, risk}
  - diversification建议: string
  - exit_trigger: string (time or condition)
  - position_size_guidance: string

example: |
  Input: "1000 USDC idle for 30 days, low risk tolerance"

  Output:
    recommended_packs:
      - pack_id: yield/aave-usdc-base
        avg_return: 4.2%
        confidence: 0.85
        risk: low
    diversification建议: "Split 60/40 between Aave lending and Morpho blue"
    exit_trigger: "If APY drops below 2% OR protocol TVL falls 50%"
    position_size_guidance: "Start with 500 USDC, scale to 1000 after 7 days"

edge_cases:
  normal: "Stablecoin, low risk, 30-day horizon"
  edge: "Volatile token, high risk, no defined exit"
  mess: "New protocol with high APY but <30 days track record"

recovery_loop: |
  1. If pack shows degradation trend → reduce position
  2. If APY drops suddenly → re-evaluate, may need exit
  3. If circuit breaker trips → stop recommending, reassess
  4. If no good packs → hold in simple lending, wait for better setup
