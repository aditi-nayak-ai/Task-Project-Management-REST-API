from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.utils.dependencies import require_role
from app.utils.pagination import get_pagination

router = APIRouter()


@router.get("/", response_model=list[AuditLogResponse])
def list_audit_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
    pagination: tuple = Depends(get_pagination),
    resource_type: Optional[str] = Query(None, description="Filter to one resource type, e.g. 'task', 'project', 'user'."),
    action: Optional[str] = Query(None, description="Filter to one action, e.g. 'task.delete'."),
):
    query = db.query(AuditLog)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if action:
        query = query.filter(AuditLog.action == action)

    offset, limit = pagination
    return query.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()
