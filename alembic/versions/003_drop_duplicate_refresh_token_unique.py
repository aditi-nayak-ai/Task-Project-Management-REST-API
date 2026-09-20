"""drop duplicate unique constraint on refresh_tokens.token_hash
 
Revision ID: 003
Revises: 002
Create Date: 2026-09-20
 
Migration 002 created token_hash with BOTH a UniqueConstraint and a unique
index (ix_refresh_tokens_token_hash). The model declares only the unique
index, so `alembic check` reported the constraint as drift. The index already
enforces uniqueness and serves lookups, so the constraint is redundant.
"""
from alembic import op
 
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None
 
 
def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint('refresh_tokens_token_hash_key', 'refresh_tokens', type_='unique')
 
 
def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.create_unique_constraint('refresh_tokens_token_hash_key', 'refresh_tokens', ['token_hash'])
