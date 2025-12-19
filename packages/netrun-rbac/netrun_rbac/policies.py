"""
PostgreSQL Row-Level Security (RLS) Policy Generator

Extracted from: Intirkast migrations/versions/001_initial_schema_creation.py
Generates SQL statements for creating RLS policies on multi-tenant tables

RLS Security Model:
- ENABLE ROW LEVEL SECURITY: Activates RLS on table
- tenant_isolation_policy: Enforces tenant isolation using session variable
- bypass_rls_policy (optional): Allows superuser/admin bypass for migrations

PostgreSQL Session Variables:
- app.current_tenant_id: Set by middleware for each request
- app.current_user_id: Set for audit logging

Example RLS Policy:
    CREATE POLICY tenant_isolation_policy ON users
        FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class RLSPolicyGenerator:
    """
    Generator for PostgreSQL Row-Level Security policies

    Extracted from: Intirkast migration patterns (20+ tables with RLS)
    """

    @staticmethod
    def enable_rls(table_name: str) -> str:
        """
        Generate SQL to enable RLS on a table

        Args:
            table_name: Table name to enable RLS

        Returns:
            SQL statement

        Example:
            ALTER TABLE users ENABLE ROW LEVEL SECURITY;
        """
        return f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"

    @staticmethod
    def disable_rls(table_name: str) -> str:
        """
        Generate SQL to disable RLS on a table

        Args:
            table_name: Table name to disable RLS

        Returns:
            SQL statement

        Example:
            ALTER TABLE users DISABLE ROW LEVEL SECURITY;
        """
        return f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;"

    @staticmethod
    def create_tenant_isolation_policy(
        table_name: str,
        tenant_column: str = "tenant_id",
        session_variable: str = "app.current_tenant_id",
        policy_name: str = "tenant_isolation_policy",
    ) -> str:
        """
        Generate SQL for tenant isolation policy (FOR ALL operations)

        Extracted from: Intirkast migration pattern (used on 19 tables)

        Args:
            table_name: Table name to apply policy
            tenant_column: Column containing tenant_id (default: tenant_id)
            session_variable: PostgreSQL session variable (default: app.current_tenant_id)
            policy_name: Policy name (default: tenant_isolation_policy)

        Returns:
            SQL CREATE POLICY statement

        Example Output:
            CREATE POLICY tenant_isolation_policy ON users
                FOR ALL
                USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

        Policy Breakdown:
        - FOR ALL: Applies to SELECT, INSERT, UPDATE, DELETE
        - USING: Filter condition for SELECT/UPDATE/DELETE
        - WITH CHECK: Validation for INSERT/UPDATE (same as USING if not specified)
        - NULLIF(..., ''): Converts empty string to NULL (handles missing variable)
        - current_setting('...', true): true = no error if variable missing
        - ::UUID: Casts string to UUID type

        Security:
        - Enforces tenant isolation at database level
        - Cannot be bypassed by application code
        - Prevents SQL injection attacks from crossing tenant boundaries
        """
        return f"""CREATE POLICY {policy_name} ON {table_name}
    FOR ALL
    USING ({tenant_column} = NULLIF(current_setting('{session_variable}', true), '')::UUID);"""

    @staticmethod
    def create_read_only_policy(
        table_name: str,
        tenant_column: str = "tenant_id",
        session_variable: str = "app.current_tenant_id",
        policy_name: str = "tenant_read_policy",
    ) -> str:
        """
        Generate SQL for read-only tenant policy (FOR SELECT only)

        Extracted from: Intirkast audit_logs pattern (read-only tenant access)

        Args:
            table_name: Table name to apply policy
            tenant_column: Column containing tenant_id
            session_variable: PostgreSQL session variable
            policy_name: Policy name

        Returns:
            SQL CREATE POLICY statement

        Example Output:
            CREATE POLICY tenant_read_policy ON audit_logs
                FOR SELECT
                USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

        Use Case:
        - Audit logs: Tenants can read their logs but cannot modify/delete
        - Immutable data: Prevent UPDATE/DELETE while allowing SELECT
        """
        return f"""CREATE POLICY {policy_name} ON {table_name}
    FOR SELECT
    USING ({tenant_column} = NULLIF(current_setting('{session_variable}', true), '')::UUID);"""

    @staticmethod
    def create_insert_only_policy(
        table_name: str,
        tenant_column: str = "tenant_id",
        session_variable: str = "app.current_tenant_id",
        policy_name: str = "tenant_insert_policy",
    ) -> str:
        """
        Generate SQL for insert-only tenant policy

        Args:
            table_name: Table name to apply policy
            tenant_column: Column containing tenant_id
            session_variable: PostgreSQL session variable
            policy_name: Policy name

        Returns:
            SQL CREATE POLICY statement

        Example Output:
            CREATE POLICY tenant_insert_policy ON audit_logs
                FOR INSERT
                WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

        Use Case:
        - Audit logs: Allow INSERT but prevent modification
        - Append-only tables: Prevent UPDATE/DELETE
        """
        return f"""CREATE POLICY {policy_name} ON {table_name}
    FOR INSERT
    WITH CHECK ({tenant_column} = NULLIF(current_setting('{session_variable}', true), '')::UUID);"""

    @staticmethod
    def drop_policy(table_name: str, policy_name: str) -> str:
        """
        Generate SQL to drop a policy

        Args:
            table_name: Table name
            policy_name: Policy name to drop

        Returns:
            SQL DROP POLICY statement

        Example:
            DROP POLICY IF EXISTS tenant_isolation_policy ON users;
        """
        return f"DROP POLICY IF EXISTS {policy_name} ON {table_name};"

    @staticmethod
    def generate_rls_for_table(
        table_name: str,
        tenant_column: str = "tenant_id",
        session_variable: str = "app.current_tenant_id",
        read_only: bool = False,
    ) -> List[str]:
        """
        Generate complete RLS setup for a table

        Args:
            table_name: Table name to protect
            tenant_column: Column containing tenant_id
            session_variable: PostgreSQL session variable
            read_only: If True, only allow SELECT (for audit tables)

        Returns:
            List of SQL statements to execute

        Example:
            statements = RLSPolicyGenerator.generate_rls_for_table("users")
            for stmt in statements:
                await session.execute(text(stmt))

        Output (for normal table):
            [
                "ALTER TABLE users ENABLE ROW LEVEL SECURITY;",
                "CREATE POLICY tenant_isolation_policy ON users FOR ALL USING (...);"
            ]

        Output (for read-only table):
            [
                "ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;",
                "CREATE POLICY tenant_read_policy ON audit_logs FOR SELECT USING (...);",
                "CREATE POLICY tenant_insert_policy ON audit_logs FOR INSERT WITH CHECK (...);"
            ]
        """
        statements = [RLSPolicyGenerator.enable_rls(table_name)]

        if read_only:
            # Read-only: Allow SELECT and INSERT, prevent UPDATE/DELETE
            statements.append(
                RLSPolicyGenerator.create_read_only_policy(
                    table_name, tenant_column, session_variable
                )
            )
            statements.append(
                RLSPolicyGenerator.create_insert_only_policy(
                    table_name, tenant_column, session_variable
                )
            )
        else:
            # Normal: Allow all operations (SELECT, INSERT, UPDATE, DELETE)
            statements.append(
                RLSPolicyGenerator.create_tenant_isolation_policy(
                    table_name, tenant_column, session_variable
                )
            )

        return statements

    @staticmethod
    def generate_migration_up(
        tables: List[str],
        tenant_column: str = "tenant_id",
        session_variable: str = "app.current_tenant_id",
        read_only_tables: Optional[List[str]] = None,
    ) -> str:
        """
        Generate complete Alembic migration upgrade function

        Args:
            tables: List of table names to protect with RLS
            tenant_column: Column containing tenant_id
            session_variable: PostgreSQL session variable
            read_only_tables: List of tables that should be read-only (e.g., audit_logs)

        Returns:
            Complete migration code

        Example:
            migration = RLSPolicyGenerator.generate_migration_up(
                tables=["users", "posts", "comments"],
                read_only_tables=["audit_logs"]
            )
            print(migration)

        Output:
            def upgrade() -> None:
                # Enable RLS on users
                op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
                op.execute(\"\"\"
                    CREATE POLICY tenant_isolation_policy ON users
                        FOR ALL
                        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
                \"\"\")
                ...
        """
        read_only_tables = read_only_tables or []

        migration_code = ['def upgrade() -> None:']

        for table in tables:
            is_read_only = table in read_only_tables

            # Enable RLS
            migration_code.append(f'    # Enable RLS on {table}')
            migration_code.append(f'    op.execute("{RLSPolicyGenerator.enable_rls(table)}")')

            # Create policies
            if is_read_only:
                # Read-only table (e.g., audit logs)
                migration_code.append(f'    op.execute("""')
                migration_code.append(
                    f'{RLSPolicyGenerator.create_read_only_policy(table, tenant_column, session_variable)}'
                )
                migration_code.append(f'    """)')
                migration_code.append(f'    op.execute("""')
                migration_code.append(
                    f'{RLSPolicyGenerator.create_insert_only_policy(table, tenant_column, session_variable)}'
                )
                migration_code.append(f'    """)')
            else:
                # Normal table
                migration_code.append(f'    op.execute("""')
                migration_code.append(
                    f'{RLSPolicyGenerator.create_tenant_isolation_policy(table, tenant_column, session_variable)}'
                )
                migration_code.append(f'    """)')

            migration_code.append('')  # Blank line between tables

        return '\n'.join(migration_code)

    @staticmethod
    def generate_migration_down(
        tables: List[str],
        read_only_tables: Optional[List[str]] = None,
    ) -> str:
        """
        Generate complete Alembic migration downgrade function

        Args:
            tables: List of table names
            read_only_tables: List of tables with read-only policies

        Returns:
            Complete downgrade migration code

        Example:
            migration = RLSPolicyGenerator.generate_migration_down(
                tables=["users", "posts"],
                read_only_tables=["audit_logs"]
            )
        """
        read_only_tables = read_only_tables or []

        migration_code = ['def downgrade() -> None:']

        for table in tables:
            is_read_only = table in read_only_tables

            # Drop policies
            if is_read_only:
                migration_code.append(
                    f'    op.execute("{RLSPolicyGenerator.drop_policy(table, "tenant_read_policy")}")'
                )
                migration_code.append(
                    f'    op.execute("{RLSPolicyGenerator.drop_policy(table, "tenant_insert_policy")}")'
                )
            else:
                migration_code.append(
                    f'    op.execute("{RLSPolicyGenerator.drop_policy(table, "tenant_isolation_policy")}")'
                )

            # Disable RLS
            migration_code.append(f'    op.execute("{RLSPolicyGenerator.disable_rls(table)}")')
            migration_code.append('')  # Blank line

        return '\n'.join(migration_code)
