import enum
from datetime import datetime
from sqlalchemy import (Column, Integer, String, DateTime, Text, UniqueConstraint, JSON, Enum, ForeignKey, Boolean)
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

# --- Modelos SQLAlchemy ORM para o Banco de Dados ---

Base = declarative_base()

# Schema: ai

class IngestionStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class IngestionQueue(Base):
    __tablename__ = 'ingestion_queue'
    __table_args__ = {'schema': 'ai'}

    id = Column(Integer, primary_key=True)
    source_uri = Column(String, nullable=False)
    namespace = Column(String, nullable=False, default='default')
    status = Column(Enum(IngestionStatus, schema="ai", native_enum=False), nullable=False, default=IngestionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processing_log = Column(Text)

class RagDocuments(Base):
    __tablename__ = 'rag_documents_1536'
    __table_args__ = (UniqueConstraint('namespace', 'content_sha256', name='uq_namespace_content_hash'), {'schema': 'ai'})

    id = Column(Integer, primary_key=True)
    namespace = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_sha256 = Column(String(64), nullable=False, index=True)
    embedding = Column(Vector(1536)) # Tamanho para text-embedding-3-small
    document_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Schema: crm

class Clients(Base):
    __tablename__ = 'clients'
    __table_args__ = {'schema': 'crm'}

    id = Column(Integer, primary_key=True)
    whatsapp_id = Column(String, nullable=False, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consents = relationship("Consents", back_populates="client")

class Consents(Base):
    __tablename__ = 'consents'
    __table_args__ = {'schema': 'crm'}

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('crm.clients.id'), nullable=False)
    consent_type = Column(String, nullable=False, default='rag_conversation') # ex: 'rag_conversation', 'marketing'
    is_given = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    client = relationship("Clients", back_populates="consents")
