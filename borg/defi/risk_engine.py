"""Risk engine module for Borg DeFi.

Provides portfolio-level risk scoring, correlation analysis, concentration risk,
protocol risk assessment, and drawdown tracking.
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from borg.defi.data_models import Position, RiskAlert, RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Result of correlation analysis between positions.
    
    Attributes:
        token_pairs: Dict of (token_a, token_b) -> correlation coefficient (-1 to 1)
        portfolio_correlation: Average correlation weighted by position size
        high_correlation_pairs: Pairs with correlation > threshold (potential risk)
    """
    token_pairs: Dict[Tuple[str, str], float]
    portfolio_correlation: float
    high_correlation_pairs: List[Tuple[str, str, float]]
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()


@dataclass
class ProtocolRiskResult:
    """Result of protocol risk assessment.
    
    Attributes:
        protocol: Protocol name
        tvl_usd: Current TVL in USD
        tvl_change_24h: 24h TVL change percentage
        tvl_trend: TVL trend direction (increasing|decreasing|stable)
        audit_status: Audit status (audited|partial|unaudited|unknown)
        risk_score: Overall risk score 0-1 (higher = riskier)
        risk_factors: List of identified risk factors
    """
    protocol: str
    tvl_usd: float
    tvl_change_24h: float
    tvl_trend: str
    audit_status: str
    risk_score: float
    risk_factors: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()


@dataclass
class ConcentrationRiskResult:
    """Result of concentration risk analysis.
    
    Attributes:
        token: Token symbol
        concentration_pct: Percentage of portfolio in this token
        exposure_usd: USD value of exposure
        threshold_exceeded: Whether concentration exceeds threshold
        risk_level: Risk severity (low|medium|high|critical)
    """
    token: str
    concentration_pct: float
    exposure_usd: float
    threshold_exceeded: bool
    risk_level: str
    alert_message: str = ""


@dataclass
class DrawdownResult:
    """Result of drawdown tracking.
    
    Attributes:
        current_drawdown_pct: Current drawdown from peak
        max_drawdown_pct: Maximum drawdown observed
        max_drawdown_duration: Duration of max drawdown in seconds
        peak_value: Peak portfolio value
        trough_value: Trough (lowest) portfolio value
        current_value: Current portfolio value
        stop_loss_triggered: Whether stop-loss was triggered
        stop_loss_threshold: The stop-loss threshold that was set
        recovery_time: Time to recover from max drawdown (if recovered)
        is_recovered: Whether portfolio has recovered from max drawdown
    """
    current_drawdown_pct: float
    max_drawdown_pct: float
    max_drawdown_duration: float
    peak_value: float
    trough_value: float
    current_value: float
    stop_loss_triggered: bool
    stop_loss_threshold: float
    recovery_time: Optional[float] = None
    is_recovered: bool = False
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()


