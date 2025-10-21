from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import DATABASE_URL

# Engine de conexão assíncrona
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Mude para True para ver os comandos SQL gerados
)

# Fábrica de sessões assíncronas
AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    """
    Dependência FastAPI para obter uma sessão de banco de dados.
    Garante que a sessão seja sempre fechada após a requisição.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()