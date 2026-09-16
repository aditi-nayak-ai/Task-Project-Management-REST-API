"""
One-off backfill for the resource-level RBAC change.

Why this exists: before this migration, `manager` was a global role --
any manager could act on any project. After it, a manager needs an
explicit ProjectManager row per project. Deploying with zero rows would
silently lock every *existing* manager out of every project they used
to be able to touch.

What it does: for every user with role=manager and every existing
project, ensures a ProjectManager row exists -- i.e. it reproduces the
old "global manager" behavior exactly, for existing managers only, as a
one-time snapshot at deploy time. It does NOT try to guess which
project a manager "really" worked on from task history, because the
data to know that doesn't exist (Task has no created_by column, only
assigned_to, which is the assignee -- not proof of who acted on it).

Any manager created *after* this runs starts with zero project access,
which is the new, intended behavior -- an admin must explicitly grant
it via POST /projects/{id}/managers/{user_id}.

Usage:
    python -m scripts.backfill_project_managers            # apply
    python -m scripts.backfill_project_managers --dry-run  # preview only

Run this once, after `alembic upgrade head` and before (or immediately
after) deploying the new RBAC-enforcing code -- not before the
project_managers table exists.
"""
import argparse

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.project_manager import ProjectManager
# Importing every model here -- not just the ones this script queries --
# so SQLAlchemy's mapper registry is fully configured before any query
# runs. Project.tasks is a relationship("Task", ...) declared by
# string name; if app.models.task was never imported in this process,
# resolving that string fails with "expression 'Task' failed to locate
# a name" the moment any Project row is touched. The app avoids this
# because app.main imports every router (and transitively every model)
# before serving a request; a standalone script has no such guarantee.
import app.models.task  # noqa: F401
import app.models.refresh_token  # noqa: F401
import app.models.audit_log  # noqa: F401


def backfill(dry_run: bool = False) -> int:
    db = SessionLocal()
    created = 0
    try:
        managers = db.query(User).filter(User.role == UserRole.manager).all()
        projects = db.query(Project).all()

        if not managers:
            print("No users with role=manager found. Nothing to do.")
            return 0
        if not projects:
            print("No projects found. Nothing to do.")
            return 0

        existing_pairs = {
            (pm.user_id, pm.project_id)
            for pm in db.query(ProjectManager).all()
        }

        for manager in managers:
            for project in projects:
                key = (manager.id, project.id)
                if key in existing_pairs:
                    continue
                created += 1
                print(f"{'[dry-run] would grant' if dry_run else 'Granting'}: "
                      f"manager {manager.email} (id={manager.id}) -> project {project.name!r} (id={project.id})")
                if not dry_run:
                    db.add(ProjectManager(user_id=manager.id, project_id=project.id))

        if not dry_run:
            db.commit()

        print(f"\n{'Would create' if dry_run else 'Created'} {created} project_managers row(s) "
              f"across {len(managers)} manager(s) and {len(projects)} project(s).")
        return created
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without writing to the DB.")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)
