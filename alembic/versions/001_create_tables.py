"""add missing indexes, fix owner_id/assigned_to FK behavior, add refresh_tokens
 
Revision ID: 002
Revises: 001
Create Date: 2026-09-08
 
"""
from alembic import op
import sqlalchemy as sa
 
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None
 
 
def _fk_name(table: str, column: str) -> str:
    """Look up the actual FK constraint name for `column` on `table`.
 
    Constraint names are NOT guaranteed to match a fixed convention across
    dialects (Postgres auto-names unnamed table-level FKs as
    "<table>_<col>_fkey", but SQLite does not reliably preserve/report a
    name for FKs that weren't given one at CREATE TABLE time). Reflecting
    the real name here means this migration works against whatever the
    original 001 migration actually produced on the DB it's running
    against, instead of guessing.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table):
        if fk.get("constrained_columns") == [column]:
            name = fk.get("name")
            if name:
                return name
    raise RuntimeError(f"Could not find a named FK constraint for {table}.{column}")
 
 
def upgrade() -> None:
    # --- Missing indexes (previously only PKs and users.email were indexed) ---
    op.create_index('ix_projects_owner_id', 'projects', ['owner_id'], unique=False)
    op.create_index('ix_tasks_project_id', 'tasks', ['project_id'], unique=False)
    op.create_index('ix_tasks_assigned_to', 'tasks', ['assigned_to'], unique=False)
    op.create_index('ix_tasks_status', 'tasks', ['status'], unique=False)
    op.create_index('ix_tasks_priority', 'tasks', ['priority'], unique=False)
    op.create_index('ix_users_role', 'users', ['role'], unique=False)
 
    # --- Fix dangerous/incorrect ON DELETE behavior on foreign keys ---
    # projects.owner_id: CASCADE -> RESTRICT. Deleting a user must not
    # silently wipe every project (and, transitively, every task) they own.
    #
    # tasks.assigned_to: no ON DELETE behavior -> SET NULL. A deleted/absent
    # assignee should unassign the task, not block user removal or error out.
    #
    # SQLite does not preserve a usable constraint name for FKs declared
    # without an explicit CONSTRAINT clause (which is how 001 declared
    # them) -- reflection reports name=None. Postgres does preserve one.
    # We branch on dialect: Postgres uses the real reflected name, SQLite
    # uses a naming_convention so batch mode can address (and recreate)
    # the table's unnamed constraints.
    bind = op.get_bind()
 
    if bind.dialect.name == "sqlite":
        naming_convention = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
        with op.batch_alter_table("projects", naming_convention=naming_convention) as batch_op:
            batch_op.drop_constraint("fk_projects_owner_id_users", type_="foreignkey")
            batch_op.create_foreign_key(
                "fk_projects_owner_id_users", "users", ["owner_id"], ["id"], ondelete="RESTRICT"
            )
        with op.batch_alter_table("tasks", naming_convention=naming_convention) as batch_op:
            batch_op.drop_constraint("fk_tasks_assigned_to_users", type_="foreignkey")
            batch_op.create_foreign_key(
                "fk_tasks_assigned_to_users", "users", ["assigned_to"], ["id"], ondelete="SET NULL"
            )
    else:
        owner_fk = _fk_name("projects", "owner_id")
        with op.batch_alter_table("projects") as batch_op:
            batch_op.drop_constraint(owner_fk, type_="foreignkey")
            batch_op.create_foreign_key(owner_fk, "users", ["owner_id"], ["id"], ondelete="RESTRICT")
 
        assigned_fk = _fk_name("tasks", "assigned_to")
        with op.batch_alter_table("tasks") as batch_op:
            batch_op.drop_constraint(assigned_fk, type_="foreignkey")
            batch_op.create_foreign_key(assigned_fk, "users", ["assigned_to"], ["id"], ondelete="SET NULL")
 
    # --- New table: hashed refresh tokens for revocable session refresh ---
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('ix_refresh_tokens_id', 'refresh_tokens', ['id'], unique=False)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)
 
 
def downgrade() -> None:
    op.drop_index('ix_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
 
    bind = op.get_bind()
 
    if bind.dialect.name == "sqlite":
        naming_convention = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
        with op.batch_alter_table("tasks", naming_convention=naming_convention) as batch_op:
            batch_op.drop_constraint("fk_tasks_assigned_to_users", type_="foreignkey")
            batch_op.create_foreign_key("fk_tasks_assigned_to_users", "users", ["assigned_to"], ["id"])
        with op.batch_alter_table("projects", naming_convention=naming_convention) as batch_op:
            batch_op.drop_constraint("fk_projects_owner_id_users", type_="foreignkey")
            batch_op.create_foreign_key(
                "fk_projects_owner_id_users", "users", ["owner_id"], ["id"], ondelete="CASCADE"
            )
    else:
        assigned_fk = _fk_name("tasks", "assigned_to")
        with op.batch_alter_table("tasks") as batch_op:
            batch_op.drop_constraint(assigned_fk, type_="foreignkey")
            batch_op.create_foreign_key(assigned_fk, "users", ["assigned_to"], ["id"])
 
        owner_fk = _fk_name("projects", "owner_id")
        with op.batch_alter_table("projects") as batch_op:
            batch_op.drop_constraint(owner_fk, type_="foreignkey")
            batch_op.create_foreign_key(owner_fk, "users", ["owner_id"], ["id"], ondelete="CASCADE")
 
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_tasks_priority', table_name='tasks')
    op.drop_index('ix_tasks_status', table_name='tasks')
    op.drop_index('ix_tasks_assigned_to', table_name='tasks')
    op.drop_index('ix_tasks_project_id', table_name='tasks')
    op.drop_index('ix_projects_owner_id', table_name='projects')
