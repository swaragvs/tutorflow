"""Initial schema creation with User, StudentProfile, and Session tables.

Revision ID: 0001
Revises: 
Create Date: 2026-09-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create enums explicitly with checkfirst to avoid duplicate creation errors
    role_enum = postgresql.ENUM('TUTOR', 'STUDENT', name='role_enum')
    session_status_enum = postgresql.ENUM(
        'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'AI_REVIEWED',
        name='session_status_enum'
    )
    role_enum.create(op.get_bind(), checkfirst=True)
    session_status_enum.create(op.get_bind(), checkfirst=True)

    # Create users table
    # Use create_type=False since we already created the enum above
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', postgresql.ENUM('TUTOR', 'STUDENT', name='role_enum', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Create student_profiles table
    op.create_table(
        'student_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tutor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('learning_goals', sa.Text(), nullable=True),
        sa.Column('skill_level', sa.Text(), nullable=True),
        sa.Column('preferences', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['tutor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # Create sessions table
    # Use create_type=False since we already created the enum above
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tutor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('status', postgresql.ENUM('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'AI_REVIEWED', name='session_status_enum', create_type=False), nullable=False, server_default='SCHEDULED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('homework', sa.Text(), nullable=True),
        sa.Column('ai_plan', sa.Text(), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tutor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create composite index for overlap checking
    op.create_index('ix_sessions_tutor_start', 'sessions', ['tutor_id', 'start_time'])


def downgrade() -> None:
    """Drop initial database schema."""
    
    # Drop indexes
    op.drop_index('ix_sessions_tutor_start', table_name='sessions')
    
    # Drop tables (in reverse order of creation)
    op.drop_table('sessions')
    op.drop_table('student_profiles')
    op.drop_table('users')
    
    # Drop enums
    sa.Enum('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'AI_REVIEWED', name='session_status_enum').drop(op.get_bind())
    sa.Enum('TUTOR', 'STUDENT', name='role_enum').drop(op.get_bind())
