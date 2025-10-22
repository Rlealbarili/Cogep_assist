import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.models import Base
from dotenv import load_dotenv

load_dotenv() # Ensure .env is loaded first

# Manually construct DATABASE_URL using os.getenv() after load_dotenv()
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

async def init_db():
    """
    Função para inicializar o banco de dados.
    Força a remoção de tipos conflitantes (como ENUMs) e recria o schema.
    """
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=True, # Set to True for debugging
    )
    async with async_engine.begin() as conn:
        print("Limpando schemas e tipos conflitantes (CASCADE)...")
        # A pesquisa [cite: 61, 99] confirmou que CASCADE é necessário para ENUMs
        await conn.execute(text("DROP SCHEMA IF EXISTS crm CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS ai CASCADE"))
        # Limpa explicitamente o tipo ENUM que estava causando o conflito
        await conn.execute(text("DROP TYPE IF EXISTS ingestionstatus CASCADE"))

        print("Recriando schemas...")
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS crm"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai"))
        
        print("Recriando todas as tabelas e tipos (CREATE ALL)...")
        # Agora o create_all irá recriar o ENUM ingestionstatus do zero
        await conn.run_sync(Base.metadata.create_all)
        
    print("Banco de dados inicializado com sucesso (schemas limpos).")
    await async_engine.dispose()

if __name__ == "__main__":
    print("Iniciando processo de inicialização do banco de dados...")
    asyncio.run(init_db())