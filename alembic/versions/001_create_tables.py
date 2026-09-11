
"""create initial tables: users, projects, tasks
 
Revision ID: 001
Revises:
Create Date: 2026-09-08
 
This is the initial schema migration. It was missing from the shipped
repository -- alembic/versions/ contained only an incremental migration
(now 002) that ALTERs users/projects/tasks and assumes they already
exist. On a fresh database `alembic upgrade head` failed immediately
because there was nothing to create those tables in the first place.
 
FK constraints are given explicit, stable names here (fk_<table>_<col>_<ref>)
rather than left to dialect auto-naming, because 002 depends on being able
to address (drop/recreate) these exact constraints by name on SQLite, where
unnamed FKs aren't reliably reflectable.
"""
from alembic import op
import sqlalchemy as sa
 
revision = '001'
down_revision = None
branch_labels = None
depends_on = None
 
 
def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column(
            'role',
            sa.Enum('user', 'manager', 'admin', name='userrole'),
            nullable=False,
            server_default='user',
        ),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
 
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['owner_id'], ['users.id'],
            name='fk_projects_owner_id_users', ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_projects_id', 'projects', ['id'], unique=False)
 
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('todo', 'in_progress', 'done', name='taskstatus'),
            nullable=False,
            server_default='todo',
        ),
        sa.Column(
            'priority',
            sa.Enum('low', 'medium', 'high', name='taskpriority'),
            nullable=False,
            server_default='medium',
        ),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['project_id'], ['projects.id'],
            name='fk_tasks_project_id_projects', ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['assigned_to'], ['users.id'],
            name='fk_tasks_assigned_to_users',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tasks_id', 'tasks', ['id'], unique=False)
 
 
def downgrade() -> None:
    op.drop_index('ix_tasks_id', table_name='tasks')
    op.drop_table('tasks')
    op.drop_index('ix_projects_id', table_name='projects')
    op.drop_table('projects')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='taskstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='taskpriority').drop(op.get_bind(), checkfirst=True)
