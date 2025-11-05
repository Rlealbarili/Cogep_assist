import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from core.models import PyIngestionStatus, PyConsentType, PyTicketStatus

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def check_migration():
    async with engine.connect() as conn:
        # Verificar se os tipos ENUM foram criados
        result = await conn.execute(text("SELECT enumlabel FROM pg_enum WHERE enumlabel = 'PENDING' AND enumtypid IN (SELECT oid FROM pg_type WHERE typname = 'ingestionstatus')"))
        enum_values = result.fetchall()
        print(f"Valores do enum 'ingestionstatus' encontrados: {len(enum_values)}")
        
        # Verificar se a tabela tickets foi criada
        result = await conn.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'crm' AND table_name = 'tickets'"))
        tickets_columns = result.fetchall()
        print("Colunas da tabela 'crm.tickets':")
        for col in tickets_columns:
            print(f"  - {col[0]}: {col[1]}, nullable: {col[2]}")
        
        # Verificar o tipo da coluna status em ingestion_queue
        result = await conn.execute(text("SELECT data_type, udt_name FROM information_schema.columns WHERE table_schema = 'ai' AND table_name = 'ingestion_queue' AND column_name = 'status'"))
        ingestion_status_info = result.fetchone()
        print(f"Tipo da coluna status em ingestion_queue: {ingestion_status_info[1] if ingestion_status_info else 'N/A'}")
        
        # Verificar o tipo da coluna consent_type em consents
        result = await conn.execute(text("SELECT data_type, udt_name FROM information_schema.columns WHERE table_schema = 'crm' AND table_name = 'consents' AND column_name = 'consent_type'"))
        consent_type_info = result.fetchone()
        print(f"Tipo da coluna consent_type em consents: {consent_type_info[1] if consent_type_info else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(check_migration())