import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def check_enum_compatibility():
    async with engine.connect() as conn:
        # Verificar valores distintos na coluna status de ingestion_queue
        result = await conn.execute(text("SELECT DISTINCT status FROM ai.ingestion_queue"))
        statuses = result.fetchall()
        print("Status distintos em ingestion_queue:")
        for status in statuses:
            print(f"  - {status[0]}")
        
        # Verificar valores distintos na coluna consent_type de consents
        result = await conn.execute(text("SELECT DISTINCT consent_type FROM crm.consents"))
        consent_types = result.fetchall()
        print("\nTipos de consentimento distintos em consents:")
        for consent_type in consent_types:
            print(f"  - {consent_type[0]}")

if __name__ == "__main__":
    asyncio.run(check_enum_compatibility())