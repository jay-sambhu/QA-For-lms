"""Initial schema for users and scans

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), server_default='student', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. Create scans table
    op.create_table(
        'scans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('report_path', sa.Text(), nullable=True),
        sa.Column('json_path', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scans_user_id', 'scans', ['user_id'], unique=False)
    op.create_index('ix_scans_status', 'scans', ['status'], unique=False)
    op.create_index('ix_scans_created_at', 'scans', ['created_at'], unique=False)
    op.create_index('ix_scans_user_created', 'scans', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_scans_user_created', table_name='scans')
    op.drop_index('ix_scans_created_at', table_name='scans')
    op.drop_index('ix_scans_status', table_name='scans')
    op.drop_index('ix_scans_user_id', table_name='scans')
    op.drop_table('scans')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