class RiskEngine:
    """Portfolio risk analysis engine.
    
    Provides methods for:
    - Correlation analysis between positions
    - Protocol risk assessment (TVL, audits)
    - Concentration risk detection
    - Drawdown tracking with stop-loss triggers
    """
    
    # Thresholds
    CONCENTRATION_WARNING_THRESHOLD = 0.25  # 25% warning
    CONCENTRATION_CRITICAL_THRESHOLD = 0.40  # 40% critical
    HIGH_CORRELATION_THRESHOLD = 0.70  # 0.7 correlation
    DEFAULT_STOP_LOSS_THRESHOLD = 0.20  # 20% drawdown default
    MIN_TVL_FOR_LOW_RISK = 10_000_000  # $10M TVL for low risk protocol
    
    def __init__(
        self,
        concentration_warning_threshold: float = CONCENTRATION_WARNING_THRESHOLD,
        concentration_critical_threshold: float = CONCENTRATION_CRITICAL_THRESHOLD,
        high_correlation_threshold: float = HIGH_CORRELATION_THRESHOLD,
        default_stop_loss: float = DEFAULT_STOP_LOSS_THRESHOLD,
    ):
        """Initialize risk engine.
        
        Args:
            concentration_warning_threshold: % threshold for warning (default 25%)
            concentration_critical_threshold: % threshold for critical (default 40%)
            high_correlation_threshold: Correlation coefficient threshold (default 0.7)
            default_stop_loss: Default stop-loss threshold (default 20%)
        """
        self.concentration_warning_threshold = concentration_warning_threshold
        self.concentration_critical_threshold = concentration_critical_threshold
        self.high_correlation_threshold = high_correlation_threshold
        self.default_stop_loss = default_stop_loss
        
        # Historical data for drawdown tracking
        self._value_history: List[Tuple[float, float]] = []  # (timestamp, value)
        self._peak_value = 0.0
        self._peak_timestamp = 0.0
        self._trough_value = 0.0
        self._trough_timestamp = 0.0
        self._in_drawdown = False
        self._drawdown_start = 0.0
        
        # Historical max drawdown tracking
        self._max_drawdown_pct = 0.0
        
        # Stop-loss state
        self._stop_loss_triggered = False
        self._stop_loss_threshold = default_stop_loss
    
    def correlation_analysis(
        self,
        positions: List[Position],
        price_history: Optional[Dict[str, List[float]]] = None,
    ) -> CorrelationResult:
        """Analyze correlation between portfolio positions.
        
        Uses price history to calculate correlation coefficients between
        token pairs. If no price history provided, uses P&L percentage
        changes as proxy.
        
        Args:
            positions: List of portfolio positions
            price_history: Optional dict of token -> list of historical prices
            
        Returns:
            CorrelationResult with pairwise correlations and risk assessment
        """
        if len(positions) < 2:
            return CorrelationResult(
                token_pairs={},
                portfolio_correlation=0.0,
                high_correlation_pairs=[],
            )
        
        # Build correlation matrix using price returns
        tokens = [p.token for p in positions]
        n = len(tokens)
        
        # Calculate returns for each token
        returns: Dict[str, List[float]] = {}
        
        if price_history:
            # Use provided price history
            for token in tokens:
                prices = price_history.get(token, [])
                if len(prices) > 1:
                    returns[token] = self._calculate_returns(prices)
        else:
            # Fallback: use pnl_pct as proxy for returns
            for p in positions:
                returns[p.token] = [p.pnl_pct / 100]  # Single point
        
        # Calculate pairwise correlations
        token_pairs: Dict[Tuple[str, str], float] = {}
        high_corr_pairs: List[Tuple[str, str, float]] = []
        
        for i in range(n):
            for j in range(i + 1, n):
                token_a = tokens[i]
                token_b = tokens[j]
                
                returns_a = returns.get(token_a, [0])
                returns_b = returns.get(token_b, [0])
                
                corr = self._pearson_correlation(returns_a, returns_b)
                token_pairs[(token_a, token_b)] = corr
                
                if abs(corr) >= self.high_correlation_threshold:
                    high_corr_pairs.append((token_a, token_b, corr))
        
        # Calculate portfolio-weighted average correlation
        total_value = sum(p.value_usd for p in positions)
        portfolio_corr = 0.0
        
        if total_value > 0 and token_pairs:
            weighted_sum = 0.0
            weight_sum = 0.0
            
            for (token_a, token_b), corr in token_pairs.items():
                # Find positions
                pos_a = next((p for p in positions if p.token == token_a), None)
                pos_b = next((p for p in positions if p.token == token_b), None)
                
                if pos_a and pos_b:
                    weight = (pos_a.value_usd * pos_b.value_usd) / (total_value ** 2)
                    weighted_sum += corr * weight
                    weight_sum += weight
            
            portfolio_corr = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        return CorrelationResult(
            token_pairs=token_pairs,
            portfolio_correlation=portfolio_corr,
            high_correlation_pairs=high_corr_pairs,
        )
    
    def protocol_risk_assessment(
        self,
        positions: List[Position],
        tvl_data: Optional[Dict[str, Dict[str, Any]]] = None,
        audit_data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, ProtocolRiskResult]:
        """Assess risk for protocols in the portfolio.
        
        Args:
            positions: List of portfolio positions
            tvl_data: Optional dict of protocol -> {tvl_usd, tvl_history: []}
            audit_data: Optional dict of protocol -> audit_status
            
        Returns:
            Dict of protocol -> ProtocolRiskResult
        """
        results: Dict[str, ProtocolRiskResult] = {}
        
        # Group positions by protocol
        protocol_positions: Dict[str, List[Position]] = {}
        for p in positions:
            if p.protocol not in protocol_positions:
                protocol_positions[p.protocol] = []
            protocol_positions[p.protocol].append(p)
        
        for protocol, prot_positions in protocol_positions.items():
            # Get TVL data
            tvl_info = tvl_data.get(protocol, {}) if tvl_data else {}
            tvl_usd = tvl_info.get("tvl_usd", 0.0)
            tvl_history = tvl_info.get("tvl_history", [])
            
            # Calculate TVL change
            if len(tvl_history) >= 2:
                tvl_change_24h = ((tvl_history[-1] - tvl_history[-2]) / tvl_history[-2] * 100) if tvl_history[-2] > 0 else 0.0
            else:
                tvl_change_24h = 0.0
            
            # Determine TVL trend
            if len(tvl_history) >= 7:
                recent_avg = sum(tvl_history[-7:]) / 7
                older_avg = sum(tvl_history[-14:-7]) / 7 if len(tvl_history) >= 14 else recent_avg
                if recent_avg > older_avg * 1.05:
                    tvl_trend = "increasing"
                elif recent_avg < older_avg * 0.95:
                    tvl_trend = "decreasing"
                else:
                    tvl_trend = "stable"
            else:
                tvl_trend = "stable"
            
            # Get audit status
            audit_status = (audit_data or {}).get(protocol, "unknown")
            
            # Calculate risk score
            risk_score = self._calculate_protocol_risk(
                protocol=protocol,
                tvl_usd=tvl_usd,
                tvl_change_24h=tvl_change_24h,
                tvl_trend=tvl_trend,
                audit_status=audit_status,
            )
            
            # Identify risk factors
            risk_factors = self._identify_protocol_risk_factors(
                protocol=protocol,
                tvl_usd=tvl_usd,
                tvl_change_24h=tvl_change_24h,
                tvl_trend=tvl_trend,
                audit_status=audit_status,
                positions=prot_positions,
            )
            
            results[protocol] = ProtocolRiskResult(
                protocol=protocol,
                tvl_usd=tvl_usd,
                tvl_change_24h=tvl_change_24h,
                tvl_trend=tvl_trend,
                audit_status=audit_status,
                risk_score=risk_score,
                risk_factors=risk_factors,
            )
        
        return results
    
    def concentration_risk(
        self,
        positions: List[Position],
    ) -> List[ConcentrationRiskResult]:
        """Analyze single-token concentration risk.
        
        Args:
            positions: List of portfolio positions
            
        Returns:
            List of ConcentrationRiskResult for tokens exceeding thresholds
        """
        if not positions:
            return []
        
        results: List[ConcentrationRiskResult] = []
        total_value = sum(p.value_usd for p in positions)
        
        if total_value <= 0:
            return []
        
        # Group by token
        token_values: Dict[str, float] = {}
        for p in positions:
            token_values[p.token] = token_values.get(p.token, 0.0) + p.value_usd
        
        for token, exposure_usd in token_values.items():
            concentration_pct = exposure_usd / total_value
            
            # Determine if threshold exceeded
            threshold_exceeded = concentration_pct >= self.concentration_warning_threshold
            
            # Determine risk level
            if concentration_pct >= self.concentration_critical_threshold:
                risk_level = "critical"
            elif concentration_pct >= self.concentration_warning_threshold:
                risk_level = "high"
            else:
                risk_level = "low"
            
            # Generate alert message
            if concentration_pct >= self.concentration_critical_threshold:
                alert_message = f"CRITICAL: {token} is {concentration_pct*100:.1f}% of portfolio (${exposure_usd:.2f})"
            elif concentration_pct >= self.concentration_warning_threshold:
                alert_message = f"WARNING: {token} is {concentration_pct*100:.1f}% of portfolio (${exposure_usd:.2f})"
            else:
                alert_message = ""
            
            result = ConcentrationRiskResult(
                token=token,
                concentration_pct=concentration_pct,
                exposure_usd=exposure_usd,
                threshold_exceeded=threshold_exceeded,
                risk_level=risk_level,
                alert_message=alert_message,
            )
            results.append(result)
        
        # Sort by concentration (highest first)
        results.sort(key=lambda x: x.concentration_pct, reverse=True)
        
        return results
    
    def concentration_alerts(self, positions: List[Position]) -> List[RiskAlert]:
        """Generate risk alerts for concentration issues.
        
        Args:
            positions: List of portfolio positions
            
        Returns:
            List of RiskAlert for concentration warnings
        """
        alerts: List[RiskAlert] = []
        
        concentrations = self.concentration_risk(positions)
        
        for conc in concentrations:
            if conc.threshold_exceeded:
                severity = "critical" if conc.risk_level == "critical" else "warning"
                
                alert = RiskAlert(
                    alert_type="concentration",
                    severity=severity,
                    message=conc.alert_message,
                    affected_positions=[conc.token],
                )
                alerts.append(alert)
        
        return alerts
    
    def drawdown_tracking(
        self,
        current_value: float,
        timestamp: Optional[float] = None,
        stop_loss_threshold: Optional[float] = None,
    ) -> DrawdownResult:
        """Track portfolio drawdown from peak value.
        
        Args:
            current_value: Current portfolio value in USD
            timestamp: Optional Unix timestamp (defaults to now)
            stop_loss_threshold: Optional override for stop-loss threshold
            
        Returns:
            DrawdownResult with current and max drawdown metrics
        """
        if timestamp is None:
            timestamp = datetime.now().timestamp()
        
        if stop_loss_threshold is not None:
            self._stop_loss_threshold = stop_loss_threshold
        
        # Initialize peak tracking
        if self._peak_value == 0.0 or current_value > self._peak_value:
            self._peak_value = current_value
            self._peak_timestamp = timestamp
            # Don't reset trough_value - keep the historical trough!
            # Only reset trough if this is the first value
            if self._trough_value == 0.0:
                self._trough_value = current_value
                self._trough_timestamp = timestamp
            self._in_drawdown = False
        
        # Track if in drawdown
        if current_value < self._peak_value:
            if not self._in_drawdown:
                self._in_drawdown = True
                self._drawdown_start = timestamp
            
            # Update trough
            if current_value < self._trough_value:
                self._trough_value = current_value
                self._trough_timestamp = timestamp
            
            # Always track max drawdown when in drawdown
            if self._peak_value > 0:
                current_dd = (self._peak_value - current_value) / self._peak_value
                self._max_drawdown_pct = max(self._max_drawdown_pct, current_dd)
        else:
            # Recovered above peak
            if self._in_drawdown:
                self._in_drawdown = False
        
        # Calculate current drawdown
        if self._peak_value > 0:
            current_drawdown_pct = (self._peak_value - current_value) / self._peak_value
        else:
            current_drawdown_pct = 0.0
        
        # Max drawdown is tracked continuously during drawdown
        max_drawdown_pct = self._max_drawdown_pct
        
        # Calculate max drawdown duration
        max_drawdown_duration = self._trough_timestamp - self._peak_timestamp if self._in_drawdown else 0.0
        
        # Calculate recovery time (if recovered)
        recovery_time = None
        is_recovered = False
        if max_drawdown_pct > 0 and current_value >= self._peak_value:
            recovery_time = timestamp - self._trough_timestamp
            is_recovered = True
        
        # Check stop-loss
        stop_loss_triggered = current_drawdown_pct >= self._stop_loss_threshold
        
        if stop_loss_triggered and not self._stop_loss_triggered:
            logger.warning(
                f"STOP LOSS TRIGGERED: {current_drawdown_pct*100:.2f}% drawdown "
                f"(threshold: {self._stop_loss_threshold*100:.1f}%)"
            )
            self._stop_loss_triggered = True
        
        # Store history
        self._value_history.append((timestamp, current_value))
        
        # Trim history if too long (keep last 10000 points)
        if len(self._value_history) > 10000:
            self._value_history = self._value_history[-10000:]
        
        return DrawdownResult(
            current_drawdown_pct=current_drawdown_pct,
            max_drawdown_pct=max_drawdown_pct,
            max_drawdown_duration=max_drawdown_duration,
            peak_value=self._peak_value,
            trough_value=self._trough_value,
            current_value=current_value,
            stop_loss_triggered=stop_loss_triggered,
            stop_loss_threshold=self._stop_loss_threshold,
            recovery_time=recovery_time,
            is_recovered=is_recovered,
        )
    
    def reset_drawdown_tracking(self) -> None:
        """Reset drawdown tracking state."""
        self._value_history.clear()
        self._peak_value = 0.0
        self._peak_timestamp = 0.0
        self._trough_value = 0.0
        self._trough_timestamp = 0.0
        self._in_drawdown = False
        self._drawdown_start = 0.0
        self._max_drawdown_pct = 0.0
        self._stop_loss_triggered = False
    
    def calculate_portfolio_risk_score(
        self,
        positions: List[Position],
        tvl_data: Optional[Dict[str, Dict[str, Any]]] = None,
        audit_data: Optional[Dict[str, str]] = None,
        price_history: Optional[Dict[str, List[float]]] = None,
    ) -> float:
        """Calculate overall portfolio risk score (0-1, higher = riskier).
        
        Combines correlation, concentration, protocol, and drawdown risks.
        
        Args:
            positions: List of portfolio positions
            tvl_data: Optional TVL data for protocol risk assessment
            audit_data: Optional audit status data
            price_history: Optional price history for correlation analysis
            
        Returns:
            Risk score 0.0-1.0
        """
        if not positions:
            return 0.0
        
        risk_components: List[float] = []
        
        # 1. Concentration risk (weight: 30%)
        concentrations = self.concentration_risk(positions)
        if concentrations:
            max_concentration = max(c.concentration_pct for c in concentrations)
            concentration_risk = min(1.0, max_concentration * 2)  # 50%+ = max risk
            risk_components.append(concentration_risk * 0.30)
        
        # 2. Protocol risk (weight: 30%)
        protocol_risks = self.protocol_risk_assessment(positions, tvl_data, audit_data)
        if protocol_risks:
            avg_protocol_risk = sum(r.risk_score for r in protocol_risks.values()) / len(protocol_risks)
            risk_components.append(avg_protocol_risk * 0.30)
        
        # 3. Correlation risk (weight: 20%)
        correlation = self.correlation_analysis(positions, price_history)
        if correlation.high_correlation_pairs:
            corr_risk = min(1.0, len(correlation.high_correlation_pairs) * 0.2)
            risk_components.append(corr_risk * 0.20)
        else:
            risk_components.append(0.0)
        
        # 4. Drawdown risk (weight: 20%)
        total_value = sum(p.value_usd for p in positions)
        if total_value > 0 and self._peak_value > 0:
            drawdown_risk = min(1.0, self._peak_value - total_value) / self._peak_value if self._peak_value > 0 else 0.0
            risk_components.append(drawdown_risk * 0.20)
        
        return min(1.0, sum(risk_components))
    
    # ========================================================================
    # Helper methods
    # ========================================================================
    
    @staticmethod
    def _calculate_returns(prices: List[float]) -> List[float]:
        """Calculate returns from price series."""
        if len(prices) < 2:
            return []
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        return returns
    
    @staticmethod
    def _pearson_correlation(x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient between two series."""
        if len(x) < 2 or len(y) < 2:
            return 0.0
        
        n = min(len(x), len(y))
        x = x[:n]
        y = y[:n]
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)
        
        denominator = math.sqrt(sum_sq_x * sum_sq_y)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    @staticmethod
    def _calculate_protocol_risk(
        protocol: str,
        tvl_usd: float,
        tvl_change_24h: float,
        tvl_trend: str,
        audit_status: str,
    ) -> float:
        """Calculate risk score for a protocol."""
        risk = 0.5  # baseline
        
        # TVL-based risk (lower TVL = higher risk)
        if tvl_usd < 100_000:
            risk += 0.25
        elif tvl_usd < 1_000_000:
            risk += 0.15
        elif tvl_usd < 10_000_000:
            risk += 0.05
        elif tvl_usd >= RiskEngine.MIN_TVL_FOR_LOW_RISK:
            risk -= 0.1
        
        # TVL trend risk
        if tvl_trend == "decreasing":
            risk += 0.15
        elif tvl_trend == "increasing":
            risk -= 0.05
        
        # 24h change risk (large outflows/inflows)
        if abs(tvl_change_24h) > 20:
            risk += 0.1
        elif abs(tvl_change_24h) > 50:
            risk += 0.15
        
        # Audit status risk
        if audit_status == "unaudited":
            risk += 0.2
        elif audit_status == "partial":
            risk += 0.1
        elif audit_status == "audited":
            risk -= 0.05
        
        # Protocol-specific adjustments
        high_risk_protocols = {"unproven", "newdex", "ponzi", "honeypot"}
        low_risk_protocols = {"aave", "compound", "morpho", "euler", "uniswap", "curve"}
        
        if protocol.lower() in high_risk_protocols:
            risk += 0.2
        elif protocol.lower() in low_risk_protocols:
            risk -= 0.1
        
        return max(0.0, min(1.0, risk))
    
    @staticmethod
    def _identify_protocol_risk_factors(
        protocol: str,
        tvl_usd: float,
        tvl_change_24h: float,
        tvl_trend: str,
        audit_status: str,
        positions: List[Position],
    ) -> List[str]:
        """Identify specific risk factors for a protocol."""
        factors = []
        
        if tvl_usd < 100_000:
            factors.append(f"Low TVL: ${tvl_usd:,.0f}")
        elif tvl_usd < 1_000_000:
            factors.append(f"Medium TVL: ${tvl_usd:,.0f}")
        
        if tvl_trend == "decreasing":
            factors.append("Declining TVL trend")
        
        if abs(tvl_change_24h) > 20:
            factors.append(f"Large TVL change: {tvl_change_24h:+.1f}%")
        
        if audit_status == "unaudited":
            factors.append("Protocol is unaudited")
        elif audit_status == "partial":
            factors.append("Partial audits")
        
        # IL risk for LP positions
        lp_positions = [p for p in positions if p.position_type == "lp"]
        if lp_positions:
            factors.append(f"Impermanent loss risk ({len(lp_positions)} LP positions)")
        
        return factors
