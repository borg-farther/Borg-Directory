---
name: defi-yield-strategy
trigger: "Agent has idle capital and needs a yield recommendation"
---

# DeFi Yield Strategy

## Principles
1. Yield = reward for lending/liquidity — too high means hidden risk.
2. Impermanent loss (IL) is the silent killer — volatile pair APR rarely covers 50%+ IL.
3. Smart contract risk is binary — 2% pool that drains = 100% loss.
4. Liquidity lock age + audit status predict rugged better than APR.
5. Exit liquidity — if you can't exit without moving price 20%, yield is fictional.

## Output Format
Return: Strategy (protocol/pool, APY, risk) | Entry rationale | Exit conditions | Risks

## Edge Cases
- HIGH IL volatile pair: short duration only
- UNAUDITED protocol: cap at 5% portfolio
- EXPIRED APY: check current utilization

## Example
INPUT: "1000 USDC idle, low-medium risk"
OUTPUT:
```
Strategy: Morpho Blue USDC/DAI, 4.2% APY, Risk: Low
Rationale: Overcollateralized, no IL, blue-chip
Exit: APY < 2% or risk-off signal
Risk: Smart contract (2 audits), supply cap
```

## Recovery
APY drops 50%+ or unexpected IL? Exit immediately.
