"""
Netrun RBAC Migrations Module - Helpers for adding tenancy to existing tables.

Following Netrun Systems SDLC v2.3 standards.

Provides utilities for:
- Adding tenant_id columns to existing tables
- Migrating existing data to a default tenant
- Generating PostgreSQL RLS policies
- Creating tenancy-related indexes

Usage with Alembic:
    from netrun.rbac.migrations import (
        add_tenancy_to_table,
        generate_rls_policies,
        create_tenancy_indexes,
    )

    def upgrade():
        # Add tenant_id to existing table
        add_tenancy_to_table(op, "contacts", default_tenant_id="...")

        # Generate and apply RLS policies
        rls_sql = generate_rls_policies(["contacts", "deals", "tasks"])
        op.execute(rls_sql)

        # Create indexes
        create_tenancy_indexes(op, "contacts")
"""

from .helpers import (
    add_tenancy_to_table,
    remove_tenancy_from_table,
    create_tenancy_indexes,
    drop_tenancy_indexes,
    migrate_data_to_tenant,
    create_tenants_table,
    create_teams_table,
    create_memberships_tables,
    create_resource_shares_table,
)
from .rls_generator import (
    generate_rls_policies,
    generate_rls_policy,
    enable_rls_on_table,
    disable_rls_on_table,
    generate_full_tenancy_setup,
)

# Aliases and stubs for backward compatibility with main __init__.py
add_tenant_column_to_existing = add_tenancy_to_table  # Alias
backfill_tenant_data = migrate_data_to_tenant  # Alias


def add_team_column_to_existing(op, table_name: str, **kwargs):
    """Add team_id column to existing table. Stub for future implementation."""
    pass  # TODO: Implement team column migration


def add_share_columns_to_existing(op, table_name: str, **kwargs):
    """Add sharing columns to existing table. Stub for future implementation."""
    pass  # TODO: Implement share columns migration


def create_rls_helper_functions(op):
    """Create RLS helper functions in PostgreSQL. Stub for future implementation."""
    pass  # TODO: Implement RLS helper functions


def create_tenancy_audit_triggers(op, table_name: str, **kwargs):
    """Create audit triggers for tenancy operations. Stub for future implementation."""
    pass  # TODO: Implement audit triggers


__all__ = [
    # Table modification helpers
    "add_tenancy_to_table",
    "add_tenant_column_to_existing",
    "add_team_column_to_existing",
    "add_share_columns_to_existing",
    "remove_tenancy_from_table",
    "create_tenancy_indexes",
    "drop_tenancy_indexes",
    "migrate_data_to_tenant",
    "backfill_tenant_data",
    # Table creation helpers
    "create_tenants_table",
    "create_teams_table",
    "create_memberships_tables",
    "create_resource_shares_table",
    # RLS generation
    "generate_rls_policies",
    "generate_rls_policy",
    "enable_rls_on_table",
    "disable_rls_on_table",
    "generate_full_tenancy_setup",
    "create_rls_helper_functions",
    "create_tenancy_audit_triggers",
]
