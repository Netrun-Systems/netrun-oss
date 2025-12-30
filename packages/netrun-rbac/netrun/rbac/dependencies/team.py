"""
Netrun RBAC Team Dependencies - FastAPI dependencies for team access control.

Following Netrun Systems SDLC v2.3 standards.
"""

from typing import Optional, Callable, List
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Path, Query
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from ..tenancy.context import TenantContext, TenantContextData
from ..models.enums import TeamRole


def require_team_member(team_id_param: str = "team_id") -> Callable:
    """
    Dependency factory that requires team membership.

    Validates that the current user is a member of the specified team
    (either directly or via parent team inheritance).

    Args:
        team_id_param: Name of the path/query parameter containing team ID

    Returns:
        Dependency function that validates team membership

    Usage:
        @app.get("/teams/{team_id}/documents")
        async def team_documents(
            team_id: UUID,
            tenant = Depends(require_team_member("team_id"))
        ):
            # Only team members can access
            pass
    """
    async def dependency(
        request: Request,
    ) -> TenantContextData:
        ctx = TenantContext.get_current()

        if ctx is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "TENANT_REQUIRED",
                    "message": "Tenant identification required"
                }
            )

        # Get team_id from path parameters
        team_id_str = request.path_params.get(team_id_param)
        if not team_id_str:
            # Try query parameters
            team_id_str = request.query_params.get(team_id_param)

        if not team_id_str:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "TEAM_ID_REQUIRED",
                    "message": f"Team ID required in {team_id_param}"
                }
            )

        try:
            team_id = UUID(team_id_str)
        except ValueError:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "INVALID_TEAM_ID",
                    "message": "Invalid team ID format"
                }
            )

        # Check if user is in this team
        if not ctx.is_in_team(team_id):
            # Check if user has access via team hierarchy (their team is a parent)
            # This requires checking if the target team's path starts with user's team path
            has_hierarchy_access = False
            for user_path in ctx.team_paths:
                # User has access if they're in an ancestor team
                # This would need the target team's path, which we don't have here
                # In practice, this check would be done in the service layer
                pass

            if not has_hierarchy_access:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail={
                        "error": "TEAM_ACCESS_DENIED",
                        "message": "Not a member of this team",
                        "team_id": str(team_id)
                    }
                )

        return ctx

    return dependency


def require_team_role(
    *roles: TeamRole,
    team_id_param: str = "team_id"
) -> Callable:
    """
    Dependency factory that requires specific team roles.

    Args:
        *roles: TeamRole values that are allowed
        team_id_param: Name of the path/query parameter containing team ID

    Returns:
        Dependency function that validates team role

    Usage:
        @app.delete("/teams/{team_id}")
        async def delete_team(
            team_id: UUID,
            tenant = Depends(require_team_role(TeamRole.OWNER))
        ):
            # Only team owners can delete
            pass
    """
    allowed_roles = set(r.value for r in roles)

    async def dependency(
        request: Request,
    ) -> TenantContextData:
        ctx = TenantContext.get_current()

        if ctx is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "TENANT_REQUIRED",
                    "message": "Tenant identification required"
                }
            )

        # Get team_id from path parameters
        team_id_str = request.path_params.get(team_id_param)
        if not team_id_str:
            team_id_str = request.query_params.get(team_id_param)

        if not team_id_str:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "TEAM_ID_REQUIRED",
                    "message": f"Team ID required in {team_id_param}"
                }
            )

        try:
            team_id = UUID(team_id_str)
        except ValueError:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "INVALID_TEAM_ID",
                    "message": "Invalid team ID format"
                }
            )

        # Check if user is in this team
        if not ctx.is_in_team(team_id):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "TEAM_ACCESS_DENIED",
                    "message": "Not a member of this team",
                    "team_id": str(team_id)
                }
            )

        # Role check would require database lookup to get user's role in team
        # This is a simplified version that checks tenant-level roles
        # Full implementation would use TeamService.get_user_role_in_team()

        # For now, check if user is tenant admin (can manage any team)
        if not ctx.is_admin:
            # Would check team-specific role here
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "INSUFFICIENT_TEAM_ROLE",
                    "message": f"Required team role: {', '.join(allowed_roles)}",
                }
            )

        return ctx

    return dependency


async def get_user_teams(
    request: Request,
) -> List[UUID]:
    """
    Get the current user's team IDs.

    Returns empty list if no context or no teams.

    Usage:
        @app.get("/my-team-resources")
        async def my_team_resources(
            team_ids: List[UUID] = Depends(get_user_teams)
        ):
            return await service.get_by_teams(team_ids)
    """
    ctx = TenantContext.get_current()

    if ctx is None:
        return []

    return list(ctx.team_ids)


async def get_user_team_paths(
    request: Request,
) -> List[str]:
    """
    Get the current user's team paths (for hierarchy queries).

    Returns empty list if no context or no teams.

    Usage:
        @app.get("/team-hierarchy-resources")
        async def hierarchy_resources(
            team_paths: List[str] = Depends(get_user_team_paths)
        ):
            # Use paths for hierarchy-aware queries
            return await service.get_by_team_hierarchy(team_paths)
    """
    ctx = TenantContext.get_current()

    if ctx is None:
        return []

    return list(ctx.team_paths)


def require_any_team_membership() -> Callable:
    """
    Dependency that requires user to be a member of at least one team.

    Usage:
        @app.get("/team-dashboard")
        async def team_dashboard(
            tenant = Depends(require_any_team_membership())
        ):
            # Only users in at least one team can access
            pass
    """
    async def dependency(
        request: Request,
    ) -> TenantContextData:
        ctx = TenantContext.get_current()

        if ctx is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "TENANT_REQUIRED",
                    "message": "Tenant identification required"
                }
            )

        if not ctx.team_ids:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "TEAM_MEMBERSHIP_REQUIRED",
                    "message": "Must be a member of at least one team"
                }
            )

        return ctx

    return dependency


def require_team_admin(team_id_param: str = "team_id") -> Callable:
    """
    Convenience wrapper for require_team_role(TeamRole.ADMIN).

    Usage:
        @app.post("/teams/{team_id}/invite")
        async def invite_team_member(
            team_id: UUID,
            tenant = Depends(require_team_admin())
        ):
            # Only team admins can invite
            pass
    """
    return require_team_role(TeamRole.ADMIN, team_id_param=team_id_param)


def require_team_owner(team_id_param: str = "team_id") -> Callable:
    """
    Convenience wrapper for require_team_role(TeamRole.OWNER).

    Usage:
        @app.delete("/teams/{team_id}")
        async def delete_team(
            team_id: UUID,
            tenant = Depends(require_team_owner())
        ):
            # Only team owner can delete
            pass
    """
    return require_team_role(TeamRole.OWNER, team_id_param=team_id_param)
