from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    # Required, not optional: the client must send back the version it
    # last read so the server can detect a concurrent write. Omitting it
    # entirely is a 422, not "skip the check".
    version: int = Field(..., description="Version of the project last read by the client, for optimistic concurrency.")


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    owner_id: int
    version: int
    created_at: datetime
    updated_at: datetime
