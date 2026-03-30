#!/usr/bin/env python3
"""Temporary import test script."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.defi.cron import run_whale_scan, run_yield_scan, run_alpha_scan, run_portfolio_report, run_liquidation_scan, run_risk_check
print('✓ All cron functions importable from borg.defi.cron')

from borg.defi import run_whale_scan, run_yield_scan, run_alpha_scan, run_portfolio_report, run_liquidation_scan, run_risk_check
print('✓ All cron functions importable from borg.defi')

from borg.defi import AlphaSignalEngine, RiskEngine, StrategyBacktester
print('✓ Phase 3 modules importable from borg.defi')

from borg.defi import SmartMoneyFlow, VolumeSpike, NewPairAlert, BridgeFlow
print('✓ Alpha signal types importable')

from borg.defi import CorrelationResult, ProtocolRiskResult, ConcentrationRiskResult, DrawdownResult
print('✓ Risk engine types importable')

from borg.defi import BacktestTrade, BacktestResult, WhaleReplayResult, LPSimulationResult, PerformanceMetrics
print('✓ Backtester types importable')

print()
print('All imports successful!')
