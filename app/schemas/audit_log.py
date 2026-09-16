from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: Optional[int]
    actor_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[int]
    detail: Optional[str]
    created_at: datetime
