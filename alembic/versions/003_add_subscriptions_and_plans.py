"""Add plan_tier to users and create subscriptions and payment_transactions tables

Revision ID: 003_add_subscriptions_and_plans
Revises: 002_add_is_authenticated
Create Date: 2026-09-01 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_subscriptions_and_plans'
down_revision: Union[str, None] = '002_add_is_authenticated'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    # 1. Add plan_tier to users
    if 'users' in existing_tables:
        cols = [c['name'] for c in insp.get_columns('users')]
        if 'plan_tier' not in cols:
            try:
                op.add_column('users', sa.Column('plan_tier', sa.String(), nullable=True, server_default='free'))
            except Exception:
                pass

    # 2. Create subscriptions table if not present
    if 'subscriptions' not in existing_tables:
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('plan_id', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='active'),
            sa.Column('gateway', sa.String(), nullable=False),
            sa.Column('customer_id', sa.String(), nullable=True),
            sa.Column('subscription_id', sa.String(), nullable=True),
            sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
            sa.Column('cancel_at_period_end', sa.Boolean(), default=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
        op.create_index('ix_subscriptions_subscription_id', 'subscriptions', ['subscription_id'])

    # 3. Create payment_transactions table if not present
    if 'payment_transactions' not in existing_tables:
        op.create_table(
            'payment_transactions',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('gateway', sa.String(), nullable=False),
            sa.Column('transaction_id', sa.String(), nullable=True),
            sa.Column('amount_cents', sa.Integer(), nullable=False),
            sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
            sa.Column('status', sa.String(), nullable=False, server_default='succeeded'),
            sa.Column('plan_id', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_payment_transactions_user_id', 'payment_transactions', ['user_id'])
        op.create_index('ix_payment_transactions_transaction_id', 'payment_transactions', ['transaction_id'])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    if 'payment_transactions' in existing_tables:
        try:
            op.drop_index('ix_payment_transactions_transaction_id', table_name='payment_transactions')
            op.drop_index('ix_payment_transactions_user_id', table_name='payment_transactions')
        except Exception:
            pass
        op.drop_table('payment_transactions')

    if 'subscriptions' in existing_tables:
        try:
            op.drop_index('ix_subscriptions_subscription_id', table_name='subscriptions')
            op.drop_index('ix_subscriptions_user_id', table_name='subscriptions')
        except Exception:
            pass
        op.drop_table('subscriptions')

    if 'users' in existing_tables:
        try:
            op.drop_column('users', 'plan_tier')
        except Exception:
            pass
