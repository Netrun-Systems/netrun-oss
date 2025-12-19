"""
RBAC Models - Role and Permission definitions

Extracted from: Intirkast middleware/rbac.py
Generalized for multi-project reuse
"""

from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, Field


class Role(str, Enum):
    """
    Role hierarchy for multi-tenant SaaS platforms

    Hierarchy (lowest to highest):
    - viewer: Read-only access (view content, analytics)
    - member: Create/edit own content (schedule posts, generate videos)
    - admin: Manage team (invite users, edit all content)
    - owner: Full control (billing, tenant settings, delete tenant)
    """

    VIEWER = "viewer"
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"


class Permission(str, Enum):
    """
    Fine-grained permissions for resource access control

    Pattern: {resource}:{action}
    Example: posts:create, users:delete, billing:read
    """

    # User management
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"

    # Tenant management
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"

    # Content management (generic)
    CONTENT_READ = "content:read"
    CONTENT_CREATE = "content:create"
    CONTENT_UPDATE = "content:update"
    CONTENT_DELETE = "content:delete"

    # Billing
    BILLING_READ = "billing:read"
    BILLING_UPDATE = "billing:update"

    # Invitations
    INVITATIONS_CREATE = "invitations:create"
    INVITATIONS_DELETE = "invitations:delete"


class RoleHierarchy:
    """
    Role hierarchy and permission mapping

    Provides:
    - Hierarchical role comparison
    - Permission-to-role mapping
    - Role validation utilities
    """

    # Role hierarchy (higher number = more permissions)
    HIERARCHY: Dict[Role, int] = {
        Role.VIEWER: 0,
        Role.MEMBER: 1,
        Role.ADMIN: 2,
        Role.OWNER: 3,
    }

    # Permission mappings (role -> list of permissions)
    PERMISSIONS: Dict[Role, List[Permission]] = {
        Role.VIEWER: [
            Permission.USERS_READ,
            Permission.TENANT_READ,
            Permission.CONTENT_READ,
            Permission.BILLING_READ,
        ],
        Role.MEMBER: [
            # Inherits viewer permissions
            Permission.USERS_READ,
            Permission.TENANT_READ,
            Permission.CONTENT_READ,
            Permission.BILLING_READ,
            # Additional member permissions
            Permission.CONTENT_CREATE,
            Permission.CONTENT_UPDATE,  # Own content only
        ],
        Role.ADMIN: [
            # Inherits member permissions
            Permission.USERS_READ,
            Permission.TENANT_READ,
            Permission.CONTENT_READ,
            Permission.BILLING_READ,
            Permission.CONTENT_CREATE,
            Permission.CONTENT_UPDATE,  # All content
            Permission.CONTENT_DELETE,
            # Additional admin permissions
            Permission.USERS_CREATE,
            Permission.USERS_UPDATE,
            Permission.INVITATIONS_CREATE,
            Permission.INVITATIONS_DELETE,
        ],
        Role.OWNER: [
            # All permissions
            Permission.USERS_READ,
            Permission.USERS_CREATE,
            Permission.USERS_UPDATE,
            Permission.USERS_DELETE,
            Permission.TENANT_READ,
            Permission.TENANT_UPDATE,
            Permission.TENANT_DELETE,
            Permission.CONTENT_READ,
            Permission.CONTENT_CREATE,
            Permission.CONTENT_UPDATE,
            Permission.CONTENT_DELETE,
            Permission.BILLING_READ,
            Permission.BILLING_UPDATE,
            Permission.INVITATIONS_CREATE,
            Permission.INVITATIONS_DELETE,
        ],
    }

    @classmethod
    def has_permission(cls, user_role: str, required_permission: Permission) -> bool:
        """
        Check if a role has a specific permission

        Args:
            user_role: User's role (string)
            required_permission: Required permission

        Returns:
            True if role has permission
        """
        try:
            role = Role(user_role)
        except ValueError:
            return False

        return required_permission in cls.PERMISSIONS.get(role, [])

    @classmethod
    def check_role_permission(cls, user_role: str, required_role: str) -> bool:
        """
        Check if user role has sufficient permissions (hierarchical)

        Args:
            user_role: User's current role
            required_role: Minimum required role

        Returns:
            True if user has sufficient permissions
        """
        try:
            user_role_enum = Role(user_role)
            required_role_enum = Role(required_role)
        except ValueError:
            return False

        user_level = cls.HIERARCHY.get(user_role_enum, -1)
        required_level = cls.HIERARCHY.get(required_role_enum, 999)

        return user_level >= required_level

    @classmethod
    def get_role_level(cls, role: str) -> int:
        """
        Get numeric level for a role

        Args:
            role: Role name

        Returns:
            Numeric level (0-3), or -1 if invalid
        """
        try:
            role_enum = Role(role)
            return cls.HIERARCHY.get(role_enum, -1)
        except ValueError:
            return -1


class RoleAssignment(BaseModel):
    """
    Pydantic model for role assignment

    Used for API requests/responses
    """

    user_id: str = Field(..., description="User ID (UUID)")
    tenant_id: str = Field(..., description="Tenant ID (UUID)")
    role: Role = Field(..., description="Assigned role")
    assigned_by: str | None = Field(None, description="User ID who assigned the role")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
                "role": "admin",
                "assigned_by": "770e8400-e29b-41d4-a716-446655440002",
            }
        }
