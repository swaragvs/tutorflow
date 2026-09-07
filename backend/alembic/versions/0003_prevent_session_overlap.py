"""Prevent overlapping session ranges for the same tutor."""

from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "sessions_no_tutor_time_overlap"


def upgrade() -> None:
    """Add a PostgreSQL exclusion constraint for tutor session ranges."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        f"""
        ALTER TABLE sessions
        ADD CONSTRAINT {CONSTRAINT_NAME}
        EXCLUDE USING gist (
            tutor_id WITH =,
            tsrange(start_time, end_time, '[)') WITH &&
        )
        """
    )


def downgrade() -> None:
    """Remove the tutor session range exclusion constraint."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(CONSTRAINT_NAME, "sessions", type_="exclude")