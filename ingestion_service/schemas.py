from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class IngestionRequest(BaseModel):
    source_uri: str
    namespace: str = "default"


class IngestionResponse(BaseModel):
    id: int
    source_uri: str
    namespace: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None