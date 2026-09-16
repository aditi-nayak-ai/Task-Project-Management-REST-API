from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime, timezone
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """
    Append-only record of who changed what. `actor_id` is nullable with
    ON DELETE SET NULL (not CASCADE) -- deleting a user account must
    never delete the history of what that account did. `actor_email` is
    denormalized (copied at write time) for the same reason: the log
    entry stays legible even after the user row is gone or the email
    changes.

    Rows are written in the same DB transaction as the mutation they
    describe (see app/core/audit.py), so a rollback undoes the log entry
    along with the change -- there's no path where a mutation commits
    without a corresponding audit row, or vice versa.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = Column(String, nullable=True)
    action = Column(String(50), nullable=False, index=True)          # e.g. "task.create", "project.delete"
    resource_type = Column(String(30), nullable=False, index=True)   # e.g. "task", "project", "user"
    resource_id = Column(Integer, nullable=True, index=True)
    detail = Column(Text, nullable=True)                             # JSON string of changed fields / context
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
