# DeFi Collective Intelligence Experiment

## Objective

Measure whether Borg's collective intelligence mechanisms (shared outcomes, warning propagation) improve DeFi agent performance on two axes: yield optimization and rug/loss avoidance.

## Background

Prior SWE-bench experiment (n=7, the only honest paired run on disk) showed a directional +43pp improvement from reasoning traces (A=3/7, B=6/7, McNemar p=0.125, NOT statistically significant, zero negative transfer). [CORRECTION 20260408: the earlier "+50pp, p=0.031" citation was fabricated — see docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md.] This experiment extends the (directional) collective intelligence hypothesis to DeFi, where information symmetry and rapid signal propagation could provide even larger gains. [ATTENTION 20260408: the motivation for running the DeFi experiment rests on a directional, not significant, prior result. Consider whether the pending Path 1 experiment should resolve the prior before extending to DeFi.]

## Skills Under Test

- `defi-yield-strategy.md`:principles include checking collective outcomes first, diversification, set exit time, never all-in
- `defi-risk-check.md`: GoPlus scan, check warnings, verify liquidity, set stop-loss

## Hypothesis

DeFi agents with access to collective outcomes and warning propagation will:
1. Achieve higher risk-adjusted yields (collective outcomes reduce information asymmetry)
2. Avoid more rugs/losses (warning propagation enables early exit)

## Experiment Design

### Dataset

Historical DeFi data from 2023-2024，包含：
- Yield opportunities (Aave, Compound, Morpho, Curve, Balancer pools)
- Known rug events (FTX collapse, Terra Luna, various protocol exploits)
- Price/TVL/APR time series for backtesting

No real money. Paper trading only.

---

### Test A: Yield Optimization

#### Setup
- **Control Group (A1)**: Individual agents using defi-yield-strategy WITHOUT collective outcomes
- **Test Group (A2)**: Same agents using defi-yield-strategy WITH collective outcomes

#### Collective Outcome Mechanism
When selecting yield packs, agents query a shared outcomes registry:
```
CollectiveRegistry.query(pool_id) → {
  avg_return_7d: float,
  avg_return_30d: float,
  confidence: 0-1,
  n_reports: int,
  degradation_flag: bool
}
```

#### Simulation
1. Generate 100 agent instances with varied risk tolerances and capital sizes
2. Each agent receives 50 yield allocation decisions over 90-day period
3. Control group uses only on-chain APR data
4. Test group also sees collective outcome reports from other agents
5. Track: realized yield, deviation from expected, rebalancing frequency

#### Metrics
- **Primary**: Risk-adjusted return (Sharpe-like ratio, annualized)
- **Secondary**: Average deviation from optimal allocation, position resize frequency
- **Statistical**: Paired t-test across agents, 95% CI

#### Success Criteria
A2 (collective) > A1 (control) by >10% risk-adjusted return with p<0.05

---

### Test B: Rug/Loss Avoidance

#### Setup
- **Control Group (B1)**: Individual agents using defi-risk-check WITHOUT warning propagation
- **Test Group (B2)**: Same agents using defi-risk-check WITH warning propagation

#### Warning Propagation Mechanism
When an agent flags a protocol as dangerous, the warning propagates to all agents:
```
WarningRegistry.report(pack_id, severity, reason) → broadcast to all
WarningRegistry.get_active_warnings(pack_id) → [warning objects]
```

#### Simulation
1. Inject 20 known rug events into simulation timeline
2. Each event has precursor signals (TVL drop, admin activity, GoPlus score change)
3. Agents make decisions at each time step; some include rugs in their consideration set
4. Control group only checks risk metrics individually
5. Test group also receives propagated warnings from other agents who flagged issues

#### Metrics
- **Primary**: Loss avoidance rate (% of rugs detected before loss)
- **Secondary**: False positive rate (good protocols flagged as dangerous), avg warning lead time
- **Statistical**: McNemar's test for paired proportions

#### Success Criteria
B2 (collective) > B1 (control) by >15pp loss avoidance with p<0.05

---

## Simulation Infrastructure

### Agent Architecture
```
DeFiAgent:
  - risk_tolerance: low/medium/high
  - capital: USDC equivalent
  - horizon: days
  - uses defi-yield-strategy skill
  - uses defi-risk-check skill
  - has collective_outcomes_access: bool
  - has warning_propagation_access: bool
```

### Timeline
- Historical replay of 90-day window
- 1 decision per agent per day
- All agents act simultaneously, no sequential simulation

### Data Sources (simulated)
- Mock on-chain data for pools/APRs
- Predefined rug events with timestamps and severity
- Realistic TVL/price movements generated via statistical models

## Expected Outcomes

| Metric | Control | Collective | Expected Lift |
|--------|---------|------------|---------------|
| Risk-adjusted yield |基准  | +10-20% | High confidence |
| Rug avoidance rate | 基准 | +15-25pp | Medium confidence |
| False positive rate | 基准 | +/- 5pp | Uncertain |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Simulated data not realistic | Use real historical APR data where available; calibrate TVL models to real distributions |
| Overfitting to historical rugs | Hold out 30% of rug events for validation; test on out-of-sample periods |
| Agent behavior artifacts | Use diverse agent profiles; limit per-agent decision complexity |

## Success Thresholds

Experiment is conclusive if:
1. Either Test A or Test B meets its success criteria (p<0.05 AND effect size > threshold)
2. Neither test shows significant degradation in control group

## Output

Final report includes:
- Per-metric statistics with confidence intervals
- P-values for primary metrics
- Example agent decision traces (anonymized)
- Breakdown by risk tolerance cohort
- Qualitative analysis of failure modes