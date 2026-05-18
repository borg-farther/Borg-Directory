description: Use before executing any DeFi trade or entering any pool.

principles:
  - GoPlus scan: Check token security before approval
  - check warnings: Any active protocol warnings?
  - verify liquidity: Is there enough TVL to exit?
  - set stop-loss: Define max acceptable loss before entry

output_format:
  - goplus_result: {score: 0-100, flagged: boolean, issues: list}
  - active_warnings: list of {pack_id, severity, reason}
  - liquidity_ok: boolean
  - stop_loss_pct: number
  - approval: proceed | caution | abort

example: |
  Input: "Swap 1000 USDC → DEGEN token on Base"

  Output:
    goplus_result:
      score: 23
      flagged: true
      issues: ["honeypot detected", "owner can blacklist"]
    active_warnings: []
    liquidity_ok: false
    stop_loss_pct: null
    approval: abort

edge_cases:
  normal: "Blue chip token, high liquidity, clean GoPlus"
  edge: "New but audited token, moderate liquidity"
  mess: "Recent exploit in protocol, team wallet active, no audit"

recovery_loop: |
  1. If GoPlus score < 50 → abort or get second opinion
  2. If active warning on pack → do not recommend
  3. If liquidity insufficient → wait for better market conditions
  4. If stop-loss would be >20% → reconsider position size
