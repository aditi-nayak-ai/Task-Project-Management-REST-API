import json
from typing import Optional
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def record_audit(
    db: Session,
    actor: Optional[User],
    action: str,
    resource_type: str,
    resource_id: Optional[int],
    detail: Optional[dict] = None,
) -> None:
    """
    Stages an audit row via db.add() -- does NOT call db.commit(). Every
    caller must be inside a request handler that commits the mutation
    and this row together in one transaction, so a rollback (e.g. the
    version-conflict path in optimistic concurrency) discards the log
    entry along with the change, and nothing gets logged that didn't
    actually happen.
    """
    db.add(AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=json.dumps(detail, default=str) if detail is not None else None,
    ))
