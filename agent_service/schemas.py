from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from core.models import PyTicketStatus


class RetrievalRequest(BaseModel):
    query: str
    namespace: Optional[str] = None


class RetrievalChunk(BaseModel):
    content: str
    source_uri: str
    distance: float


class RetrievalResponse(BaseModel):
    chunks: List[RetrievalChunk]


class ClientBase(BaseModel):
    whatsapp_id: str
    name: Optional[str] = None


class ClientResponse(BaseModel):
    id: int
    whatsapp_id: str
    name: Optional[str]


class ConsentRequest(BaseModel):
    client_id: int
    consent_type: str
    is_given: bool


class ConsentResponse(BaseModel):
    id: int
    client_id: int
    consent_type: str
    is_given: bool
    timestamp: datetime


class TicketBase(BaseModel):
    client_id: int
    description: str
    status: PyTicketStatus


class TicketResponse(BaseModel):
    id: int
    client_id: int
    description: str
    status: PyTicketStatus
    created_at: datetime


class EvoApiMessageBody(BaseModel):
    text: str


class EvoApiMessage(BaseModel):
    body: EvoApiMessageBody


class EvoApiSender(BaseModel):
    id: str


class EvoApiPayload(BaseModel):
    sender: EvoApiSender
    message: EvoApiMessage