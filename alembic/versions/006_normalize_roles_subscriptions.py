"""Normalise users/subscriptions, add scan_secrets and webhook idempotency

- users.role: 'student'/'instructor' rows become 'user'; server default 'user'
- users.plan_tier: NOT NULL DEFAULT 'free'
- user_api_keys.is_default: NOT NULL DEFAULT false
- subscriptions: one row per (gateway, subscription_id) (duplicates from the
  insert-always webhook are collapsed onto the newest row) + unique index
- payment_transactions.event_id (unique): gateway deliveries are processed once
- scan_secrets: encrypted one-off launch credentials read by the worker
- blog_posts.slug index made unique (as the model declares)

Revision ID: 006_normalize_roles_subscriptions
Revises: 005_add_trial_scans
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_normalize_roles_subscriptions'
down_revision: Union[str, None] = '005_add_trial_scans'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(insp, table: str) -> dict:
    return {c['name']: c for c in insp.get_columns(table)}


def _index_names(insp, table: str) -> set:
    try:
        return {i['name'] for i in insp.get_indexes(table)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'users' in tables:
        op.execute(sa.text("UPDATE users SET role = 'user' WHERE role IN ('student', 'instructor') OR role IS NULL"))
        op.execute(sa.text("UPDATE users SET plan_tier = 'free' WHERE plan_tier IS NULL OR plan_tier = ''"))
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('role', existing_type=sa.String(), server_default='user', nullable=False)
            if 'plan_tier' in _cols(insp, 'users'):
                batch_op.alter_column('plan_tier', existing_type=sa.String(), server_default='free', nullable=False)

    if 'user_api_keys' in tables:
        op.execute(sa.text("UPDATE user_api_keys SET is_default = 0 WHERE is_default IS NULL")
                   if bind.dialect.name == 'sqlite'
                   else sa.text("UPDATE user_api_keys SET is_default = false WHERE is_default IS NULL"))
        with op.batch_alter_table('user_api_keys') as batch_op:
            batch_op.alter_column('is_default', existing_type=sa.Boolean(), server_default=sa.text('false'), nullable=False)

    if 'subscriptions' in tables:
        # Collapse duplicates: keep the newest row per (gateway, subscription_id)
        op.execute(sa.text(
            "DELETE FROM subscriptions WHERE subscription_id IS NOT NULL AND id NOT IN ("
            " SELECT keep_id FROM ("
            "  SELECT (SELECT s2.id FROM subscriptions s2 WHERE s2.gateway = s1.gateway"
            "          AND s2.subscription_id = s1.subscription_id"
            "          ORDER BY s2.created_at DESC, s2.id DESC LIMIT 1) AS keep_id"
            "  FROM subscriptions s1 WHERE s1.subscription_id IS NOT NULL"
            "  GROUP BY s1.gateway, s1.subscription_id) k)"
        ))
        if 'ix_subscriptions_gateway_sub' not in _index_names(insp, 'subscriptions'):
            op.create_index('ix_subscriptions_gateway_sub', 'subscriptions', ['gateway', 'subscription_id'], unique=True)

    if 'payment_transactions' in tables:
        if 'event_id' not in _cols(insp, 'payment_transactions'):
            with op.batch_alter_table('payment_transactions') as batch_op:
                batch_op.add_column(sa.Column('event_id', sa.String(), nullable=True))
        if 'ix_payment_transactions_event_id' not in _index_names(insp, 'payment_transactions'):
            op.create_index('ix_payment_transactions_event_id', 'payment_transactions', ['event_id'], unique=True)

    if 'blog_posts' in tables:
        # 004 created a non-unique slug index while the model declares a unique one
        slug_idx = next((i for i in insp.get_indexes('blog_posts') if i['name'] == 'ix_blog_posts_slug'), None)
        if slug_idx is not None and not slug_idx.get('unique'):
            op.drop_index('ix_blog_posts_slug', table_name='blog_posts')
            slug_idx = None
        if slug_idx is None:
            op.create_index('ix_blog_posts_slug', 'blog_posts', ['slug'], unique=True)

    if 'scan_secrets' not in tables:
        op.create_table(
            'scan_secrets',
            sa.Column('scan_id', sa.String(), sa.ForeignKey('scans.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('payload', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'scan_secrets' in tables:
        op.drop_table('scan_secrets')

    if 'payment_transactions' in tables:
        if 'ix_payment_transactions_event_id' in _index_names(insp, 'payment_transactions'):
            op.drop_index('ix_payment_transactions_event_id', table_name='payment_transactions')
        if 'event_id' in _cols(insp, 'payment_transactions'):
            with op.batch_alter_table('payment_transactions') as batch_op:
                batch_op.drop_column('event_id')

    if 'subscriptions' in tables and 'ix_subscriptions_gateway_sub' in _index_names(insp, 'subscriptions'):
        op.drop_index('ix_subscriptions_gateway_sub', table_name='subscriptions')

    if 'user_api_keys' in tables:
        with op.batch_alter_table('user_api_keys') as batch_op:
            batch_op.alter_column('is_default', existing_type=sa.Boolean(), server_default=None, nullable=True)

    if 'users' in tables:
        with op.batch_alter_table('users') as batch_op:
            if 'plan_tier' in _cols(insp, 'users'):
                batch_op.alter_column('plan_tier', existing_type=sa.String(), server_default='free', nullable=True)
