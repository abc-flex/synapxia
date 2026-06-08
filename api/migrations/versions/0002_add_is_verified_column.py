"""Add is_verified column to users table (fastapi-users requirement).

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08

This migration mirrors db/sql/13-admin-fastapi-users-ddl.sql and adds
the is_verified boolean column required by fastapi-users for email
verification workflows.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_verified column with default False."""
    op.add_column(
        'users',
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False)
    )


def downgrade() -> None:
    """Remove is_verified column."""
    op.drop_column('users', 'is_verified')
