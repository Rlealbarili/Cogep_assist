from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import pool # Importar pool
from typing import AsyncGenerator
from .config import DATABASE_URL

# Engine de conexão assíncrona
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Ativado para debugging - mostrar comandos SQL no console
    poolclass=pool.NullPool # Adicionar NullPool
)

# Fábrica de sessões assíncronas
AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependência FastAPI para obter uma sessão de banco de dados.
    A sessão é criada diretamente e fechada no finally.
    O gerenciamento de transação (commit/rollback) é responsabilidade do endpoint.
    """
    session = AsyncSessionFactory()
    try:
        yield session
    finally:
        await session.close()