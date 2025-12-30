"""
Netrun RBAC Test Fixtures - Pytest fixtures and factories for testing.

Following Netrun Systems SDLC v2.3 standards.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Generator
from uuid import UUID, uuid4

from ..tenancy.context import TenantContext, TenantContextData


@dataclass
class TenantFactory:
    """
    Factory for creating test tenant data.

    Usage:
        factory = TenantFactory()
        tenant1 = factory.create(name="Acme Corp")
        tenant2 = factory.create(name="Widget Inc")
    """

    _counter: int = field(default=0, repr=False)

    def create(
        self,
        *,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        status: str = "active",
        subscription_tier: str = "basic",
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a test tenant dictionary.

        Args:
            id: UUID (auto-generated if not provided)
            name: Tenant name (auto-generated if not provided)
            slug: URL-safe slug (auto-generated if not provided)
            status: Tenant status
            subscription_tier: Subscription level
            settings: Tenant settings

        Returns:
            Dictionary with tenant data
        """
        self._counter += 1
        tenant_id = id or uuid4()
        tenant_name = name or f"Test Tenant {self._counter}"
        tenant_slug = slug or f"test-tenant-{self._counter}"

        return {
            "id": tenant_id,
            "name": tenant_name,
            "slug": tenant_slug,
            "status": status,
            "subscription_tier": subscription_tier,
            "settings": settings or {},
            "max_users": 100,
            "max_teams": 50,
        }

    def create_batch(self, count: int, **kwargs) -> List[Dict[str, Any]]:
        """Create multiple test tenants."""
        return [self.create(**kwargs) for _ in range(count)]


@dataclass
class TeamFactory:
    """
    Factory for creating test team data.

    Usage:
        factory = TeamFactory()
        team1 = factory.create(tenant_id=tenant.id, name="Engineering")
        team2 = factory.create(tenant_id=tenant.id, name="Sales", parent_team_id=team1["id"])
    """

    _counter: int = field(default=0, repr=False)

    def create(
        self,
        tenant_id: UUID,
        *,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        parent_team_id: Optional[UUID] = None,
        path: Optional[str] = None,
        depth: int = 0,
    ) -> Dict[str, Any]:
        """
        Create a test team dictionary.

        Args:
            tenant_id: Parent tenant UUID
            id: Team UUID (auto-generated if not provided)
            name: Team name (auto-generated if not provided)
            parent_team_id: Parent team UUID for hierarchy
            path: Materialized path (auto-generated if not provided)
            depth: Depth in hierarchy

        Returns:
            Dictionary with team data
        """
        self._counter += 1
        team_id = id or uuid4()
        team_name = name or f"Test Team {self._counter}"

        if path is None:
            if parent_team_id:
                # Simplified path generation for testing
                path = f"/.../{team_id}"
            else:
                path = f"/{team_id}"

        return {
            "id": team_id,
            "tenant_id": tenant_id,
            "name": team_name,
            "parent_team_id": parent_team_id,
            "path": path,
            "depth": depth,
            "settings": {},
            "is_public": False,
            "max_members": 100,
        }

    def create_hierarchy(
        self,
        tenant_id: UUID,
        structure: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create a team hierarchy from a structure definition.

        Args:
            tenant_id: Parent tenant UUID
            structure: Nested dict defining hierarchy

        Example:
            structure = {
                "Engineering": {
                    "Backend": {},
                    "Frontend": {},
                },
                "Sales": {
                    "Enterprise": {},
                    "SMB": {},
                },
            }
            teams = factory.create_hierarchy(tenant_id, structure)

        Returns:
            Dict mapping team names to team data
        """
        result = {}

        def _create_tree(items: Dict, parent_id: Optional[UUID] = None, depth: int = 0):
            for name, children in items.items():
                team = self.create(
                    tenant_id,
                    name=name,
                    parent_team_id=parent_id,
                    depth=depth,
                )
                result[name] = team
                if children:
                    _create_tree(children, team["id"], depth + 1)

        _create_tree(structure)
        return result


@dataclass
class UserFactory:
    """
    Factory for creating test user data.

    Usage:
        factory = UserFactory()
        user1 = factory.create()
        admin = factory.create(roles=["admin"])
    """

    _counter: int = field(default=0, repr=False)

    def create(
        self,
        *,
        id: Optional[UUID] = None,
        email: Optional[str] = None,
        roles: Optional[List[str]] = None,
        team_ids: Optional[List[UUID]] = None,
        permissions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a test user dictionary.

        Args:
            id: User UUID (auto-generated if not provided)
            email: User email (auto-generated if not provided)
            roles: List of roles (defaults to ["member"])
            team_ids: List of team UUIDs user belongs to
            permissions: List of custom permissions

        Returns:
            Dictionary with user data
        """
        self._counter += 1
        user_id = id or uuid4()
        user_email = email or f"testuser{self._counter}@example.com"

        return {
            "id": user_id,
            "email": user_email,
            "roles": roles or ["member"],
            "team_ids": team_ids or [],
            "permissions": permissions or [],
        }


@contextmanager
def tenant_context(
    tenant_id: UUID,
    tenant_slug: str = "test-tenant",
    user_id: Optional[UUID] = None,
    user_roles: Optional[List[str]] = None,
    team_ids: Optional[List[UUID]] = None,
    team_paths: Optional[List[str]] = None,
) -> Generator[TenantContextData, None, None]:
    """
    Context manager for setting tenant context in tests.

    Usage:
        with tenant_context(tenant_id=tenant1.id, user_id=user.id):
            contacts = await service.get_all()
            # Only tenant1's contacts

    Args:
        tenant_id: UUID of the tenant
        tenant_slug: Tenant slug
        user_id: UUID of the user
        user_roles: List of role strings
        team_ids: List of team UUIDs
        team_paths: List of team paths

    Yields:
        TenantContextData
    """
    ctx = TenantContext(
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        user_id=user_id,
        user_roles=user_roles,
        team_ids=team_ids,
        team_paths=team_paths,
    )

    with ctx as data:
        yield data


def create_test_tenant(
    name: str = "Test Tenant",
    slug: str = "test-tenant",
    **kwargs
) -> Dict[str, Any]:
    """
    Quick helper to create a single test tenant.

    Args:
        name: Tenant name
        slug: Tenant slug
        **kwargs: Additional tenant attributes

    Returns:
        Tenant data dictionary
    """
    factory = TenantFactory()
    return factory.create(name=name, slug=slug, **kwargs)


def create_test_team(
    tenant_id: UUID,
    name: str = "Test Team",
    **kwargs
) -> Dict[str, Any]:
    """
    Quick helper to create a single test team.

    Args:
        tenant_id: Parent tenant UUID
        name: Team name
        **kwargs: Additional team attributes

    Returns:
        Team data dictionary
    """
    factory = TeamFactory()
    return factory.create(tenant_id, name=name, **kwargs)


def create_test_user(
    roles: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Quick helper to create a single test user.

    Args:
        roles: List of roles
        **kwargs: Additional user attributes

    Returns:
        User data dictionary
    """
    factory = UserFactory()
    return factory.create(roles=roles, **kwargs)


# Pytest fixtures (can be imported and used directly)

def pytest_tenant_factory():
    """Pytest fixture for TenantFactory."""
    return TenantFactory()


def pytest_team_factory():
    """Pytest fixture for TeamFactory."""
    return TeamFactory()


def pytest_user_factory():
    """Pytest fixture for UserFactory."""
    return UserFactory()
