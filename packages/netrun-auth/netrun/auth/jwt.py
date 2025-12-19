"""
Netrun Authentication - JWT Token Manager
==========================================

RS256 JWT authentication with rotating key pairs and Redis-backed blacklisting.

Features:
- Access tokens (15 min) and refresh tokens (30 days)
- RS256 algorithm with rotating key pairs (90-day rotation)
- Redis-backed token blacklist for secure logout
- Comprehensive claims (user, org, roles, permissions, session)
- Token refresh with security validation

Security Standards:
- NIST SP 800-63B compliant
- OWASP Authentication Cheat Sheet compliant
- SOC2 audit trail support

Changelog:
- v1.2.0: Integrated netrun-logging with structured logging and context binding
- v1.0.0: Initial release with RS256 signing and Redis blacklisting

Author: Netrun Systems
Version: 1.2.0
Date: 2025-12-05
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple, Any
import secrets
import json

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import redis.asyncio as redis

from .types import TokenType, TokenClaims, TokenPair
from .config import AuthConfig
from .exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    TokenBlacklistedError,
    AuthenticationError
)

# Graceful netrun-logging integration
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger, bind_context, log_timing
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)

logger = _logger


class KeyPair:
    """RSA key pair for JWT signing with rotation support."""

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        public_key: rsa.RSAPublicKey,
        created_at: datetime
    ):
        self.key_id = key_id
        self.private_key = private_key
        self.public_key = public_key
        self.created_at = created_at
        self.expires_at = created_at + timedelta(days=90)

    def is_expired(self) -> bool:
        """Check if key pair has expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    def get_private_pem(self) -> bytes:
        """Get private key in PEM format."""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    def get_public_pem(self) -> bytes:
        """Get public key in PEM format."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )


class JWTManager:
    """
    JWT token manager with RS256 signing and Redis blacklisting.

    Handles token generation, validation, refresh, and revocation
    with rotating RSA key pairs for enhanced security.
    """

    def __init__(
        self,
        config: Optional[AuthConfig] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize JWT manager.

        Args:
            config: Authentication configuration
            redis_client: Redis client for blacklist and session tracking
        """
        self.config = config or AuthConfig()
        self.redis_client = redis_client
        self.key_pairs: Dict[str, KeyPair] = {}
        self.current_key_id: Optional[str] = None
        self._initialize_keys()

    def _initialize_keys(self) -> None:
        """Initialize RSA key pairs for JWT signing."""
        try:
            # Try loading existing keys from config
            private_pem = self.config.load_private_key()
            public_pem = self.config.load_public_key()

            private_key = serialization.load_pem_private_key(
                private_pem.encode(),
                password=None,
                backend=default_backend()
            )
            public_key = serialization.load_pem_public_key(
                public_pem.encode(),
                backend=default_backend()
            )

            key_id = "loaded-key"
            key_pair = KeyPair(key_id, private_key, public_key, datetime.now(timezone.utc))
            self.key_pairs[key_id] = key_pair
            self.current_key_id = key_id
            logger.info(f"Loaded JWT key pair from configuration")

        except ValueError:
            # Generate new key pair if none configured
            logger.info("No keys configured, generating new key pair")
            key_pair = self._generate_key_pair()
            self.key_pairs[key_pair.key_id] = key_pair
            self.current_key_id = key_pair.key_id
            logger.info(f"Generated new JWT key pair: {key_pair.key_id}")

    def _generate_key_pair(self) -> KeyPair:
        """Generate new RSA key pair for JWT signing."""
        key_id = secrets.token_urlsafe(16)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,  # NIST minimum for RSA
            backend=default_backend()
        )
        public_key = private_key.public_key()
        created_at = datetime.now(timezone.utc)

        return KeyPair(key_id, private_key, public_key, created_at)

    def rotate_keys(self) -> None:
        """
        Rotate RSA key pairs for security.

        Generates new key pair and retains old keys for existing tokens.
        """
        new_key_pair = self._generate_key_pair()
        self.key_pairs[new_key_pair.key_id] = new_key_pair
        self.current_key_id = new_key_pair.key_id

        # Clean up expired keys (except current)
        expired_keys = [
            kid for kid, kp in self.key_pairs.items()
            if kp.is_expired() and kid != self.current_key_id
        ]
        for kid in expired_keys:
            del self.key_pairs[kid]
            logger.info(f"Removed expired key: {kid}")

        logger.info(f"Rotated to new key: {new_key_pair.key_id}")

    async def generate_token_pair(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> TokenPair:
        """
        Generate access and refresh token pair.

        Args:
            user_id: User unique identifier
            organization_id: Organization identifier
            roles: List of user roles
            permissions: List of user permissions
            session_id: Optional session identifier
            ip_address: Optional IP address
            user_agent: Optional user agent

        Returns:
            TokenPair with access_token, refresh_token, and metadata
        """
        now = datetime.now(timezone.utc)
        roles = roles or []
        permissions = permissions or []

        # Generate session ID if not provided
        if not session_id:
            session_id = secrets.token_urlsafe(32)

        # Generate access token
        access_jti = secrets.token_urlsafe(32)
        access_expiry = now + self.config.get_access_token_expiry()
        access_claims = TokenClaims(
            jti=access_jti,
            sub=user_id,
            typ=TokenType.ACCESS,
            iat=int(now.timestamp()),
            exp=int(access_expiry.timestamp()),
            nbf=int(now.timestamp()),
            iss=self.config.jwt_issuer,
            aud=self.config.jwt_audience,
            user_id=user_id,
            organization_id=organization_id,
            roles=roles,
            permissions=permissions,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Generate refresh token
        refresh_jti = secrets.token_urlsafe(32)
        refresh_expiry = now + self.config.get_refresh_token_expiry()
        refresh_claims = TokenClaims(
            jti=refresh_jti,
            sub=user_id,
            typ=TokenType.REFRESH,
            iat=int(now.timestamp()),
            exp=int(refresh_expiry.timestamp()),
            nbf=int(now.timestamp()),
            iss=self.config.jwt_issuer,
            aud=self.config.jwt_audience,
            user_id=user_id,
            organization_id=organization_id,
            roles=roles,
            permissions=[],  # Refresh tokens have no permissions
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Get current key pair
        key_pair = self.key_pairs[self.current_key_id]

        # Encode tokens
        access_token = jwt.encode(
            access_claims.to_dict(),
            key_pair.get_private_pem(),
            algorithm=self.config.jwt_algorithm,
            headers={"kid": self.current_key_id}
        )

        refresh_token = jwt.encode(
            refresh_claims.to_dict(),
            key_pair.get_private_pem(),
            algorithm=self.config.jwt_algorithm,
            headers={"kid": self.current_key_id}
        )

        # Store refresh token metadata in Redis
        if self.redis_client:
            await self._store_refresh_token(refresh_jti, user_id, session_id)

        # Audit log with structured context
        if _use_netrun_logging:
            logger.info(
                "token_pair_generated",
                user_id=user_id,
                organization_id=organization_id,
                session_id=session_id,
                access_jti=access_jti,
                refresh_jti=refresh_jti,
                ip_address=ip_address,
                roles_count=len(roles),
                permissions_count=len(permissions),
                token_type="jwt_access_refresh",
                expiry_seconds=int(self.config.get_access_token_expiry().total_seconds())
            )
        else:
            logger.info(
                f"Generated token pair for user {user_id}",
                extra={
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "session_id": session_id,
                    "access_jti": access_jti,
                    "refresh_jti": refresh_jti,
                    "ip_address": ip_address
                }
            )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=int(self.config.get_access_token_expiry().total_seconds())
        )

    async def verify_token(
        self,
        token: str,
        token_type: TokenType = TokenType.ACCESS,
        verify_blacklist: bool = True
    ) -> TokenClaims:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type
            verify_blacklist: Check if token is blacklisted

        Returns:
            Decoded token claims

        Raises:
            TokenExpiredError: If token has expired
            TokenInvalidError: If token is malformed or invalid
            TokenBlacklistedError: If token has been revoked
        """
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            if not kid or kid not in self.key_pairs:
                raise TokenInvalidError(
                    message="Invalid token key",
                    details={"key_id": kid}
                )

            # Get public key for verification
            key_pair = self.key_pairs[kid]

            # Decode and verify token
            payload = jwt.decode(
                token,
                key_pair.get_public_pem(),
                algorithms=[self.config.jwt_algorithm],
                audience=self.config.jwt_audience,
                issuer=self.config.jwt_issuer
            )

            # Parse claims
            claims = TokenClaims(**payload)

            # Verify token type
            if claims.typ != token_type:
                raise TokenInvalidError(
                    message=f"Invalid token type. Expected {token_type}, got {claims.typ}",
                    details={"expected": token_type.value, "actual": claims.typ.value}
                )

            # Check blacklist
            if verify_blacklist and self.redis_client:
                is_blacklisted = await self._is_token_blacklisted(claims.jti)
                if is_blacklisted:
                    if _use_netrun_logging:
                        logger.warning(
                            "token_blacklisted",
                            jti=claims.jti,
                            user_id=claims.user_id,
                            token_type=claims.typ.value
                        )
                    raise TokenBlacklistedError(
                        message="Token has been revoked",
                        details={"jti": claims.jti}
                    )

            # Log successful verification
            if _use_netrun_logging:
                logger.debug(
                    "token_verified",
                    jti=claims.jti,
                    user_id=claims.user_id,
                    token_type=claims.typ.value,
                    organization_id=claims.organization_id
                )

            return claims

        except jwt.ExpiredSignatureError:
            if _use_netrun_logging:
                logger.warning("token_expired", error_type="ExpiredSignatureError")
            raise TokenExpiredError(message="Token has expired")
        except jwt.InvalidTokenError as e:
            if _use_netrun_logging:
                logger.warning(
                    "token_invalid",
                    error_type="InvalidTokenError",
                    error_detail=str(e)
                )
            else:
                logger.warning(f"Invalid token: {str(e)}")
            raise TokenInvalidError(message="Invalid token format or signature")

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> TokenPair:
        """
        Refresh access and refresh tokens using valid refresh token.

        Args:
            refresh_token: Valid refresh token
            ip_address: Optional new IP address
            user_agent: Optional new user agent

        Returns:
            New TokenPair with access and refresh tokens
        """
        # Verify refresh token
        claims = await self.verify_token(refresh_token, TokenType.REFRESH)

        # Check if refresh token is still valid in Redis
        if self.redis_client:
            is_valid = await self._validate_refresh_token(claims.jti, claims.user_id)
            if not is_valid:
                raise TokenInvalidError(
                    message="Invalid or expired refresh token",
                    details={"jti": claims.jti}
                )

        # Revoke old refresh token
        await self.revoke_token(claims.jti)

        # Generate new token pair with same claims
        new_token_pair = await self.generate_token_pair(
            user_id=claims.user_id,
            organization_id=claims.organization_id,
            roles=claims.roles,
            permissions=claims.permissions,
            session_id=claims.session_id,
            ip_address=ip_address or claims.ip_address,
            user_agent=user_agent or claims.user_agent
        )

        # Audit log with structured context
        if _use_netrun_logging:
            logger.info(
                "tokens_refreshed",
                user_id=claims.user_id,
                organization_id=claims.organization_id,
                old_jti=claims.jti,
                session_id=claims.session_id,
                ip_address=ip_address or claims.ip_address,
                operation="token_refresh"
            )
        else:
            logger.info(
                f"Refreshed tokens for user {claims.user_id}",
                extra={
                    "user_id": claims.user_id,
                    "old_jti": claims.jti,
                    "session_id": claims.session_id
                }
            )

        return new_token_pair

    async def revoke_token(self, jti: str) -> None:
        """
        Revoke token by adding to blacklist.

        Args:
            jti: JWT ID to revoke
        """
        if self.redis_client:
            key = f"{self.config.redis_key_prefix}blacklist:{jti}"
            # Use refresh token expiry as TTL for blacklist entries
            ttl = int(self.config.get_refresh_token_expiry().total_seconds())
            await self.redis_client.setex(key, ttl, "1")

            if _use_netrun_logging:
                logger.info("token_revoked", jti=jti, operation="token_revoke")
            else:
                logger.info(f"Revoked token: {jti}")

    async def revoke_all_user_tokens(self, user_id: str) -> None:
        """
        Revoke all tokens for a user (logout from all sessions).

        Args:
            user_id: User ID whose tokens to revoke
        """
        if self.redis_client:
            # Get all refresh tokens for user
            pattern = f"{self.config.redis_key_prefix}refresh:{user_id}:*"
            cursor = 0
            revoked_count = 0

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match=pattern, count=100
                )
                for key in keys:
                    # Extract JTI from key and blacklist it
                    key_str = key if isinstance(key, str) else key.decode()
                    jti = key_str.split(":")[-1]
                    await self.revoke_token(jti)
                    await self.redis_client.delete(key)
                    revoked_count += 1

                if cursor == 0:
                    break

            if _use_netrun_logging:
                logger.info(
                    "user_tokens_revoked",
                    user_id=user_id,
                    revoked_count=revoked_count,
                    operation="logout_all_sessions"
                )
            else:
                logger.info(f"Revoked {revoked_count} tokens for user: {user_id}")

    async def _store_refresh_token(
        self,
        jti: str,
        user_id: str,
        session_id: str
    ) -> None:
        """Store refresh token metadata in Redis for tracking."""
        if self.redis_client:
            key = f"{self.config.redis_key_prefix}refresh:{user_id}:{session_id}:{jti}"
            ttl = int(self.config.get_refresh_token_expiry().total_seconds())
            data = json.dumps({
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            await self.redis_client.setex(key, ttl, data)

    async def _validate_refresh_token(self, jti: str, user_id: str) -> bool:
        """Validate refresh token exists in Redis."""
        if self.redis_client:
            pattern = f"{self.config.redis_key_prefix}refresh:{user_id}:*:{jti}"
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match=pattern, count=10
                )
                if keys:
                    return True
                if cursor == 0:
                    break
        return True  # Allow if Redis not available (fallback)

    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is in blacklist."""
        if self.redis_client:
            key = f"{self.config.redis_key_prefix}blacklist:{jti}"
            exists = await self.redis_client.exists(key)
            return bool(exists)
        return False

    def get_public_keys(self) -> Dict[str, str]:
        """
        Get all public keys for token verification (JWKS endpoint).

        Returns:
            Dictionary of key_id -> public_key_pem
        """
        return {
            kid: kp.get_public_pem().decode("utf-8")
            for kid, kp in self.key_pairs.items()
        }

    async def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of active session information
        """
        sessions = []
        if self.redis_client:
            pattern = f"{self.config.redis_key_prefix}refresh:{user_id}:*"
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match=pattern, count=100
                )
                for key in keys:
                    data = await self.redis_client.get(key)
                    if data:
                        session_info = json.loads(data)
                        key_str = key if isinstance(key, str) else key.decode()
                        session_info["key"] = key_str
                        session_info["session_id"] = key_str.split(":")[3]
                        sessions.append(session_info)

                if cursor == 0:
                    break

        return sessions


# Singleton instance for convenience
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager(
    config: Optional[AuthConfig] = None,
    redis_client: Optional[redis.Redis] = None
) -> JWTManager:
    """
    Get singleton JWT manager instance.

    Args:
        config: Authentication configuration
        redis_client: Redis client for blacklist

    Returns:
        JWTManager instance
    """
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager(config, redis_client)
    return _jwt_manager
