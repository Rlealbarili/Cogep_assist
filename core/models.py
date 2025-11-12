from datetime import datetime
from sqlalchemy import (Column, Integer, String, DateTime, Text, UniqueConstraint, JSON, ForeignKey, Boolean, Float, Numeric)
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql
from enum import Enum

# --- Modelos SQLAlchemy ORM para o Banco de Dados ---

Base = declarative_base()

# Schema definitions
ai_schema = 'ai'
trading_schema = 'trading'

# Definição dos Enums Python
class PyIngestionStatus(Enum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class PyOrderSide(Enum):
    BUY = 'BUY'
    SELL = 'SELL'

class PyOrderStatus(Enum):
    PENDING = 'PENDING'
    FILLED = 'FILLED'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    CANCELLED = 'CANCELLED'
    REJECTED = 'REJECTED'

class PySignalType(Enum):
    TECHNICAL = 'TECHNICAL'
    SENTIMENT = 'SENTIMENT'

# Definição dos Enums PG Nativos
pg_ingestion_status = postgresql.ENUM(PyIngestionStatus, name='ingestionstatus', schema=ai_schema)
pg_order_side = postgresql.ENUM(PyOrderSide, name='orderside', schema=trading_schema)
pg_order_status = postgresql.ENUM(PyOrderStatus, name='orderstatus', schema=trading_schema)
pg_signal_type = postgresql.ENUM(PySignalType, name='signaltype', schema=trading_schema)

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

class MarketSignal(Base):
    """Sinais de mercado (técnicos e sentimento)"""
    __tablename__ = 'market_signals'
    __table_args__ = {'schema': trading_schema}

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, index=True)  # EUR/USD, GBP/USD, etc
    signal_type = Column(pg_signal_type, nullable=False)  # TECHNICAL ou SENTIMENT
    signal_data = Column(JSON, nullable=False)  # RSI, MACD, sentiment_score, etc
    price = Column(Numeric(12, 5))  # Preço no momento do sinal
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class TradingOrder(Base):
    """Ordens de trading executadas"""
    __tablename__ = 'trading_orders'
    __table_args__ = {'schema': trading_schema}

    id = Column(Integer, primary_key=True)
    order_id = Column(String, nullable=False, unique=True, index=True)  # ID da exchange
    symbol = Column(String, nullable=False, index=True)
    side = Column(pg_order_side, nullable=False)  # BUY ou SELL
    size = Column(Numeric(12, 8), nullable=False)  # Tamanho da posição
    price = Column(Numeric(12, 5), nullable=False)  # Preço de execução
    status = Column(pg_order_status, nullable=False, default=PyOrderStatus.PENDING)
    strategy = Column(String)  # Nome da estratégia (RSI_SENTIMENT_V1, etc)
    exchange = Column(String)  # alpaca, oanda, etc
    paper_trading = Column(Boolean, default=True)
    execution_metadata = Column(JSON)  # Dados adicionais da execução
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)

class PerformanceMetric(Base):
    """Métricas de performance da estratégia"""
    __tablename__ = 'performance_metrics'
    __table_args__ = {'schema': trading_schema}

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    strategy = Column(String, nullable=False)
    metric_date = Column(DateTime, nullable=False, index=True)

    # Métricas de estratégia
    sharpe_ratio = Column(Numeric(10, 4))
    max_drawdown = Column(Numeric(10, 4))
    profit_factor = Column(Numeric(10, 4))
    win_rate = Column(Numeric(5, 2))

    # Métricas operacionais
    avg_latency_ms = Column(Numeric(10, 2))
    avg_slippage = Column(Numeric(10, 5))

    total_trades = Column(Integer)
    profitable_trades = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
