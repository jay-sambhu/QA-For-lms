"""Add the trial_scans table

Records which scans ran on the server's Gemini key as a user's free trial
scans, so the per-user allowance (TRIAL_FREE_SCANS) and the global daily cap
(TRIAL_DAILY_LIMIT) can be enforced.

Revision ID: 005_add_trial_scans
Revises: 004_add_api_keys_and_blogs
Create Date: 2026-10-15 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_add_trial_scans'
down_revision: Union[str, None] = '004_add_api_keys_and_blogs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    if 'trial_scans' not in existing_tables:
        op.create_table(
            'trial_scans',
            sa.Column('scan_id', sa.String(), sa.ForeignKey('scans.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_trial_scans_user_id', 'trial_scans', ['user_id'])
        op.create_index('ix_trial_scans_created_at', 'trial_scans', ['created_at'])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if 'trial_scans' in insp.get_table_names():
        op.drop_table('trial_scans')
