"""Add name to users.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the required user name column."""
    op.add_column('users', sa.Column('name', sa.String(length=255), nullable=False, server_default='Unknown'))
    op.alter_column('users', 'name', server_default=None)


def downgrade() -> None:
    """Remove the user name column."""
    op.drop_column('users', 'name')
