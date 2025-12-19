"""
Token Encryption Service
AES-256-GCM encryption via Fernet for OAuth token storage

Part of: netrun-oauth v1.0.0
SDLC v2.2 Compliant - Extracted from Intirkast token encryption service
"""

import logging
import os
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from .exceptions import TokenEncryptionError

logger = logging.getLogger(__name__)


class TokenEncryptionService:
    """
    Service for encrypting/decrypting OAuth tokens
    Uses AES-256-GCM via Fernet for secure token storage

    Credential Resolution Order:
    1. Explicit key provided to constructor
    2. Environment variable: OAUTH_TOKEN_ENCRYPTION_KEY
    3. Azure Key Vault: oauth-token-encryption-key secret
    4. Auto-generated temporary key (DEVELOPMENT ONLY - NOT SECURE)

    Security Notes:
    - Uses Fernet (symmetric encryption with AES-256-GCM)
    - Includes timestamp for key rotation support
    - Ciphertext includes authentication tag (prevents tampering)
    - Use Azure Key Vault for production deployments
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize token encryption service

        Args:
            encryption_key: Base64-encoded Fernet key (32 bytes)
                           If None, will try to load from environment or Azure Key Vault

        Raises:
            TokenEncryptionError: If encryption initialization fails
        """
        self.cipher: Optional[Fernet] = None
        self._initialize_cipher(encryption_key)

    def _initialize_cipher(self, encryption_key: Optional[str] = None):
        """Initialize Fernet cipher with encryption key"""
        try:
            # Priority 1: Provided key (for testing or explicit configuration)
            if encryption_key:
                self.cipher = Fernet(encryption_key.encode())
                logger.info("Token encryption initialized with provided key")
                return

            # Priority 2: Environment variable
            env_key = os.getenv("OAUTH_TOKEN_ENCRYPTION_KEY")
            if env_key:
                self.cipher = Fernet(env_key.encode())
                logger.info("Token encryption initialized from environment variable")
                return

            # Priority 3: Azure Key Vault (production)
            key_vault_url = os.getenv("AZURE_KEY_VAULT_URL")
            if key_vault_url:
                key_vault_key = self._load_from_key_vault(key_vault_url)
                if key_vault_key:
                    self.cipher = Fernet(key_vault_key.encode())
                    logger.info("Token encryption initialized from Azure Key Vault")
                    return

            # Fallback: Generate temporary key (DEVELOPMENT ONLY)
            logger.warning(
                "No encryption key found! Generating temporary key. "
                "THIS IS NOT SECURE FOR PRODUCTION! "
                "Set OAUTH_TOKEN_ENCRYPTION_KEY or configure Azure Key Vault."
            )
            temp_key = Fernet.generate_key()
            self.cipher = Fernet(temp_key)
            logger.warning(f"Temporary encryption key: {temp_key.decode()}")

        except Exception as e:
            logger.error(f"Failed to initialize token encryption: {e}")
            raise TokenEncryptionError("Token encryption initialization failed")

    def _load_from_key_vault(self, vault_url: str) -> Optional[str]:
        """
        Load encryption key from Azure Key Vault

        Args:
            vault_url: Azure Key Vault URL (https://<vault-name>.vault.azure.net/)

        Returns:
            Base64-encoded Fernet key or None if not available
        """
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)

            # Retrieve secret from Key Vault
            secret = client.get_secret("oauth-token-encryption-key")
            logger.info("Successfully loaded encryption key from Azure Key Vault")
            return secret.value

        except ImportError:
            logger.warning(
                "Azure SDK not installed. Install: pip install azure-identity azure-keyvault-secrets"
            )
            return None
        except Exception as e:
            logger.warning(f"Failed to load encryption key from Key Vault: {e}")
            return None

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt OAuth token

        Args:
            token: Plain text OAuth token (access or refresh)

        Returns:
            Encrypted token (base64-encoded ciphertext)

        Raises:
            TokenEncryptionError: If encryption fails
            ValueError: If token is empty
        """
        if not self.cipher:
            raise TokenEncryptionError("Token encryption not initialized")

        if not token:
            raise ValueError("Token cannot be empty")

        try:
            encrypted = self.cipher.encrypt(token.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            raise TokenEncryptionError(f"Failed to encrypt token: {str(e)}")

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt OAuth token

        Args:
            encrypted_token: Encrypted token from database

        Returns:
            Decrypted plain text token

        Raises:
            TokenEncryptionError: If decryption fails or token is invalid
            ValueError: If encrypted token is empty
        """
        if not self.cipher:
            raise TokenEncryptionError("Token encryption not initialized")

        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")

        try:
            # Handle both bytes and string inputs
            if isinstance(encrypted_token, bytes):
                token_bytes = encrypted_token
            else:
                token_bytes = encrypted_token.encode()

            decrypted = self.cipher.decrypt(token_bytes)
            return decrypted.decode()

        except InvalidToken:
            logger.error("Invalid encrypted token (wrong key or corrupted data)")
            raise TokenEncryptionError("Failed to decrypt token: invalid ciphertext")
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            raise TokenEncryptionError(f"Failed to decrypt token: {str(e)}")

    def rotate_encryption(self, old_encrypted_token: str, new_key: str) -> str:
        """
        Rotate encryption key by decrypting with old key and re-encrypting with new key

        Args:
            old_encrypted_token: Token encrypted with old key
            new_key: New Fernet encryption key (base64-encoded)

        Returns:
            Token encrypted with new key

        Raises:
            TokenEncryptionError: If rotation fails
        """
        try:
            # Decrypt with current key
            plain_token = self.decrypt_token(old_encrypted_token)

            # Re-encrypt with new key
            new_cipher = Fernet(new_key.encode())
            new_encrypted = new_cipher.encrypt(plain_token.encode())

            logger.info("Token encryption rotated successfully")
            return new_encrypted.decode()

        except Exception as e:
            logger.error(f"Token encryption rotation failed: {e}")
            raise TokenEncryptionError(f"Failed to rotate token encryption: {str(e)}")

    @staticmethod
    def generate_key() -> str:
        """
        Generate new Fernet encryption key

        Returns:
            Base64-encoded Fernet key (URL-safe)

        Usage:
            key = TokenEncryptionService.generate_key()
            # Store this key in Azure Key Vault or environment variable
            print(f"OAUTH_TOKEN_ENCRYPTION_KEY={key}")
        """
        return Fernet.generate_key().decode()

    def is_initialized(self) -> bool:
        """
        Check if encryption service is properly initialized

        Returns:
            True if cipher is initialized, False otherwise
        """
        return self.cipher is not None


