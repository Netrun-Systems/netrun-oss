"""
Netrun RBAC Migration Helpers - Alembic helpers for adding tenancy to existing tables.

Following Netrun Systems SDLC v2.3 standards.
"""

from typing import Optional, List


def add_tenancy_to_table(
    op,
    table_name: str,
    default_tenant_id: Optional[str] = None,
    *,
    add_team_id: bool = False,
    add_audit_fields: bool = False,
    add_soft_delete: bool = False,
):
    """
    Add tenant_id column (and optionally other tenancy columns) to an existing table.

    This is an Alembic migration helper that:
    1. Adds tenant_id column (nullable initially)
    2. Updates existing rows with default tenant ID
    3. Makes tenant_id NOT NULL
    4. Creates foreign key and index

    Args:
        op: Alembic operations object
        table_name: Name of the table to modify
        default_tenant_id: UUID string for existing rows (required if table has data)
        add_team_id: Also add team_id column
        add_audit_fields: Also add created_by, updated_by columns
        add_soft_delete: Also add is_deleted, deleted_at, deleted_by columns

    Example:
        def upgrade():
            add_tenancy_to_table(
                op,
                "contacts",
                default_tenant_id="00000000-0000-0000-0000-000000000001",
                add_team_id=True,
                add_audit_fields=True,
            )
    """
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID

    # Step 1: Add tenant_id as nullable
    op.add_column(
        table_name,
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            nullable=True,
            comment="Tenant ID for data isolation"
        )
    )

    # Step 2: Update existing rows with default tenant
    if default_tenant_id:
        op.execute(
            f"UPDATE {table_name} SET tenant_id = '{default_tenant_id}' "
            f"WHERE tenant_id IS NULL"
        )

    # Step 3: Make NOT NULL
    op.alter_column(
        table_name,
        "tenant_id",
        nullable=False
    )

    # Step 4: Add foreign key
    op.create_foreign_key(
        f"fk_{table_name}_tenant_id",
        table_name,
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # Step 5: Add index
    op.create_index(
        f"idx_{table_name}_tenant_id",
        table_name,
        ["tenant_id"]
    )

    # Optional: Add team_id
    if add_team_id:
        op.add_column(
            table_name,
            sa.Column(
                "team_id",
                UUID(as_uuid=True),
                nullable=True,
                comment="Team ID for group access"
            )
        )
        op.create_foreign_key(
            f"fk_{table_name}_team_id",
            table_name,
            "teams",
            ["team_id"],
            ["id"],
            ondelete="SET NULL"
        )
        op.create_index(
            f"idx_{table_name}_team_id",
            table_name,
            ["team_id"]
        )

    # Optional: Add audit fields
    if add_audit_fields:
        op.add_column(
            table_name,
            sa.Column(
                "created_by",
                UUID(as_uuid=True),
                nullable=True,
                comment="UUID of creating user"
            )
        )
        op.add_column(
            table_name,
            sa.Column(
                "updated_by",
                UUID(as_uuid=True),
                nullable=True,
                comment="UUID of last updating user"
            )
        )

    # Optional: Add soft delete
    if add_soft_delete:
        op.add_column(
            table_name,
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default="false",
                comment="Soft delete flag"
            )
        )
        op.add_column(
            table_name,
            sa.Column(
                "deleted_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Soft delete timestamp"
            )
        )
        op.add_column(
            table_name,
            sa.Column(
                "deleted_by",
                UUID(as_uuid=True),
                nullable=True,
                comment="UUID of deleting user"
            )
        )
        op.create_index(
            f"idx_{table_name}_is_deleted",
            table_name,
            ["is_deleted"]
        )


def remove_tenancy_from_table(
    op,
    table_name: str,
    *,
    remove_team_id: bool = False,
    remove_audit_fields: bool = False,
    remove_soft_delete: bool = False,
):
    """
    Remove tenancy columns from a table (rollback helper).

    Args:
        op: Alembic operations object
        table_name: Name of the table to modify
        remove_team_id: Also remove team_id column
        remove_audit_fields: Also remove created_by, updated_by columns
        remove_soft_delete: Also remove is_deleted, deleted_at, deleted_by columns
    """
    # Remove indexes and foreign keys first
    op.drop_index(f"idx_{table_name}_tenant_id", table_name)
    op.drop_constraint(f"fk_{table_name}_tenant_id", table_name, type_="foreignkey")
    op.drop_column(table_name, "tenant_id")

    if remove_team_id:
        try:
            op.drop_index(f"idx_{table_name}_team_id", table_name)
        except Exception:
            pass
        try:
            op.drop_constraint(f"fk_{table_name}_team_id", table_name, type_="foreignkey")
        except Exception:
            pass
        op.drop_column(table_name, "team_id")

    if remove_audit_fields:
        op.drop_column(table_name, "created_by")
        op.drop_column(table_name, "updated_by")

    if remove_soft_delete:
        try:
            op.drop_index(f"idx_{table_name}_is_deleted", table_name)
        except Exception:
            pass
        op.drop_column(table_name, "is_deleted")
        op.drop_column(table_name, "deleted_at")
        op.drop_column(table_name, "deleted_by")


def create_tenancy_indexes(
    op,
    table_name: str,
    *,
    include_composite: bool = True,
):
    """
    Create standard tenancy indexes for a table.

    Args:
        op: Alembic operations object
        table_name: Name of the table
        include_composite: Create composite indexes for common query patterns
    """
    # Basic tenant index (if not exists)
    try:
        op.create_index(
            f"idx_{table_name}_tenant_id",
            table_name,
            ["tenant_id"]
        )
    except Exception:
        pass  # Already exists

    if include_composite:
        # Composite: tenant + created_at (for time-based queries)
        try:
            op.create_index(
                f"idx_{table_name}_tenant_created",
                table_name,
                ["tenant_id", "created_at"]
            )
        except Exception:
            pass

        # Composite: tenant + is_deleted (for soft delete filtering)
        try:
            op.create_index(
                f"idx_{table_name}_tenant_deleted",
                table_name,
                ["tenant_id", "is_deleted"]
            )
        except Exception:
            pass


