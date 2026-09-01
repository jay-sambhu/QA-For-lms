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
    op.add_column('scans', sa.Column('is_authenticated', sa.Boolean(), nullable=True, server_default=sa.text('0')))


def downgrade() -> None:
    op.drop_column('scans', 'is_authenticated')
