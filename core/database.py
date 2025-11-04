from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import pool
from typing import AsyncGenerator
from .config import DATABASE_URL

# Engine de conexão assíncrona
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    poolclass=pool.NullPool
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
    Dependência FastAPI para obter uma sessão de banco de dados
    com gerenciamento de transação (commit/rollback) automático.
    Baseado na "TERCEIRA PESQUISA" [cite: 753-764].
    """
    async with AsyncSessionFactory() as session:
        try:
            # Entrega a sessão para o endpoint usar
            yield session
            # Se o endpoint retornou sem exceção, commita a transação.
            await session.commit()
        except Exception:
            # Se deu erro no endpoint, reverte a transação.
            await session.rollback()
            raise
        # O 'async with' garante que session.close() seja chamado.
