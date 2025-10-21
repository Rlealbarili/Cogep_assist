import enum
from sqlalchemy import (Column, Integer, String, DateTime, func, Enum as SAEnum)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class JobStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class IngestionJob(Base):
    __tablename__ = 'ingestion_queue'
    __table_args__ = {'schema': 'ai'}

    id = Column(Integer, primary_key=True, index=True)
    source_uri = Column(String, nullable=False)
    namespace = Column(String, nullable=False, default='default')
    status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<IngestionJob(id={self.id}, status='{self.status.value}')>"
