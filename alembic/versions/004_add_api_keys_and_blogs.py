"""Add users.gemini_api_key and the user_api_keys, api_keys and blog_posts tables

models.py gained these but no migration did, so any database built with
`alembic upgrade head` lacked users.gemini_api_key and every User query failed
("no such column: users.gemini_api_key").

Revision ID: 004_add_api_keys_and_blogs
Revises: 003_add_subscriptions_and_plans
Create Date: 2026-10-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_add_api_keys_and_blogs'
down_revision: Union[str, None] = '003_add_subscriptions_and_plans'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    if 'users' in existing_tables:
        cols = [c['name'] for c in insp.get_columns('users')]
        if 'gemini_api_key' not in cols:
            op.add_column('users', sa.Column('gemini_api_key', sa.String(), nullable=True))

    if 'user_api_keys' not in existing_tables:
        op.create_table(
            'user_api_keys',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('provider_id', sa.String(), nullable=False, server_default='gemini'),
            sa.Column('key_name', sa.String(), nullable=True),
            sa.Column('api_key', sa.Text(), nullable=False),
            sa.Column('model', sa.String(), nullable=True),
            sa.Column('endpoint', sa.String(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_user_api_keys_user_id', 'user_api_keys', ['user_id'])

    if 'api_keys' not in existing_tables:
        op.create_table(
            'api_keys',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('key_value', sa.String(), nullable=False, unique=True),
            sa.Column('status', sa.String(), nullable=False, server_default='active'),
            sa.Column('service', sa.String(), nullable=False, server_default='gemini'),
            sa.Column('rate_limit_reset_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )

    if 'blog_posts' not in existing_tables:
        op.create_table(
            'blog_posts',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('slug', sa.String(), nullable=False, unique=True),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('excerpt', sa.Text(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('category', sa.String(), nullable=False, server_default='AI & Automation'),
            sa.Column('tags', sa.Text(), nullable=True, server_default=''),
            sa.Column('author_name', sa.String(), nullable=False, server_default='Nexus Core Engineering'),
            sa.Column('author_role', sa.String(), nullable=False, server_default='Platform Architecture Team'),
            sa.Column('author_avatar', sa.String(), nullable=False, server_default='/logo.png'),
            sa.Column('reading_time', sa.String(), nullable=False, server_default='5 min read'),
            sa.Column('status', sa.String(), nullable=False, server_default='published'),
            sa.Column('published_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_blog_posts_slug', 'blog_posts', ['slug'])
        op.create_index('ix_blog_posts_status', 'blog_posts', ['status'])
        op.create_index('ix_blog_posts_published_at', 'blog_posts', ['published_at'])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()

    for table in ('blog_posts', 'api_keys', 'user_api_keys'):
        if table in existing_tables:
            op.drop_table(table)

    if 'users' in existing_tables:
        cols = [c['name'] for c in insp.get_columns('users')]
        if 'gemini_api_key' in cols:
            with op.batch_alter_table('users') as batch_op:
                batch_op.drop_column('gemini_api_key')
