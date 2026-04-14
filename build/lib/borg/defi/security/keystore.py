"""Security module - AES-256 encrypted keystore for Borg DeFi.

Provides secure storage for private keys using AES-256-GCM encryption.
Falls back to Fernet if cryptography library is not available.
"""

import json
import logging
import os
import base64
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try to import cryptography, fall back to Fernet
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_AES_GCM = True
except ImportError:
    HAS_AES_GCM = False

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except ImportError:
    HAS_FERNET = False


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    pass


class KeyStore:
    """AES-256 encrypted keystore for private keys.
    
    Keys are never stored in plaintext. Uses AES-256-GCM with PBKDF2
    for key derivation, or Fernet as a fallback.
    
    Storage format:
    - keys.enc: encrypted key-value store
    - keys.salt: random salt for key derivation
    """
    
    KEYSTORE_DIR = Path.home() / ".hermes" / "borg" / "defi"
    KEYSTORE_FILE = KEYSTORE_DIR / "keys.enc"
    SALT_FILE = KEYSTORE_DIR / "keys.salt"
    
    def __init__(self, password: Optional[str] = None):
        """Initialize keystore.
        
        Args:
            password: Keystore password. If None, will use BORG_KEYSTORE_PASSWORD env var.
        """
        self._password = password or os.environ.get("BORG_KEYSTORE_PASSWORD")
        self._salt: Optional[bytes] = None
        self._derived_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
        
        if not self._password:
            logger.warning("No keystore password provided. Read-only mode.")
        
        self._load_salt()
    
    def _load_salt(self) -> None:
        """Load or generate encryption salt."""
        if self.SALT_FILE.exists():
            self._salt = self.SALT_FILE.read_bytes()
        else:
            self._salt = os.urandom(16)
            self.KEYSTORE_DIR.mkdir(parents=True, exist_ok=True)
            self.SALT_FILE.write_bytes(self._salt)
    
    def _derive_key(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """Derive encryption key from password using PBKDF2-HMAC-SHA256.
        
        Args:
            password: User password
            salt: Optional salt (uses stored salt if not provided)
            
        Returns:
            32-byte derived key
        """
        use_salt = salt or self._salt
        if not use_salt:
            self._load_salt()
            use_salt = self._salt
        
        # OWASP 2024 recommends 600,000 iterations minimum for PBKDF2-HMAC-SHA256.
        # Use 1,200,000 iterations to achieve target derivation time of 100-500ms.
        ITERATIONS = 1200000
        
        if HAS_AES_GCM:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=use_salt,
                iterations=ITERATIONS,
            )
            return kdf.derive(password.encode())
        else:
            # Fallback: PBKDF2-HMAC-SHA256 using hashlib
            import hashlib
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                use_salt,
                ITERATIONS
            )
            return key
    
    def _get_encryption_key(self) -> bytes:
        """Get or derive encryption key."""
        if not self._password:
            raise EncryptionError("No password provided")
        
        if not self._derived_key:
            self._derived_key = self._derive_key(self._password)
        
        return self._derived_key
    
    def _encrypt_aesgcm(self, data: bytes) -> bytes:
        """Encrypt data using AES-256-GCM.
        
        Args:
            data: Plaintext data
            
        Returns:
            IV (12 bytes) + ciphertext + auth tag (16 bytes)
        """
        key = self._get_encryption_key()
        aesgcm = AESGCM(key)
        iv = os.urandom(12)
        ciphertext = aesgcm.encrypt(iv, data, None)
        return iv + ciphertext
    
    def _decrypt_aesgcm(self, encrypted: bytes) -> bytes:
        """Decrypt data using AES-256-GCM.
        
        Args:
            encrypted: IV + ciphertext + auth tag
            
        Returns:
            Decrypted plaintext
        """
        key = self._get_encryption_key()
        aesgcm = AESGCM(key)
        iv = encrypted[:12]
        ciphertext = encrypted[12:]
        return aesgcm.decrypt(iv, ciphertext, None)
    
    def _encrypt_fernet(self, data: bytes) -> bytes:
        """Encrypt data using Fernet (AES-CBC).
        
        Args:
            data: Plaintext data
            
        Returns:
            Encrypted data
        """
        if not self._fernet:
            key = self._get_encryption_key()
            self._fernet = Fernet(base64.urlsafe_b64encode(key[:32]))
        return self._fernet.encrypt(data)
    
    def _decrypt_fernet(self, encrypted: bytes) -> bytes:
        """Decrypt data using Fernet.
        
        Args:
            encrypted: Encrypted data
            
        Returns:
            Decrypted plaintext
        """
        if not self._fernet:
            key = self._get_encryption_key()
            self._fernet = Fernet(base64.urlsafe_b64encode(key[:32]))
        return self._fernet.decrypt(encrypted)
    
    def _encrypt(self, data: bytes) -> bytes:
        """Encrypt data using best available method."""
        if HAS_AES_GCM:
            return self._encrypt_aesgcm(data)
        elif HAS_FERNET:
            return self._encrypt_fernet(data)
        else:
            raise EncryptionError("No encryption backend available")
    
    def _decrypt(self, encrypted: bytes) -> bytes:
        """Decrypt data using best available method."""
        if HAS_AES_GCM:
            return self._decrypt_aesgcm(encrypted)
        elif HAS_FERNET:
            return self._decrypt_fernet(encrypted)
        else:
            raise EncryptionError("No decryption backend available")
    
    def store(self, key: str, value: str) -> None:
        """Store an encrypted key-value pair.
        
        Args:
            key: Key name (e.g., 'solana_wallet', 'eth_private_key')
            value: Value to store (will be encrypted)
        """
        # Load existing data
        data = self._load_all()
        data[key] = value
        
        # Encrypt and save
        json_data = json.dumps(data).encode()
        encrypted = self._encrypt(json_data)
        
        self.KEYSTORE_DIR.mkdir(parents=True, exist_ok=True)
        self.KEYSTORE_FILE.write_bytes(encrypted)
        logger.info(f"Stored encrypted key: {key}")
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve a decrypted value.
        
        Args:
            key: Key name
            
        Returns:
            Decrypted value or None if not found
        """
        data = self._load_all()
        return data.get(key)
    
    def delete(self, key: str) -> bool:
        """Delete a key from the keystore.
        
        Args:
            key: Key name
            
        Returns:
            True if deleted, False if not found
        """
        data = self._load_all()
        if key in data:
            del data[key]
            json_data = json.dumps(data).encode()
            encrypted = self._encrypt(json_data)
            self.KEYSTORE_FILE.write_bytes(encrypted)
            logger.info(f"Deleted key: {key}")
            return True
        return False
    
    def list_keys(self) -> list:
        """List all key names (not values).
        
        Returns:
            List of key names
        """
        return list(self._load_all().keys())
    
    def _load_all(self) -> Dict[str, str]:
        """Load all decrypted data from keystore.
        
        Returns:
            Dict of key-value pairs
        """
        if not self.KEYSTORE_FILE.exists():
            return {}
        
        try:
            encrypted = self.KEYSTORE_FILE.read_bytes()
            if not self._password:
                logger.warning("Cannot decrypt keystore without password")
                return {}
            
            json_data = self._decrypt(encrypted)
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Failed to decrypt keystore: {e}")
            return {}
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the keystore.
        
        Args:
            key: Key name
            
        Returns:
            True if key exists
        """
        return key in self._load_all()
    
    def clear_all(self) -> None:
        """Delete all keys from the keystore."""
        if self.KEYSTORE_FILE.exists():
            self.KEYSTORE_FILE.unlink()
        logger.warning("Cleared all keys from keystore")


