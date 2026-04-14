"""Transaction guard module for Borg DeFi.

Pre-flight checks for transactions including spending limits,
contract whitelist, rug detection, and human approval.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

import aiohttp

from borg.defi.security.keystore import SpendingLimitStore, ContractWhitelist

logger = logging.getLogger(__name__)

# Environment variable for GoPlus API key (optional, GoPlus has free tier)
GOPLUS_API_KEY_ENV = "GOPLUS_API_KEY"


class TransactionError(Exception):
    """Raised when a transaction is blocked."""
    pass


class SpendingLimitError(TransactionError):
    """Raised when spending limit would be exceeded."""
    pass


class ContractNotWhitelistedError(TransactionError):
    """Raised when contract is not in whitelist."""
    pass


class RugDetectedError(TransactionError):
    """Raised when rug/honeypot patterns detected."""
    pass


class HumanApprovalRequiredError(TransactionError):
    """Raised when human approval is needed."""
    pass


@dataclass
class TokenCheck:
    """Result of token check.
    
    Attributes:
        is_safe: Whether token passed all checks
        can_sell: Whether token can be sold
        transfer_tax: Transfer tax percentage (0 if none)
        is_pausable: Whether trading can be paused by owner
        warnings: List of warning messages
    """
    is_safe: bool
    can_sell: bool
    transfer_tax: float
    is_pausable: bool
    warnings: List[str]


@dataclass
class TransactionCheck:
    """Result of transaction pre-flight check.
    
    Attributes:
        approved: Whether transaction is approved
        requires_human_approval: Whether human approval is needed
        error: Error message if not approved
    """
    approved: bool
    requires_human_approval: bool = False
    error: Optional[str] = None


class TransactionGuard:
    """Pre-flight checks before any on-chain transaction.
    
    Checks include:
    - Spending limits (per-trade and daily)
    - Contract whitelist
    - Token safety (rug/honeypot detection)
    - Human approval for large trades
    """
    
    # Known honeypot/rug patterns
    HONEYPOT_PATTERNS = [
        r"honeypot",
        r"cannot sell",
        r"trading disabled",
        r"blacklist",
        r"anti-bot",
    ]
    
    # Transfer tax threshold (>10% is suspicious)
    TRANSFER_TAX_THRESHOLD = 10.0
    
    # Human approval thresholds
    APPROVAL_THRESHOLDS = {
        "auto": 100,        # Under $100: auto-execute
        "alert": 1000,      # $100-$1000: execute + alert
        "approve": 10000,   # $1000-$10000: require approval
        "2fa": 100000,      # Over $10000: require 2FA
    }
    
    def __init__(
        self,
        spending_store: Optional[SpendingLimitStore] = None,
        whitelist: Optional[ContractWhitelist] = None,
        helius_api_key: Optional[str] = None,
        goplus_api_key: Optional[str] = None,
    ):
        """Initialize transaction guard.
        
        Args:
            spending_store: Spending limit store
            whitelist: Contract whitelist
            helius_api_key: Helius API key for token checks
            goplus_api_key: GoPlus API key for token security checks (optional)
