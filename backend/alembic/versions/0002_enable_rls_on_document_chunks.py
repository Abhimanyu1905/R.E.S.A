"""Enable Row-Level Security on document_chunks and create non-owner app role.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31

Enables Row-Level Security (RLS) on document_chunks and creates a policy
that restricts chunk visibility based on the session variable app.user_level.
Also forces RLS on table owners and creates the non-owner role 'resa_app'.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Non-owner app role for RLS enforcement ──────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'resa_app') THEN
                CREATE ROLE resa_app WITH LOGIN PASSWORD 'resa_app_pass';
            ELSE
                ALTER ROLE resa_app WITH LOGIN PASSWORD 'resa_app_pass';
            END IF;
        END $$;
    """)
    op.execute("GRANT USAGE ON SCHEMA public TO resa_app")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO resa_app"
    )
    op.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO resa_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO resa_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO resa_app"
    )

    # ── Enable & Force Row-Level Security on document_chunks ─────────────────
    op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_chunks FORCE ROW LEVEL SECURITY")

    # ── Policy: compare app.user_level to min_role_level ────────────────────
    op.execute("DROP POLICY IF EXISTS rbac_chunk_policy ON document_chunks")
    op.execute("""
        CREATE POLICY rbac_chunk_policy ON document_chunks
        FOR SELECT
        USING (current_setting('app.user_level', true)::int >= min_role_level)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rbac_chunk_policy ON document_chunks")
    op.execute("ALTER TABLE document_chunks NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_chunks DISABLE ROW LEVEL SECURITY")

    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM resa_app")
    op.execute("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM resa_app")
    op.execute("REVOKE ALL PRIVILEGES ON SCHEMA public FROM resa_app")
    op.execute("DROP OWNED BY resa_app")
    op.execute("DROP ROLE IF EXISTS resa_app")