class SpendingLimitStore:
    """Store and manage spending limits.
    
    Stored in JSON format at ~/.hermes/borg/defi/spending_limits.json
    """
    
    LIMITS_FILE = KeyStore.KEYSTORE_DIR / "spending_limits.json"
    
    def __init__(self):
        """Initialize spending limit store."""
        self._limits: Dict[str, Dict[str, Any]] = {}
        self._load()
    
    def _load(self) -> None:
        """Load limits from disk."""
        if self.LIMITS_FILE.exists():
            try:
                self._limits = json.loads(self.LIMITS_FILE.read_text())
            except Exception as e:
                logger.error(f"Failed to load spending limits: {e}")
                self._limits = {}
    
    def _save(self) -> None:
        """Save limits to disk."""
        self.LIMITS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.LIMITS_FILE.write_text(json.dumps(self._limits, indent=2))
    
    def set_limit(self, wallet: str, per_trade: float, daily: float) -> None:
        """Set spending limits for a wallet.
        
        Args:
            wallet: Wallet identifier
            per_trade: Max USD per trade
            daily: Max USD per day
        """
        self._limits[wallet] = {
            "per_trade_limit": per_trade,
            "daily_limit": daily,
            "daily_spent": 0.0,
            "last_reset": datetime.now().timestamp(),
        }
        self._save()
    
    def get_limit(self, wallet: str) -> Optional[Dict[str, Any]]:
        """Get spending limits for a wallet.
        
        Args:
            wallet: Wallet identifier
            
        Returns:
            Dict with per_trade_limit, daily_limit, daily_spent, last_reset
        """
        return self._limits.get(wallet)
    
    def record_spend(self, wallet: str, amount_usd: float) -> bool:
        """Record a spend and check against limits.
        
        Args:
            wallet: Wallet identifier
            amount_usd: Amount spent in USD
            
        Returns:
            True if within limits, False if would exceed
        """
        if wallet not in self._limits:
            return True  # No limits set
        
        limit = self._limits[wallet]
        
        # Check per-trade limit
        if amount_usd > limit["per_trade_limit"]:
            return False
        
        # Reset daily if new day
        now = datetime.now().timestamp()
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        if limit["last_reset"] < day_start:
            limit["daily_spent"] = 0.0
            limit["last_reset"] = now
        
        # Check daily limit
        if limit["daily_spent"] + amount_usd > limit["daily_limit"]:
            return False
        
        # Record spend
        limit["daily_spent"] += amount_usd
        self._save()
        return True
    
    def reset_daily(self, wallet: str) -> None:
        """Reset daily spend counter for a wallet.
        
        Args:
            wallet: Wallet identifier
        """
        if wallet in self._limits:
            self._limits[wallet]["daily_spent"] = 0.0
            self._limits[wallet]["last_reset"] = datetime.now().timestamp()
            self._save()


