from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ProjectManagerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    created_at: datetime
