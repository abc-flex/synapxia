"""Baseline migration: document current schema from db/sql/ DDL files.

Revision ID: 0001
Revises:
Create Date: 2026-06-08

This is the baseline migration representing the schema created by the
append-only db/sql/NN-*.sql DDL files. It does not create tables (they
already exist from Docker entrypoint initialization), but instead serves
as a reference point for future Alembic-based mutations.

When starting with an existing database schema (cold start from db/sql/),
run: alembic stamp head
to mark the current state as migrated.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Baseline schema: no-op (schema created by db/sql/ DDL files)."""
    pass


def downgrade() -> None:
    """Cannot downgrade baseline."""
    raise RuntimeError(
        "Cannot downgrade the baseline migration. "
        "The baseline represents the schema created by db/sql/ files; "
        "downgrading is not supported."
    )
