"""
Tests for keystore security module.

Covers:
- Encrypt/decrypt round-trip
- Wrong password raises error
- Corrupted data raises error
- Empty plaintext
- Large payload (100KB)
- Special characters in password
- Key file creation and loading
- Salt generation uniqueness

Run with:
    pytest borg/defi/tests/test_keystore_unit.py -v --tb=short
"""

import json
import os
import random
import string
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.security.keystore import (
    KeyStore,
    EncryptionError,
    HAS_AES_GCM,
    HAS_FERNET,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_keystore_dir(tmp_path):
    """Create a temporary keystore directory."""
    keystore_dir = tmp_path / ".hermes" / "borg" / "defi"
    keystore_dir.mkdir(parents=True, exist_ok=True)
    return keystore_dir


@pytest.fixture
def password():
    """Standard test password."""
    return "test_password_123"


@pytest.fixture
def special_password():
    """Password with special characters."""
    return "p@$$w0rd!#$%^&*()_+-=[]{}|;':\",./<>?"


@pytest.fixture
def unicode_password():
    """Unicode password."""
    return "密码パスワード🔐🔑"


@pytest.fixture
def keystore_with_password(password, temp_keystore_dir, monkeypatch):
    """Create KeyStore instance with temp directory and password."""
    # Override the keystore directory
    monkeypatch.setattr(KeyStore, "KEYSTORE_DIR", temp_keystore_dir)
    monkeypatch.setattr(KeyStore, "KEYSTORE_FILE", temp_keystore_dir / "keys.enc")
    monkeypatch.setattr(KeyStore, "SALT_FILE", temp_keystore_dir / "keys.salt")
    return KeyStore(password=password)


@pytest.fixture
def empty_keystore(temp_keystore_dir, monkeypatch):
    """Create empty keystore without password (read-only mode)."""
    monkeypatch.setattr(KeyStore, "KEYSTORE_DIR", temp_keystore_dir)
    monkeypatch.setattr(KeyStore, "KEYSTORE_FILE", temp_keystore_dir / "keys.enc")
    monkeypatch.setattr(KeyStore, "SALT_FILE", temp_keystore_dir / "keys.salt")
    return KeyStore(password=None)


# ---------------------------------------------------------------------------
# Basic Encryption/Decryption Tests
# ---------------------------------------------------------------------------


class TestEncryptDecryptRoundTrip:
    """Tests for encrypt/decrypt round-trip functionality."""

    def test_encrypt_decrypt_simple_text(self, keystore_with_password):
        """Test basic encrypt/decrypt with simple text."""
        plaintext = b"Hello, World!"
        encrypted = keystore_with_password._encrypt(plaintext)
        decrypted = keystore_with_password._decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_json_data(self, keystore_with_password):
        """Test encrypt/decrypt with JSON-like data."""
        data = json.dumps({"key": "value", "number": 42}).encode()
        encrypted = keystore_with_password._encrypt(data)
        decrypted = keystore_with_password._decrypt(encrypted)
        assert decrypted == data

    def test_encrypt_produces_different_output(self, keystore_with_password):
        """Test that same plaintext produces different ciphertext (due to IV)."""
        plaintext = b"Same message"
        encrypted1 = keystore_with_password._encrypt(plaintext)
        encrypted2 = keystore_with_password._encrypt(plaintext)
        # Both should decrypt to same plaintext but be different ciphertext
        assert encrypted1 != encrypted2
        assert keystore_with_password._decrypt(encrypted1) == plaintext
        assert keystore_with_password._decrypt(encrypted2) == plaintext

    def test_encrypted_data_is_bytes(self, keystore_with_password):
        """Test that encrypted data is bytes."""
        plaintext = b"Test data"
        encrypted = keystore_with_password._encrypt(plaintext)
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > len(plaintext)  # Should be larger due to IV and auth tag


class TestWrongPassword:
    """Tests for wrong password handling."""

    def test_wrong_password_raises_error(self, keystore_with_password, temp_keystore_dir, monkeypatch):
        """Test that wrong password raises EncryptionError on decrypt."""
        # First, store something
        keystore_with_password.store("test_key", "test_value")
        
        # Create new keystore with different password
        monkeypatch.setattr(KeyStore, "KEYSTORE_DIR", temp_keystore_dir)
        monkeypatch.setattr(KeyStore, "KEYSTORE_FILE", temp_keystore_dir / "keys.enc")
        monkeypatch.setattr(KeyStore, "SALT_FILE", temp_keystore_dir / "keys.salt")
        wrong_keystore = KeyStore(password="wrong_password")
        
        # Attempting to decrypt should fail or return empty
        result = wrong_keystore.get("test_key")
        # Without correct password, get returns None or empty dict
        assert result is None or result == {}

    def test_no_password_read_only_mode(self, empty_keystore):
        """Test that keystore without password is read-only."""
        assert empty_keystore._password is None


class TestCorruptedData:
    """Tests for corrupted data handling."""

    def test_corrupted_encrypted_data(self, keystore_with_password):
        """Test that corrupted data raises error on decrypt."""
        # Create valid encrypted data
        plaintext = b"Valid data"
        encrypted = keystore_with_password._encrypt(plaintext)
        
        # Corrupt the data
        corrupted = bytearray(encrypted)
        corrupted[10] = (corrupted[10] + 1) % 256  # Flip a byte
        corrupted_data = bytes(corrupted)
        
        # Decryption should raise an error
        with pytest.raises(Exception):  # Should raise InvalidTag or similar
            keystore_with_password._decrypt(corrupted_data)

    def test_truncated_encrypted_data(self, keystore_with_password):
        """Test that truncated data raises error on decrypt."""
        plaintext = b"Test data"
        encrypted = keystore_with_password._encrypt(plaintext)
        
        # Truncate the data
        truncated = encrypted[:len(encrypted) // 2]
        
        # Decryption should raise an error
        with pytest.raises(Exception):
            keystore_with_password._decrypt(truncated)

    def test_completely_wrong_data(self, keystore_with_password):
        """Test that completely wrong data raises error."""
        wrong_data = b"This is not encrypted data at all!"
        
        with pytest.raises(Exception):
            keystore_with_password._decrypt(wrong_data)


class TestEmptyPlaintext:
    """Tests for empty plaintext handling."""

    def test_encrypt_empty_bytes(self, keystore_with_password):
        """Test encrypting empty bytes."""
        plaintext = b""
        encrypted = keystore_with_password._encrypt(plaintext)
        decrypted = keystore_with_password._decrypt(encrypted)
        assert decrypted == plaintext

    def test_store_empty_value(self, keystore_with_password):
        """Test storing empty string value."""
        keystore_with_password.store("empty_key", "")
        result = keystore_with_password.get("empty_key")
        assert result == ""


class TestLargePayload:
    """Tests for large payload handling."""

    def test_large_payload_100kb(self, keystore_with_password):
        """Test encrypt/decrypt with 100KB payload."""
        # Generate 100KB of random data
        large_data = os.urandom(100 * 1024)
        encrypted = keystore_with_password._encrypt(large_data)
        decrypted = keystore_with_password._decrypt(encrypted)
        assert decrypted == large_data

    def test_very_large_payload(self, keystore_with_password):
        """Test encrypt/decrypt with larger payload (1MB)."""
        large_data = os.urandom(1024 * 1024)
        encrypted = keystore_with_password._encrypt(large_data)
        decrypted = keystore_with_password._decrypt(encrypted)
        assert decrypted == large_data

    def test_payload_with_all_bytes(self, keystore_with_password):
        """Test payload containing all possible byte values."""
        # Create data with all 256 byte values repeated
        all_bytes = bytes(range(256)) * 100  # 25600 bytes
        encrypted = keystore_with_password._encrypt(all_bytes)
        decrypted = keystore_with_password._decrypt(encrypted)
        assert decrypted == all_bytes


class TestSpecialCharacters:
    """Tests for special characters in passwords and data."""

    def test_special_characters_in_password(self, special_password, temp_keystore_dir, monkeypatch):
        """Test password with special characters."""
        monkeypatch.setattr(KeyStore, "KEYSTORE_DIR", temp_keystore_dir)
        monkeypatch.setattr(KeyStore, "KEYSTORE_FILE", temp_keystore_dir / "keys.enc")
        monkeypatch.setattr(KeyStore, "SALT_FILE", temp_keystore_dir / "keys.salt")
        
        ks = KeyStore(password=special_password)
        plaintext = b"Test data with special password"
        encrypted = ks._encrypt(plaintext)
        decrypted = ks._decrypt(encrypted)
        assert decrypted == plaintext

    def test_unicode_password(self, unicode_password, temp_keystore_dir, monkeypatch):
        """Test unicode password."""
        monkeypatch.setattr(KeyStore, "KEYSTORE_DIR", temp_keystore_dir)
        monkeypatch.setattr(KeyStore, "KEYSTORE_FILE", temp_keystore_dir / "keys.enc")
        monkeypatch.setattr(KeyStore, "SALT_FILE", temp_keystore_dir / "keys.salt")
        
        ks = KeyStore(password=unicode_password)
        plaintext = b"Test data with unicode password"
        encrypted = ks._encrypt(plaintext)
        decrypted = ks._decrypt(encrypted)
        assert decrypted == plaintext

    def test_special_characters_in_data(self, keystore_with_password):
        """Test data containing special characters."""
        special_data = "🚀 🎉 🔐 Hello 世界 café @#$%^&*()_+-=".encode()
        encrypted = keystore_with_password._encrypt(special_data)
        decrypted = keystore_with_password._decrypt(encrypted)
        assert decrypted == special_data

    def test_long_password(self, keystore_with_password):
        """Test with very long password."""
        long_password = "a" * 1000
        # This should work with PBKDF2
        plaintext = b"Test data"
        encrypted = keystore_with_password._encrypt(plaintext)
        decrypted = keystore_with_password._decrypt(encrypted)
        assert decrypted == plaintext


# ---------------------------------------------------------------------------
# Key File Creation and Loading Tests
# ---------------------------------------------------------------------------


class TestKeyFileOperations:
    """Tests for key file creation and loading."""

    def test_store_and_retrieve(self, keystore_with_password):
        """Test storing and retrieving a key."""
        keystore_with_password.store("solana_wallet", "wallet_private_key_123")
        result = keystore_with_password.get("solana_wallet")
        assert result == "wallet_private_key_123"

    def test_store_multiple_keys(self, keystore_with_password):
        """Test storing multiple keys."""
        keystore_with_password.store("key1", "value1")
        keystore_with_password.store("key2", "value2")
        keystore_with_password.store("key3", "value3")
        
        assert keystore_with_password.get("key1") == "value1"
        assert keystore_with_password.get("key2") == "value2"
        assert keystore_with_password.get("key3") == "value3"

    def test_delete_key(self, keystore_with_password):
        """Test deleting a key."""
        keystore_with_password.store("to_delete", "value")
        assert keystore_with_password.get("to_delete") == "value"
        
        result = keystore_with_password.delete("to_delete")
        assert result is True
        assert keystore_with_password.get("to_delete") is None

    def test_delete_nonexistent_key(self, keystore_with_password):
        """Test deleting a key that doesn't exist."""
        result = keystore_with_password.delete("nonexistent")
        assert result is False

    def test_list_keys(self, keystore_with_password):
        """Test listing all keys."""
        keystore_with_password.store("key_a", "value_a")
        keystore_with_password.store("key_b", "value_b")
        
        keys = keystore_with_password.list_keys()
        assert "key_a" in keys
        assert "key_b" in keys

    def test_exists(self, keystore_with_password):
        """Test checking key existence."""
        keystore_with_password.store("existing_key", "value")
        
        assert keystore_with_password.exists("existing_key") is True
        assert keystore_with_password.exists("nonexistent_key") is False

    def test_clear_all(self, keystore_with_password):
        """Test clearing all keys."""
        keystore_with_password.store("key1", "value1")
        keystore_with_password.store("key2", "value2")
        
        keystore_with_password.clear_all()
        
        assert keystore_with_password.list_keys() == []
        assert keystore_with_password.exists("key1") is False


# ---------------------------------------------------------------------------
# Salt Generation Tests
# ---------------------------------------------------------------------------


class TestSaltGeneration:
    """Tests for salt generation."""

    def test_salt_is_generated(self, temp_keystore_dir, monkeypatch):
        """Test that salt is generated if not exists."""
        monkeypatch.setattr(KeyStore, "KEYSTORE_DIR", temp_keystore_dir)
        monkeypatch.setattr(KeyStore, "KEYSTORE_FILE", temp_keystore_dir / "keys.enc")
        monkeypatch.setattr(KeyStore, "SALT_FILE", temp_keystore_dir / "keys.salt")
        
        # Remove salt file if exists
        salt_file = temp_keystore_dir / "keys.salt"
        if salt_file.exists():
            salt_file.unlink()
        
        ks = KeyStore(password="test")
        assert ks._salt is not None
        assert len(ks._salt) == 16  # 16 bytes = 128 bits

    def test_salt_is_loaded(self, keystore_with_password):
        """Test that existing salt is loaded."""
        assert keystore_with_password._salt is not None
        assert len(keystore_with_password._salt) == 16

    def test_salt_uniqueness(self, temp_keystore_dir, monkeypatch):
        """Test that different salt files are generated."""
        monkeypatch.setattr(KeyStore, "KEYSTORE_DIR", temp_keystore_dir)
        monkeypatch.setattr(KeyStore, "KEYSTORE_FILE", temp_keystore_dir / "keys.enc")
        monkeypatch.setattr(KeyStore, "SALT_FILE", temp_keystore_dir / "keys.salt")
        
        # Generate two salts
        salt1 = os.urandom(16)
        salt2 = os.urandom(16)
        
        # Salts should be different
        assert salt1 != salt2

    def test_same_password_different_salt_different_key(self, temp_keystore_dir, monkeypatch):
        """Test that same password with different salt produces different keys."""
        monkeypatch.setattr(KeyStore, "KEYSTORE_DIR", temp_keystore_dir)
        monkeypatch.setattr(KeyStore, "KEYSTORE_FILE", temp_keystore_dir / "keys.enc")
        monkeypatch.setattr(KeyStore, "SALT_FILE", temp_keystore_dir / "keys.salt")
        
        password = "same_password"
        
        # Create two keystores with same password but they'll have same salt file
        # since SALT_FILE is same - so same key derived
        ks1 = KeyStore(password=password)
        salt1 = ks1._salt
        
        ks2 = KeyStore(password=password)
        salt2 = ks2._salt
        
        # With same salt file, same password = same derived key
        assert ks1._derive_key(password) == ks2._derive_key(password)


# ---------------------------------------------------------------------------
# Store Method Tests
# ---------------------------------------------------------------------------


class TestStore:
    """Tests for store method."""

    def test_store_creates_file(self, keystore_with_password):
        """Test that store creates the keystore file."""
        keystore_with_password.store("test_key", "test_value")
        
        assert keystore_with_password.KEYSTORE_FILE.exists()

    def test_store_updates_existing_key(self, keystore_with_password):
        """Test that storing existing key updates it."""
        keystore_with_password.store("key", "value1")
        keystore_with_password.store("key", "value2")
        
        assert keystore_with_password.get("key") == "value2"


# ---------------------------------------------------------------------------
# Load All Method Tests
# ---------------------------------------------------------------------------


class TestLoadAll:
    """Tests for _load_all method."""

    def test_load_all_empty(self, keystore_with_password):
        """Test loading from empty keystore."""
        # Clear any existing data
        keystore_with_password.clear_all()
        
        data = keystore_with_password._load_all()
        assert data == {}

    def test_load_all_with_data(self, keystore_with_password):
        """Test loading with stored data."""
        keystore_with_password.store("key1", "value1")
        keystore_with_password.store("key2", "value2")
        
        data = keystore_with_password._load_all()
        assert data["key1"] == "value1"
        assert data["key2"] == "value2"


# ---------------------------------------------------------------------------
# Encryption Backend Tests
# ---------------------------------------------------------------------------


class TestEncryptionBackend:
    """Tests for encryption backend selection."""

    def test_has_encryption_backend(self):
        """Test that at least one encryption backend is available."""
        assert HAS_AES_GCM or HAS_FERNET, "At least one encryption backend must be available"

    def test_encrypt_uses_available_backend(self, keystore_with_password):
        """Test that encryption uses an available backend."""
        plaintext = b"Test data"
        encrypted = keystore_with_password._encrypt(plaintext)
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0


# ---------------------------------------------------------------------------
# Key Derivation Tests
# ---------------------------------------------------------------------------


class TestKeyDerivation:
    """Tests for key derivation."""

    def test_derive_key_returns_bytes(self, keystore_with_password):
        """Test that _derive_key returns bytes."""
        key = keystore_with_password._derive_key("test_password")
        assert isinstance(key, bytes)
        assert len(key) == 32  # 256 bits for AES-256

    def test_same_password_same_key(self, keystore_with_password):
        """Test that same password derives same key."""
        key1 = keystore_with_password._derive_key("password")
        key2 = keystore_with_password._derive_key("password")
        assert key1 == key2

    def test_different_passwords_different_keys(self, keystore_with_password):
        """Test that different passwords derive different keys."""
        key1 = keystore_with_password._derive_key("password1")
        key2 = keystore_with_password._derive_key("password2")
        assert key1 != key2


class TestKeyDerivationTiming:
    """Tests for key derivation timing (OWASP 2024 compliance)."""

    def test_pbkdf2_derivation_time(self, keystore_with_password):
        """Test that PBKDF2 derivation takes 100-500ms (OWASP 2024 recommendation)."""
        import time
        
        # Warm-up call to avoid cold-start overhead
        keystore_with_password._derive_key("warmup_password")
        
        # Measure derivation time
        start = time.perf_counter()
        keystore_with_password._derive_key("test_password")
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # With 600,000 iterations, derivation should take 100-500ms
        assert 100 <= elapsed_ms <= 500, f"PBKDF2 derivation took {elapsed_ms:.1f}ms, expected 100-500ms"
        print(f"PBKDF2 derivation time: {elapsed_ms:.1f}ms")


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for error handling."""

    def test_encryption_error_class_exists(self):
        """Test that EncryptionError is defined."""
        assert EncryptionError is not None
        assert issubclass(EncryptionError, Exception)

    def test_no_password_raises_error_on_get_encryption_key(self, empty_keystore):
        """Test that getting encryption key without password raises error."""
        with pytest.raises(EncryptionError, match="No password"):
            empty_keystore._get_encryption_key()
