"""
Risk Cron — Scheduled portfolio risk analysis.

Wraps RiskEngine to perform correlation analysis, protocol risk assessment,
concentration risk detection, and drawdown tracking on a portfolio,
returning formatted risk alert strings.

Usage:
    wallets = {"solana": ["Wallet1"], "ethereum": ["0x123..."]}
    positions = await get_all_positions(wallets)
    alerts = await run_risk_check(wallets, positions)
"""

import logging
from typing import Any, Dict, List, Optional

from borg.defi.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


async def run_risk_check(
    wallets: Optional[Dict[str, List[str]]] = None,
    positions: Optional[List[Any]] = None,
    concentration_warning_threshold: float = 0.25,
    concentration_critical_threshold: float = 0.40,
    high_correlation_threshold: float = 0.70,
    default_stop_loss: float = 0.20,
    current_portfolio_value: float = 0.0,
    tvl_data: Optional[Dict[str, Dict[str, Any]]] = None,
    audit_data: Optional[Dict[str, str]] = None,
) -> List[str]:
    """
    Run comprehensive risk analysis on a portfolio and return alert messages.

    Args:
        wallets: Dict mapping chain name -> list of wallet addresses.
                Used for correlation analysis context.
        positions: List of Position objects to analyze.
                   If None, risk check returns empty list.
        concentration_warning_threshold: % threshold for warning (default 25%).
        concentration_critical_threshold: % threshold for critical (default 40%).
        high_correlation_threshold: Correlation coefficient threshold (default 0.70).
        default_stop_loss: Default stop-loss threshold (default 20% drawdown).
        current_portfolio_value: Current total portfolio value in USD for drawdown tracking.
        tvl_data: Optional dict of protocol -> {tvl_usd, tvl_history: []} for protocol risk.
        audit_data: Optional dict of protocol -> audit_status for protocol risk.

    Returns:
        List of formatted Telegram message strings.
        Includes correlation alerts, concentration alerts, protocol risk alerts,
        and drawdown alerts. Returns empty list if no risk issues detected.
    """
    if positions is None or not positions:
        logger.info("No positions provided for risk check")
        return []

    # Initialize risk engine with thresholds
    engine = RiskEngine(
        concentration_warning_threshold=concentration_warning_threshold,
        concentration_critical_threshold=concentration_critical_threshold,
        high_correlation_threshold=high_correlation_threshold,
        default_stop_loss=default_stop_loss,
    )

    alerts: List[str] = []

    try:
        # 1. Correlation Analysis
        correlation_result = engine.correlation_analysis(positions)
        if correlation_result.high_correlation_pairs:
            for token_a, token_b, corr in correlation_result.high_correlation_pairs:
                alert_msg = (
                    f"📊 *CORRELATION ALERT*\n"
                    f"High correlation detected:\n"
                    f"{token_a} ↔ {token_b}: {corr:.2f}\n"
                    f"Portfolio avg correlation: {correlation_result.portfolio_correlation:.2f}\n"
                    f"⚠️ Consider diversifying to reduce risk"
                )
                alerts.append(alert_msg)
                logger.debug(f"Correlation alert: {token_a}/{token_b} = {corr:.2f}")

        # 2. Concentration Risk
        concentration_results = engine.concentration_risk(positions)
        for conc in concentration_results:
            if conc.threshold_exceeded:
                severity_emoji = "🔴" if conc.risk_level == "critical" else "🟡"
                alert_msg = (
                    f"{severity_emoji} *CONCENTRATION {'CRITICAL' if conc.risk_level == 'critical' else 'WARNING'}*\n"
                    f"{conc.alert_message}"
                )
                alerts.append(alert_msg)
                logger.debug(f"Concentration alert: {conc.token} = {conc.concentration_pct*100:.1f}%")

        # 3. Protocol Risk Assessment
        if tvl_data is not None or audit_data is not None:
            protocol_results = engine.protocol_risk_assessment(
                positions, tvl_data=tvl_data, audit_data=audit_data
            )
            for protocol, result in protocol_results.items():
                if result.risk_score > 0.5:  # High risk
                    risk_emoji = "🔴" if result.risk_score > 0.7 else "🟡"
                    factors_str = "\n".join(f"  - {f}" for f in result.risk_factors[:3])
                    alert_msg = (
                        f"{risk_emoji} *PROTOCOL RISK: {protocol.upper()}*\n"
                        f"Risk Score: {result.risk_score:.2f}\n"
                        f"TVL: ${result.tvl_usd/1e6:.1f}M ({result.tvl_change_24h:+.1f}% 24h)\n"
                        f"TVL Trend: {result.tvl_trend}\n"
                        f"Audit Status: {result.audit_status}\n"
                        f"Risk Factors:\n{factors_str}"
                    )
                    alerts.append(alert_msg)
                    logger.debug(f"Protocol risk: {protocol} score={result.risk_score:.2f}")

        # 4. Drawdown Tracking
        if current_portfolio_value > 0:
            drawdown_result = engine.drawdown_tracking(current_portfolio_value)

            if drawdown_result.stop_loss_triggered:
                alert_msg = (
                    f"🚨 *STOP-LOSS TRIGGERED*\n"
                    f"Portfolio drawdown: {drawdown_result.current_drawdown_pct*100:.1f}%\n"
                    f"Max drawdown: {drawdown_result.max_drawdown_pct*100:.1f}%\n"
                    f"Threshold: {drawdown_result.stop_loss_threshold*100:.1f}%"
                )
                alerts.append(alert_msg)
                logger.warning(f"Stop-loss triggered: drawdown={drawdown_result.current_drawdown_pct*100:.1f}%")

            elif drawdown_result.current_drawdown_pct > 0.1:  # >10% drawdown warning
                alert_msg = (
                    f"📉 *DRAWDOWN WARNING*\n"
                    f"Current drawdown: {drawdown_result.current_drawdown_pct*100:.1f}%\n"
                    f"Max drawdown: {drawdown_result.max_drawdown_pct*100:.1f}%\n"
                    f"Peak: ${drawdown_result.peak_value:,.2f}\n"
                    f"Current: ${drawdown_result.current_value:,.2f}"
                )
                alerts.append(alert_msg)

        logger.info(f"Risk check complete: {len(alerts)} risk alerts generated")

    except Exception as e:
        logger.error(f"Risk check error: {e}")

    return alerts
