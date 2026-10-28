"""Add is_authenticated column to scans table

Revision ID: 002_add_is_authenticated
Revises: 001_initial_schema
Create Date: 2026-09-01 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_is_authenticated'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'scans' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('scans')}
    if 'is_authenticated' not in cols:
        op.add_column('scans', sa.Column('is_authenticated', sa.Boolean(), nullable=True, server_default=sa.text('false')))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'scans' in insp.get_table_names() and 'is_authenticated' in {c['name'] for c in insp.get_columns('scans')}:
        with op.batch_alter_table('scans') as batch_op:
            batch_op.drop_column('is_authenticated')
