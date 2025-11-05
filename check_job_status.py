import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
from core.models import IngestionQueue, PyIngestionStatus

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def check_job_status():
    async with engine.connect() as conn:
        # Consultar o trabalho recém-criado
        result = await conn.execute(select(IngestionQueue).filter(IngestionQueue.id == 11))
        job = result.first()
        
        if job:
            print(f"Job ID: {job.id}")
            print(f"Status: {job.status}")
            print(f"Source URI: {job.source_uri}")
            print(f"Namespace: {job.namespace}")
            print(f"Created at: {job.created_at}")
            print(f"Updated at: {job.updated_at}")
            
            # Verificar se o status é um enum
            print(f"Tipo do status: {type(job.status)}")
        else:
            print("Job não encontrado")

if __name__ == "__main__":
    asyncio.run(check_job_status())