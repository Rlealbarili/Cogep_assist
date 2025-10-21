import asyncio
from sqlalchemy import text
from core.database import async_engine
from core.schemas import Base

async def init_db():
    """
    Função para inicializar o banco de dados.
    Cria o schema 'ai' e todas as tabelas definidas nos modelos SQLAlchemy.
    """
    async with async_engine.begin() as conn:
        print("Verificando e criando schema 'ai' se necessário...")
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai"))
        
        print("Recriando todas as tabelas...")
        # Em um ambiente de desenvolvimento, dropar as tabelas primeiro é útil
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    print("Banco de dados inicializado com sucesso.")

if __name__ == "__main__":
    print("Iniciando processo de inicialização do banco de dados...")
    # Lembre-se de que seu arquivo .env deve estar configurado corretamente.
    asyncio.run(init_db())
