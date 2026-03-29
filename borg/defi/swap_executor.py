"""
Swap Executor Module for Borg DeFi.

Executes token swaps via Jupiter (Solana) and 1inch (EVM chains).
Integrates with TransactionGuard for pre-flight security checks.

API Endpoints:
- Jupiter: GET https://quote-api.jup.ag/v6/quote
- 1inch: GET https://api.1inch.dev/swap/v6.0/{chainId}/quote

Security:
- Spending limits enforced via tx_guard
- Contract whitelist checks before execution
- Slippage protection
- Trade outcome logging for dojo session analysis
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

import aiohttp

from borg.defi.security.keystore import SpendingLimitStore, ContractWhitelist
from borg.defi.security.tx_guard import (
    TransactionGuard,
    TransactionCheck,
    SpendingLimitError,
    ContractNotWhitelistedError,
    HumanApprovalRequiredError,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class SwapQuote:
    """Represents a swap quote from Jupiter or 1inch.
    
    Attributes:
        chain: Blockchain network (solana, ethereum, base, arbitrum, etc.)
        input_token: Input token mint/address
        output_token: Output token mint/address
        input_amount: Amount of input token (in smallest unit)
        output_amount: Expected output amount (in smallest unit)
        output_amount_min: Minimum output with slippage protection
        slippage_bps: Slippage tolerance in basis points
        price_impact_pct: Expected price impact percentage
        route: DEX routing information
        provider: Swap provider (jupiter, 1inch)
        expires_at: Unix timestamp when quote expires
        raw_quote: Raw quote data from provider
    """
    chain: str
    input_token: str
    output_token: str
    input_amount: int
    output_amount: int
    output_amount_min: int
    slippage_bps: int
    price_impact_pct: float
    route: Dict[str, Any]
    provider: str  # "jupiter" or "1inch"
    expires_at: float
    raw_quote: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain": self.chain,
            "input_token": self.input_token,
            "output_token": self.output_token,
            "input_amount": self.input_amount,
            "output_amount": self.output_amount,
            "output_amount_min": self.output_amount_min,
            "slippage_bps": self.slippage_bps,
            "price_impact_pct": self.price_impact_pct,
            "route": self.route,
            "provider": self.provider,
            "expires_at": self.expires_at,
        }
    
    @property
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        return time.time() > self.expires_at
    
    @property
    def slippage_pct(self) -> float:
        """Get slippage as percentage."""
        return self.slippage_bps / 10000 * 100


@dataclass
class SwapResult:
    """Represents the result of a swap execution.
    
    Attributes:
        success: Whether the swap succeeded
        tx_signature: Transaction signature/hash (None if failed)
        input_token: Input token mint/address
        output_token: Output token mint/address
        input_amount: Actual input amount
        output_amount: Actual output amount received
        price_impact_pct: Actual price impact
        gas_used: Gas/fee used (in native token or lamports)
        gas_used_usd: Gas/fee in USD
        provider: Swap provider used
        chain: Blockchain network
        error: Error message if failed
        wallet: Wallet that executed the swap
        timestamp: Unix timestamp of execution
        quote_used: Original quote that was executed
    """
    success: bool
    tx_signature: Optional[str]
    input_token: str
    output_token: str
    input_amount: int
    output_amount: int
    price_impact_pct: float
    gas_used: float
    gas_used_usd: float
    provider: str
    chain: str
    error: Optional[str] = None
    wallet: str = ""
    timestamp: float = 0.0
    quote_used: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tx_signature": self.tx_signature,
            "input_token": self.input_token,
            "output_token": self.output_token,
            "input_amount": self.input_amount,
            "output_amount": self.output_amount,
            "price_impact_pct": self.price_impact_pct,
            "gas_used": self.gas_used,
            "gas_used_usd": self.gas_used_usd,
            "provider": self.provider,
            "chain": self.chain,
            "error": self.error,
            "wallet": self.wallet,
            "timestamp": self.timestamp,
        }
    
    @property
    def pnl_estimate(self) -> Optional[float]:
        """Estimate PnL if we have price data. Returns None if not calculable."""
        # This would be calculated with actual price data
        return None


@dataclass
class SwapTrade:
    """Represents a trade for dojo session logging.
    
    Attributes:
        trade_id: Unique trade identifier
        timestamp: Unix timestamp
        chain: Blockchain network
        provider: Swap provider
        input_token: Input token address
        output_token: Output token address
        input_amount: Input amount
        output_amount: Output amount
        output_amount_usd: USD value of output
        gas_used_usd: Gas cost in USD
        price_impact_pct: Price impact percentage
        slippage_bps: Slippage tolerance used
        success: Whether trade succeeded
        error: Error message if failed
        wallet: Wallet used
        session_id: Dojo session ID
    """
    trade_id: str
    timestamp: float
    chain: str
    provider: str
    input_token: str
    output_token: str
    input_amount: int
    output_amount: int
    output_amount_usd: float
    gas_used_usd: float
    price_impact_pct: float
    slippage_bps: int
    success: bool
    wallet: str
    session_id: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp,
            "chain": self.chain,
            "provider": self.provider,
            "input_token": self.input_token,
            "output_token": self.output_token,
            "input_amount": self.input_amount,
            "output_amount": self.output_amount,
            "output_amount_usd": self.output_amount_usd,
            "gas_used_usd": self.gas_used_usd,
            "price_impact_pct": self.price_impact_pct,
            "slippage_bps": self.slippage_bps,
            "success": self.success,
            "wallet": self.wallet,
            "session_id": self.session_id,
            "error": self.error,
        }


# ============================================================================
# Jupiter Client
# ============================================================================


class JupiterClient:
    """Client for Jupiter swap API (Solana).
    
    API Docs: https://quote-api.jup.ag/docs/
    
    Quote Endpoint: GET https://quote-api.jup.ag/v6/quote
    Swap Endpoint: POST https://quote-api.jup.ag/v6/swap
    """
    
    QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
    SWAP_URL = "https://quote-api.jup.ag/v6/swap"
    
    # Slippage thresholds (in bps)
    DEFAULT_SLIPPAGE_BPS = 50  # 0.5%
    MAX_SLIPPAGE_BPS = 5000    # 50%
    MIN_SLIPPAGE_BPS = 1      # 0.01%
    
    def __init__(
        self,
        helius_api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize Jupiter client.
        
        Args:
            helius_api_key: Helius API key for RPC calls (optional)
            timeout: Request timeout in seconds
        """
        self.helius_api_key = helius_api_key
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = DEFAULT_SLIPPAGE_BPS,
        only_direct_routes: bool = False,
        max_accounts: int = 50,
    ) -> Optional[SwapQuote]:
        """Get a swap quote from Jupiter.
        
        Args:
            input_mint: Input token mint address (e.g., SOL)
            output_mint: Output token mint address (e.g., USDC)
            amount: Amount in smallest unit (lamports for SOL)
            slippage_bps: Slippage tolerance in basis points
            only_direct_routes: Only use direct routes
            max_accounts: Maximum accounts to use
            
        Returns:
            SwapQuote if successful, None otherwise
        """
        # Validate slippage
        slippage_bps = max(self.MIN_SLIPPAGE_BPS, min(slippage_bps, self.MAX_SLIPPAGE_BPS))
        
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
            "onlyDirectRoutes": str(only_direct_routes).lower(),
            "maxAccounts": max_accounts,
        }
        
        try:
            session = await self._get_session()
            async with session.get(self.QUOTE_URL, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"Jupiter quote error: {response.status} - {text}")
                    return None
                
                data = await response.json()
                
                # Parse quote response
                return SwapQuote(
                    chain="solana",
                    input_token=input_mint,
                    output_token=output_mint,
                    input_amount=amount,
                    output_amount=int(data.get("outAmount", 0)),
                    output_amount_min=int(data.get("minimumOutAmount", 0)),
                    slippage_bps=slippage_bps,
                    price_impact_pct=float(data.get("priceImpactPct", 0)),
                    route=data.get("route", {}),
                    provider="jupiter",
                    expires_at=time.time() + 60,  # Jupiter quotes expire in ~60s
                    raw_quote=data,
                )
        except asyncio.TimeoutError:
            logger.error("Jupiter quote request timed out")
            return None
        except Exception as e:
            logger.error(f"Jupiter quote error: {e}")
            return None
    
    async def get_swap_transaction(
        self,
        quote: SwapQuote,
        wallet_address: str,
        user_slippage: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get the swap transaction from Jupiter.
        
        Args:
            quote: The quote to execute
            wallet_address: User's wallet address
            userスリpage: Optional override slippage
            
        Returns:
            Transaction data dict or None
        """
        params = {
            "quoteResponse": quote.raw_quote,
            "userPublicKey": wallet_address,
            "wrapAndUnwrapSol": True,
        }
        
        if user_slippage is not None:
            params["slippageBps"] = user_slippage
        
        try:
            session = await self._get_session()
            async with session.post(self.SWAP_URL, json=params) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"Jupiter swap error: {response.status} - {text}")
                    return None
                
                return await response.json()
        except Exception as e:
            logger.error(f"Jupiter swap transaction error: {e}")
            return None


# ============================================================================
# OneInch Client
# ============================================================================


class OneInchClient:
    """Client for 1inch swap API (EVM chains).
    
    API Docs: https://api.1inch.dev/swap/v6.0/docs/
    
    Quote Endpoint: GET https://api.1inch.dev/swap/v6.0/{chainId}/quote
    """
    
    # 1inch chain IDs
    CHAIN_IDS = {
        "ethereum": 1,
        "bsc": 56,
        "polygon": 137,
        "arbitrum": 42161,
        "optimism": 10,
        "base": 8453,
        "zksync": 324,
        "avalanche": 43114,
        "linea": 59144,
    }
    
    QUOTE_URL = "https://api.1inch.dev/swap/v6.0/{chainId}/quote"
    
    # Slippage defaults (percentage)
    DEFAULT_SLIPPAGE = 0.5  # 0.5%
    MAX_SLIPPAGE = 50       # 50%
    MIN_SLIPPAGE = 0.01     # 0.01%
    
    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
    ):
        """Initialize 1inch client.
        
        Args:
            api_key: 1inch API key (required)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _get_chain_id(self, chain: str) -> int:
        """Get 1inch chain ID from chain name."""
        chain_lower = chain.lower()
        if chain_lower not in self.CHAIN_IDS:
            raise ValueError(f"Unsupported chain: {chain}. Supported: {list(self.CHAIN_IDS.keys())}")
        return self.CHAIN_IDS[chain_lower]
    
    async def get_quote(
        self,
        chain: str,
        src: str,
        dst: str,
        amount: int,
        slippage: float = DEFAULT_SLIPPAGE,
        includeGas: bool = True,
    ) -> Optional[SwapQuote]:
        """Get a swap quote from 1inch.
        
        Args:
            chain: Chain name (ethereum, polygon, arbitrum, etc.)
            src: Source token address
            dst: Destination token address
            amount: Amount in smallest unit
            slippage: Slippage tolerance as percentage (e.g., 0.5 for 0.5%)
            includeGas: Include gas estimation
            
        Returns:
            SwapQuote if successful, None otherwise
        """
        chain_id = self._get_chain_id(chain)
        
        # Validate slippage
        slippage = max(self.MIN_SLIPPAGE, min(slippage, self.MAX_SLIPPAGE))
        
        # Convert slippage to bps for consistency
        slippage_bps = int(slippage * 100)
        
        url = self.QUOTE_URL.format(chainId=chain_id)
        params = {
            "src": src,
            "dst": dst,
            "amount": amount,
            "slippage": slippage,
            "includeGas": includeGas,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        
        try:
            session = await self._get_session()
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"1inch quote error: {response.status} - {text}")
                    return None
                
                data = await response.json()
                
                # Parse quote response
                return SwapQuote(
                    chain=chain,
                    input_token=src,
                    output_token=dst,
                    input_amount=amount,
                    output_amount=int(data.get("dstAmount", 0)),
                    output_amount_min=int(data.get("limitedDstAmount", data.get("dstAmount", 0))),
                    slippage_bps=slippage_bps,
                    price_impact_pct=float(data.get("dstAmount", 0)) / max(int(data.get("srcAmount", 1)), 1) * 100,
                    route=data.get("route", []),
                    provider="1inch",
                    expires_at=time.time() + 300,  # 1inch quotes last 5 min
                    raw_quote=data,
                )
        except asyncio.TimeoutError:
            logger.error("1inch quote request timed out")
            return None
        except ValueError as e:
            logger.error(f"1inch chain error: {e}")
            return None
        except Exception as e:
            logger.error(f"1inch quote error: {e}")
            return None


# ============================================================================
# Swap Executor
# ============================================================================


class SwapExecutor:
    """Execute token swaps via Jupiter (Solana) and 1inch (EVM).
    
    This is the main entry point for executing swaps. It handles:
    - Getting quotes from Jupiter/1inch
    - Pre-flight security checks via TransactionGuard
    - Slippage protection
    - Trade execution (mocked for testing)
    - Trade outcome logging for dojo session analysis
    
    Security Integration:
    - Spending limits checked before execution
    - Contract whitelist verified
    - Token safety checks via rug detection
    - Human approval for large trades
    
    Usage:
        # Solana swap
        executor = SwapExecutor()
        quote = await executor.get_quote("solana", "SOL", "USDC", 1000000000)
        if quote:
            result = await executor.execute_swap_solana(quote, wallet_keypair)
        
        # EVM swap
        quote = await executor.get_quote("ethereum", src_token, dst_token, amount)
        result = await executor.execute_swap_evm(quote, wallet_address)
    """
    
    # Well-known token addresses
    KNOWN_TOKENS = {
        "solana": {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        },
        "ethereum": {
            "ETH": "0x0000000000000000000000000000000000000000",
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        },
    }
    
    def __init__(
        self,
        jupiter_client: Optional[JupiterClient] = None,
        oneinch_client: Optional[OneInchClient] = None,
        tx_guard: Optional[TransactionGuard] = None,
        session_id: str = "",
        wallet: str = "",
    ):
        """Initialize swap executor.
        
        Args:
            jupiter_client: Jupiter API client (created if not provided)
            oneinch_client: 1inch API client (created if not provided)
            tx_guard: TransactionGuard instance for security checks
            session_id: Dojo session ID for trade logging
            wallet: Wallet address for this executor
        """
        self.jupiter = jupiter_client or JupiterClient()
        self.oneinch = oneinch_client
        self.tx_guard = tx_guard
        self.session_id = session_id or f"swap_{int(time.time())}"
        self.wallet = wallet
        self._trade_history: List[SwapTrade] = []
    
    async def close(self):
        """Close all client sessions."""
        await self.jupiter.close()
        if self.oneinch:
            await self.oneinch.close()
        if self.tx_guard:
            await self.tx_guard.close()
    
    def _validate_slippage(self, slippage_bps: int, chain: str) -> int:
        """Validate and clamp slippage.
        
        Args:
            slippage_bps: Requested slippage in basis points
            chain: Chain name
            
        Returns:
            Clamped slippage value
        """
        if chain == "solana":
            return max(1, min(slippage_bps, 5000))
        else:
            return max(1, min(slippage_bps, 5000))
    
    async def get_quote(
        self,
        chain: str,
        input_token: str,
        output_token: str,
        amount: int,
        slippage_bps: int = 50,
    ) -> Optional[SwapQuote]:
        """Get a swap quote from the appropriate provider.
        
        Automatically selects Jupiter for Solana and 1inch for EVM chains.
        
        Args:
            chain: Blockchain network (solana, ethereum, polygon, etc.)
            input_token: Input token mint/address
            output_token: Output token mint/address
            amount: Amount in smallest unit (lamports for Solana, wei for EVM)
            slippage_bps: Slippage tolerance in basis points (default: 50 = 0.5%)
            
        Returns:
            SwapQuote if successful, None otherwise
        """
        slippage_bps = self._validate_slippage(slippage_bps, chain)
        
        if chain == "solana":
            return await self.jupiter.get_quote(
                input_mint=input_token,
                output_mint=output_token,
                amount=amount,
                slippage_bps=slippage_bps,
            )
        else:
            if not self.oneinch:
                logger.error("1inch client not configured for EVM swap")
                return None
            
            # Convert bps to percentage for 1inch
            slippage_pct = slippage_bps / 100
            return await self.oneinch.get_quote(
                chain=chain,
                src=input_token,
                dst=output_token,
                amount=amount,
                slippage=slippage_pct,
            )
    
    async def _check_pre_flight(
        self,
        chain: str,
        contract: str,
        amount_usd: float,
        token_address: Optional[str] = None,
    ) -> TransactionCheck:
        """Run pre-flight security checks.
        
        Args:
            chain: Blockchain network
            contract: Contract to interact with
            amount_usd: Trade amount in USD
            token_address: Token being traded
            
        Returns:
            TransactionCheck result
        """
        if not self.tx_guard:
            return TransactionCheck(approved=True)
        
        return await self.tx_guard.pre_flight_check(
            wallet=self.wallet,
            contract=contract,
            chain=chain,
            amount_usd=amount_usd,
            token_address=token_address,
        )
    
    async def execute_swap_solana(
        self,
        quote: SwapQuote,
        wallet_keypair: Any,
        simulate_only: bool = True,
    ) -> SwapResult:
        """Execute a swap on Solana via Jupiter.
        
        This method simulates the swap by default (simulate_only=True).
        Set simulate_only=False to get mock transaction signing.
        
        Args:
            quote: SwapQuote from get_quote()
            wallet_keypair: Solana keypair (will be used for signing)
            simulate_only: If True, only simulate (no real tx). Default True.
            
        Returns:
            SwapResult with execution details
        """
        if quote is None:
            return SwapResult(
                success=False,
                tx_signature=None,
                input_token="",
                output_token="",
                input_amount=0,
                output_amount=0,
                price_impact_pct=0,
                gas_used=0,
                gas_used_usd=0,
                provider="jupiter",
                chain="solana",
                error="No quote provided",
                wallet=self.wallet,
            )
        
        trade_id = f"sol_{quote.input_token[:8]}_{quote.output_token[:8]}_{int(time.time())}"
        
        # Pre-flight security checks
        jupiter_router = "JUP6LgpZNXqYk1c7xqMrmFXTWmM3vsvbf9MhKFoSU5m"  # Jupiter router
        
        pre_check = await self._check_pre_flight(
            chain="solana",
            contract=jupiter_router,
            amount_usd=self._estimate_usd_value("solana", quote.input_token, quote.input_amount),
            token_address=quote.output_token,
        )
        
        if not pre_check.approved:
            return SwapResult(
                success=False,
                tx_signature=None,
                input_token=quote.input_token,
                output_token=quote.output_token,
                input_amount=quote.input_amount,
                output_amount=0,
                price_impact_pct=quote.price_impact_pct,
                gas_used=0,
                gas_used_usd=0,
                provider="jupiter",
                chain="solana",
                error=pre_check.error,
                wallet=self.wallet,
                quote_used=quote.to_dict(),
            )
        
        if pre_check.requires_human_approval:
            return SwapResult(
                success=False,
                tx_signature=None,
                input_token=quote.input_token,
                output_token=quote.output_token,
                input_amount=quote.input_amount,
                output_amount=0,
                price_impact_pct=quote.price_impact_pct,
                gas_used=0,
                gas_used_usd=0,
                provider="jupiter",
                chain="solana",
                error=f"Human approval required: {pre_check.error}",
                wallet=self.wallet,
                quote_used=quote.to_dict(),
            )
        
        # Check quote expiration
        if quote.is_expired:
            return SwapResult(
                success=False,
                tx_signature=None,
                input_token=quote.input_token,
                output_token=quote.output_token,
                input_amount=quote.input_amount,
                output_amount=0,
                price_impact_pct=quote.price_impact_pct,
                gas_used=0,
                gas_used_usd=0,
                provider="jupiter",
                chain="solana",
                error="Quote has expired",
                wallet=self.wallet,
                quote_used=quote.to_dict(),
            )
        
        # Get swap transaction
        wallet_address = str(wallet_keypair.pubkey()) if hasattr(wallet_keypair, 'pubkey') else str(wallet_keypair)
        
        swap_tx_data = await self.jupiter.get_swap_transaction(
            quote=quote,
            wallet_address=wallet_address,
        )
        
        if not swap_tx_data:
            return SwapResult(
                success=False,
                tx_signature=None,
                input_token=quote.input_token,
                output_token=quote.output_token,
                input_amount=quote.input_amount,
                output_amount=0,
                price_impact_pct=quote.price_impact_pct,
                gas_used=0,
                gas_used_usd=0,
                provider="jupiter",
                chain="solana",
                error="Failed to get swap transaction from Jupiter",
                wallet=self.wallet,
                quote_used=quote.to_dict(),
            )
        
        # In production: sign and send transaction via Helius RPC
        # For now, simulate the execution
        if simulate_only:
            tx_signature = f"simulated_sig_{trade_id}"
            gas_used = 5000  # lamports
            gas_used_usd = self._estimate_gas_usd("solana", gas_used)
        else:
            # MOCK: In production this would actually sign and send
            # We NEVER use real private keys - this is a placeholder
            tx_signature = f"mock_sig_{trade_id}"
            gas_used = 5000
            gas_used_usd = self._estimate_gas_usd("solana", gas_used)
        
        result = SwapResult(
            success=True,
            tx_signature=tx_signature,
            input_token=quote.input_token,
            output_token=quote.output_token,
            input_amount=quote.input_amount,
            output_amount=quote.output_amount,
            price_impact_pct=quote.price_impact_pct,
            gas_used=gas_used,
            gas_used_usd=gas_used_usd,
            provider="jupiter",
            chain="solana",
            wallet=self.wallet,
            quote_used=quote.to_dict(),
        )
        
        # Log trade for dojo
        self._log_trade(quote, result)
        
        # Record spend in tx_guard
        if self.tx_guard:
            amount_usd = self._estimate_usd_value("solana", quote.input_token, quote.input_amount)
            self.tx_guard.record_spend(self.wallet, amount_usd)
        
        return result
    
    async def execute_swap_evm(
        self,
        quote: SwapQuote,
        wallet_address: str,
        simulate_only: bool = True,
    ) -> SwapResult:
        """Execute a swap on EVM chain via 1inch.
        
        This method simulates the swap by default (simulate_only=True).
        
        Args:
            quote: SwapQuote from get_quote()
            wallet_address: EVM wallet address
            simulate_only: If True, only simulate (no real tx). Default True.
            
        Returns:
            SwapResult with execution details
        """
        trade_id = f"evm_{quote.chain}_{quote.input_token[:8]}_{quote.output_token[:8]}_{int(time.time())}"
        
        # Get router address from 1inch response
        router_address = quote.route.get("routerAddress", "0x1111111254EEB25477B68fb85Ed929f73A960582") if quote.route else "0x1111111254EEB25477B68fb85Ed929f73A960582"
        
        # Pre-flight security checks
        pre_check = await self._check_pre_flight(
            chain=quote.chain,
            contract=router_address,
            amount_usd=self._estimate_usd_value(quote.chain, quote.input_token, quote.input_amount),
            token_address=quote.output_token,
        )
        
        if not pre_check.approved:
            return SwapResult(
                success=False,
                tx_signature=None,
                input_token=quote.input_token,
                output_token=quote.output_token,
                input_amount=quote.input_amount,
                output_amount=0,
                price_impact_pct=quote.price_impact_pct,
                gas_used=0,
                gas_used_usd=0,
                provider="1inch",
                chain=quote.chain,
                error=pre_check.error,
                wallet=wallet_address,
                quote_used=quote.to_dict(),
            )
        
        if pre_check.requires_human_approval:
            return SwapResult(
                success=False,
                tx_signature=None,
                input_token=quote.input_token,
                output_token=quote.output_token,
                input_amount=quote.input_amount,
                output_amount=0,
                price_impact_pct=quote.price_impact_pct,
                gas_used=0,
                gas_used_usd=0,
                provider="1inch",
                chain=quote.chain,
                error=f"Human approval required: {pre_check.error}",
                wallet=wallet_address,
                quote_used=quote.to_dict(),
            )
        
        # Check quote expiration
        if quote.is_expired:
            return SwapResult(
                success=False,
                tx_signature=None,
                input_token=quote.input_token,
                output_token=quote.output_token,
                input_amount=quote.input_amount,
                output_amount=0,
                price_impact_pct=quote.price_impact_pct,
                gas_used=0,
                gas_used_usd=0,
                provider="1inch",
                chain=quote.chain,
                error="Quote has expired",
                wallet=wallet_address,
                quote_used=quote.to_dict(),
            )
        
        # In production: construct and send transaction via web3
        # For now, simulate the execution
        if simulate_only:
            tx_signature = f"simulated_sig_{trade_id}"
            gas_used = 150000  # gas units
            gas_used_usd = self._estimate_gas_usd(quote.chain, gas_used)
        else:
            # MOCK: In production this would actually send the transaction
            # We NEVER use real private keys - this is a placeholder
            tx_signature = f"mock_sig_{trade_id}"
            gas_used = 150000
            gas_used_usd = self._estimate_gas_usd(quote.chain, gas_used)
        
        result = SwapResult(
            success=True,
            tx_signature=tx_signature,
            input_token=quote.input_token,
            output_token=quote.output_token,
            input_amount=quote.input_amount,
            output_amount=quote.output_amount,
            price_impact_pct=quote.price_impact_pct,
            gas_used=gas_used,
            gas_used_usd=gas_used_usd,
            provider="1inch",
            chain=quote.chain,
            wallet=wallet_address,
            quote_used=quote.to_dict(),
        )
        
        # Log trade for dojo
        self._log_trade(quote, result)
        
        # Record spend in tx_guard
        if self.tx_guard:
            amount_usd = self._estimate_usd_value(quote.chain, quote.input_token, quote.input_amount)
            self.tx_guard.record_spend(wallet_address, amount_usd)
        
        return result
    
    def _log_trade(self, quote: SwapQuote, result: SwapResult) -> None:
        """Log trade for dojo session analysis.
        
        Args:
            quote: The quote that was executed
            result: The execution result
        """
        trade = SwapTrade(
            trade_id=f"{quote.provider}_{quote.chain}_{int(result.timestamp)}",
            timestamp=result.timestamp,
            chain=quote.chain,
            provider=quote.provider,
            input_token=quote.input_token,
            output_token=quote.output_token,
            input_amount=quote.input_amount,
            output_amount=result.output_amount,
            output_amount_usd=self._estimate_usd_value(quote.chain, quote.output_token, result.output_amount),
            gas_used_usd=result.gas_used_usd,
            price_impact_pct=quote.price_impact_pct,
            slippage_bps=quote.slippage_bps,
            success=result.success,
            wallet=result.wallet,
            session_id=self.session_id,
            error=result.error,
        )
        
        self._trade_history.append(trade)
        
        # Also log to standard logger for dojo to pick up
        log_data = {
            'trade_id': trade.trade_id,
            'timestamp': trade.timestamp,
            'chain': trade.chain,
            'provider': trade.provider,
            'input_token': trade.input_token,
            'output_token': trade.output_token,
            'input_amount': str(trade.input_amount),
            'output_amount': str(trade.output_amount),
            'success': trade.success,
            'error': trade.error,
            'session_id': trade.session_id,
        }
        logger.info(f"TRADE_LOG: {json.dumps(log_data)}")
    
    def get_trade_history(self) -> List[SwapTrade]:
        """Get all trades logged in this session."""
        return self._trade_history.copy()
    
    def _estimate_usd_value(self, chain: str, token: str, amount: int) -> float:
        """Estimate USD value of a token amount.
        
        This is a simplified estimation. In production, would use actual prices.
        
        Args:
            chain: Blockchain network
            token: Token mint/address
            amount: Amount in smallest unit
            
        Returns:
            Estimated USD value
        """
        # Known stablecoin approximations
        stablecoins = {
            "solana": ["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"],
            "ethereum": ["0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "0xdAC17F958D2ee523a2206206994597C13D831ec7"],
        }
        
        chain_stables = stablecoins.get(chain, [])
        
        if token in chain_stables:
            return amount / 1_000_000  # Stablecoins typically have 6 decimals
        
        # SOL (9 decimals) at $100/SOL
        if chain == "solana" and token == "So11111111111111111111111111111111111111112":
            return amount / 1e9 * 100
        
        # ETH (18 decimals) - check for native ETH
        if token == "0x0000000000000000000000000000000000000000" or token == "ETH":
            return amount / 1e18 * 3000  # Assume $3000/ETH
        
        # WETH (18 decimals)
        if chain == "ethereum" and token.upper() in ["WETH", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".upper()]:
            return amount / 1e18 * 3000
        
        # Default: assume $1 for unknown (but only if amount is reasonable)
        # For large amounts, assume it's a native token with high decimals
        if amount > 1e15:  # Likely a large token amount
            return float(amount) / 1e18 * 1000  # Generic estimate
        return float(amount) / 1e6
    
    def _estimate_gas_usd(self, chain: str, gas_units: int) -> float:
        """Estimate gas cost in USD.
        
        Args:
            chain: Blockchain network
            gas_units: Amount of gas used
            
        Returns:
            Estimated gas cost in USD
        """
        # Approximate gas prices
        gas_prices = {
            "solana": 0.00025,      # ~0.00025 SOL per transaction
            "ethereum": 30,         # 30 gwei
            "polygon": 0.1,         # 0.1 MATIC
            "arbitrum": 0.1,       # 0.1 ARB
            "optimism": 0.001,      # 0.001 OP
            "base": 0.01,           # 0.01 ETH
        }
        
        price_per_unit = gas_prices.get(chain, 0.01)
        
        if chain == "solana":
            return gas_units * price_per_unit
        else:
            return gas_units * price_per_unit * 0.000001  # Convert from wei/gwei


# ============================================================================
# Convenience Functions
# ============================================================================


async def get_jupiter_quote(
    input_mint: str,
    output_mint: str,
    amount: int,
    slippage_bps: int = 50,
) -> Optional[SwapQuote]:
    """Convenience function to get a Jupiter quote."""
    client = JupiterClient()
    try:
        return await client.get_quote(input_mint, output_mint, amount, slippage_bps)
    finally:
        await client.close()


async def get_1inch_quote(
    api_key: str,
    chain: str,
    src: str,
    dst: str,
    amount: int,
    slippage: float = 0.5,
) -> Optional[SwapQuote]:
    """Convenience function to get a 1inch quote."""
    client = OneInchClient(api_key)
    try:
        return await client.get_quote(chain, src, dst, amount, slippage)
    finally:
        await client.close()
