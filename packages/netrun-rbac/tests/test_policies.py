"""
Tests for PostgreSQL RLS Policy Generator

Tests SQL generation for Row-Level Security policies
"""

import pytest

from netrun.rbac.policies import RLSPolicyGenerator


class TestRLSPolicyGenerator:
    """Test RLS policy SQL generation"""

    def test_enable_rls(self):
        """Test ENABLE RLS statement"""
        sql = RLSPolicyGenerator.enable_rls("users")
        assert sql == "ALTER TABLE users ENABLE ROW LEVEL SECURITY;"

    def test_disable_rls(self):
        """Test DISABLE RLS statement"""
        sql = RLSPolicyGenerator.disable_rls("users")
        assert sql == "ALTER TABLE users DISABLE ROW LEVEL SECURITY;"

    def test_create_tenant_isolation_policy_default(self):
        """Test tenant isolation policy with default parameters"""
        sql = RLSPolicyGenerator.create_tenant_isolation_policy("users")

        # Should contain key components
        assert "CREATE POLICY tenant_isolation_policy ON users" in sql
        assert "FOR ALL" in sql
        assert "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)" in sql

    def test_create_tenant_isolation_policy_custom(self):
        """Test tenant isolation policy with custom parameters"""
        sql = RLSPolicyGenerator.create_tenant_isolation_policy(
            table_name="organizations",
            tenant_column="org_id",
            session_variable="app.current_org_id",
            policy_name="org_isolation_policy",
        )

        assert "CREATE POLICY org_isolation_policy ON organizations" in sql
        assert "FOR ALL" in sql
        assert "org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID" in sql

    def test_create_read_only_policy(self):
        """Test read-only policy generation"""
        sql = RLSPolicyGenerator.create_read_only_policy("audit_logs")

        assert "CREATE POLICY tenant_read_policy ON audit_logs" in sql
        assert "FOR SELECT" in sql
        assert "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)" in sql

    def test_create_insert_only_policy(self):
        """Test insert-only policy generation"""
        sql = RLSPolicyGenerator.create_insert_only_policy("audit_logs")

        assert "CREATE POLICY tenant_insert_policy ON audit_logs" in sql
        assert "FOR INSERT" in sql
        assert "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)" in sql

    def test_drop_policy(self):
        """Test DROP POLICY statement"""
        sql = RLSPolicyGenerator.drop_policy("users", "tenant_isolation_policy")
        assert sql == "DROP POLICY IF EXISTS tenant_isolation_policy ON users;"

    def test_generate_rls_for_table_normal(self):
        """Test complete RLS setup for normal table"""
        statements = RLSPolicyGenerator.generate_rls_for_table("users")

        # Should have 2 statements: ENABLE RLS + CREATE POLICY
        assert len(statements) == 2

        # First: Enable RLS
        assert "ALTER TABLE users ENABLE ROW LEVEL SECURITY" in statements[0]

        # Second: Create tenant isolation policy
        assert "CREATE POLICY tenant_isolation_policy ON users" in statements[1]
        assert "FOR ALL" in statements[1]

    def test_generate_rls_for_table_read_only(self):
        """Test complete RLS setup for read-only table"""
        statements = RLSPolicyGenerator.generate_rls_for_table("audit_logs", read_only=True)

        # Should have 3 statements: ENABLE RLS + READ POLICY + INSERT POLICY
        assert len(statements) == 3

        # First: Enable RLS
        assert "ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY" in statements[0]

        # Second: Create read policy
        assert "CREATE POLICY tenant_read_policy ON audit_logs" in statements[1]
        assert "FOR SELECT" in statements[1]

        # Third: Create insert policy
        assert "CREATE POLICY tenant_insert_policy ON audit_logs" in statements[2]
        assert "FOR INSERT" in statements[2]

    def test_generate_migration_up(self):
        """Test migration upgrade code generation"""
        migration = RLSPolicyGenerator.generate_migration_up(
            tables=["users", "posts"],
            read_only_tables=["audit_logs"]
        )

        # Should contain function definition
        assert "def upgrade() -> None:" in migration

        # Should contain ENABLE RLS for users
        assert "ALTER TABLE users ENABLE ROW LEVEL SECURITY" in migration

        # Should contain policy creation
        assert "CREATE POLICY tenant_isolation_policy ON users" in migration

        # Should contain op.execute calls
        assert "op.execute" in migration

    def test_generate_migration_down(self):
        """Test migration downgrade code generation"""
        migration = RLSPolicyGenerator.generate_migration_down(
            tables=["users", "posts"],
            read_only_tables=["audit_logs"]
        )

        # Should contain function definition
        assert "def downgrade() -> None:" in migration

        # Should contain DROP POLICY
        assert "DROP POLICY IF EXISTS" in migration

        # Should contain DISABLE RLS
        assert "DISABLE ROW LEVEL SECURITY" in migration

    def test_migration_preserves_table_order(self):
        """Test that migration generation preserves table order"""
        tables = ["users", "posts", "comments", "social_accounts"]
        migration = RLSPolicyGenerator.generate_migration_up(tables)

        # Find positions of each table in migration
        pos_users = migration.find("users")
        pos_posts = migration.find("posts")
        pos_comments = migration.find("comments")
        pos_social = migration.find("social_accounts")

        # Verify order is preserved
        assert pos_users < pos_posts < pos_comments < pos_social