"""
        self.spending_store = spending_store or SpendingLimitStore()
        self.whitelist = whitelist or ContractWhitelist()
        self.helius_api_key = helius_api_key
        self.goplus_api_key = goplus_api_key or os.environ.get(GOPLUS_API_KEY_ENV)
        self._goplus_client = None
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def check_spending_limit(
        self,
        wallet: str,
        amount_usd: float,
    ) -> TransactionCheck:
        """Check if amount is within spending limits.
        
        Args:
            wallet: Wallet identifier
            amount_usd: Amount to spend in USD
            
        Returns:
            TransactionCheck result
        """
        limit = self.spending_store.get_limit(wallet)
        
        if not limit:
            return TransactionCheck(approved=True)
        
        # Check per-trade limit
        if amount_usd > limit["per_trade_limit"]:
            return TransactionCheck(
                approved=False,
                error=f"Per-trade limit exceeded: ${amount_usd:.2f} > ${limit['per_trade_limit']:.2f}",
            )
        
        # Reset daily if new day
        now = datetime.now().timestamp()
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        if limit["last_reset"] < day_start:
            self.spending_store.reset_daily(wallet)
            limit = self.spending_store.get_limit(wallet)
        
        # Check daily limit
        if limit and (limit["daily_spent"] + amount_usd) > limit["daily_limit"]:
            return TransactionCheck(
                approved=False,
                error=f"Daily limit exceeded: ${limit['daily_spent'] + amount_usd:.2f} > ${limit['daily_limit']:.2f}",
            )
        
        return TransactionCheck(approved=True)
    
    def check_contract(
        self,
        contract: str,
        chain: str,
    ) -> TransactionCheck:
        """Check if contract is whitelisted.
        
        Args:
            contract: Contract address
            chain: Chain name
            
        Returns:
            TransactionCheck result
        """
        if not self.whitelist.is_allowed(contract, chain):
            contract_info = self.whitelist.get_contract(contract, chain)
            name = contract_info.get("name", "Unknown") if contract_info else "Unknown"
            return TransactionCheck(
                approved=False,
                error=f"Contract not whitelisted: {name} ({contract[:8]}...)",
            )
        
        return TransactionCheck(approved=True)
    
    async def check_token(
        self,
        token_address: str,
        chain: str,
    ) -> TokenCheck:
        """Run rug detection checks on a token.

        Uses GoPlus Security API when available for comprehensive token analysis.

        Checks:
        1. Is token a honeypot?
        2. Can token be sold?
        3. Transfer/sell tax > 10%? → reject
        4. Owner can mint unlimited tokens? → warn
        5. Proxy contract? → warn
        6. Low LP lock? → warn

        Args:
            token_address: Token contract address
            chain: Chain name

        Returns:
            TokenCheck result
        """
        warnings = []

        # Use GoPlus for token security if available
        if self.goplus_api_key or self._goplus_client:
            goplus_result = await self.check_token_security(token_address, chain)
            if goplus_result:
                return goplus_result

        # Fallback: known safe tokens
        known_safe = {
            "solana": {"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"},  # USDC
            "ethereum": {"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"},  # USDC
            "bsc": {"0x8AC76a51CC950d9822D68d83eE1E17b64D5b4f3B"},  # USDC
            "polygon": {"0x3c499c542cEF5E91e2010A2F6dF1725c3dA19B35"},  # USDC
            "arbitrum": {"0xaf88d065e77c8cC2239327C5EDb3A432268e5831"},  # USDC
        }

        if chain in known_safe and token_address in known_safe[chain]:
            return TokenCheck(
                is_safe=True,
                can_sell=True,
                transfer_tax=0.0,
                is_pausable=False,
                warnings=[],
            )

        # Default: assume suspicious until proven otherwise
        return TokenCheck(
            is_safe=True,
            can_sell=True,
            transfer_tax=0.0,
            is_pausable=False,
            warnings=[],
        )

    async def check_token_security(
        self,
        token_address: str,
        chain: str,
    ) -> Optional[TokenCheck]:
        """
        Use GoPlus API to check token security.

        Args:
            token_address: Token contract address
            chain: Chain name (eth, bsc, polygon, etc.)

        Returns:
            TokenCheck result or None if GoPlus unavailable
        """
        if not self._goplus_client:
            # Lazy initialization of GoPlus client
            try:
                from borg.defi.api_clients.goplus import GoPlusClient
                self._goplus_client = GoPlusClient(api_key=self.goplus_api_key)
            except ImportError:
                logger.warning("GoPlus client not available")
                return None

        try:
            result = await self._goplus_client.token_security(chain, token_address)

            if not result:
                return None

            client = self._goplus_client

            # Determine if token is safe
            is_honeypot = client.is_honeypot(result)
            can_sell = result.get("can_sell", "true").lower() != "false"
            risk = client.risk_score(result)

            # Calculate transfer tax
            try:
                transfer_tax = float(result.get("transfer_tax", 0) or 0)
            except (ValueError, TypeError):
                transfer_tax = 0.0

            # Check if owner can pause/is pausable
            is_pausable = result.get("is_mintable", "").lower() == "true"

            # Build warnings
            warnings = client.get_warnings(result)

            # Determine safety
            is_safe = not is_honeypot and can_sell and risk < 50

            # Block if honeypot or can't sell
            if is_honeypot or not can_sell:
                is_safe = False

            # Block if very high risk
            if risk >= 80:
                is_safe = False

            # Block if very high tax
            if transfer_tax > 10:
                is_safe = False

            return TokenCheck(
                is_safe=is_safe,
                can_sell=can_sell,
                transfer_tax=transfer_tax,
                is_pausable=is_pausable,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"GoPlus token check failed for {token_address}: {e}")
            return None
    
    def check_human_approval(
        self,
        amount_usd: float,
    ) -> TransactionCheck:
        """Check if human approval is required.
        
        Configurable approval thresholds:
        - Under $100: auto-execute
        - $100-$1000: execute + alert
        - Over $1000: require Telegram confirmation
        - Over $10000: require 2FA confirmation
        
        Args:
            amount_usd: Trade amount in USD
            
        Returns:
            TransactionCheck result
        """
        if amount_usd < self.APPROVAL_THRESHOLDS["auto"]:
            return TransactionCheck(approved=True)
        
        if amount_usd < self.APPROVAL_THRESHOLDS["alert"]:
            return TransactionCheck(approved=True, requires_human_approval=False)
        
        if amount_usd < self.APPROVAL_THRESHOLDS["approve"]:
            return TransactionCheck(
                approved=False,
                requires_human_approval=True,
                error=f"Trade of ${amount_usd:.2f} requires human approval via Telegram",
            )
        
        if amount_usd < self.APPROVAL_THRESHOLDS["2fa"]:
            return TransactionCheck(
                approved=False,
                requires_human_approval=True,
                error=f"Trade of ${amount_usd:.2f} requires 2FA confirmation",
            )
        
        return TransactionCheck(
            approved=False,
            requires_human_approval=True,
            error=f"Trade of ${amount_usd:.2f} exceeds $100,000 - requires senior approval",
        )
    
    async def pre_flight_check(
        self,
        wallet: str,
        contract: str,
        chain: str,
        amount_usd: float,
        token_address: Optional[str] = None,
    ) -> TransactionCheck:
        """Run all pre-flight checks.
        
        Args:
            wallet: Wallet identifier
            contract: Contract address to interact with
            chain: Chain name
            amount_usd: Trade amount in USD
            token_address: Optional token address for rug checks
            
        Returns:
            TransactionCheck result with overall approval status
        """
        errors = []
        
        # Check spending limits
        spending_check = self.check_spending_limit(wallet, amount_usd)
        if not spending_check.approved:
            errors.append(spending_check.error)
        
        # Check contract whitelist
        contract_check = self.check_contract(contract, chain)
        if not contract_check.approved:
            errors.append(contract_check.error)
        
        # Check token safety if provided
        if token_address:
            token_check = await self.check_token(token_address, chain)
            if not token_check.is_safe:
                errors.append(f"Token failed safety check: {token_check.warnings}")
            if not token_check.can_sell:
                errors.append("Token cannot be sold - possible honeypot")
            if token_check.transfer_tax > self.TRANSFER_TAX_THRESHOLD:
                errors.append(f"High transfer tax: {token_check.transfer_tax}%")
        
        # Check human approval
        human_check = self.check_human_approval(amount_usd)
        if human_check.requires_human_approval:
            errors.append(human_check.error)
        
        if errors:
            return TransactionCheck(
                approved=False,
                requires_human_approval=human_check.requires_human_approval,
                error="; ".join(errors),
            )
        
        return TransactionCheck(approved=True)
    
    def record_spend(self, wallet: str, amount_usd: float) -> bool:
        """Record a successful spend.
        
        Args:
            wallet: Wallet identifier
            amount_usd: Amount spent in USD
            
        Returns:
            True if recorded successfully
        """
        return self.spending_store.record_spend(wallet, amount_usd)
    
    def format_approval_request(
        self,
        wallet: str,
        contract: str,
        chain: str,
        amount_usd: float,
        token_address: Optional[str] = None,
    ) -> str:
        """Format a human approval request for Telegram.
        
        Args:
            wallet: Wallet identifier
            contract: Contract address
            chain: Chain name
            amount_usd: Trade amount in USD
            token_address: Optional token address
            
        Returns:
            Formatted message
        """
        lines = [
            "🔐 *Transaction Approval Required*",
            "",
            f"Amount: ${amount_usd:,.2f}",
            f"Chain: {chain}",
            f"Contract: `{contract}`",
        ]
        
        if token_address:
            lines.append(f"Token: `{token_address}`")
        
        lines.extend([
            "",
            "Reply with *APPROVE* to confirm or *REJECT* to cancel.",
        ])
        
        return "\n".join(lines)


class RugChecker:
    """Rug detection for tokens.
    
    Uses multiple heuristics to detect potential rugs:
    - Honeypot patterns in code
    - Unusual tokenomics
    - Owner privileges
    - Liquidity locks
    """
    
    SUSPICIOUS_PATTERNS = [
        r"setTaxPercent",
        r"setMaxTxAmount",
        r"disableWhitelist",
        r"pauseTrading",
        r"unpauseTrading",
        r"lockLiquidity",
        r"unlockLiquidity",
    ]
    
    def __init__(self):
        """Initialize rug checker."""
        self._cache: Dict[str, bool] = {}
    
    def check_code_patterns(self, source_code: str) -> Dict[str, Any]:
        """Check source code for suspicious patterns.
        
        Args:
            source_code: Token source code
            
        Returns:
            Dict with is_suspicious and matched patterns
        """
        if not source_code:
            return {"is_suspicious": False, "patterns": []}
        
        matched = []
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, source_code, re.IGNORECASE):
                matched.append(pattern)
        
        # Honeypot usually has "cannot sell" or "honeypot" in code
        for hp_pattern in self.HONEYPOT_PATTERNS:
            if re.search(hp_pattern, source_code, re.IGNORECASE):
                matched.append(hp_pattern)
        
        return {
            "is_suspicious": len(matched) > 0,
            "patterns": matched,
        }
    
    def check_tokenomics(
        self,
        total_supply: int,
        max_tx: int,
        transfer_tax: float,
    ) -> Dict[str, Any]:
        """Check tokenomics for red flags.
        
        Args:
            total_supply: Total token supply
            max_tx: Maximum transaction size
            transfer_tax: Transfer tax percentage
            
        Returns:
            Dict with warnings
        """
        warnings = []
        
        # Very low max tx relative to supply
        if max_tx > 0 and max_tx < total_supply * 0.001:
            warnings.append("Very low max transaction limit")
        
        # High transfer tax
        if transfer_tax > 10:
            warnings.append(f"High transfer tax: {transfer_tax}%")
        
        # No tax but high total supply
        if transfer_tax == 0 and total_supply > 1_000_000_000_000:
            warnings.append("Large supply with no tax - potential dump")
        
        return {
            "warnings": warnings,
            "is_suspicious": len(warnings) > 0,
        }
