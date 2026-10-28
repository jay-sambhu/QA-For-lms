"""Make user_api_keys the single source of truth and encrypt secrets at rest

1. Backfill: a user whose only key lives in the legacy users.gemini_api_key
   column gets a default gemini row in user_api_keys.
2. Encrypt user_api_keys.api_key and api_keys.key_value in place when
   API_KEY_ENCRYPTION_KEY is configured (rows already prefixed are skipped;
   without a key the rows stay as they are and the app encrypts lazily at
   startup once a key exists).
3. Drop users.gemini_api_key.

Revision ID: 007_encrypt_keys_drop_legacy_gemini
Revises: 006_normalize_roles_subscriptions
Create Date: 2026-10-16 00:10:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '007_encrypt_keys_drop_legacy_gemini'
down_revision: Union[str, None] = '006_normalize_roles_subscriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(insp, table: str) -> set:
    return {c['name'] for c in insp.get_columns(table)}


def _encrypt(value):
    try:
        from api.secrets import encrypt_secret
        return encrypt_secret(value)
    except Exception:
        return value


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if 'users' in tables and 'gemini_api_key' in _cols(insp, 'users') and 'user_api_keys' in tables:
        rows = bind.execute(sa.text(
            "SELECT u.id, u.gemini_api_key FROM users u"
            " WHERE u.gemini_api_key IS NOT NULL AND TRIM(u.gemini_api_key) <> ''"
            " AND NOT EXISTS (SELECT 1 FROM user_api_keys k WHERE k.user_id = u.id)"
        )).fetchall()
        for user_id, legacy_key in rows:
            bind.execute(
                sa.text(
                    "INSERT INTO user_api_keys (id, user_id, provider_id, key_name, api_key, model, is_default, created_at)"
                    " VALUES (:id, :user_id, 'gemini', 'Google Gemini Studio', :api_key, :model, :is_default, CURRENT_TIMESTAMP)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "api_key": _encrypt(legacy_key.strip()),
                    "model": "gemini-3.8-flash",
                    "is_default": True,
                },
            )

    for table, column, pk in (('user_api_keys', 'api_key', 'id'), ('api_keys', 'key_value', 'id')):
        if table in tables:
            rows = bind.execute(sa.text(
                f"SELECT {pk}, {column} FROM {table} WHERE {column} IS NOT NULL AND {column} NOT LIKE 'enc:%'"
            )).fetchall()
            for row_id, plain in rows:
                if not plain:
                    continue
                encrypted = _encrypt(plain)
                if encrypted != plain:
                    bind.execute(
                        sa.text(f"UPDATE {table} SET {column} = :value WHERE {pk} = :id"),
                        {"value": encrypted, "id": row_id},
                    )

    if 'users' in tables and 'gemini_api_key' in _cols(insp, 'users'):
        with op.batch_alter_table('users') as batch_op:
            batch_op.drop_column('gemini_api_key')


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'users' in insp.get_table_names() and 'gemini_api_key' not in _cols(insp, 'users'):
        with op.batch_alter_table('users') as batch_op:
            batch_op.add_column(sa.Column('gemini_api_key', sa.String(), nullable=True))