def drop_tenancy_indexes(op, table_name: str):
    """
    Drop tenancy indexes from a table.

    Args:
        op: Alembic operations object
        table_name: Name of the table
    """
    indexes_to_drop = [
        f"idx_{table_name}_tenant_id",
        f"idx_{table_name}_team_id",
        f"idx_{table_name}_tenant_created",
        f"idx_{table_name}_tenant_deleted",
        f"idx_{table_name}_is_deleted",
    ]

    for idx in indexes_to_drop:
        try:
            op.drop_index(idx, table_name)
        except Exception:
            pass


def migrate_data_to_tenant(
    op,
    table_name: str,
    tenant_id: str,
    *,
    where_clause: Optional[str] = None,
):
    """
    Migrate existing data to a specific tenant.

    Args:
        op: Alembic operations object
        table_name: Name of the table
        tenant_id: UUID string of target tenant
        where_clause: Optional WHERE condition for selective migration
    """
    sql = f"UPDATE {table_name} SET tenant_id = '{tenant_id}'"

    if where_clause:
        sql += f" WHERE {where_clause}"
    else:
        sql += " WHERE tenant_id IS NULL"

    op.execute(sql)


def create_tenants_table(op):
    """
    Create the tenants table.

    Args:
        op: Alembic operations object
    """
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID, JSONB

    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("domain", sa.String(255), unique=True, nullable=True),
        sa.Column("subscription_tier", sa.String(50), nullable=False, server_default="basic"),
        sa.Column("status", sa.String(20), nullable=False, server_default="trial"),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_teams", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("max_storage_gb", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("settings", JSONB(), nullable=False, server_default="{}"),
        sa.Column("security_settings", JSONB(), nullable=False, server_default="{}"),
        sa.Column("enabled_features", JSONB(), nullable=False, server_default="[]"),
        sa.Column("billing_email", sa.String(255), nullable=True),
        sa.Column("technical_contact", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("idx_tenants_slug", "tenants", ["slug"])
    op.create_index("idx_tenants_domain", "tenants", ["domain"])
    op.create_index("idx_tenants_status", "tenants", ["status"])


def create_teams_table(op):
    """
    Create the teams table with hierarchy support.

    Args:
        op: Alembic operations object
    """
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID, JSONB

    op.create_table(
        "teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True),
        sa.Column("path", sa.String(1000), nullable=False, server_default="/"),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settings", JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_members", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
    )

    op.create_index("idx_teams_tenant_id", "teams", ["tenant_id"])
    op.create_index("idx_teams_parent_team_id", "teams", ["parent_team_id"])
    op.create_index("idx_teams_path", "teams", ["path"])
    op.create_index("idx_teams_tenant_parent", "teams", ["tenant_id", "parent_team_id"])
    op.create_index("idx_teams_tenant_depth", "teams", ["tenant_id", "depth"])


def create_memberships_tables(op):
    """
    Create tenant_memberships and team_memberships tables.

    Args:
        op: Alembic operations object
    """
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID, JSONB

    # Tenant memberships
    op.create_table(
        "tenant_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("custom_permissions", JSONB(), nullable=False, server_default="[]"),
        sa.Column("invited_by", UUID(as_uuid=True), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_membership_tenant_user"),
    )

    op.create_index("idx_tenant_membership_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_index("idx_tenant_membership_user_id", "tenant_memberships", ["user_id"])
    op.create_index("idx_tenant_membership_user_active", "tenant_memberships", ["user_id", "is_active"])

    # Team memberships
    op.create_table(
        "team_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("inherited_from", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("custom_permissions", JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_membership_team_user"),
    )

    op.create_index("idx_team_membership_team_id", "team_memberships", ["team_id"])
    op.create_index("idx_team_membership_user_id", "team_memberships", ["user_id"])
    op.create_index("idx_team_membership_user_active", "team_memberships", ["user_id", "is_active"])
    op.create_index("idx_team_membership_inherited", "team_memberships", ["inherited_from"])


def create_resource_shares_table(op):
    """
    Create the resource_shares table.

    Args:
        op: Alembic operations object
    """
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID, JSONB

    op.create_table(
        "resource_shares",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=False),
        sa.Column("shared_with_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("shared_with_team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True),
        sa.Column("shared_with_tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("shared_externally", sa.String(255), nullable=True),
        sa.Column("permission", sa.String(20), nullable=False, server_default="view"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shared_by", UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_token", sa.String(100), unique=True, nullable=True),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            """
            (shared_with_user_id IS NOT NULL)::int +
            (shared_with_team_id IS NOT NULL)::int +
            (shared_with_tenant_id IS NOT NULL)::int +
            (shared_externally IS NOT NULL)::int = 1
            """,
            name="chk_resource_share_one_target"
        ),
    )

    op.create_index("idx_resource_share_tenant", "resource_shares", ["tenant_id"])
    op.create_index("idx_resource_share_resource", "resource_shares", ["resource_type", "resource_id"])
    op.create_index("idx_resource_share_user", "resource_shares", ["shared_with_user_id"])
    op.create_index("idx_resource_share_team", "resource_shares", ["shared_with_team_id"])
    op.create_index("idx_resource_share_external_token", "resource_shares", ["external_token"])
    op.create_index("idx_resource_share_expires", "resource_shares", ["expires_at"])
