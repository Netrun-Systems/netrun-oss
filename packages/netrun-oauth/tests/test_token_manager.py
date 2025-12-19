"""
Tests for TokenEncryptionService

Part of: netrun-oauth v1.0.0
"""

import pytest
from cryptography.fernet import Fernet
from netrun_oauth import (
    TokenEncryptionService,
    TokenEncryptionError,
    get_token_encryption,
    initialize_token_encryption,
)


def test_token_encryption_service_initialization():
    """Test TokenEncryptionService initializes correctly"""
    key = Fernet.generate_key().decode()
    service = TokenEncryptionService(encryption_key=key)
    assert service.is_initialized()


def test_encrypt_decrypt_roundtrip():
    """Test encrypting and decrypting a token"""
    key = Fernet.generate_key().decode()
    service = TokenEncryptionService(encryption_key=key)

    original_token = "ya29.a0AfH6SMC..."
    encrypted = service.encrypt_token(original_token)
    decrypted = service.decrypt_token(encrypted)

    assert encrypted != original_token
    assert decrypted == original_token


def test_encrypt_empty_token_raises_error():
    """Test encrypting empty token raises ValueError"""
    key = Fernet.generate_key().decode()
    service = TokenEncryptionService(encryption_key=key)

    with pytest.raises(ValueError):
        service.encrypt_token("")


def test_decrypt_empty_token_raises_error():
    """Test decrypting empty token raises ValueError"""
    key = Fernet.generate_key().decode()
    service = TokenEncryptionService(encryption_key=key)

    with pytest.raises(ValueError):
        service.decrypt_token("")


def test_decrypt_invalid_token_raises_error():
    """Test decrypting invalid token raises TokenEncryptionError"""
    key = Fernet.generate_key().decode()
    service = TokenEncryptionService(encryption_key=key)

    with pytest.raises(TokenEncryptionError):
        service.decrypt_token("invalid_ciphertext")


def test_decrypt_with_wrong_key_raises_error():
    """Test decrypting with wrong key raises TokenEncryptionError"""
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()

    service1 = TokenEncryptionService(encryption_key=key1)
    service2 = TokenEncryptionService(encryption_key=key2)

    encrypted = service1.encrypt_token("test_token")

    with pytest.raises(TokenEncryptionError):
        service2.decrypt_token(encrypted)


def test_rotate_encryption_key():
    """Test rotating encryption key"""
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()

    service = TokenEncryptionService(encryption_key=old_key)
    original_token = "test_token"

    # Encrypt with old key
    old_encrypted = service.encrypt_token(original_token)

    # Rotate to new key
    new_encrypted = service.rotate_encryption(old_encrypted, new_key)

    # Decrypt with new key
    new_service = TokenEncryptionService(encryption_key=new_key)
    decrypted = new_service.decrypt_token(new_encrypted)

    assert decrypted == original_token


def test_generate_key():
    """Test generating new encryption key"""
    key = TokenEncryptionService.generate_key()
    assert isinstance(key, str)
    assert len(key) > 0

    # Key should be valid for Fernet
    service = TokenEncryptionService(encryption_key=key)
    assert service.is_initialized()


def test_global_token_encryption_service():
    """Test global singleton token encryption service"""
    key = Fernet.generate_key().decode()
    initialize_token_encryption(encryption_key=key)

    service1 = get_token_encryption()
    service2 = get_token_encryption()

    # Should return same instance
    assert service1 is service2
    assert service1.is_initialized()
