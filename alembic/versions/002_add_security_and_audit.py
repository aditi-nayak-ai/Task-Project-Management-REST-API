"""create refresh_tokens, project_managers, audit_logs; add optimistic-concurrency version columns

Revision ID: 002
Revises: 001
Create Date: 2026-09-16

Two things bundled into one migration:

1. `refresh_tokens` was never migrated. The model and the code using it
   (app/models/refresh_token.py, app/api/auth.py) have existed since
   before this revision, but 001 only created users/projects/tasks.
   Tests never caught this because tests/conftest.py builds the schema
   directly via Base.metadata.create_all(), bypassing Alembic entirely.
   On a real `alembic upgrade head` deploy, /auth/login would fail the
   first time it tried to write a refresh token. This migration creates
   the table that should have shipped with the feature.

2. New tables/columns for resource-level RBAC, audit logging, and
   optimistic concurrency: `project_managers` (scopes a manager to
   specific projects), `audit_logs` (append-only change history), and
   a `version` column on `projects`/`tasks` (409-on-conflict for
   concurrent edits).
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- refresh_tokens (previously missing entirely) --
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name='fk_refresh_tokens_user_id_users', ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('ix_refresh_tokens_id', 'refresh_tokens', ['id'], unique=False)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)

    # -- project_managers --
    op.create_table(
        'project_managers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['project_id'], ['projects.id'],
            name='fk_project_managers_project_id_projects', ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name='fk_project_managers_user_id_users', ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_managers_project_user'),
    )
    op.create_index('ix_project_managers_id', 'project_managers', ['id'], unique=False)
    op.create_index('ix_project_managers_project_id', 'project_managers', ['project_id'], unique=False)
    op.create_index('ix_project_managers_user_id', 'project_managers', ['user_id'], unique=False)

    # -- audit_logs --
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_email', sa.String(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=30), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['actor_id'], ['users.id'],
            name='fk_audit_logs_actor_id_users', ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'], unique=False)
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)

    # -- optimistic concurrency columns --
    op.add_column('projects', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('tasks', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('tasks', 'version')
    op.drop_column('projects', 'version')

    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_actor_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_id', table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index('ix_project_managers_user_id', table_name='project_managers')
    op.drop_index('ix_project_managers_project_id', table_name='project_managers')
    op.drop_index('ix_project_managers_id', table_name='project_managers')
    op.drop_table('project_managers')

    op.drop_index('ix_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