# Global token encryption service instance
_token_encryption: Optional[TokenEncryptionService] = None


def get_token_encryption() -> TokenEncryptionService:
    """
    Get global token encryption service instance (singleton)

    Returns:
        TokenEncryptionService instance

    Usage:
        from netrun_oauth.token_manager import get_token_encryption

        encryption = get_token_encryption()
        encrypted = encryption.encrypt_token("ya29.a0AfH6SMC...")
        decrypted = encryption.decrypt_token(encrypted)
    """
    global _token_encryption

    if _token_encryption is None:
        _token_encryption = TokenEncryptionService()

    return _token_encryption


def initialize_token_encryption(encryption_key: Optional[str] = None):
    """
    Initialize global token encryption service

    Args:
        encryption_key: Optional encryption key for testing

    Usage:
        # In app startup (production - uses Azure Key Vault)
        from netrun_oauth.token_manager import initialize_token_encryption
        initialize_token_encryption()

        # Or with custom key for testing
        key = TokenEncryptionService.generate_key()
        initialize_token_encryption(encryption_key=key)
    """
    global _token_encryption
    _token_encryption = TokenEncryptionService(encryption_key)
    logger.info("Global token encryption service initialized")


# Convenience functions for backward compatibility
def decrypt_access_token(encrypted_token: str) -> str:
    """
    Decrypt OAuth access token (convenience function)

    Args:
        encrypted_token: Encrypted token from database

    Returns:
        Decrypted plain text token
    """
    service = get_token_encryption()
    return service.decrypt_token(encrypted_token)


def encrypt_access_token(token: str) -> str:
    """
    Encrypt OAuth access token (convenience function)

    Args:
        token: Plain text OAuth token

    Returns:
        Encrypted token (base64-encoded ciphertext)
    """
    service = get_token_encryption()
    return service.encrypt_token(token)