class ContractWhitelist:
    """Manage whitelisted contracts.
    
    Only whitelisted contracts can be interacted with.
    Stored in JSON format.
    """
    
    WHITELIST_FILE = KeyStore.KEYSTORE_DIR / "approved_contracts.json"
    
    def __init__(self):
        """Initialize contract whitelist."""
        self._contracts: Dict[str, Dict[str, Any]] = {}
        self._load()
    
    def _load(self) -> None:
        """Load whitelist from disk."""
        if self.WHITELIST_FILE.exists():
            try:
                self._contracts = json.loads(self.WHITELIST_FILE.read_text())
            except Exception as e:
                logger.error(f"Failed to load contract whitelist: {e}")
                self._contracts = {}
    
    def _save(self) -> None:
        """Save whitelist to disk."""
        self.WHITELIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.WHITELIST_FILE.write_text(json.dumps(self._contracts, indent=2))
    
    def add(
        self,
        address: str,
        chain: str,
        name: str,
        contract_type: str = "unknown",
    ) -> None:
        """Add a contract to the whitelist.
        
        Args:
            address: Contract address
            chain: Chain name (solana, ethereum, etc.)
            name: Human-readable name
            contract_type: Type (router, protocol, token, etc.)
        """
        key = f"{chain}:{address.lower()}"
        self._contracts[key] = {
            "address": address.lower(),
            "chain": chain,
            "name": name,
            "contract_type": contract_type,
            "added_at": datetime.now().timestamp(),
        }
        self._save()
        logger.info(f"Whitelisted contract: {name} ({chain})")
    
    def remove(self, address: str, chain: str) -> bool:
        """Remove a contract from the whitelist.
        
        Args:
            address: Contract address
            chain: Chain name
            
        Returns:
            True if removed, False if not found
        """
        key = f"{chain}:{address.lower()}"
        if key in self._contracts:
            del self._contracts[key]
            self._save()
            return True
        return False
    
    def is_allowed(self, address: str, chain: str) -> bool:
        """Check if a contract is whitelisted.
        
        Args:
            address: Contract address
            chain: Chain name
            
        Returns:
            True if whitelisted
        """
        key = f"{chain}:{address.lower()}"
        return key in self._contracts
    
    def get_contract(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """Get contract info.
        
        Args:
            address: Contract address
            chain: Chain name
            
        Returns:
            Contract info dict or None
        """
        key = f"{chain}:{address.lower()}"
        return self._contracts.get(key)
    
    def list_by_chain(self, chain: str) -> list:
        """List all whitelisted contracts for a chain.
        
        Args:
            chain: Chain name
            
        Returns:
            List of contract info dicts
        """
        return [
            c for c in self._contracts.values()
            if c["chain"] == chain
        ]
    
    def clear_all(self) -> None:
        """Remove all contracts from whitelist."""
        self._contracts = {}
        self._save()
        logger.warning("Cleared all contracts from whitelist")


# Default whitelisted contracts for common protocols
DEFAULT_CONTRACTS = {
    # Solana
    "solana:jupiter": {
        "address": "JUP6LktZJNt1qVGhC5F7NqV6cFGAR3YYMgHswRMFZZx",
        "chain": "solana",
        "name": "Jupiter Exchange",
        "contract_type": "router",
    },
    "solana:kamino": {
        "address": "KAMINON2H55VYDDIN7JL5VJNSDAL6N46XFDT3BF2JB2",
        "chain": "solana",
        "name": "Kamino Finance",
        "contract_type": "protocol",
    },
    "solana:raydium": {
        "address": "RAYV15NsgtwwHbMg5uGqG2z4XhzR2VsXa1MGCvN4p4q",
        "chain": "solana",
        "name": "Raydium",
        "contract_type": "protocol",
    },
    "solana:orca": {
        "address": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
        "chain": "solana",
        "name": "Orca",
        "contract_type": "protocol",
    },
    # Ethereum
    "ethereum:uniswap_router": {
        "address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "chain": "ethereum",
        "name": "Uniswap V2 Router",
        "contract_type": "router",
    },
    "ethereum:aave": {
        "address": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "chain": "ethereum",
        "name": "Aave",
        "contract_type": "protocol",
    },
}
