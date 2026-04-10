# DeFi API Landscape for Autonomous Agents

A comprehensive reference for DeFi infrastructure APIs needed by autonomous trading agents operating on Solana, EVM chains, and cross-chain environments.

---

## Table of Contents
1. [Solana APIs](#1-solana-apis)
   - [Jupiter API](#11-jupiter-api)
   - [Raydium API](#12-raydium-api)
   - [Orca API](#13-orca-api)
   - [Helius RPC](#14-helius-rpc)
   - [Birdeye API](#15-birdeye-api)
   - [DexScreener API](#16-dexscreener-api)
   - [Solscan API](#17-solscan-api)
2. [EVM APIs](#2-evm-apis)
   - [1inch API](#21-1inch-api)
   - [Uniswap SDK](#22-uniswap-sdk)
   - [Aave API](#23-aave-api)
   - [Compound API](#24-compound-api)
   - [The Graph](#25-the-graph)
   - [Alchemy](#26-alchemy)
   - [Infura](#27-infura)
3. [Cross-Chain APIs](#3-cross-chain-apis)
   - [LayerZero](#31-layerzero)
   - [Wormhole](#32-wormhole)
4. [Data & Analytics APIs](#4-data--analytics-apis)
   - [Dune Analytics API](#41-dune-analytics-api)
   - [DeFiLlama API](#42-defillama-api)
   - [Nansen](#43-nansen)
   - [Arkham Intelligence API](#44-arkham-intelligence-api)
5. [MEV Infrastructure](#5-mev-infrastructure)
   - [Flashbots](#51-flashbots)
   - [Jito (Solana MEV)](#52-jito-solana-mev)

---

## 1. Solana APIs

### 1.1 Jupiter API

**What It Provides**
- Swap aggregation across 100+ DEXs (Raydium, Orca, Meteora, Phoenix, etc.)
- Best price route discovery and execution
- Limit orders, DCA (dollar-cost averaging), and recurring orders
- Token metadata and price feeds
- MEV-protected transactions
- Gasless swaps for supported tokens

**Authentication**
- API key from [Jupiter Developer Portal](https://portal.jup.ag)
- Single API key unlocks all Jupiter APIs
- Key passed via `Authorization: Bearer <key>` header

**Rate Limits**
| Tier | Requests/Minute | Window | Cost |
|------|-----------------|--------|------|
| Free | 60 | 60 seconds | Free |
| Pro I | ~600 | 10 seconds | Paid/month |
| Pro II | ~3,000 | 10 seconds | Paid/month |
| Pro III | ~6,000 | 10 seconds | Paid/month |
| Ultra | Dynamic | Dynamic | Pay-per-use |

**Cost**
- Free tier available with rate-limited access
- Pro plans: paid monthly based on tier
- Ultra tier: pay-per-request model

**How an Agent Would Use It**
```python
# Get quote for SOL -> USDC swap
GET https://api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=1000000000&slippageBps=50

# Execute swap
POST https://api.jup.ag/v6/swap
Headers: { "Authorization": "Bearer <key>", "Content-Type": "application/json" }
Body: { "quoteResponse": {...}, "userPublicKey": "..." }
```

**Key Endpoints**
- `GET /v6/quote` - Get swap quote with routes
- `POST /v6/swap` - Execute swap transaction
- `GET /v6/price` - Token price lookup
- `GET /v6/tokens` - Token list with metadata
- `POST /v6/limit-instructions` - Create limit orders

**Documentation**: https://dev.jup.ag/

---

### 1.2 Raydium API

**What It Provides**
- Raydium CLMM (Concentrated Liquidity Market Maker) pools
- Standard AMM pools
- Liquidity provision and farm management
- Token swap execution
- Farm reward tracking
- Program accounts data

**Authentication**
- Public endpoints available (no auth for read operations)
- API key optional for higher rate limits
- WebSocket connections for real-time data

**Rate Limits**
- Public API: ~300 requests/minute
- Authenticated: Higher limits available
- Rate limits are per-IP and per-endpoint

**Cost**
- Free for public endpoints
- Higher tiers available for professional use

**How an Agent Would Use It**
```python
# Get pool info
GET https://api.raydium.io/v2/pool/<poolId>/info

# Get quote
GET https://api.raydium.io/v2/quote?inputMint=...&outputMint=...&amount=...

# Get farm positions
GET https://api.raydium.io/v2/farm/user/<ownerAddress>
```

**Key Endpoints**
- `GET /v2/pool/<poolId>/info` - Pool metadata and liquidity
- `GET /v2/quote` - Swap quote
- `GET /v2/farm/user/<address>` - User's farm positions
- `GET /v2/sdk/token/amount` - Token amounts

**Documentation**: https://docs.raydium.io/raydium/api-reference/

---

### 1.3 Orca API

**What It Provides**
- Whirlpools (Orca's CLMM format)
- Token swap quotes and execution
- Liquidity positions
- Price data
- Token metadata

**Authentication**
- Public API available
- Optional API key for analytics/premium features

**Rate Limits**
- Public endpoints: ~100 requests/minute
- Authenticated: Higher limits

**Cost**
- Free tier available
- Premium tiers for higher throughput

**How an Agent Would Use It**
```python
# Get whirlpool data
GET https://api.orca.so/v2/whirlpool/<whirlpoolPubkey>

# Get quote
GET https://api.orca.so/v2/quote?tokenMintA=...&tokenMintB=...&amount=...&feeBps=...
```

**Key Endpoints**
- `GET /v2/whirlpool/<pubkey>` - Whirlpool state
- `GET /v2/quote` - Swap quote
- `GET /v1/prices` - Token prices
- `GET /v1/positions/<owner>` - User positions

**Documentation**: https://docs.orca.so/

---

### 1.4 Helius RPC

**What It Provides**
- Solana RPC node access (full nodes, dedicated nodes)
- Enhanced API endpoints
- Webhook notifications
- Priority fee estimation
- Transaction解析
- Block data and confirmations
- NFT compression support
- DAS (Digital Asset Standard) API for token data
- LaserStream (low-latency shred delivery)
- Helius Sender (for transaction boosting)

**Authentication**
- API key from Helius dashboard
- Key passed via `Authorization` header or in RPC request

**Rate Limits**
- Free tier: Limited credits, ~100K credits/month
- Paid plans: Range from $50-$500+/month
- Credits consumed per API call (varies by endpoint)
- Example: Basic RPC calls ~1-10 credits, enhanced endpoints ~10-100 credits

**Cost**
| Plan | Price | Credits/Month |
|------|-------|---------------|
| Free | $0 | ~100K |
| Starter | $50/mo | ~5M |
| Pro | $200/mo | ~25M |
| Business | $500/mo | ~75M |
| Enterprise | Custom | Custom |

**How an Agent Would Use It**
```python
# Standard RPC call via Helius
POST https://mainnet.helius-rpc.com/
Headers: { "Authorization": "Bearer <helius-api-key>" }
Body: {
  "jsonrpc": "2.0",
  "id": 1,
  "method": "getAccountInfo",
  "params": ["<pubkey>", {"encoding": "base64"}]
}

# Get priority fees
GET https://api.helius.xyz/v0/priority-fees?api_key=<key>
```

**Special Features for Agents**
- **Gatekeeper**: Ultra-low latency transaction submission
- **Webhook Rebates**: Backrun transaction rebates
- **Enhanced Transactions API**: Parse transaction metadata
- **Websockets**: Real-time block and transaction updates

**Documentation**: https://docs.helius.xyz/

---

### 1.5 Birdeye API

**What It Provides**
- Multi-chain DEX price data
- Token swap quotes across DEXs
- Liquidity information
- Wallet portfolio tracking
- Trending tokens
- Security data (honeypot checks)
- Historical price charts

**Authentication**
- API key required
- Key from Birdeye dashboard

**Rate Limits**
- Free tier: 10 requests/second
- Pro tier: 50-100 requests/second
- Enterprise: Custom limits

**Cost**
- Free: Limited to 10 req/s, 100K calls/month
- Pro: $49-$499/month based on tier

**How an Agent Would Use It**
```python
# Get token price
GET https://public-api.birdeye.so/public/v1/token/price?address=<token>&chain=solana

# Get swap quote
GET https://public-api.birdeye.so/public/v1/swap?outputToken=<address>&inputAmount=1000000&chain=solana
```

**Key Endpoints**
- `GET /public/v1/token/price` - Token price
- `GET /public/v1/swap` - DEX swap quotes
- `GET /public/v1/token_metadata` - Token info
- `GET /private/v1/wallet/portfolio` - Wallet holdings

**Documentation**: https://docs.birdeye.so/

---

### 1.6 DexScreener API

**What It Provides**
- Real-time DEX pair data
- Token pair prices and liquidity
- Recent trades
- New token discoveries
- Pair price charts (OHLCV)
- Liquidity pool information
- Buys/sells in real-time

**Authentication**
- No API key required for basic endpoints
- API key available for higher limits

**Rate Limits**
- No auth: ~30 requests/minute
- With API key: Higher limits

**Cost**
- Free tier available
- Premium tiers for professional trading

**How an Agent Would Use It**
```python
# Get pair info by pair address
GET https://api.dexscreener.com/dex/pairs/solana/<pairAddress>

# Get latest pairs
GET https://api.dexscreener.com/dex/pairs/solana?sort=volume&order=desc

# Get price history
GET https://api.dexscreener.com/dex/pairs/solana/<pairAddress>/sparkline
```

**Key Endpoints**
- `GET /dex/pairs/solana` - List pairs on Solana
- `GET /dex/pairs/solana/<pairAddress>` - Single pair data
- `GET /dex/tokens/solana/<tokenAddress>` - Token pair data
- Real-time trade feed via WebSocket

**Documentation**: https://docs.dexscreener.com/

---

### 1.7 Solscan API

**What It Provides**
- Complete Solana blockchain data
- Token metadata and balances
- Transaction details and history
- NFT data
- Token transfers
- Account information
- Staking data
- DeFi protocol interactions

**Authentication**
- Free tier: No auth required
- Pro tier: API key required

**Rate Limits**
- Free: 30 requests/minute
- Pro: 300 requests/minute
- Enterprise: Custom

**Cost**
- Free tier available
- Pro: ~$29-99/month

**How an Agent Would Use It**
```python
# Get account info
GET https://api.solscan.io/v2/account?address=<pubkey>

# Get token holders
GET https://api.solscan.io/v2/token/holders?tokenAddress=<mint>

# Get transaction details
GET https://api.solscan.io/v2/transaction/<txSig>
```

**Key Endpoints**
- `GET /v2/account` - Account data
- `GET /v2/token/holders` - Token holder list
- `GET /v2/transaction/<txId>` - Transaction details
- `GET /v2/staking/rewards` - Staking rewards

**Documentation**: https://api.solscan.io/docs

---

## 2. EVM APIs

### 2.1 1inch API

**What It Provides**
- DEX aggregation across 100+ sources
- Best price route discovery
- Swap execution
- Quote validation
- Token approval tracking
- Liquidity source data
-gas estimation

**Authentication**
- API key from 1inch developer portal
- Free tier available
- Key passed in header or query param

**Rate Limits**
| Tier | Requests/Minute | Cost |
|------|-----------------|------|
| Free | 60 | Free |
| Base | 300 | $50/month |
| Pro | 1,000 | $200/month |
| Enterprise | Custom | Custom |

**Cost**
- Free tier: Limited to 60 req/min
- Paid tiers: Start at $50/month

**How an Agent Would Use It**
```python
# Get quote
GET https://api.1inch.dev/swap/v6.0/1/quote?src=<token>&dst=<token>&amount=<amount>&protocols=<protocols>

# Get swap data
GET https://api.1inch.dev/swap/v6.0/1/ swap?src=<token>&dst=<token>&amount=<amount>&from=<wallet>&slippage=<bps>

# Get tokens (allowance, etc.)
GET https://api.1inch.dev/swap/v6.0/1/approve/transaction?token=<token>
```

**Key Endpoints**
- `GET /swap/v6.0/{chainId}/quote` - Get quote
- `GET /swap/v6.0/{chainId}/swap` - Get swap calldata
- `POST /swap/v5.2/{chainId}/quote` - Advanced quote (POST body)
- `GET /approve/transaction` - Get approval tx
- `GET /tokens` - Supported token list

**Documentation**: https://docs.1inch.dev/

---

### 2.2 Uniswap SDK

**What It Provides**
- V2 and V3 pool data
- Price quotes
- Route calculation
- Smart order routing
- Liquidity provision
- Flash swaps
- Pool state data

**Authentication**
- No API key needed for read operations
- Requires RPC provider (Infura, Alchemy, etc.) for Ethereum calls

**Rate Limits**
- No direct rate limits on SDK
- Rate limits depend on RPC provider

**Cost**
- Free to use
- Requires Ethereum node access (Alchemy/Infura)

**How an Agent Would Use It**
```typescript
import { ethers } from 'ethers';
import { Token, CurrencyAmount, TradeType, Route } from '@uniswap/sdk-core';
import { Pair, Trade } from '@uniswap/v2-sdk';
import { Pool } from '@uniswap/v3-sdk';

// Example: Get quote using Uniswap SDK
const tokenA = new Token(1, '0x...', 18); // ETH
const tokenB = new Token(1, '0x...', 18); // USDC
const pair = await Pair.getReserves(...);
const route = new Route([pair], tokenA, tokenB);
const trade = Trade.createUncheckedTrade({
  route,
  inputAmount: CurrencyAmount.fromRawAmount(tokenA, '1000000000000000000'),
  outputAmount: CurrencyAmount.fromRawAmount(tokenB, '2000000000'),
  tradeType: TradeType.EXACT_INPUT,
});
```

**SDK Packages**
- `@uniswap/sdk-core` - Core types
- `@uniswap/v2-sdk` - V2 AMM
- `@uniswap/v3-sdk` - V3 concentrated liquidity
- `@uniswap/smart-order-router` - Auto router

**Documentation**: https://docs.unisplug.org/

---

### 2.3 Aave API

**What It Provides**
- Reserve data (asset parameters)
- User positions and health factor
- Lending and borrowing rates
- Collateral management
- Liquidation data
- Incentive rewards
- V3 Perps (Aave Arc)

**Authentication**
- Public data endpoints free
- Protected endpoints require API key for rate limiting
- GraphQL API available

**Rate Limits**
- Free: Rate limited
- Power users: Higher limits with auth
- Flash loans: No rate limit (gas-dependent)

**Cost**
- Free for public data
- No mandatory paid tier

**How an Agent Would Use It**
```python
# GraphQL endpoint
POST https://api.thegraph.com/subgraphs/name/aave/v3

# REST endpoints
GET https://aave-api-mainnet.protofire.io/v2/reserves
GET https://aave-api-mainnet.protofire.io/v2/users/<address>

# V3 GraphQL
POST https://gateway.thegraph.com/api/<api-key>/subgraphs/id/...
```

**Key Endpoints**
- `GET /v2/reserves` - All reserve data
- `GET /v2/users/<address>` - User positions
- `GET /v2/health-factor/<address>` - User health factor
- GraphQL: Full protocol state queries

**Key Queries for Agents**
```graphql
query {
  reserves(first: 10) {
    id
    symbol
    liquidityRate
    variableBorrowRate
    stableBorrowRate
    availableLiquidity
  }
}
```

**Documentation**: https://docs.aave.com/developers

---

### 2.4 Compound API

**What It Provides**
- Market data (cToken prices, rates)
- User positions and balances
- Supply/borrow rates
- Market liquidity
- Governance data
- Rewards calculation

**Authentication**
- Public endpoints available
- API key for higher rate limits

**Rate Limits**
- Public: ~10 requests/second
- Authenticated: Higher limits

**Cost**
- Free tier available
- Compound III (Comet) requires RPC

**How an Agent Would Use It**
```python
# Get markets
GET https://api.compound.finance/v2/comp APR

# Get account liquidity
GET https://api.compound.finance/v2/account/<address>

# CToken interaction
GET https://api.compound.finance/v2/ctoken

# Comet (V3) via subgraph
POST https://gateway.thegraph.com/api/<key>/subgraphs/id/...
```

**Key Endpoints**
- `GET /v2/comp APR` - Supply/borrow rates
- `GET /v2/account/<address>` - User positions
- `GET /v2/ctoken` - CToken metadata
- `GET /v2/governance/proposals` - DAO proposals

**Documentation**: https://docs.compound.finance/

---

### 2.5 The Graph

**What It Provides**
- Decentralized indexing protocol
- Subgraph data for 100s of protocols
- Historical on-chain data
- Custom queries via GraphQL
- Real-time updates via subscriptions

**Authentication**
- Free tier: Public API endpoints
- Premium: API key required
- Graph Protocol API key from dashboard

**Rate Limits**
| Tier | Requests/Second | Cost |
|------|-----------------|------|
| Free | 10 | Free |
| Starter | 100 | $75/month |
| Pay as you grow | 1000+ | $0.0003/req |

**Cost**
- Free tier with 10 req/s
- Paid tiers from $75/month

**How an Agent Would Use It**
```graphql
# Example: Get Uniswap V3 pool data
query {
  pool(id: "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8") {
    token0 { symbol }
    token1 { symbol }
    feeTier
    liquidity
    sqrtPrice
    tick
  }
}

# POST to:
POST https://gateway.thegraph.com/api/<key>/subgraphs/id/...
```

**Popular Subgraphs**
- Uniswap V3: `5zvR8u6kFBjBg4UsJTYE3N93my - 5yG"
- Aave V3: `ZX4m24bskfWWZN8DHFwFtyY3"
- Compound: `nmM5MDHhHDisEn - 2gZ4
- SushiSwap: "3Ukh1sfGSW8WD" oN9X

**Documentation**: https://thegraph.com/docs/en/

---

### 2.6 Alchemy

**What It Provides**
- Ethereum RPC (all EVM chains)
- Enhanced APIs (Transfers, NFTs, Token)
- Webhook notifications ( Notify API)
- Smart wallet infrastructure
- MEV protection via Flashbots
- NFT API with rarity
- Composer (no-code transaction builder)
- Tracing and debug APIs

**Authentication**
- API key from Alchemy dashboard
- Free tier available
- Key in all requests

**Rate Limits**
| Plan | Calls/Second | Compute Units |
|------|--------------|---------------|
| Free | 5 | 100K/month |
| Growth | 25 | 5M/month |
| Starter | 150 | 30M/month |
| Pro | 330 | 100M/month |
| Enterprise | Custom | Unlimited |

**Cost**
| Plan | Price/Month |
|------|-------------|
| Free | $0 |
| Growth | $49 |
| Starter | $149 |
| Pro | $299 |
| Enterprise | Custom |

**How an Agent Would Use It**
```python
# Standard JSON-RPC call
POST https://eth-mainnet.g.alchemy.com/v2/<apiKey>
{
  "jsonrpc": "2.0",
  "method": "eth_getBlockByNumber",
  "params": ["latest", false],
  "id": 1
}

# Use enhanced API for token balances
POST https://eth-mainnet.g.alchemy.com/v2/<apiKey>
{
  "jsonrpc": "2.0",
  "method": "alchemy_getTokenBalances",
  "params": ["0x...", "erc20"],
  "id": 1
}

# Get NFT metadata
POST https://eth-mainnet.g.alchemy.com/v2/<apiKey>
{
  "jsonrpc": "2.0",
  "method": "alchemy_getNftMetadata",
  "params": [{ "contractAddress": "0x...", "tokenId": "1" }],
  "id": 1
}
```

**Special Features for Agents**
- **Notify API**: Webhooks for wallet/token activity
- **Transfers API**: Enhanced token transfer history
- **NFT API**: Metadata and rarity
- **Alchemy Search**: Natural language to SQL for blockchain
- **SDK**: TypeScript/Python/Go SDKs

**Documentation**: https://docs.alchemy.com/

---

### 2.7 Infura

**What It Provides**
- Ethereum RPC (all EVM chains)
- IPFS storage
- Filecoin access
- Polygon, BSC, Avalanche support
- Archive data access
- Tracing support

**Authentication**
- Project ID and Secret from Infura dashboard
- Basic auth or JWT tokens

**Rate Limits**
| Plan | Requests/Second | Archive |
|------|-----------------|---------|
| Free | 10 | No |
| Starter | 100 | No |
| Developer+ | 500 | Optional |
| Scaling | 1000+ | Yes |

**Cost**
| Plan | Price/Month |
|------|-------------|
| Free | $0 |
| Starter | $50 |
| Developer | $150 |
| Scaling | $450 |
| Enterprise | Custom |

**How an Agent Would Use It**
```python
# Standard JSON-RPC
POST https://mainnet.infura.io/v3/<projectId>
{
  "jsonrpc": "2.0",
  "method": "eth_blockNumber",
  "params": [],
  "id": 1
}

# With secret (for writes)
POST https://mainnet.infura.io/v3/<projectId>
Headers: { "Authorization": "Basic <base64(projectId:projectSecret)>" }
```

**Special Features**
- **Archive mode**: Full state history
- **Tracing**: debug_traceCall support
- **IPFS**: Decentralized storage
- **Network webhook alerts**: Via third-party integration

**Documentation**: https://docs.infura.io/

---

## 3. Cross-Chain APIs

### 3.1 LayerZero

**What It Provides**
- Omnichain message passing
- DVN (Decentralized Verifier Networks)
- Cross-chain token transfers (OFT)
- Message library for custom apps
- Endpoint contracts on 50+ chains

**Authentication**
- No API key for basic usage
- Dev tools and dashboard require registration
- OApp registration for production

**Rate Limits**
- No rate limits on protocol (gas-based)
- Dev tooling may have limits

**Cost**
- Gas costs on source and destination chains
- No protocol fees
- Optional DVN fees for enhanced security

**How an Agent Would Use It**
```typescript
import { OVMDstm, ethers } from "@layerzerolabs/lz-omnichannel";
import { EndpointId } from "@layerzerolabs/lz-definitions";

// Send cross-chain message
const omnichain = new OVMDstm(signer, provider);
await omnichain.send({
  destination: EndpointId.ETHEREUM_V2_MAINNET,
  recipient: ethers.utils.solidityPack(["address"], [destinationAddress]),
  message: ethers.utils.toUtf8Bytes("Hello Cross-Chain"),
  gasLimit: 300000,
  value: 0,
});

// Example: Send ERC-20 cross-chain using OFT
import { IOFT, OFTMintable } from "@layerzerolabs/lz-omnichannel";

// Adapter for existing tokens
const oft = await OFTMintable.createOFT(
  "MyToken",
  "MTK",
  18,
  localConnection,
  remoteConnection
);
await oft.send(
  toAddress,
  amount,
  { refundAddress: walletAddress }
);
```

**Key Concepts**
- **Endpoint**: Contract that handles message dispatch
- **DVN**: Verifier networks that confirm delivery
- **OApp**: Omnichain Applications (your custom contracts)
- **OFT**: Omnichain Fungible Token standard

**Documentation**: https://layerzero.gitbook.io/docs/

---

### 3.2 Wormhole

**What It Provides**
- Token Bridge (locked/minted tokens)
- Native Token Transfers (NTT) - native asset transfers
- Wormhole Connect (UI widget)
- Circle CCTP integration (USDC transfers)
- General message passing
- Guardian network (19 validators)
- 30+ chain support

**Authentication**
- No auth required for basic protocol
- API key for Wormhole APIs (analytics, etc.)

**Rate Limits**
- Protocol: No rate limits (gas-based)
- REST APIs: ~100-1000 req/min depending on endpoint

**Cost**
- Gas on source + destination chains
-relayer fees (optional, for convenience)
- No mandatory protocol fees

**How an Agent Would Use It**
```typescript
import { Wormhole, SolanaSigner, ETHSigner } from "@wormhole-foundation/sdk";

// Initialize Wormhole
const wh = new Wormhole("MAINNET", [SolanaSigner, ETHSigner]);

// Token Transfer via Token Bridge
const tokenTransfer = wh.tokenTransfer(
  "0x...", // token address on source
  1000000, // amount (with decimals)
  {
    sender: senderAddress,
    recipient: recipientAddress,
  },
  "solana", // destination chain
  undefined, // delivery provider (automatic)
);

// Parse and submit VAA
const { txTag, pendingTransfers } = await tokenTransfer.transfer();
```

**Products**
- **Token Bridge**: Lock/mint bridge (traditional)
- **Native Token Transfers (NTT)**: Native tokens across chains
- **CCTP**: USDC via Circle's Cross-Chain Transfer Protocol
- **Connect**: Pre-built UI widget
- **Messaging**: Generic message passing
- **Queries**: Cross-chain data retrieval

**Documentation**: https://wormhole.com/docs/

---

## 4. Data & Analytics APIs

### 4.1 Dune Analytics API

**What It Provides**
- Decoded on-chain data from 50+ protocols
- Pre-built dashboards
- Custom query execution (Spark SQL)
- Result export (CSV, JSON)
- Historical data
- Community tables

**Authentication**
- API key from Dune dashboard
- Free tier available

**Rate Limits**
| Plan | Queries/Minute | Concurrent |
|------|----------------|------------|
| Free | 10 | 1 |
| Plus | 30 | 3 |
| Pro | 60 | 10 |
| Business | 200 | 25 |

**Cost**
| Plan | Price/Month |
|------|-------------|
| Free | $0 |
| Plus | $420 |
| Pro | $750 |
| Business | Custom |

**How an Agent Would Use It**
```python
import requests

DUNE_API_KEY = "your_api_key"
BASE_URL = "https://api.dune.com/api/v1"

# Execute query
response = requests.post(
    f"{BASE_URL}/query/{query_id}/execute",
    headers={"X-Dune-API-Key": DUNE_API_KEY}
)

# Get results
response = requests.get(
    f"{BASE_URL}/query/{query_id}/results",
    headers={"X-Dune-API-Key": DUNE_API_KEY}
)

# Example: Get Uniswap V3 daily volume
GET https://api.dune.com/api/v1/query/xxxxx/results?params={}
```

**Key Endpoints**
- `POST /query/<id>/execute` - Execute a query
- `GET /query/<id>/results` - Get query results
- `GET /query/<id>/status` - Check execution status
- `POST /query` - Create new query
- `GET /table/<namespace>/<table>` - Get table schema

**Popular Tables for Agents**
- `dex.trades` - All DEX trades across chains
- `nft.trades` - NFT marketplace trades
- `lending.borrow` - Lending protocol borrows
- `stablecoin.transfers` - Stablecoin flows

**Documentation**: https://docs.dune.com/

---

### 4.2 DeFiLlama API

**What It Provides**
- Total Value Locked (TVL) for all DeFi protocols
- Historical TVL data
- Yield rankings
- Token prices
- Protocol metrics
- Bridge liquidity
- Chain breakdowns

**Authentication**
- Free tier: No auth required
- Premium tier: API key

**Rate Limits**
- Free: ~30 requests/minute
- Premium: Higher limits

**Cost**
- Free tier available
- Premium: ~$25-100/month

**How an Agent Would Use It**
```python
# Get all protocol TVLs
GET https://api.llama.fi/protocols

# Get protocol TVL history
GET https://api.llama.fi/protocol/<protocol-name>

# Get all pools yields
GET https://yields.llama.fi/pools

# Get token prices
GET https://coins.llama.fi/prices/current/<token-address>

# Get TVL by chain
GET https://api.llama.fi/chains
```

**Key Endpoints**
- `GET /protocols` - All protocols with TVL
- `GET /protocol/<name>` - Single protocol data
- `GET /pools` - All yield pools
- `GET /pools/<chain>` - Pools by chain
- `GET /coins/price/<id>` - Token prices
- `GET /stablecoins` - Stablecoin supplies

**Documentation**: https://defillama.com/docs/api

---

### 4.3 Nansen

**What It Provides**
- Wallet labeling (smart money tracking)
- Token god mode (whale activity)
- NFT wallet tracking
- DeFi position monitoring
- NFT floor prices
- Fund flow analysis
- Real-time alerts

**Authentication**
- API key from Nansen dashboard
- No free tier

**Rate Limits**
- Based on subscription tier

**Cost**
- Institutional pricing (expensive, $1K+/month)
- No public pricing

**How an Agent Would Use It**
```python
# Get wallet labeled tags
GET https://api.nansen.ai/query

# Get token flow
POST https://api.nansen.ai/query
{
  "query": "label_addresses",
  "params": {
    "address": "0x...",
    "chain": "ethereum"
  }
}
```

**Key Features for Agents**
- **Smart Money**: Track institutional wallets
- **Token God Mode**: Real-time whale trading
- **NFT Intelligence**: Floor prices and wallet tracking
- **Alert API**: Real-time notifications

**Documentation**: Not publicly available (institutional product)

---

### 4.4 Arkham Intelligence API

**What It Provides**
- Wallet labeling and entity identification
- Transaction tracing
- Fund flow visualization
- Token holdings
- Trade history
- Entity clustering
- Multi-chain support

**Authentication**
- API key required
- Free tier available

**Rate Limits**
| Plan | Requests/Month | Cost |
|------|----------------|------|
| Free | 1,000 | $0 |
| Pro | 50,000 | $99 |
| Business | 500,000 | $499 |
| Enterprise | Unlimited | Custom |

**Cost**
- Free: 1K requests/month
- Pro: $99/month
- Business: $499/month

**How an Agent Would Use It**
```python
# Get entity info
GET https://api.arkhamintelligence.com/entity/<address>

# Get token holdings
GET https://api.arkhamintelligence.com/tokens?address=<address>

# Get transactions
GET https://api.arkhamintelligence.com/transactions?address=<address>
```

**Key Endpoints**
- `GET /entity/<address>` - Label and entity data
- `GET /transactions` - Transaction history
- `GET /tokens` - Token balances
- `GET /flow` - Fund flow analysis
- `GET /clusters` - Entity clusters

**Documentation**: https://docs.arkhamintelligence.com/

---

## 5. MEV Infrastructure

### 5.1 Flashbots

**What It Provides**
- MEV-Boost (Proposer-Builder Separation)
- Protect RPC ( frontrunning protection)
- MEV-Share (user MEV sharing)
- Flashbots Builder (block building)
- MEV research data

**Authentication**
- Protect RPC: No auth for basic use
- MEV-Boost: Validator authentication
- MEV-Share: API key

**Rate Limits**
- Protect RPC: Free, rate limited
- MEV-Boost: Validator-based
- MEV-Share: API key limits

**Cost**
- Protect RPC: Free
- MEV-Boost: Validators share rewards
- MEV-Share: Free for beta

**How an Agent Would Use It**
```python
# Use Flashbots Protect RPC
# Just send transactions to:
# https://rpc.mevblocker.io

# Or with Flashbots:
from flashbots import flashbot
from eth_account import Account

# Initialize
flashbot(signer, "<endpoint_url>")

# Send bundle
bundle = [
    {"signed_transaction": signed_tx},
    {"address": "0x...", "calldata": "..."}
]
flashbots_send_bundle(bundle, target_block_number + 1)
```

**Products**
- **Protect RPC**: Free frontrunning protection, gas refunds
- **MEV-Boost**: PBS for validators
- **BuilderNet**: TEE-based block building
- **rbuilder**: Open source block builder
- **Rollup-Boost**: Rollup block building

**Documentation**: https://docs.flashbots.net/

---

### 5.2 Jito (Solana MEV)

**What It Provides**
- Low-latency transaction submission
- MEV bundles
- ShredStream (low-latency block data)
- Transaction landing guarantees
- MEV rewards for validators

**Authentication**
- No auth required for basic use
- Jito client runs as validator or connected to validator

**Rate Limits**
- No protocol rate limits
- Network-dependent

**Cost**
- Bundle tips paid to validators
- Small fee in SOL for priority

**How an Agent Would Use It**
```python
# Connect to Jito Block Engine
JITO_RPC = "https://arweave.net/..."

# Send bundle via Jito
POST https://amman.laine.pro/
{
  "jsonrpc": "2.0",
  "method": "sendBundle",
  "params": [[
    {
      "transaction": "<base64_tx>",
      "preflightCommitment": "confirmed"
    }
  ]],
  "id": 1
}

# For low-latency block data (ShredStream)
# Connect to WebSocket: wss://shredstream.jito.wtf
```

**Products**
- **Fast Transaction Send**: Sub-second tx submission
- **Bundles**: Atomic tx bundles with revert protection
- **ShredStream**: <100ms block data delivery
- **Tip Manager**: Jito tips for prioritization

**Key Endpoints**
- `POST /bundle` - Submit bundle
- WebSocket `wss://shredstream.jito.wtf` - Real-time shreds

**Documentation**: https://docs.jito.wtf/

---

## Summary: API Selection for Autonomous Agent

### Solana Operations
| Use Case | Primary API | Backup |
|----------|------------|--------|
| Swap routing | Jupiter API | Raydium API |
| RPC/Read | Helius RPC | QuickNode, Triton |
| Price data | Birdeye | DexScreener |
| Wallet tracking | Helius Webhooks | Birdeye |
| MEV protection | Jito Bundles | Jupiter Ultra |

### EVM Operations
| Use Case | Primary API | Backup |
|----------|------------|--------|
| Swap routing | 1inch API | Uniswap SDK |
| RPC | Alchemy | Infura |
| Lending | Aave API | Compound API |
| Data | The Graph | Dune |
| MEV | Flashbots | Other |

### Cross-Chain
| Use Case | API |
|----------|-----|
| Bridge | Wormhole, LayerZero |
| Messaging | Wormhole, LayerZero |
| Analytics | Dune, DeFiLlama |

### Data & Intelligence
| Use Case | API |
|----------|-----|
| On-chain data | Dune, The Graph |
| Wallet tracking | Arkham, Nansen |
| Protocol TVL | DeFiLlama |
| Prices | Birdeye, DeFiLlama |

### MEV
| Chain | Solution |
|-------|----------|
| Ethereum | Flashbots Protect + MEV-Boost |
| Solana | Jito Bundles + ShredStream |

---

## Environment Setup Notes

### Python Dependencies
```bash
pip install solana web3 eth-typing httpx aiohttp
pip install solders pyyaml requests
pip install @solana/web3.js ethers
```

### Node Dependencies
```bash
npm install @solana/web3.js @project-serum/anchor
npm install ethers @uniswap/sdk-core @uniswap/v3-sdk
npm install @layerzerolabs/sdk @wormhole-foundation/sdk
```

### Environment Variables
```bash
# Solana
export HELIUS_API_KEY="your_helius_key"
export JUPITER_API_KEY="your_jupiter_key"

# EVM
export ALCHEMY_API_KEY="your_alchemy_key"
export INFURA_PROJECT_ID="your_infura_id"
export INFURA_PROJECT_SECRET="your_infura_secret"

# Data
export DUNE_API_KEY="your_dune_key"
export ARKHAM_API_KEY="your_arkham_key"

# Cross-chain
export LAYERZERO_ENDPOINT="..."
export WORMHOLE_RPC="..."
```

---

*Last Updated: March 2026*
*Note: API pricing and rate limits are subject to change. Verify current terms on respective documentation pages.*
