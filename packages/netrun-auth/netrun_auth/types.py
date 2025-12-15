"""
Netrun Authentication - Type Definitions
=========================================

Pydantic models for authentication context, token claims, and user types.

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class TokenType(str, Enum):
    """Token type enumeration."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class TokenClaims(BaseModel):
    """
    JWT token claims structure.

    Attributes:
        jti: JWT ID (unique identifier)
        sub: Subject (user_id)
        typ: Token type (access/refresh/api_key)
        iat: Issued at timestamp
        exp: Expiration timestamp
        nbf: Not before timestamp
        iss: Issuer
        aud: Audience
        user_id: User unique identifier
        organization_id: Organization unique identifier
        roles: List of user roles
        permissions: List of user permissions
        session_id: Session identifier for tracking
        ip_address: IP address of token creation
        user_agent: User agent of token creation
    """
    model_config = ConfigDict(extra="forbid")

    jti: str = Field(..., description="JWT unique identifier")
    sub: str = Field(..., description="Subject (user_id)")
    typ: TokenType = Field(..., description="Token type")
    iat: int = Field(..., description="Issued at timestamp")
    exp: int = Field(..., description="Expiration timestamp")
    nbf: int = Field(default=0, description="Not before timestamp")
    iss: str = Field(..., description="Issuer")
    aud: str = Field(..., description="Audience")
    user_id: str = Field(..., description="User unique identifier")
    organization_id: Optional[str] = Field(None, description="Organization identifier")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_id: Optional[str] = Field(None, description="Session identifier")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")

    def to_dict(self) -> Dict[str, Any]:
        """Convert claims to dictionary for JWT encoding."""
        return self.model_dump(exclude_none=True, mode="json")


class User(BaseModel):
    """
    Authenticated user model.

    Simplified user representation for authentication context.
    Full user details should be fetched from user service.
    """
    model_config = ConfigDict(extra="allow")

    user_id: str = Field(..., description="User unique identifier")
    organization_id: Optional[str] = Field(None, description="Organization identifier")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_id: Optional[str] = Field(None, description="Session identifier")
    email: Optional[str] = Field(None, description="User email address")
    display_name: Optional[str] = Field(None, description="User display name")

    def has_role(self, role: str) -> bool:
        """Check if user has specified role."""
        return role in self.roles

    def has_any_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def has_all_roles(self, *roles: str) -> bool:
        """Check if user has all specified roles."""
        return all(role in self.roles for role in roles)

    def has_permission(self, permission: str) -> bool:
        """Check if user has specified permission."""
        return permission in self.permissions

    def has_any_permission(self, *permissions: str) -> bool:
        """Check if user has any of the specified permissions."""
        return any(perm in self.permissions for perm in permissions)

    def has_all_permissions(self, *permissions: str) -> bool:
        """Check if user has all specified permissions."""
        return all(perm in self.permissions for perm in permissions)

    async def has_permission_casbin(
        self,
        enforcer: Any,
        resource: str,
        action: str,
        tenant_id: str | None = None,
    ) -> bool:
        """
        Check permission using Casbin enforcer.

        Args:
            enforcer: Casbin Enforcer instance
            resource: Resource name
            action: Action name
            tenant_id: Tenant/organization identifier (optional, uses user's org if None)

        Returns:
            True if user has permission

        Example:
            from casbin import Enforcer
            enforcer = Enforcer("model.conf", "policy.csv")

            if await user.has_permission_casbin(enforcer, "users", "read"):
                # User can read users
                pass
        """
        tenant = tenant_id or self.organization_id
        if tenant:
            return await enforcer.enforce(self.user_id, tenant, resource, action)
        else:
            return await enforcer.enforce(self.user_id, resource, action)


class AuthContext(BaseModel):
    """
    Authentication context for request processing.

    Injected into request.state for access in route handlers.
    """
    model_config = ConfigDict(extra="allow")

    user_id: str = Field(..., description="User unique identifier")
    organization_id: Optional[str] = Field(None, description="Organization identifier")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_id: str = Field(..., description="Session identifier")
    authenticated_at: datetime = Field(..., description="Authentication timestamp")
    auth_method: Literal["jwt", "api_key", "oauth"] = Field(..., description="Authentication method")
    token_jti: Optional[str] = Field(None, description="Token JWT ID")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")

    def to_user(self) -> User:
        """Convert AuthContext to User model."""
        return User(
            user_id=self.user_id,
            organization_id=self.organization_id,
            roles=self.roles,
            permissions=self.permissions,
            session_id=self.session_id
        )


class TokenPair(BaseModel):
    """Token pair response model."""
    access_token: str = Field(..., description="Access token (15 min expiry)")
    refresh_token: str = Field(..., description="Refresh token (30 day expiry)")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until access token expires")


class APIKey(BaseModel):
    """API key model."""
    model_config = ConfigDict(extra="forbid")

    key_id: str = Field(..., description="API key unique identifier")
    key_hash: str = Field(..., description="Hashed API key value")
    user_id: str = Field(..., description="User who owns the key")
    organization_id: Optional[str] = Field(None, description="Organization identifier")
    name: str = Field(..., description="API key display name")
    scopes: List[str] = Field(default_factory=list, description="API key scopes")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(default=True, description="Active status")


class Permission(BaseModel):
    """Permission model."""
    model_config = ConfigDict(extra="forbid")

    resource: str = Field(..., description="Resource name (e.g., 'users', 'projects')")
    action: str = Field(..., description="Action name (e.g., 'read', 'write', 'delete')")

    def __str__(self) -> str:
        """String representation in resource:action format."""
        return f"{self.resource}:{self.action}"

    @classmethod
    def from_string(cls, permission_str: str) -> "Permission":
        """Parse permission from string format."""
        parts = permission_str.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid permission format: {permission_str}. Expected 'resource:action'")
        return cls(resource=parts[0], action=parts[1])


class Role(BaseModel):
    """Role model with permission aggregation."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Role name (e.g., 'admin', 'user', 'viewer')")
    permissions: List[str] = Field(default_factory=list, description="Permission strings")
    inherits_from: Optional[List[str]] = Field(None, description="Parent roles to inherit permissions")
    description: Optional[str] = Field(None, description="Role description")

    def has_permission(self, permission: str) -> bool:
        """Check if role grants specified permission."""
        return permission in self.permissions

    def add_permission(self, permission: str) -> None:
        """Add permission to role."""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: str) -> None:
        """Remove permission from role."""
        if permission in self.permissions:
            self.permissions.remove(permission)
