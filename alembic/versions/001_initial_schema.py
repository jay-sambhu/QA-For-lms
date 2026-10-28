"""Initial schema for users and scans

Idempotent: a database bootstrapped with ``Base.metadata.create_all`` (local
sqlite) already has these tables, and ``alembic upgrade head`` must not fail
with "relation already exists" on it.

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


def _index_names(insp, table: str) -> set:
    try:
        return {i["name"] for i in insp.get_indexes(table)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('role', sa.String(), server_default='user', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_users_email', 'users', ['email'], unique=True)
    elif 'ix_users_email' not in _index_names(insp, 'users'):
        op.create_index('ix_users_email', 'users', ['email'], unique=True)

    if 'scans' not in existing_tables:
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
        existing_idx = set()
    else:
        existing_idx = _index_names(insp, 'scans')
    for name, cols in (
        ('ix_scans_user_id', ['user_id']),
        ('ix_scans_status', ['status']),
        ('ix_scans_created_at', ['created_at']),
        ('ix_scans_user_created', ['user_id', 'created_at']),
    ):
        if name not in existing_idx:
            op.create_index(name, 'scans', cols, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    if 'payment_transactions' in existing_tables:
        op.drop_table('payment_transactions')
    if 'subscriptions' in existing_tables:
        op.drop_table('subscriptions')
    if 'scans' in existing_tables:
        for name in ('ix_scans_user_created', 'ix_scans_created_at', 'ix_scans_status', 'ix_scans_user_id'):
            try:
                op.drop_index(name, table_name='scans')
            except Exception:
                pass
        op.drop_table('scans')
    if 'users' in existing_tables:
        try:
            op.drop_index('ix_users_email', table_name='users')
        except Exception:
            pass
        op.drop_table('users')
