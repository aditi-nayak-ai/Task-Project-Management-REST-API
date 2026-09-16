from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from datetime import datetime, timezone
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class ProjectManager(Base):
    """
    Many-to-many link between managers and the projects they're allowed
    to act on. `require_role("manager")` alone can only express "this
    user holds the manager role" -- it can't express "manager *of which
    project*". Without this table, any manager could create/update/
    delete tasks on any project, which is the resource-level RBAC gap
    this closes.

    Admins are NOT expected to have rows here -- admin bypass is checked
    in code (role == admin), not modeled as implicit membership in every
    project, so this table only ever needs to grow with actual manager
    assignments.
    """
    __tablename__ = "project_managers"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_managers_project_user"),
    )
