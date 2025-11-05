from datetime import datetime
from sqlalchemy import (Column, Integer, String, DateTime, Text, UniqueConstraint, JSON, ForeignKey, Boolean)
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql
from enum import Enum

# --- Modelos SQLAlchemy ORM para o Banco de Dados ---

Base = declarative_base()

# Schema definitions
ai_schema = 'ai'
crm_schema = 'crm'

# Definição dos Enums Python
class PyIngestionStatus(Enum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class PyConsentType(Enum):
    LGPD_V1 = 'LGPD_V1'
    TERMS_OF_SERVICE = 'TERMS_OF_SERVICE'

class PyTicketStatus(Enum):
    OPEN = 'OPEN'
    IN_PROGRESS = 'IN_PROGRESS'
    RESOLVED = 'RESOLVED'
    CLOSED = 'CLOSED'

# Definição dos Enums PG Nativos
pg_ingestion_status = postgresql.ENUM(PyIngestionStatus, name='ingestionstatus', schema=ai_schema)
pg_consent_type = postgresql.ENUM(PyConsentType, name='consenttype', schema=crm_schema)
pg_ticket_status = postgresql.ENUM(PyTicketStatus, name='ticketstatus', schema=crm_schema)

class IngestionQueue(Base):
    __tablename__ = 'ingestion_queue'
    __table_args__ = {'schema': ai_schema}

    id = Column(Integer, primary_key=True)
    source_uri = Column(String, nullable=False)
    namespace = Column(String, nullable=False, default='default')
    status = Column(pg_ingestion_status, nullable=False, default=PyIngestionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processing_log = Column(Text)

class RagDocuments1536(Base):  # Renamed to match table name exactly
    __tablename__ = 'rag_documents_1536'
    __table_args__ = (UniqueConstraint('namespace', 'content_sha256', name='uq_namespace_content_hash'), {'schema': ai_schema})

    id = Column(Integer, primary_key=True)
    namespace = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_sha256 = Column(String(64), nullable=False, index=True)
    embedding = Column(Vector(1536))  # Tamanho para text-embedding-3-small
    document_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Clients(Base):
    __tablename__ = 'clients'
    __table_args__ = {'schema': crm_schema}

    id = Column(Integer, primary_key=True)
    whatsapp_id = Column(String, nullable=False, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consents = relationship("Consents", back_populates="client")
    tickets = relationship("Tickets", back_populates="client")

class Consents(Base):
    __tablename__ = 'consents'
    __table_args__ = {'schema': crm_schema}

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('crm.clients.id'), nullable=False)
    consent_type = Column(pg_consent_type, nullable=False, default=PyConsentType.LGPD_V1)
    is_given = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    client = relationship("Clients", back_populates="consents")

class Tickets(Base):
    __tablename__ = 'tickets'
    __table_args__ = {'schema': crm_schema}

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('crm.clients.id'), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(pg_ticket_status, nullable=False, default=PyTicketStatus.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Clients", back_populates="tickets")
